"""
Módulo para estimativa iterativa de pesos para aeronaves.

Este módulo implementa um método iterativo para estimativa de pesos para aeronaves,
focando na convergência do MTOW (Maximum Takeoff Weight) baseado em frações de peso.
Utiliza equações empíricas e cálculos de desempenho para determinar a relação entre
peso vazio, peso de combustível e peso máximo de decolagem.
"""

import math
from typing import Dict, Optional, Union, Tuple
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def calculate_empty_weight_fraction(W0_N: float) -> float:
    """
    Calcula a fração de peso vazio usando a fórmula empírica de Raymer para jatos executivos.
    
    Args:
        W0_N: Peso máximo de decolagem em Newtons
    
    Returns:
        Fração de peso vazio (We/W0)
    """
    # Coeficientes de Raymer para jatos executivos
    A = 1.118
    C = -0.070
    
    return A * W0_N**(C)


def calculate_total_fuel_fraction(W0_kg: float, R_km: float, V_mps: float, 
                                 h_m: float, L_D_cruise: float = 16.0, 
                                 TSFC_kgNs: float = 2.0e-5) -> float:
    """
    Calcula a fração de combustível baseada na missão completa da aeronave.
    
    Args:
        W0_kg: Peso máximo de decolagem em kg
        R_km: Alcance da missão em km
        V_mps: Velocidade de cruzeiro em m/s
        h_m: Altitude de cruzeiro em metros
        L_D_cruise: Razão de planeio (L/D) durante o cruzeiro
        TSFC_kgNs: Consumo específico de combustível em kg/(N·s)
    
    Returns:
        Fração de combustível total (Wf/W0)
    """
    g = 9.81  # Aceleração da gravidade em m/s²
    R_m = R_km * 1000  # Conversão de km para m
    
    # Cálculo da fração para fase de cruzeiro utilizando a equação de Breguet
    W3_W2 = math.exp(-(R_m * g * TSFC_kgNs) / (V_mps * L_D_cruise))
    
    # Fatores para outras fases da missão
    W_taxi = 0.97       # Redução de peso devido ao taxi
    W_takeoff = 0.985   # Redução de peso devido à decolagem
    W_climb = 0.985     # Redução de peso devido à subida
    W_descent = 0.995   # Redução de peso devido à descida e pouso
    
    # Fator combinado para fases que não são cruzeiro
    W_other_phases_ratio = W_taxi * W_takeoff * W_climb * W_descent
    
    # Fator para reserva de combustível (típico 5-10%)
    W_reserve_ratio = 0.98  # 2% de reserva neste exemplo
    
    # Fração total de combustível (1 - fração de peso final)
    Wf_W0 = 1.0 - (W3_W2 * W_other_phases_ratio * W_reserve_ratio)
    
    return Wf_W0


def estimate_weights_iterative(W_payload_kg: float, R_km: float, V_mps: float, 
                              h_m: float, initial_W0_guess_kg: float,
                              tolerance: float = 1.0, 
                              max_iterations: int = 50,
                              verbose: bool = True) -> Optional[Dict[str, float]]:
    """
    Realiza a estimativa iterativa de pesos para uma aeronave.
    
    Utiliza um processo iterativo para encontrar o MTOW que equilibra a equação
    de peso: W0 = W_payload + W_empty + W_fuel, onde W_empty e W_fuel são
    expressos como frações de W0.
    
    Args:
        W_payload_kg: Peso da carga paga em kg
        R_km: Alcance da missão em km
        V_mps: Velocidade de cruzeiro em m/s
        h_m: Altitude de cruzeiro em metros
        initial_W0_guess_kg: Estimativa inicial do MTOW em kg
        tolerance: Tolerância para convergência em kg
        max_iterations: Número máximo de iterações permitidas
        verbose: Se True, imprime detalhes de cada iteração
    
    Returns:
        Dicionário com MTOW, OEW e peso de combustível em kg, ou None se falhar
    """
    W0_kg = initial_W0_guess_kg
    g = 9.81  # Aceleração da gravidade em m/s²
    W_payload_N = W_payload_kg * g
    
    if verbose:
        logger.info("Iteração | W0 Estimado (kg) | W_empty/W0 | W_fuel/W0 | W0 Calculado (kg) | Residual (kg)")
        logger.info("-" * 80)

    for i in range(max_iterations):
        # 1. Calcular fração de peso vazio usando fórmula empírica
        We_W0_ratio = calculate_empty_weight_fraction(W0_kg * g)

        # 2. Calcular fração de combustível baseada na missão
        Wf_W0_ratio = calculate_total_fuel_fraction(W0_kg, R_km, V_mps, h_m)

        # 3. Calcular novo W0 usando a equação de balanceamento de pesos
        # W0 = W_payload / (1 - We/W0 - Wf/W0)
        denominator = 1.0 - We_W0_ratio - Wf_W0_ratio
        
        if denominator <= 0:
            logger.error("Erro: Denominador não positivo (%.5f). Verifique as frações de peso.", denominator)
            return None
            
        W0_calc_N = W_payload_N / denominator
        W0_calc_kg = W0_calc_N / g
        
        residual_kg = W0_kg - W0_calc_kg
        
        if verbose:
            logger.info(f"{i:^8} | {W0_kg:^16.2f} | {We_W0_ratio:^10.5f} | {Wf_W0_ratio:^9.5f} | {W0_calc_kg:^17.2f} | {residual_kg:^13.2f}")

        # Verificar convergência
        if abs(residual_kg) < tolerance:
            if verbose:
                logger.info("\nConvergência alcançada após %d iterações.", i+1)
            
            W_empty_kg = W0_calc_kg * We_W0_ratio
            W_fuel_kg = W0_calc_kg * Wf_W0_ratio
            
            return {
                "MTOW_kg": W0_calc_kg, 
                "OEW_kg": W_empty_kg, 
                "W_fuel_kg": W_fuel_kg,
                "iterations": i+1
            }
            
        # Atualizar estimativa para próxima iteração
        W0_kg = W0_calc_kg  # Método de substituição direta

    # Se atingir o máximo de iterações sem convergir
    if verbose:
        logger.warning("\nAtenção: Máximo de %d iterações atingido sem convergência total.", max_iterations)
        logger.warning("Residual final: %.2f kg", residual_kg)
    
    W_empty_kg = W0_calc_kg * We_W0_ratio
    W_fuel_kg = W0_calc_kg * Wf_W0_ratio
    
    return {
        "MTOW_kg": W0_calc_kg, 
        "OEW_kg": W_empty_kg, 
        "W_fuel_kg": W_fuel_kg,
        "iterations": max_iterations,
        "converged": False
    }


def run_example() -> None:
    """Executa um exemplo de uso do estimador de pesos."""
    # Parâmetros para um jato executivo similar ao Gulfstream G550
    W_payload_kg = 2812.0      # Carga paga típica
    R_km = 7200.0              # Alcance de projeto
    V_mps = 250.56             # ~902 km/h em velocidade de cruzeiro
    h_m = 12497                # ~FL410 (para densidade 0.301 kg/m³)
    initial_W0_guess_kg = 40000.0  # Estimativa inicial do MTOW
    
    logger.info("=== EXEMPLO: ESTIMATIVA DE PESOS PARA JATO EXECUTIVO ===")
    logger.info("Parâmetros de entrada:")
    logger.info("  Carga paga:          %.2f kg", W_payload_kg)
    logger.info("  Alcance:             %.2f km", R_km)
    logger.info("  Velocidade cruzeiro: %.2f m/s (%.2f km/h)", V_mps, V_mps*3.6)
    logger.info("  Altitude cruzeiro:   %.2f m (~FL%.0f)", h_m, h_m/30.48)
    logger.info("  Estimativa inicial:  %.2f kg", initial_W0_guess_kg)
    logger.info("")
    
    # Executar estimativa
    results = estimate_weights_iterative(
        W_payload_kg, R_km, V_mps, h_m, initial_W0_guess_kg
    )
    
    if results:
        logger.info("\nResultados Convergidos:")
        logger.info("  MTOW: %9.2f kg", results["MTOW_kg"])
        logger.info("  OEW:  %9.2f kg", results["OEW_kg"])
        logger.info("  Fuel: %9.2f kg", results["W_fuel_kg"])
        logger.info("  Payload/MTOW: %.4f", W_payload_kg / results["MTOW_kg"])
        logger.info("  OEW/MTOW:    %.4f", results["OEW_kg"] / results["MTOW_kg"])
        logger.info("  Fuel/MTOW:   %.4f", results["W_fuel_kg"] / results["MTOW_kg"])


if __name__ == "__main__":
    run_example()