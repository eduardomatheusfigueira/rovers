"""
Lei de mola das juntas passivas (suspensão elástica e C-STS), pura e testável.

Por que num nó e não no SDF: `<spring_stiffness>` em SDF depende do motor de
física (DART aplica, ODE ignora) e não existe em URDF. Manter a lei de mola num
nó ROS torna o modelo **portátil entre simuladores** e — mais importante — usa
exatamente as mesmas constantes que o dimensionamento analítico.

Requisito de taxa: a malha precisa ser bem mais rápida que a maior frequência
natural do sistema, ω = sqrt(k/m). Com k = 1000 N/m e m = 0,64 kg (massa não
suspensa por roda), ω ≈ 40 rad/s; o gerador de configuração calcula a frequência
mínima e a coloca em `controle.frequencia_passivas_hz`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MolaLinear:
    """Suspensão elástica: F = −k·x − c·ẋ, com batente de fim de curso."""

    rigidez: float          # N/m
    amortecimento: float    # N·s/m
    curso: float            # m
    rigidez_batente: float = 2.0e4

    def esforco(self, x: float, v: float) -> float:
        f = -self.rigidez * x - self.amortecimento * v
        if x > self.curso:
            f -= self.rigidez_batente * (x - self.curso)
        elif x < 0.0:
            f -= self.rigidez_batente * x
        return f

    def afundamento_estatico(self, carga_n: float) -> float:
        return carga_n / self.rigidez


@dataclass(frozen=True)
class MolaTorsional:
    """C-STS: τ = −kt·θ − ct·θ̇, com batente angular."""

    rigidez: float          # N·m/rad
    amortecimento: float    # N·m·s/rad
    limite: float           # rad
    rigidez_batente: float = 400.0

    def esforco(self, theta: float, omega: float) -> float:
        t = -self.rigidez * theta - self.amortecimento * omega
        if abs(theta) > self.limite:
            t -= self.rigidez_batente * (abs(theta) - self.limite) * (1 if theta > 0 else -1)
        return t

    def energia(self, theta: float) -> float:
        return 0.5 * self.rigidez * theta ** 2
