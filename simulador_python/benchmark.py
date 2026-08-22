"""
Benchmark Comparativo: Roda com C-STS vs Roda Rígida (Jeong & Kim, 2025)
Escalada de Escada Padrão de Blondel (E = 17 cm, P = 30 cm)
Gera gráficos científicos comparativos e estatísticas de desaceleração.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from .multibody_dynamics import RoverMultibodySimulator
from .config import STAIR_RISER, STAIR_TREAD, BLONDEL_VALUE

def run_comparative_benchmark(output_image_path: str = "comparativo_csts_blondel.png"):
    """
    Executa a simulação comparativa idêntica em duas configurações:
    1. Com Suspensão Complacente Torsional C-STS
    2. Sem Suspensão (Roda Rígida Convencional)
    """
    print("=" * 70)
    print("  INICIANDO BENCHMARK CIENTÍFICO: C-STS vs RODA RÍGIDA")
    print(f"  Escada de Blondel: Espelho = {STAIR_RISER*100:.1f} cm | Piso = {STAIR_TREAD*100:.1f} cm (2E+P = {BLONDEL_VALUE*100:.1f} cm)")
    print("=" * 70)

    sim_time = 12.0 # segundos de teste
    dt = 0.005      # 200 Hz de taxa de amostragem física

    # 1. Simulação COM C-STS
    sim_csts = RoverMultibodySimulator(with_csts=True)
    sim_csts.reset(x=0.0, z=0.5, heading=0.0)

    print("\n[1/2] Executando simulação COM Suspensão C-STS...")
    for step in range(int(sim_time / dt)):
        # Avançar em direção à escada
        sim_csts.step(throttle_cmd=0.8, steer_cmd=0.0, mode='stair', dt=dt)

    # 2. Simulação SEM C-STS (Rígida)
    sim_rigid = RoverMultibodySimulator(with_csts=False)
    sim_rigid.reset(x=0.0, z=0.5, heading=0.0)

    print("[2/2] Executando simulação SEM Suspensão (Roda Rígida)...")
    for step in range(int(sim_time / dt)):
        sim_rigid.step(throttle_cmd=0.8, steer_cmd=0.0, mode='stair', dt=dt)

    # Estatísticas de Desempenho (Jeong & Kim, 2025)
    speeds_csts = np.array(sim_csts.history['speed'])
    speeds_rigid = np.array(sim_rigid.history['speed'])

    mean_v_csts = np.mean(speeds_csts)
    std_v_csts = np.std(speeds_csts)
    max_decel_csts = np.max(sim_csts.history['deceleration_spike_max'])

    mean_v_rigid = np.mean(speeds_rigid)
    std_v_rigid = np.std(speeds_rigid)
    max_decel_rigid = np.max(sim_rigid.history['deceleration_spike_max'])

    decel_reduction = ((max_decel_rigid - max_decel_csts) / max_decel_rigid) * 100.0

    print("\n" + "=" * 70)
    print("  RESULTADOS ESTATÍSTICOS DO BENCHMARK")
    print("=" * 70)
    print(f"  Métrica                          | Roda Rígida | Com C-STS   | Ganho/Melhoria")
    print(f"  ---------------------------------+-------------+-------------+---------------")
    print(f"  Velocidade Média (m/s)           | {mean_v_rigid:.3f}       | {mean_v_csts:.3f}       | +{((mean_v_csts/mean_v_rigid)-1)*100:+.1f}%")
    print(f"  Desvio Padrão da Vel. (s)        | {std_v_rigid:.3f}       | {std_v_csts:.3f}       | -{((std_v_rigid-std_v_csts)/std_v_rigid)*100:.1f}% (Mais Estável)")
    print(f"  Pico Máximo de Desaceleração (m/s²)| {max_decel_rigid:.2f}        | {max_decel_csts:.2f}        | -{decel_reduction:.1f}% (Menor Choque)")
    print("=" * 70)

    # Geração dos Gráficos Comparativos
    fig, axs = plt.subplots(3, 1, figsize=(11, 10), sharex=True)
    plt.style.use('dark_background')
    fig.suptitle('Benchmark Dinâmico: Roda com C-STS vs Roda Rígida na Escada de Blondel\nJeong & Kim (2025) / Wong (2022)',
                 fontsize=13, fontweight='bold', color='#00e5ff')

    t_csts = sim_csts.history['time']
    t_rigid = sim_rigid.history['time']

    # Subplot 1: Perfil de Velocidade Linear CoR
    axs[0].plot(t_rigid, sim_rigid.history['speed'], color='#ff1744', linestyle='--', label='Roda Rígida (Sem Suspensão)', alpha=0.8)
    axs[0].plot(t_csts, sim_csts.history['speed'], color='#00e5ff', linewidth=2.0, label='Com Suspensão C-STS (Jeong & Kim, 2025)')
    axs[0].set_ylabel('Velocidade Linear (m/s)', fontsize=10)
    axs[0].set_title('1. Perfil de Velocidade Linear do Centro de Rotação (CoR)', fontsize=11, color='#ffffff')
    axs[0].grid(True, alpha=0.25)
    axs[0].legend(loc='upper right')

    # Subplot 2: Picos de Desaceleração de Impacto (DCS)
    axs[1].plot(t_rigid, sim_rigid.history['deceleration_spike_max'], color='#ff5252', linestyle=':', label='Choques DCS (Rígida)', alpha=0.7)
    axs[1].plot(t_csts, sim_csts.history['deceleration_spike_max'], color='#ffb300', linewidth=1.8, label='Choques DCS Suavizados (C-STS)')
    axs[1].set_ylabel('Desaceleração a_i (m/s²)', fontsize=10)
    axs[1].set_title(f'2. Picos de Desaceleração na Transição dos Raios (Redução de {decel_reduction:.1f}%)', fontsize=11, color='#ffffff')
    axs[1].grid(True, alpha=0.25)
    axs[1].legend(loc='upper right')

    # Subplot 3: Arfagem (Pitch) e Energia Armazenada
    axs[2].plot(t_csts, sim_csts.history['pitch'], color='#00e676', linewidth=1.8, label='Pitch do Chassi (Graus)')
    axs[2].plot(t_csts, sim_csts.history['pendulum_pitch'], color='#d4a359', linestyle='--', label='Balanço Pendular da Caixa Útil')
    axs[2].set_xlabel('Tempo de Simulação (s)', fontsize=10)
    axs[2].set_ylabel('Ângulo (°)', fontsize=10)
    axs[2].set_title('3. Estabilidade Angular do Chassi e Auto-Nivelamento Pendular', fontsize=11, color='#ffffff')
    axs[2].grid(True, alpha=0.25)
    axs[2].legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(output_image_path, dpi=200, bbox_inches='tight')
    print(f"\n[OK] Gráfico comparativo gerado e salvo em: {os.path.abspath(output_image_path)}")
    return output_image_path
