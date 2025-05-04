"""
Módulo para estimativa de distâncias de pista para aeronaves.

Implementa métodos para calcular distâncias de decolagem e pouso usando
abordagens semi-empíricas baseadas em princípios de dinâmica de voo.
"""

import math
from typing import Dict, Optional, Union, Tuple
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def estimate_takeoff_distance(
        W_kg: float, 
        S_m2: float, 
        T_N_static: float, 
        CLmax_TO: float, 
        rho0_kgm3: float = 1.225, 
        g_ms2: float = 9.81, 
        mu_roll: float = 0.03, 
        CL_ground: float = 0.1, 
        CD0_takeoff: float = 0.048, 
        K: float = 0.049, 
        Vlof_factor: float = 1.15, 
        V_avg_factor: float = 0.7, 
        t_rot_s: float = 2.0, 
        h_obs_m: float = 10.7
    ) -> Dict[str, float]:
    """
    Estima distância de decolagem usando o método de aceleração média.
    
    O método calcula corrida no solo + rotação + distância aérea até superar 
    um obstáculo de altura h_obs_m.
    
    Args:
        W_kg: Peso de decolagem em kg
        S_m2: Área da asa em m²
        T_N_static: Empuxo estático total dos motores em Newtons
        CLmax_TO: Coeficiente de sustentação máximo na configuração de decolagem
        rho0_kgm3: Densidade do ar ao nível do mar (padrão = 1.225 kg/m³)
        g_ms2: Aceleração da gravidade (padrão = 9.81 m/s²)
        mu_roll: Coeficiente de atrito de rolamento (padrão = 0.03)
        CL_ground: Coeficiente de sustentação médio durante corrida no solo (padrão = 0.1)
        CD0_takeoff: Coeficiente de arrasto parasita na configuração de decolagem (padrão = 0.048)
        K: Fator de arrasto induzido da polar de arrasto (padrão = 0.049)
        Vlof_factor: Fator para velocidade de rotação como múltiplo de Vs_TO (padrão = 1.15)
        V_avg_factor: Fator para velocidade média durante aceleração (padrão = 0.7)
        t_rot_s: Tempo de rotação em segundos (padrão = 2.0)
        h_obs_m: Altura do obstáculo a ser superado (padrão = 10.7 m, equiv. a 35 pés)
    
    Returns:
        Dicionário com resultados detalhados da análise de decolagem
    """
    # Conversão do peso para Newtons
    W_N = W_kg * g_ms2
    
    # Cálculo da velocidade de stall na configuração de decolagem
    Vs_TO = math.sqrt((2 * W_N) / (rho0_kgm3 * S_m2 * CLmax_TO))
    
    # Velocidade de rotação (liftoff)
    Vlof = Vlof_factor * Vs_TO
    
    # Velocidade média durante a corrida no solo
    V_avg = V_avg_factor * Vlof
    
    # Empuxo médio durante a corrida (simplificação - considera constante)
    T_avg = T_N_static
    
    # Cálculos para fase de corrida no solo
    CL_avg_g = CL_ground
    CD_avg_g = CD0_takeoff + K * (CL_avg_g**2)  # Equação da polar de arrasto
    
    # Força de sustentação média durante corrida
    L_avg_g = 0.5 * rho0_kgm3 * (V_avg**2) * S_m2 * CL_avg_g
    
    # Força de arrasto média durante corrida
    D_avg_g = 0.5 * rho0_kgm3 * (V_avg**2) * S_m2 * CD_avg_g
    
    # Aceleração média durante corrida (equilíbrio de forças)
    a_avg = (g_ms2 / W_N) * (T_avg - D_avg_g - mu_roll * (W_N - L_avg_g))
    
    # Verificação de aceleração positiva
    if a_avg <= 0:
        logger.warning("Aviso: Aceleração média não positiva. Decolagem não é possível.")
        return {
            "S_ground_run_m": float("inf"), 
            "S_rotation_m": 0, 
            "S_airborne_m": 0, 
            "S_total_takeoff_m": float("inf"), 
            "Vs_TO_mps": Vs_TO, 
            "Vlof_mps": Vlof, 
            "a_avg_ms2": a_avg, 
            "gamma_climb_deg": 0
        }
    
    # Distância de corrida no solo (usando equação cinemática)
    Sg = (Vlof**2) / (2 * a_avg)
    
    # Distância percorrida durante rotação (aproximação)
    Sr = Vlof * t_rot_s
    
    # Cálculos para fase de subida inicial
    # Considerando equilíbrio de forças na subida
    CL_climb = min(W_N / (0.5 * rho0_kgm3 * (Vlof**2) * S_m2), CLmax_TO)
    CD_climb = CD0_takeoff + K * (CL_climb**2)
    D_climb = 0.5 * rho0_kgm3 * (Vlof**2) * S_m2 * CD_climb
    
    # Ângulo de subida (com base no excesso de empuxo)
    sin_gamma_cl = (T_avg - D_climb) / W_N
    
    # Verificação da capacidade de subida
    if sin_gamma_cl <= 0:
        logger.warning("Aviso: Excesso de empuxo insuficiente para subida após decolagem.")
        S_air = float("inf")
        gamma_cl = 0
    else:
        # Ângulo de subida em radianos
        gamma_cl = math.asin(sin_gamma_cl)
        # Tangente do ângulo de subida
        tan_gamma_cl = math.tan(gamma_cl)
        # Distância horizontal para atingir a altura do obstáculo
        S_air = h_obs_m / tan_gamma_cl if tan_gamma_cl > 0 else float("inf")
    
    # Distância total de decolagem
    S_total = Sg + Sr + S_air
    
    # Retornar resultados completos
    return {
        "Vs_TO_mps": Vs_TO,                  # Velocidade de stall (m/s)
        "Vlof_mps": Vlof,                    # Velocidade de rotação (m/s)
        "a_avg_ms2": a_avg,                  # Aceleração média (m/s²)
        "gamma_climb_deg": math.degrees(gamma_cl),  # Ângulo de subida (graus)
        "S_ground_run_m": Sg,                # Distância de corrida no solo (m)
        "S_rotation_m": Sr,                  # Distância de rotação (m)
        "S_airborne_m": S_air,               # Distância de subida até obstáculo (m)
        "S_total_takeoff_m": S_total         # Distância total de decolagem (m)
    }


def estimate_landing_distance(
        W_land_kg: float, 
        S_m2: float, 
        CLmax_land: float, 
        rho0_kgm3: float = 1.225, 
        g_ms2: float = 9.81, 
        mu_brake: float = 0.4, 
        CD0_landing: float = 0.063, 
        K: float = 0.049, 
        CL_land_ground: float = 0.1, 
        Vapp_factor: float = 1.3, 
        Vtd_factor: float = 1.15, 
        gamma_app_deg: float = 3.0, 
        h_obs_m: float = 15.2, 
        h_flare_m: float = 10.0, 
        t_flare_s: float = 3.0, 
        T_rev_N: float = 0
    ) -> Dict[str, float]:
    """
    Estima distância de pouso usando o método de desaceleração média.
    
    Calcula distância de aproximação + arredondamento (flare) + corrida de pouso.
    
    Args:
        W_land_kg: Peso de pouso em kg
        S_m2: Área da asa em m²
        CLmax_land: Coeficiente de sustentação máximo na configuração de pouso
        rho0_kgm3: Densidade do ar ao nível do mar (padrão = 1.225 kg/m³)
        g_ms2: Aceleração da gravidade (padrão = 9.81 m/s²)
        mu_brake: Coeficiente de atrito com frenagem (padrão = 0.4)
        CD0_landing: Coeficiente de arrasto parasita na configuração de pouso (padrão = 0.063)
        K: Fator de arrasto induzido da polar de arrasto (padrão = 0.049)
        CL_land_ground: Coeficiente de sustentação médio em solo (padrão = 0.1)
        Vapp_factor: Fator para velocidade de aproximação vs. Vs_land (padrão = 1.3)
        Vtd_factor: Fator para velocidade de toque vs. Vs_land (padrão = 1.15)
        gamma_app_deg: Ângulo de aproximação em graus (padrão = 3.0)
        h_obs_m: Altura do obstáculo na aproximação (padrão = 15.2 m, equiv. a 50 pés)
        h_flare_m: Altura de início do arredondamento (padrão = 10.0 m)
        t_flare_s: Tempo do arredondamento em segundos (padrão = 3.0)
        T_rev_N: Empuxo reverso em Newtons (padrão = 0, sem reverso)
    
    Returns:
        Dicionário com resultados detalhados da análise de pouso
    """
    # Conversão do peso para Newtons
    W_land_N = W_land_kg * g_ms2
    
    # Cálculo da velocidade de stall na configuração de pouso
    Vs_land = math.sqrt((2 * W_land_N) / (rho0_kgm3 * S_m2 * CLmax_land))
    
    # Velocidade de aproximação
    Vapp = Vapp_factor * Vs_land
    
    # Velocidade de toque (touchdown)
    Vtd = Vtd_factor * Vs_land
    
    # Conversão do ângulo de aproximação para radianos
    gamma_app_rad = math.radians(gamma_app_deg)
    
    # Distância horizontal na aproximação até altura de arredondamento
    Sa = (h_obs_m - h_flare_m) / math.tan(gamma_app_rad)
    
    # Distância horizontal durante o arredondamento (aproximação simples)
    Sf = Vapp * t_flare_s
    
    # Velocidade média durante a corrida de pouso
    V_avg_land = 0.7 * Vtd
    
    # Parâmetros aerodinâmicos médios durante a corrida
    CL_avg_land_g = CL_land_ground
    CD_avg_land_g = CD0_landing + K * (CL_avg_land_g**2)  # Polar de arrasto
    
    # Forças aerodinâmicas médias durante a corrida
    L_avg_land_g = 0.5 * rho0_kgm3 * (V_avg_land**2) * S_m2 * CL_avg_land_g
    D_avg_land_g = 0.5 * rho0_kgm3 * (V_avg_land**2) * S_m2 * CD_avg_land_g
    
    # Desaceleração média durante a corrida (com freios e possível reverso)
    # Nota: T_rev_N é negativo para empuxo reverso (contribui para frenagem)
    a_avg_land = (g_ms2 / W_land_N) * (T_rev_N - D_avg_land_g - mu_brake * (W_land_N - L_avg_land_g))
    
    # Verificação de desaceleração (deve ser negativa para parar)
    if a_avg_land >= 0:
        logger.warning("Aviso: Desaceleração média não negativa. Parada não é possível.")
        Sg_land = float("inf")
    else:
        # Distância de corrida no solo (usando equação cinemática)
        Sg_land = -(Vtd**2) / (2 * a_avg_land)
    
    # Distância total de pouso
    S_total = Sa + Sf + Sg_land
    
    # Retornar resultados completos
    return {
        "Vs_land_mps": Vs_land,               # Velocidade de stall (m/s)
        "Vapp_mps": Vapp,                     # Velocidade de aproximação (m/s)
        "Vtd_mps": Vtd,                       # Velocidade de toque (m/s)
        "a_avg_land_ms2": a_avg_land,         # Desaceleração média (m/s²)
        "S_approach_m": Sa,                   # Distância de aproximação (m)
        "S_flare_m": Sf,                      # Distância de arredondamento (m)
        "S_ground_roll_m": Sg_land,           # Distância de corrida no solo (m)
        "S_total_landing_m": S_total          # Distância total de pouso (m)
    }


def run_example() -> None:
    """Executa um exemplo de análise de distâncias de pista para um jato executivo."""
    # Parâmetros para um jato executivo similar ao Gulfstream G550
    W_takeoff_kg = 41557.66  # Peso máximo de decolagem
    S_m2 = 113.7             # Área da asa
    T_N_static = 136880      # Empuxo estático total (2x motores)
    CLmax_TO = 2.1           # CL máximo em configuração de decolagem
    CD0_takeoff = 0.048      # CD0 em configuração de decolagem
    K = 0.049                # Fator de arrasto induzido
    
    W_land_kg = 26389        # Peso típico de pouso
    CLmax_land = 2.6         # CL máximo em configuração de pouso
    CD0_landing = 0.063      # CD0 em configuração de pouso
    
    # Análise de decolagem
    logger.info("=== ANÁLISE DE DISTÂNCIA DE DECOLAGEM ===")
    takeoff_results = estimate_takeoff_distance(
        W_kg=W_takeoff_kg, 
        S_m2=S_m2, 
        T_N_static=T_N_static, 
        CLmax_TO=CLmax_TO, 
        CD0_takeoff=CD0_takeoff, 
        K=K
    )
    
    logger.info("Resultados da decolagem:")
    logger.info("  Velocidade de stall (Vs_TO): %.2f m/s (%.2f kt)", 
               takeoff_results["Vs_TO_mps"], 
               takeoff_results["Vs_TO_mps"] * 1.94384)
    logger.info("  Velocidade de rotação (Vlof): %.2f m/s (%.2f kt)", 
               takeoff_results["Vlof_mps"], 
               takeoff_results["Vlof_mps"] * 1.94384)
    logger.info("  Aceleração média: %.2f m/s²", takeoff_results["a_avg_ms2"])
    logger.info("  Ângulo de subida inicial: %.2f°", takeoff_results["gamma_climb_deg"])
    logger.info("  Distância de corrida no solo: %.2f m", takeoff_results["S_ground_run_m"])
    logger.info("  Distância de rotação: %.2f m", takeoff_results["S_rotation_m"])
    logger.info("  Distância após rotação até obstáculo: %.2f m", takeoff_results["S_airborne_m"])
    logger.info("  Distância total de decolagem: %.2f m", takeoff_results["S_total_takeoff_m"])
    
    # Análise de pouso
    logger.info("\n=== ANÁLISE DE DISTÂNCIA DE POUSO ===")
    landing_results = estimate_landing_distance(
        W_land_kg=W_land_kg, 
        S_m2=S_m2, 
        CLmax_land=CLmax_land, 
        CD0_landing=CD0_landing, 
        K=K
    )
    
    logger.info("Resultados do pouso:")
    logger.info("  Velocidade de stall (Vs_land): %.2f m/s (%.2f kt)", 
               landing_results["Vs_land_mps"], 
               landing_results["Vs_land_mps"] * 1.94384)
    logger.info("  Velocidade de aproximação: %.2f m/s (%.2f kt)", 
               landing_results["Vapp_mps"], 
               landing_results["Vapp_mps"] * 1.94384)
    logger.info("  Velocidade de toque: %.2f m/s (%.2f kt)", 
               landing_results["Vtd_mps"], 
               landing_results["Vtd_mps"] * 1.94384)
    logger.info("  Desaceleração média: %.2f m/s²", landing_results["a_avg_land_ms2"])
    logger.info("  Distância de aproximação: %.2f m", landing_results["S_approach_m"])
    logger.info("  Distância de arredondamento: %.2f m", landing_results["S_flare_m"])
    logger.info("  Distância de corrida no solo: %.2f m", landing_results["S_ground_roll_m"])
    logger.info("  Distância total de pouso: %.2f m", landing_results["S_total_landing_m"])


if __name__ == "__main__":
    run_example()