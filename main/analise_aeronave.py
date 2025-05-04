#!/usr/bin/env python3
"""
Programa de Análise de Desempenho de Aeronaves

Este programa combina módulos de estimativa de pesos, cálculo de distâncias de pista
e geração de diagrama payload-range para realizar uma análise completa de desempenho
de aeronaves de transporte.

Autor: [Seu Nome]
Versão: 1.0
Data: Maio 2025
"""

import argparse
import logging
import json
import os
from typing import Dict, Optional, Union, List, Tuple

# Importar os módulos implementados
try:
    from estimativa_de_peso import estimate_weights_iterative, calculate_empty_weight_fraction, calculate_total_fuel_fraction
    from calculo_distancia_pista import estimate_takeoff_distance, estimate_landing_distance
    from payload_range import calculate_payload_range_points, plot_payload_range_diagram
    modules_imported = True
except ImportError:
    # Fallback para importação local se os arquivos estiverem no mesmo diretório
    modules_imported = False
    print("Aviso: Módulos não foram importados com sucesso. Será necessário copiar as funções desses módulos.")

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_aircraft_config(config_file: str) -> Dict:
    """
    Carrega a configuração da aeronave a partir de um arquivo JSON.
    
    Args:
        config_file: Caminho para o arquivo de configuração JSON
        
    Returns:
        Dicionário com parâmetros da aeronave
    """
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info(f"Configuração carregada de: {config_file}")
        return config
    except Exception as e:
        logger.error(f"Erro ao carregar configuração: {str(e)}")
        raise


def save_results(results: Dict, output_file: str) -> None:
    """
    Salva os resultados da análise em um arquivo JSON.
    
    Args:
        results: Dicionário com resultados da análise
        output_file: Caminho para o arquivo de saída
    """
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=4)
        logger.info(f"Resultados salvos em: {output_file}")
    except Exception as e:
        logger.error(f"Erro ao salvar resultados: {str(e)}")


def run_full_analysis(config: Dict, output_dir: str) -> Dict:
    """
    Executa análise completa da aeronave.
    
    Args:
        config: Dicionário com configuração da aeronave
        output_dir: Diretório para salvar resultados e gráficos
        
    Returns:
        Dicionário com resultados da análise
    """
    # Criar diretório de saída se não existir
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Diretório de saída criado: {output_dir}")
    
    results = {}
    
    # 1. Análise de pesos
    logger.info("Iniciando análise de pesos...")
    weight_config = config.get("weight_params", {})
    
    weight_results = estimate_weights_iterative(
        W_payload_kg=weight_config.get("W_payload_kg", 2812.0),
        R_km=weight_config.get("R_km", 7200.0),
        V_mps=weight_config.get("V_mps", 250.56),
        h_m=weight_config.get("h_m", 12497),
        initial_W0_guess_kg=weight_config.get("initial_W0_guess_kg", 40000.0),
        verbose=True
    )
    
    if weight_results:
        results["weight_analysis"] = weight_results
        logger.info("Análise de pesos concluída.")
    else:
        logger.error("Falha na análise de pesos.")
        return {}
    
    # 2. Análise de distâncias de pista
    logger.info("Iniciando análise de distâncias de pista...")
    runway_config = config.get("runway_params", {})
    
    # Análise de decolagem
    takeoff_results = estimate_takeoff_distance(
        W_kg=weight_results["MTOW_kg"],
        S_m2=runway_config.get("S_m2", 113.7),
        T_N_static=runway_config.get("T_N_static", 136880),
        CLmax_TO=runway_config.get("CLmax_TO", 2.1),
        CD0_takeoff=runway_config.get("CD0_takeoff", 0.048),
        K=runway_config.get("K", 0.049)
    )
    
    results["takeoff_analysis"] = takeoff_results
    
    # Análise de pouso
    # Tipicamente 65-70% do MTOW para pouso
    W_land_kg = runway_config.get("W_land_kg", weight_results["MTOW_kg"] * 0.65)
    
    landing_results = estimate_landing_distance(
        W_land_kg=W_land_kg,
        S_m2=runway_config.get("S_m2", 113.7),
        CLmax_land=runway_config.get("CLmax_land", 2.6),
        CD0_landing=runway_config.get("CD0_landing", 0.063),
        K=runway_config.get("K", 0.049)
    )
    
    results["landing_analysis"] = landing_results
    logger.info("Análise de distâncias de pista concluída.")
    
    # 3. Análise de diagrama payload-range
    logger.info("Gerando diagrama payload-range...")
    pr_config = config.get("payload_range_params", {})
    
    # Usar resultados da análise de pesos se disponíveis
    if "weight_analysis" in results:
        OEW_kg = results["weight_analysis"]["OEW_kg"]
        MTOW_kg = results["weight_analysis"]["MTOW_kg"]
    else:
        OEW_kg = pr_config.get("OEW_kg", 22000.0)
        MTOW_kg = pr_config.get("MTOW_kg", 41500.0)
    
    pr_points = calculate_payload_range_points(
        OEW_kg=OEW_kg,
        W_payload_max_kg=pr_config.get("W_payload_max_kg", 2812.0),
        W_fuel_max_kg=pr_config.get("W_fuel_max_kg", 18733.0),
        MTOW_kg=MTOW_kg,
        rho_kgm3=pr_config.get("rho_kgm3", 0.301),
        S_m2=pr_config.get("S_m2", 113.7),
        V_mps=pr_config.get("V_mps", 250.56),
        C_D0=pr_config.get("C_D0", 0.018),
        k_2=pr_config.get("k_2", 0.049),
        TSFC_kgNs=pr_config.get("TSFC_kgNs", 2.0028e-5)
    )
    
    results["payload_range_points"] = pr_points
    
    # Gerar diagrama
    aircraft_name = config.get("aircraft_name", "Jato Executivo")
    diagram_path = os.path.join(output_dir, f"payload_range_{aircraft_name.replace(' ', '_')}.png")
    
    plot_result = plot_payload_range_diagram(
        points=pr_points,
        aircraft_name=aircraft_name,
        output_path=diagram_path
    )
    
    results["payload_range_diagram_path"] = diagram_path
    logger.info("Diagrama payload-range gerado.")
    
    # 4. Resumo dos resultados principais
    results["summary"] = {
        "aircraft_name": aircraft_name,
        "MTOW_kg": weight_results["MTOW_kg"],
        "OEW_kg": weight_results["OEW_kg"],
        "fuel_capacity_kg": weight_results["W_fuel_kg"],
        "max_payload_kg": pr_config.get("W_payload_max_kg", 2812.0),
        "range_with_max_payload_km": pr_points["B"]["range_km"],
        "max_range_km": pr_points["D"]["range_km"],
        "takeoff_distance_m": takeoff_results["S_total_takeoff_m"],
        "landing_distance_m": landing_results["S_total_landing_m"]
    }
    
    logger.info("Análise completa concluída com sucesso.")
    return results


def create_default_config() -> Dict:
    """
    Cria um arquivo de configuração padrão para exemplo.
    
    Returns:
        Dicionário com configuração padrão
    """
    config = {
        "aircraft_name": "Gulfstream G550",
        "weight_params": {
            "W_payload_kg": 2812.0,
            "R_km": 7200.0,
            "V_mps": 250.56,
            "h_m": 12497,
            "initial_W0_guess_kg": 40000.0
        },
        "runway_params": {
            "S_m2": 113.7,
            "T_N_static": 136880,
            "CLmax_TO": 2.1,
            "CD0_takeoff": 0.048,
            "K": 0.049,
            "CLmax_land": 2.6,
            "CD0_landing": 0.063
        },
        "payload_range_params": {
            "W_payload_max_kg": 2812.0,
            "W_fuel_max_kg": 18733.0,
            "rho_kgm3": 0.301,
            "S_m2": 113.7,
            "V_mps": 250.56,
            "C_D0": 0.018,
            "k_2": 0.049,
            "TSFC_kgNs": 2.0028e-5
        }
    }
    return config


def main():
    """Função principal do programa."""
    # Configurar argumentos de linha de comando
    parser = argparse.ArgumentParser(description="Programa de Análise de Desempenho de Aeronaves")
    parser.add_argument("-c", "--config", help="Arquivo de configuração da aeronave (JSON)")
    parser.add_argument("-o", "--output-dir", default="./output", help="Diretório para salvar resultados")
    parser.add_argument("--create-config", action="store_true", help="Criar arquivo de configuração padrão")
    args = parser.parse_args()
    
    # Criar configuração padrão se solicitado
    if args.create_config:
        config = create_default_config()
        config_path = "aircraft_config_default.json"
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            logger.info(f"Arquivo de configuração padrão criado: {config_path}")
            return
        except Exception as e:
            logger.error(f"Erro ao criar arquivo de configuração: {str(e)}")
            return
    
    # Carregar configuração
    if args.config:
        config = load_aircraft_config(args.config)
    else:
        logger.info("Nenhum arquivo de configuração fornecido. Usando valores padrão.")
        config = create_default_config()
    
    # Executar análise
    results = run_full_analysis(config, args.output_dir)
    
    # Salvar resultados
    if results:
        output_file = os.path.join(args.output_dir, "analysis_results.json")
        save_results(results, output_file)
        
        # Mostrar resumo dos resultados
        print("\n=== RESUMO DOS RESULTADOS DA ANÁLISE ===")
        summary = results.get("summary", {})
        for key, value in summary.items():
            if isinstance(value, float):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value}")
    else:
        logger.error("A análise falhou. Verifique os erros acima.")


if __name__ == "__main__":
    main()