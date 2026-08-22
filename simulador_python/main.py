"""
Ponto de Entrada Principal do Simulador Python do Rover Frugal 4WD/4WS
"""

import sys
import argparse
import tkinter as tk

from .gui_app import RoverSimulatorGUI
from .benchmark import run_comparative_benchmark

def main():
    parser = argparse.ArgumentParser(description="Simulador Físico Avançado do Rover Frugal 4WD/4WS")
    parser.add_argument("--benchmark", action="store_true", help="Executa apenas o benchmark comparativo C-STS vs Roda Rígida")
    parser.add_argument("--out", type=str, default="comparativo_csts_blondel.png", help="Caminho do arquivo de saída do gráfico")

    args = parser.parse_args()

    if args.benchmark:
        run_comparative_benchmark(output_image_path=args.out)
    else:
        # Modo Padrão: Interface Gráfica Interativa Tkinter
        root = tk.Tk()
        app = RoverSimulatorGUI(root)
        root.mainloop()

if __name__ == "__main__":
    main()
