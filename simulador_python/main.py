"""CLI do simulador do Rover Frugal 4WD/4WS."""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m simulador_python.main",
        description="Simulador físico e ferramentas de projeto do Rover Frugal 4WD/4WS",
    )
    parser.add_argument("--parametros", action="store_true",
                        help="imprime o resumo dos parâmetros mestres resolvidos")
    parser.add_argument("--benchmark", action="store_true",
                        help="executa a bateria completa de benchmarks e gera as figuras")
    parser.add_argument("--relatorio", action="store_true",
                        help="gera o Relatório de Engenharia em Markdown")
    parser.add_argument("--marcha", action="store_true",
                        help="resolve a marcha na escada e imprime as métricas")
    parser.add_argument("--sintese", action="store_true",
                        help="varre o espaço de projeto (N x r_max) por robustez de fase")
    parser.add_argument("--gui", action="store_true",
                        help="abre a interface gráfica interativa (requer Tkinter)")
    parser.add_argument("--variante", type=str, default=None,
                        help="variante de projeto do YAML (v1_legado, v2_sincrona, v3_degrau_reduzido)")
    parser.add_argument("--out", type=str, default="resultados",
                        help="diretório de saída das figuras e relatórios")

    args = parser.parse_args()

    if args.variante:
        from . import config as cfgmod
        cfgmod.P = cfgmod.carregar(args.variante)
        print(f"[!] Variante '{args.variante}' carregada. Atenção: módulos já importados "
              f"mantêm os valores da variante padrão; prefira editar `meta.variante_ativa`.")

    if not any((args.parametros, args.benchmark, args.relatorio, args.marcha,
                args.sintese, args.gui)):
        args.parametros = True

    if args.parametros:
        from . import config as cfgmod
        print(cfgmod.resumo())

    if args.marcha:
        from .geometria_escada import PerfilEscada, RodaRaiosCurvos, SimuladorMarcha
        sim = SimuladorMarcha(RodaRaiosCurvos(), PerfilEscada(num_degraus=6))
        print("\n" + sim.simular(x_inicial=-0.8, degraus_alvo=4).resumo())

    if args.sintese:
        import numpy as np
        from .geometria_escada import avaliar_robustez
        from .config import P
        print("\nVarredura do espaço de projeto (robustez de fase, degrau de referência):")
        print(f"{'N':>3} {'Φ [mm]':>8} {'síncrona':>9} {'sucesso':>8} {'deg/volta':>10} {'T pico':>8}")
        for n in (3, 4):
            for r in (0.15, 0.18, 0.20, 0.22, 0.24):
                rb = avaliar_robustez(n, r, num_fases=8, degraus_alvo=3)
                print(f"{n:>3} {2*r*1000:8.0f} {'sim' if rb.sincrona else 'não':>9} "
                      f"{rb.taxa_sucesso*100:7.0f}% {rb.degraus_por_volta_medio:10.2f} "
                      f"{rb.torque_pior_caso:7.2f}")

    if args.benchmark:
        from .benchmark import run_comparative_benchmark
        run_comparative_benchmark(args.out)

    if args.relatorio:
        from .relatorio import gerar
        gerar(args.out)

    if args.gui:
        try:
            import tkinter as tk
        except ImportError:
            print("Tkinter não disponível neste ambiente. Use --benchmark ou --relatorio.")
            return 1
        from .gui_app import RoverSimulatorGUI
        raiz = tk.Tk()
        RoverSimulatorGUI(raiz)
        raiz.mainloop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
