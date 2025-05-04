"""
Módulo para geração de diagramas Payload-Range para aeronaves.

Este módulo implementa funções para calcular os pontos característicos do
diagrama Payload-Range e gerar uma visualização gráfica das capacidades
operacionais da aeronave.
"""

import math
from typing import Dict, List, Tuple, Optional, Union
import logging
import matplotlib.pyplot as plt
from pathlib import Path
import os

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def calculate_L_D(W_kg: float, rho_kgm3: float, S_m2: float, 
                 V_mps: float, C_D0: float, k_2: float) -> float:
    """
    Calcula a razão sustentação/arrasto (L/D) para condições específicas de voo.
    
    Args:
        W_kg: Peso da aeronave em kg
        rho_kgm3: Densidade do ar em kg/m³
        S_m2: Área da asa em m²
        V_mps: Velocidade verdadeira em m/s
        C_D0: Coeficiente de arrasto parasita
        k_2: Fator de arrasto induzido (K)
    
    Returns:
        Razão sustentação/arrasto (L/D)
    """
    # Conversão de peso para força em Newtons
    W_N = W_kg * 9.81
    
    # Cálculo do coeficiente de sustentação necessário para o voo nivelado
    CL = (2 * W_N) / (rho_kgm3 * S_m2 * V_mps**2)
    
    # Evitar divisão por zero
    if CL == 0:
        return 0
    
    # Cálculo da eficiência aerodinâmica (L/D)
    # Usando a equação: L/D = CL/(CD0 + k*CL²)
    L_D = 1 / ((C_D0 / CL) + k_2 * CL)
    
    return L_D


def calculate_range_km(W_start_kg: float, W_end_kg: float, 
                      L_D_avg: float, V_mps: float, 
                      TSFC_kgNs: float) -> float:
    """
    Calcula o alcance usando a equação de Breguet para voo de cruzeiro.
    
    Args:
        W_start_kg: Peso inicial da aeronave em kg
        W_end_kg: Peso final da aeronave em kg
        L_D_avg: Razão sustentação/arrasto média durante o cruzeiro
        V_mps: Velocidade de cruzeiro em m/s
        TSFC_kgNs: Consumo específico de combustível em kg/(N·s)
    
    Returns:
        Alcance em km
    """
    # Verificações de segurança
    if W_end_kg <= 0 or W_start_kg <= W_end_kg:
        return 0
    
    g_ms2 = 9.81  # Aceleração da gravidade em m/s²
    
    # Equação de Breguet para alcance
    R_m = (V_mps * L_D_avg) / (g_ms2 * TSFC_kgNs) * math.log(W_start_kg / W_end_kg)
    
    # Conversão de metros para quilômetros
    return R_m / 1000


def calculate_payload_range_points(
        OEW_kg: float, 
        W_payload_max_kg: float, 
        W_fuel_max_kg: float, 
        MTOW_kg: float, 
        rho_kgm3: float, 
        S_m2: float, 
        V_mps: float, 
        C_D0: float, 
        k_2: float, 
        TSFC_kgNs: float
    ) -> Dict[str, Dict[str, float]]:
    """
    Calcula os pontos característicos do diagrama Payload-Range.
    
    Args:
        OEW_kg: Peso operacional vazio em kg
        W_payload_max_kg: Capacidade máxima de carga paga em kg
        W_fuel_max_kg: Capacidade máxima de combustível em kg
        MTOW_kg: Peso máximo de decolagem em kg
        rho_kgm3: Densidade do ar em kg/m³
        S_m2: Área da asa em m²
        V_mps: Velocidade de cruzeiro em m/s
        C_D0: Coeficiente de arrasto parasita
        k_2: Fator de arrasto induzido (K)
        TSFC_kgNs: Consumo específico de combustível em kg/(N·s)
    
    Returns:
        Dicionário com pontos (A, B, C, D) do diagrama e seus valores.
        Cada ponto contém alcance em km e carga paga em kg.
    """
    # Ponto A/B (carga paga máxima, combustível limitado pelo MTOW)
    # Point A corresponde a alcance zero
    # Point B corresponde a alcance com carga paga máxima
    
    # Quantidade de combustível para o ponto B
    W_fuel_design_kg = MTOW_kg - OEW_kg - W_payload_max_kg
    W_fuel_design_kg = min(W_fuel_design_kg, W_fuel_max_kg)
    
    # Pesos inicial e final para o ponto B
    W_start_AB = OEW_kg + W_payload_max_kg + W_fuel_design_kg
    W_end_AB = OEW_kg + W_payload_max_kg
    
    # Peso médio para cálculo de L/D
    W_avg_AB = (W_start_AB + W_end_AB) / 2
    
    # Eficiência aerodinâmica para o ponto B
    L_D_avg_AB = calculate_L_D(W_avg_AB, rho_kgm3, S_m2, V_mps, C_D0, k_2)
    
    # Alcance para o ponto B
    Range_AB_km = calculate_range_km(W_start_AB, W_end_AB, L_D_avg_AB, V_mps, TSFC_kgNs)
    
    # Carga paga para os pontos A e B
    Payload_AB_kg = W_payload_max_kg
    
    # Ponto C (tanque cheio, carga paga reduzida para respeitar MTOW)
    # Carga paga reduzida para permitir tanque cheio sem exceder MTOW
    W_start_C = MTOW_kg
    Payload_C_kg = max(MTOW_kg - OEW_kg - W_fuel_max_kg, 0)
    W_end_C = OEW_kg + Payload_C_kg
    
    # Peso médio para cálculo de L/D
    W_avg_C = (W_start_C + W_end_C) / 2
    
    # Eficiência aerodinâmica para o ponto C
    L_D_avg_C = calculate_L_D(W_avg_C, rho_kgm3, S_m2, V_mps, C_D0, k_2)
    
    # Alcance para o ponto C
    Range_C_km = calculate_range_km(W_start_C, W_end_C, L_D_avg_C, V_mps, TSFC_kgNs)
    
    # Ponto D (tanque cheio, zero carga paga, alcance máximo)
    Payload_D_kg = 0
    
    # Peso inicial (limitado por MTOW se necessário)
    W_start_D = min(OEW_kg + W_fuel_max_kg, MTOW_kg)
    W_end_D = OEW_kg
    
    # Peso médio para cálculo de L/D
    W_avg_D = (W_start_D + W_end_D) / 2
    
    # Eficiência aerodinâmica para o ponto D
    L_D_avg_D = calculate_L_D(W_avg_D, rho_kgm3, S_m2, V_mps, C_D0, k_2)
    
    # Alcance para o ponto D
    Range_D_km = calculate_range_km(W_start_D, W_end_D, L_D_avg_D, V_mps, TSFC_kgNs)
    
    # Compilar resultados
    return {
        "A": {"range_km": 0, "payload_kg": Payload_AB_kg},
        "B": {"range_km": Range_AB_km, "payload_kg": Payload_AB_kg},
        "C": {"range_km": Range_C_km, "payload_kg": Payload_C_kg},
        "D": {"range_km": Range_D_km, "payload_kg": Payload_D_kg}
    }


def plot_payload_range_diagram(
        points: Dict[str, Dict[str, float]], 
        aircraft_name: str = "Aircraft",
        output_path: Optional[str] = None,
        show_plot: bool = False
    ) -> str:
    """
    Gera um diagrama Payload-Range a partir dos pontos calculados.
    
    Args:
        points: Dicionário com pontos (A, B, C, D) do diagrama
        aircraft_name: Nome da aeronave para o título do gráfico
        output_path: Caminho para salvar o gráfico (opcional)
        show_plot: Se True, exibe o gráfico
    
    Returns:
        Caminho onde o arquivo foi salvo ou mensagem de erro
    """
    # Extrair valores para plotagem
    ranges = [
        points["A"]["range_km"], 
        points["B"]["range_km"], 
        points["C"]["range_km"], 
        points["D"]["range_km"]
    ]
    
    payloads = [
        points["A"]["payload_kg"], 
        points["B"]["payload_kg"], 
        points["C"]["payload_kg"], 
        points["D"]["payload_kg"]
    ]
    
    # Criar figura
    plt.figure(figsize=(10, 6))
    
    # Plotar curva
    plt.plot(ranges, payloads, marker='o', linestyle='-', linewidth=2)
    
    # Adicionar anotações
    plt.annotate(
        f"A\n(0 km, {points['A']['payload_kg']:.0f} kg)", 
        (points["A"]["range_km"], points["A"]["payload_kg"]), 
        textcoords="offset points", 
        xytext=(10, 5), 
        ha='left'
    )
    
    plt.annotate(
        f"B\n({points['B']['range_km']:.0f} km, {points['B']['payload_kg']:.0f} kg)", 
        (points["B"]["range_km"], points["B"]["payload_kg"]), 
        textcoords="offset points", 
        xytext=(0, 10), 
        ha='center'
    )
    
    plt.annotate(
        f"C\n({points['C']['range_km']:.0f} km, {points['C']['payload_kg']:.0f} kg)", 
        (points["C"]["range_km"], points["C"]["payload_kg"]), 
        textcoords="offset points", 
        xytext=(0, -15), 
        ha='center'
    )
    
    plt.annotate(
        f"D\n({points['D']['range_km']:.0f} km, {points['D']['payload_kg']:.0f} kg)", 
        (points["D"]["range_km"], points["D"]["payload_kg"]), 
        textcoords="offset points", 
        xytext=(-10, -15), 
        ha='right'
    )
    
    # Configurar detalhes do gráfico
    plt.xlabel("Alcance (km)")
    plt.ylabel("Carga Paga (kg)")
    plt.title(f"Diagrama Carga Paga vs. Alcance - {aircraft_name}")
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.ylim(bottom=0)
    plt.xlim(left=0)
    
    # Adicionar descrição dos pontos
    description = (
        "A: Zero alcance, carga paga máxima\n"
        "B: Alcance com carga paga máxima\n"
        "C: Alcance com tanques cheios e carga paga reduzida\n"
        "D: Alcance máximo, zero carga paga"
    )
    plt.figtext(0.15, 0.15, description, fontsize=9, 
                bbox=dict(facecolor='white', alpha=0.8))
    
    # Salvar o gráfico se o caminho for fornecido
    if output_path:
        try:
            # Criar diretório se não existir
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Gráfico salvo em: {output_path}")
            
            if show_plot:
                plt.show()
                
            return output_path
            
        except Exception as e:
            error_msg = f"Erro ao salvar gráfico: {str(e)}"
            logger.error(error_msg)
            return error_msg
    else:
        # Se nenhum caminho for fornecido, apenas mostrar se solicitado
        if show_plot:
            plt.show()
        return "Gráfico não foi salvo (nenhum caminho de saída fornecido)"


def run_example() -> None:
    """Executa um exemplo de geração de diagrama Payload-Range para um jato executivo."""
    # Parâmetros para um jato executivo similar ao Gulfstream G550
    OEW_kg = 22069.24            # Peso operacional vazio
    W_payload_max_kg = 2812.00   # Capacidade máxima de carga paga
    W_fuel_max_kg = 18733.00     # Capacidade máxima de combustível
    MTOW_kg = 41557.66           # Peso máximo de decolagem
    
    # Parâmetros de desempenho
    rho_kgm3 = 0.301             # Densidade do ar em altitude de cruzeiro
    S_m2 = 113.7                 # Área da asa
    V_mps = 250.56               # Velocidade de cruzeiro (~902 km/h)
    C_D0 = 0.018                 # Coeficiente de arrasto parasita
    k_2 = 0.049                  # Fator de arrasto induzido
    TSFC_kgNs = 2.0028e-5        # Consumo específico de combustível
    
    logger.info("=== CÁLCULO DE DIAGRAMA PAYLOAD-RANGE ===")
    logger.info("Parâmetros da aeronave:")
    logger.info("  OEW:              %.2f kg", OEW_kg)
    logger.info("  Payload máximo:   %.2f kg", W_payload_max_kg)
    logger.info("  Combustível máx:  %.2f kg", W_fuel_max_kg)
    logger.info("  MTOW:             %.2f kg", MTOW_kg)
    logger.info("")
    
    # Calcular pontos do diagrama
    points = calculate_payload_range_points(
        OEW_kg, W_payload_max_kg, W_fuel_max_kg, MTOW_kg, 
        rho_kgm3, S_m2, V_mps, C_D0, k_2, TSFC_kgNs
    )
    
    # Mostrar resultados numéricos
    logger.info("Pontos do diagrama Payload-Range:")
    logger.info("  A: (%.0f km, %.0f kg) - Zero alcance, carga paga máxima", 
               points["A"]["range_km"], points["A"]["payload_kg"])
    logger.info("  B: (%.0f km, %.0f kg) - Alcance com carga paga máxima", 
               points["B"]["range_km"], points["B"]["payload_kg"])
    logger.info("  C: (%.0f km, %.0f kg) - Alcance com tanques cheios", 
               points["C"]["range_km"], points["C"]["payload_kg"])
    logger.info("  D: (%.0f km, %.0f kg) - Alcance máximo, zero carga paga", 
               points["D"]["range_km"], points["D"]["payload_kg"])
    
    # Gerar e salvar o diagrama
    # Usar caminho relativo para maior portabilidade
    output_path = "payload_range_diagram_G550.png"
    plot_payload_range_diagram(
        points, 
        aircraft_name="Gulfstream G550 (Estimado)",
        output_path=output_path,
        show_plot=False
    )
    
    logger.info(f"\nDiagrama salvo como: {output_path}")


if __name__ == "__main__":
    run_example()