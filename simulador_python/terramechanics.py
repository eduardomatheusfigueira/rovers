"""
Terramecânica e distribuição de cargas (J. Y. Wong, *Theory of Ground Vehicles*, 2022).

Corrige três problemas do modelo anterior:
  1. A repartição lateral usava frações ad-hoc `0.5 ± (h/b)·sin(roll)` que não
     correspondem a nenhum equilíbrio de momentos. Aqui a repartição sai do
     equilíbrio em torno do eixo longitudinal, com a indeterminação estática
     resolvida pela distribuição de rigidez de rolagem entre os eixos.
  2. Não havia detecção de descolamento de roda (Fz -> 0), que é justamente o
     início do tombamento.
  3. A comparação com skid-steer usava um fator arbitrário de 1,8. Agora usa o
     momento resistente de derrapagem de Wong, M_r = μ_t·W·L/4.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from .config import P as PARAMS

IDS = ("FL", "FR", "RL", "RR")
G = 9.80665


@dataclass
class EstadoContato:
    fz: Dict[str, float]              # reações normais [N]
    descolou: Dict[str, bool]
    margem_tombamento_long: float     # rad até o tombamento longitudinal
    margem_tombamento_lat: float      # rad até o tombamento lateral
    tracao_maxima: float              # esforço trativo total disponível [N]
    drawbar_pull: float               # esforço líquido de barra de tração [N]

    @property
    def carga_maxima_roda(self) -> float:
        return max(self.fz.values())

    def resumo(self) -> str:
        cargas = "  ".join(f"{k}={self.fz[k]:5.1f}N" for k in IDS)
        return (f"{cargas}\n  margem de tombamento: long {np.degrees(self.margem_tombamento_long):.1f}°, "
                f"lat {np.degrees(self.margem_tombamento_lat):.1f}°\n"
                f"  tração disponível {self.tracao_maxima:.1f} N, drawbar pull {self.drawbar_pull:.1f} N")


class TerramecanicaWong:
    def __init__(self, massa: Optional[float] = None, entre_eixos: Optional[float] = None,
                 bitola: Optional[float] = None, altura_cg: Optional[float] = None,
                 mu: Optional[float] = None):
        self.massa = PARAMS.massas.massa_total if massa is None else massa
        self.L = PARAMS.veiculo.entre_eixos_L if entre_eixos is None else entre_eixos
        self.B = PARAMS.veiculo.bitola_W if bitola is None else bitola
        self.h = PARAMS.veiculo.altura_cg_total if altura_cg is None else altura_cg
        self.mu = PARAMS.ambiente.piso.mu_borracha_concreto if mu is None else mu
        self.peso = self.massa * G

    # ------------------------------------------------------------------
    def cargas_normais(self, pitch: float = 0.0, roll: float = 0.0,
                       ax: float = 0.0, ay: float = 0.0,
                       fracao_rigidez_dianteira: float = 0.5) -> Dict[str, float]:
        """Reações normais nas quatro rodas [N].

        Equilíbrio em torno do eixo transversal (repartição dianteira/traseira) e
        do eixo longitudinal (repartição esquerda/direita). A transferência
        lateral é distribuída entre os eixos pela fração de rigidez de rolagem —
        é o que resolve a indeterminação estática de um veículo de 4 apoios.
        """
        w_normal = self.peso * np.cos(pitch) * np.cos(roll)
        lf = lr = self.L / 2.0

        # Longitudinal: peso tangencial + inércia longitudinal deslocam carga para trás
        transferencia_long = (self.peso * np.sin(pitch) + self.massa * ax) * self.h / self.L
        fz_dianteiro = w_normal * lr / self.L - transferencia_long
        fz_traseiro = w_normal * lf / self.L + transferencia_long

        # Lateral: componente lateral do peso + inércia lateral
        transferencia_lat = (self.peso * np.sin(roll) + self.massa * ay) * self.h / self.B
        dt_dianteiro = transferencia_lat * fracao_rigidez_dianteira
        dt_traseiro = transferencia_lat * (1.0 - fracao_rigidez_dianteira)

        fz = {
            "FL": fz_dianteiro / 2.0 - dt_dianteiro,
            "FR": fz_dianteiro / 2.0 + dt_dianteiro,
            "RL": fz_traseiro / 2.0 - dt_traseiro,
            "RR": fz_traseiro / 2.0 + dt_traseiro,
        }
        # Uma roda não traciona: reação normal nunca é negativa (ela descola).
        return {k: max(0.0, v) for k, v in fz.items()}

    # ------------------------------------------------------------------
    def avaliar(self, pitch: float = 0.0, roll: float = 0.0, ax: float = 0.0,
                ay: float = 0.0, crr: Optional[float] = None,
                mu: Optional[float] = None) -> EstadoContato:
        mu = self.mu if mu is None else mu
        crr = PARAMS.ambiente.piso.crr_asfalto if crr is None else crr
        fz = self.cargas_normais(pitch, roll, ax, ay)
        descolou = {k: v <= 1e-6 for k, v in fz.items()}

        tracao = sum(mu * v for v in fz.values())
        resistencia = (crr * sum(fz.values())
                       + self.peso * np.sin(abs(pitch)))
        return EstadoContato(
            fz=fz, descolou=descolou,
            margem_tombamento_long=self.angulo_tombamento_longitudinal() - abs(pitch),
            margem_tombamento_lat=self.angulo_tombamento_lateral() - abs(roll),
            tracao_maxima=tracao,
            drawbar_pull=max(0.0, tracao - resistencia),
        )

    # ------------------------------------------------------------------
    def angulo_tombamento_longitudinal(self) -> float:
        """Inclinação em que a reação dianteira zera (empinamento)."""
        return float(np.arctan2(self.L / 2.0, self.h))

    def angulo_tombamento_lateral(self) -> float:
        return float(np.arctan2(self.B / 2.0, self.h))

    def aceleracao_lateral_limite(self) -> float:
        """Aceleração lateral que descola as rodas internas [m/s²]."""
        return G * (self.B / 2.0) / self.h

    def velocidade_curva_limite(self, raio: float) -> float:
        """Velocidade máxima numa curva de raio dado, antes do tombamento [m/s]."""
        return float(np.sqrt(self.aceleracao_lateral_limite() * max(raio, 1e-3)))

    # ------------------------------------------------------------------
    def torque_por_roda(self, forca_trativa: float, raio_roda: Optional[float] = None,
                        num_rodas: int = 4) -> float:
        r = PARAMS.roda.raio_max if raio_roda is None else raio_roda
        return forca_trativa * r / num_rodas

    def atrito_minimo_exigido(self, pitch: float, crr: Optional[float] = None) -> float:
        """Coeficiente de atrito mínimo para subir uma rampa de inclinação `pitch`."""
        crr = PARAMS.ambiente.piso.crr_asfalto if crr is None else crr
        return float(np.tan(abs(pitch)) + crr)

    # ------------------------------------------------------------------
    def comparar_com_skid_steer(self, velocidade: float, raio_curva: float,
                                mu_lateral: Optional[float] = None) -> Dict[str, float]:
        """4WS coordenado x skid-steer, pelo momento resistente de Wong (cap. 6).

        No skid-steer o veículo gira arrastando lateralmente as rodas; o momento
        resistente é M_r = μ_t·W·L/4 (Wong, eq. 6.23, para pressão uniforme ao
        longo do comprimento de contato L). A potência gasta só para vencer esse
        arrasto é M_r·ω, e não existe no 4WS coordenado, cujo resíduo de
        deslizamento é nulo por construção.
        """
        mu_lat = self.mu if mu_lateral is None else mu_lateral
        crr = PARAMS.ambiente.piso.crr_asfalto
        omega = velocidade / max(raio_curva, 1e-3)

        p_rolamento = crr * self.peso * velocidade
        momento_resistente = mu_lat * self.peso * self.L / 4.0
        p_skid = p_rolamento + momento_resistente * omega

        return {
            "potencia_4ws_w": p_rolamento,
            "potencia_skid_w": p_skid,
            "momento_resistente_nm": momento_resistente,
            "economia_percentual": 100.0 * (1.0 - p_rolamento / p_skid) if p_skid > 0 else 0.0,
            "razao": p_skid / max(p_rolamento, 1e-9),
        }


def carga_projeto_por_roda(inclinacao_rad: Optional[float] = None) -> float:
    """Carga vertical de dimensionamento numa roda que escala a escada [N].

    Subindo, a transferência longitudinal é PARA TRÁS: são as rodas traseiras
    que ficam carregadas e fazem o esforço de içamento. Esta é a hipótese de
    carga correta para dimensionar torque e C-STS — usar W/2 (metade do peso em
    duas rodas) superestima em ~35%.
    """
    if inclinacao_rad is None:
        inclinacao_rad = PARAMS.ambiente.escada.inclinacao_rad
    t = TerramecanicaWong()
    fz = t.cargas_normais(pitch=inclinacao_rad)
    return max(fz["RL"], fz["RR"])


# Alias de compatibilidade com o código anterior
class TerramechanicsWong(TerramecanicaWong):
    def calculate_normal_loads(self, pitch: float, roll: float, ax: float = 0.0, az: float = 0.0):
        return self.cargas_normais(pitch, roll, ax=az, ay=0.0)
