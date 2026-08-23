"""
Geometria de Escalada: perfil de escada, roda de raios curvos e simulador de marcha.

Este módulo responde, de forma verificável, à pergunta central do projeto:

    "Uma roda de N raios curvos de raio r_max consegue escalar um degrau de
     espelho E e piso P? Com que marcha, com que torque e com que impacto?"

MODELO
------
Trabalha no plano sagital (x = avanço, y = altura). A escada é uma poligonal
monotônica em x; a roda é um conjunto de N curvas (os raios) amostradas
densamente. A marcha é resolvida de forma QUASE-ESTÁTICA por eventos:

  1. A roda pivota em torno do ponto de contato corrente (rolamento sem
     escorregamento: o ponto de contato é instantaneamente fixo).
  2. Integra-se o ângulo de giro até que qualquer ponto da roda penetre o
     terreno; o instante exato é isolado por bisseção.
  3. O ponto que penetrou torna-se o novo pivô e o ciclo recomeça.

Isso reproduz exatamente a alternância CCS/DCS descrita por Jeong & Kim (2025)
sem nenhum fator de ajuste empírico: a queda de altura do cubo entre eventos
(e portanto o impacto) é uma CONSEQUÊNCIA da geometria, não um parâmetro.

CONDIÇÃO ANALÍTICA DE MARCHA SÍNCRONA
-------------------------------------
Para que a roda avance exatamente um degrau por raio (marcha síncrona, a mais
suave possível), dois raios consecutivos precisam tocar dois narizes
consecutivos simultaneamente. Sendo o ângulo entre raios 2*pi/N e ambos os
contatos na ponta (raio r_max), a corda vale 2*r_max*sin(pi/N). Logo:

        D = hypot(E, P) <= 2 * r_max * sin(pi / N)
        r_max >= D / (2 * sin(pi / N))                              (Eq. 1)

Limitações conhecidas do modelo estão documentadas em
`03_Simulacao_e_Prototipacao_Digital/04_Verificacao_e_Validacao_do_Modelo.md`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np

from .config import P as PARAMS

TOL_PENETRACAO = 1e-6   # m — profundidade tolerada antes de declarar contato
TOL_ANGULO = 1e-7       # rad — resolução da bisseção do instante de contato


# =============================================================================
# 1. TERRENO
# =============================================================================
@dataclass
class PerfilEscada:
    """Escada civil no plano sagital, subindo no sentido +x.

    Nariz i (aresta do degrau i) fica em (x0 + i*P, (i+1)*E), i = 0..n-1.
    """

    espelho: float = PARAMS.ambiente.escada.espelho_E
    piso: float = PARAMS.ambiente.escada.piso_P
    num_degraus: int = 6
    x_inicio: float = 0.0
    y_base: float = 0.0
    comprimento_patamar: float = 2.0

    @property
    def passo(self) -> float:
        """Distância nariz-a-nariz D = hypot(E, P)."""
        return float(np.hypot(self.espelho, self.piso))

    @property
    def blondel(self) -> float:
        """Valor da fórmula de Blondel 2E + P (NBR 9050: 0,63 a 0,65 m)."""
        return 2.0 * self.espelho + self.piso

    @property
    def inclinacao(self) -> float:
        return float(np.arctan2(self.espelho, self.piso))

    @property
    def altura_total(self) -> float:
        return self.num_degraus * self.espelho

    def narizes(self) -> List[Tuple[float, float]]:
        return [
            (self.x_inicio + i * self.piso, self.y_base + (i + 1) * self.espelho)
            for i in range(self.num_degraus)
        ]

    def altura(self, x: float | np.ndarray) -> float | np.ndarray:
        """Cota do terreno em x (superfície superior sólida)."""
        x = np.asarray(x, dtype=float)
        idx = np.floor((x - self.x_inicio) / self.piso) + 1.0
        idx = np.clip(idx, 0.0, float(self.num_degraus))
        y = self.y_base + idx * self.espelho
        return float(y) if np.isscalar(x) or y.ndim == 0 else y

    def penetracao(self, pontos: np.ndarray) -> np.ndarray:
        """Profundidade vertical de penetração (>0 significa dentro do sólido)."""
        return self.altura(pontos[:, 0]) - pontos[:, 1]

    def classificar_contato(self, ponto: np.ndarray, tol: float = 2.5e-3):
        """Classifica um contato em 'piso', 'espelho' ou 'nariz' e devolve a normal.

        A tolerância `tol` acompanha o espaçamento da amostragem do raio: um
        contato a menos de `tol` de uma aresta é um contato de nariz.
        """
        x, y = float(ponto[0]), float(ponto[1])
        narizes = np.array(self.narizes()) if self.num_degraus else np.empty((0, 2))
        if len(narizes):
            d = np.hypot(narizes[:, 0] - x, narizes[:, 1] - y)
            if float(d.min()) <= tol:
                # Normal média do canto: bissetriz entre piso (0,1) e espelho (-1,0)
                return "nariz", np.array([-np.sqrt(0.5), np.sqrt(0.5)])
            for nx, ny in narizes:
                if abs(x - nx) <= tol and (ny - self.espelho - tol) <= y <= (ny + tol):
                    return "espelho", np.array([-1.0, 0.0])
        return "piso", np.array([0.0, 1.0])

    def poligonal(self) -> np.ndarray:
        """Poligonal do perfil, para desenho."""
        pts = [(self.x_inicio - 1.0, self.y_base), (self.x_inicio, self.y_base)]
        for i in range(self.num_degraus):
            x = self.x_inicio + i * self.piso
            y = self.y_base + (i + 1) * self.espelho
            pts.append((x, y))
            pts.append((x + self.piso, y))
        pts.append((self.x_inicio + self.num_degraus * self.piso + self.comprimento_patamar,
                    self.y_base + self.altura_total))
        return np.array(pts)


@dataclass
class PerfilPlano:
    """Terreno plano opcional (validação: a roda deve rolar com ripple conhecido)."""

    y_base: float = 0.0

    def altura(self, x):
        x = np.asarray(x, dtype=float)
        return np.full_like(x, self.y_base) if x.ndim else float(self.y_base)

    def penetracao(self, pontos: np.ndarray) -> np.ndarray:
        return self.altura(pontos[:, 0]) - pontos[:, 1]

    def classificar_contato(self, ponto):
        return "piso", np.array([0.0, 1.0])

    def poligonal(self) -> np.ndarray:
        return np.array([(-5.0, self.y_base), (20.0, self.y_base)])


@dataclass
class PerfilMeioFio:
    """Degrau isolado (meio-fio), para os ensaios de nível 3."""

    altura_degrau: float = PARAMS.ambiente.meio_fio.altura_maxima
    x_degrau: float = 0.0
    y_base: float = 0.0

    def altura(self, x):
        x = np.asarray(x, dtype=float)
        y = np.where(x >= self.x_degrau, self.y_base + self.altura_degrau, self.y_base)
        return float(y) if y.ndim == 0 else y

    def penetracao(self, pontos: np.ndarray) -> np.ndarray:
        return self.altura(pontos[:, 0]) - pontos[:, 1]

    def classificar_contato(self, ponto, tol: float = 2.5e-3):
        x, y = float(ponto[0]), float(ponto[1])
        topo = self.y_base + self.altura_degrau
        if np.hypot(x - self.x_degrau, y - topo) <= tol:
            return "nariz", np.array([-np.sqrt(0.5), np.sqrt(0.5)])
        if abs(x - self.x_degrau) <= tol and self.y_base - tol <= y <= topo + tol:
            return "espelho", np.array([-1.0, 0.0])
        return "piso", np.array([0.0, 1.0])

    def poligonal(self) -> np.ndarray:
        return np.array([
            (self.x_degrau - 1.0, self.y_base), (self.x_degrau, self.y_base),
            (self.x_degrau, self.y_base + self.altura_degrau),
            (self.x_degrau + 2.0, self.y_base + self.altura_degrau),
        ])


# =============================================================================
# 2. RODA DE RAIOS CURVOS
# =============================================================================
@dataclass
class RodaRaiosCurvos:
    """Roda de N raios curvos (perfil espiral) segundo Jeong & Kim (2025)."""

    num_raios: int = PARAMS.roda.num_raios_N
    raio_max: float = PARAMS.roda.raio_max
    raio_cubo: float = PARAMS.roda.raio_cubo
    varredura: float = PARAMS.roda.varredura_rad
    expoente: float = PARAMS.roda.expoente_perfil
    sentido: int = PARAMS.roda.sentido_curvatura
    amostras_por_raio: int = 220

    _perfil_local: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._perfil_local = self._construir_perfil()

    def _construir_perfil(self) -> np.ndarray:
        """Pontos (x, y) dos N raios no referencial da roda, ângulo de giro nulo."""
        u = np.linspace(0.0, 1.0, self.amostras_por_raio)
        r = self.raio_cubo + u * (self.raio_max - self.raio_cubo)
        varredura = self.sentido * self.varredura * u ** self.expoente
        pontos = []
        for s in range(self.num_raios):
            base = s * 2.0 * np.pi / self.num_raios
            th = base + varredura
            pontos.append(np.column_stack((r * np.cos(th), r * np.sin(th))))
        return np.vstack(pontos)

    @property
    def alcance_nariz_a_nariz(self) -> float:
        """Maior distância entre pontas de dois raios consecutivos (Eq. 1)."""
        return 2.0 * self.raio_max * float(np.sin(np.pi / self.num_raios))

    @staticmethod
    def raio_sincrono(passo: float, num_raios: int) -> float:
        """Raio mínimo para marcha síncrona (Eq. 1 invertida)."""
        return passo / (2.0 * float(np.sin(np.pi / num_raios)))

    def marcha_sincrona(self, passo: float) -> bool:
        return self.alcance_nariz_a_nariz >= passo - 1e-9

    def pontos(self, cubo: np.ndarray, psi: float) -> np.ndarray:
        """Pontos da roda no mundo, com o cubo em `cubo` e giro `psi` (horário=avanço)."""
        c, s = np.cos(psi), np.sin(psi)
        rot = np.array([[c, s], [-s, c]])          # rotação horária de psi
        return self._perfil_local @ rot.T + cubo

    def pontas(self, cubo: np.ndarray, psi: float) -> np.ndarray:
        """Somente as N pontas dos raios."""
        idx = [(k + 1) * self.amostras_por_raio - 1 for k in range(self.num_raios)]
        return self.pontos(cubo, psi)[idx]


# =============================================================================
# 3. SIMULADOR DE MARCHA (quase-estático, dirigido a eventos)
# =============================================================================
@dataclass
class EventoTransferencia:
    """Transferência de contato de um raio para o seguinte (transição CCS -> DCS)."""

    psi: float                  # ângulo de giro acumulado da roda [rad]
    cubo: np.ndarray            # posição do cubo no instante da transferência [m]
    contato_anterior: np.ndarray
    contato_novo: np.ndarray
    tipo: str                   # 'piso' | 'nariz' | 'espelho'
    raio_anterior: float        # raio efetivo antes da transferência [m]
    raio_novo: float            # raio efetivo depois da transferência [m]
    queda_cubo: float           # descida do cubo desde o último máximo local [m]
    salto: float                # distância entre os dois pontos de contato [m]


@dataclass
class ResultadoMarcha:
    eventos: List[EventoTransferencia]
    trajetoria_cubo: np.ndarray       # (n, 2) — histórico fino do cubo
    psi: np.ndarray                   # (n,)
    torque: np.ndarray                # (n,) — torque de acionamento exigido [N·m]
    raio_efetivo: np.ndarray          # (n,) — distância cubo-contato [m]
    sucesso: bool
    motivo: str
    degraus_vencidos: int
    voltas: float
    avanco_total: float
    folga_narizes: float = float("nan")   # menor distância cubo -> linha dos narizes [m]

    @property
    def degraus_por_volta(self) -> float:
        return self.degraus_vencidos / self.voltas if self.voltas > 0 else 0.0

    @property
    def transferencias_por_degrau(self) -> float:
        return len(self.eventos) / self.degraus_vencidos if self.degraus_vencidos else float("inf")

    @property
    def queda_maxima(self) -> float:
        return max((e.queda_cubo for e in self.eventos), default=0.0)

    @property
    def velocidade_impacto(self) -> float:
        """Velocidade de queda livre equivalente à maior descida do cubo."""
        return float(np.sqrt(2.0 * 9.80665 * self.queda_maxima))

    @property
    def torque_pico(self) -> float:
        return float(np.max(self.torque)) if len(self.torque) else 0.0

    @property
    def torque_medio(self) -> float:
        return float(np.mean(self.torque)) if len(self.torque) else 0.0

    @property
    def ripple_cubo(self) -> float:
        """Amplitude pico-a-pico da altura do cubo em torno da rampa média."""
        if len(self.trajetoria_cubo) < 3:
            return 0.0
        x, y = self.trajetoria_cubo[:, 0], self.trajetoria_cubo[:, 1]
        a, b = np.polyfit(x, y, 1)
        residuo = y - (a * x + b)
        return float(residuo.max() - residuo.min())

    @property
    def avanco_por_volta(self) -> float:
        return self.avanco_total / self.voltas if self.voltas > 0 else 0.0

    def contatos_em_espelho(self) -> int:
        return sum(1 for e in self.eventos if e.tipo == "espelho")

    def resumo(self) -> str:
        return (
            f"{'ESCALOU' if self.sucesso else 'FALHOU'} — {self.motivo}\n"
            f"  degraus vencidos ............ {self.degraus_vencidos} em {self.voltas:.2f} voltas "
            f"({self.degraus_por_volta:.2f} degraus/volta)\n"
            f"  transferências por degrau ... {self.transferencias_por_degrau:.2f} "
            f"(marcha síncrona ideal = 1,00)\n"
            f"  queda máxima do cubo ........ {self.queda_maxima*1000:.1f} mm "
            f"(impacto equivalente {self.velocidade_impacto:.2f} m/s)\n"
            f"  ripple do cubo .............. {self.ripple_cubo*1000:.1f} mm pico-a-pico\n"
            f"  torque exigido (pico/médio) . {self.torque_pico:.2f} / {self.torque_medio:.2f} N·m por roda\n"
            f"  contatos na face do espelho . {self.contatos_em_espelho()}"
        )


class SimuladorMarcha:
    """Marcha quase-estática de uma roda de raios curvos sobre um perfil.

    Hipóteses (ver doc de V&V):
      H1. Plano sagital; a roda é rígida (a complacência C-STS é tratada à parte,
          em `csts.py`, alimentada pelas quedas de cubo obtidas aqui).
      H2. Rolamento sem escorregamento no ponto de contato.
      H3. Quase-estático: a carga vertical no cubo é constante e o torque
          exigido decorre do equilíbrio de momentos em torno do contato.
      H4. Contato pontual, amostrado ao longo da curva do raio.
    """

    #: salto mínimo, em metros, para considerar que houve transferência de raio
    LIMIAR_TRANSFERENCIA = 3.0e-3

    def __init__(self, roda: RodaRaiosCurvos, terreno, carga_por_roda_N: float | None = None):
        self.roda = roda
        self.terreno = terreno
        if carga_por_roda_N is None:
            from .terramechanics import carga_projeto_por_roda
            carga_por_roda_N = carga_projeto_por_roda()
        self.carga = float(carga_por_roda_N)

    # --- utilidades ---------------------------------------------------------
    def _penetracao_max(self, cubo: np.ndarray, psi: float) -> Tuple[float, int]:
        pts = self.roda.pontos(cubo, psi)
        pen = self.terreno.penetracao(pts)
        k = int(np.argmax(pen))
        return float(pen[k]), k

    def _assentar(self, x_cubo: float) -> Tuple[np.ndarray, float, int]:
        """Assenta a roda em x_cubo no giro que resulta na menor cota de cubo."""
        melhor = None
        passo_setor = 2.0 * np.pi / self.roda.num_raios
        for psi in np.linspace(0.0, passo_setor, 91):
            pts = self.roda.pontos(np.array([x_cubo, 0.0]), psi)
            elevacao = float(np.max(self.terreno.altura(pts[:, 0]) - pts[:, 1]))
            if melhor is None or elevacao < melhor[0]:
                melhor = (elevacao, psi)
        elevacao, psi = melhor
        cubo = np.array([x_cubo, elevacao])
        _, k = self._penetracao_max(cubo, psi)
        return cubo, psi, k

    @staticmethod
    def _girar(cubo, psi, pivo, d):
        c, s = np.cos(d), np.sin(d)
        rot = np.array([[c, s], [-s, c]])       # rotação horária = avanço
        return rot @ (cubo - pivo) + pivo, psi + d

    def _resolver_contato(self, cubo, psi, pivo, dpsi):
        """Gira dpsi em torno do pivô; se houver penetração, isola o instante."""
        cubo_p, psi_p = self._girar(cubo, psi, pivo, dpsi)
        pen, k_hi = self._penetracao_max(cubo_p, psi_p)
        if pen <= TOL_PENETRACAO:
            return cubo_p, psi_p, None, None
        lo, hi = 0.0, dpsi
        while hi - lo > TOL_ANGULO:
            mid = 0.5 * (lo + hi)
            cubo_m, psi_m = self._girar(cubo, psi, pivo, mid)
            pen_m, k_m = self._penetracao_max(cubo_m, psi_m)
            if pen_m > TOL_PENETRACAO:
                hi, k_hi = mid, k_m
            else:
                lo = mid
        # O ponto de contato é o que PENETROU em `hi`; a pose devolvida é a de
        # `lo`, a última sem interferência. Tomar o índice em `lo` devolveria o
        # próprio pivô (folga nula) e travaria a marcha.
        cubo_f, psi_f = self._girar(cubo, psi, pivo, lo)
        contato = self.roda.pontos(cubo_f, psi_f)[k_hi]
        return cubo_f, psi_f, contato, k_hi

    # --- laço principal -----------------------------------------------------
    def simular(
        self,
        x_inicial: float = -0.60,
        dpsi: float = np.radians(0.25),
        max_voltas: float = 14.0,
        degraus_alvo: Optional[int] = None,
    ) -> ResultadoMarcha:
        cubo, psi, k_pivo = self._assentar(x_inicial)
        pivo = self.roda.pontos(cubo, psi)[k_pivo].copy()
        psi_inicial = psi

        eventos: List[EventoTransferencia] = []
        traj: List[np.ndarray] = [cubo.copy()]
        psis: List[float] = [psi]
        torques: List[float] = [self.carga * max(0.0, float(pivo[0] - cubo[0]))]
        raios: List[float] = [float(np.linalg.norm(pivo - cubo))]

        y_max_local = cubo[1]
        motivo = "curso máximo de rotação atingido"
        sucesso = False
        x_marca, psi_marca = cubo[0], psi

        max_passos = int(max_voltas * 2.0 * np.pi / dpsi)
        for _ in range(max_passos):
            cubo_n, psi_n, contato, k = self._resolver_contato(cubo, psi, pivo, dpsi)

            if contato is not None:
                salto = float(np.linalg.norm(contato - pivo))
                raio_ant = float(np.linalg.norm(pivo - cubo_n))
                raio_novo = float(np.linalg.norm(contato - cubo_n))
                if salto > self.LIMIAR_TRANSFERENCIA:
                    tipo, _ = self.terreno.classificar_contato(contato)
                    eventos.append(EventoTransferencia(
                        psi=psi_n, cubo=cubo_n.copy(),
                        contato_anterior=pivo.copy(), contato_novo=contato.copy(),
                        tipo=tipo, raio_anterior=raio_ant, raio_novo=raio_novo,
                        queda_cubo=max(0.0, float(y_max_local - cubo_n[1])), salto=salto,
                    ))
                    y_max_local = cubo_n[1]
                    if tipo == "espelho":
                        motivo = ("bloqueio: apoio na face vertical do espelho — a reação "
                                  "sai do cone de atrito e a roda escorrega em vez de subir")
                        cubo, psi = cubo_n, psi_n
                        traj.append(cubo.copy()); psis.append(psi)
                        torques.append(self.carga * max(0.0, float(contato[0] - cubo[0])))
                        raios.append(raio_novo)
                        break
                pivo = contato

            cubo, psi = cubo_n, psi_n
            y_max_local = max(y_max_local, cubo[1])
            traj.append(cubo.copy())
            psis.append(psi)
            torques.append(self.carga * max(0.0, float(pivo[0] - cubo[0])))
            raios.append(float(np.linalg.norm(pivo - cubo)))

            if degraus_alvo is not None and self._degraus_vencidos(cubo) >= degraus_alvo:
                sucesso, motivo = True, f"{degraus_alvo} degraus vencidos"
                break

            # Detecção de travamento: uma volta inteira sem avanço apreciável
            if psi - psi_marca >= 2.0 * np.pi:
                if cubo[0] - x_marca < 0.20 * self.roda.raio_max:
                    motivo = "travamento: uma volta completa sem avanço significativo"
                    break
                x_marca, psi_marca = cubo[0], psi

        traj_arr = np.array(traj)
        degraus = self._degraus_vencidos(cubo)
        voltas = max((psis[-1] - psi_inicial) / (2.0 * np.pi), 1e-9)
        folga = self._folga_linha_narizes(traj_arr)
        if degraus_alvo is None and degraus > 0 and "bloqueio" not in motivo:
            sucesso, motivo = True, f"{degraus} degraus vencidos"
        return ResultadoMarcha(
            eventos=eventos, trajetoria_cubo=traj_arr, psi=np.array(psis),
            torque=np.array(torques), raio_efetivo=np.array(raios),
            sucesso=sucesso, motivo=motivo, degraus_vencidos=degraus,
            voltas=voltas, avanco_total=float(traj_arr[-1, 0] - traj_arr[0, 0]),
            folga_narizes=folga,
        )

    def _folga_linha_narizes(self, traj: np.ndarray) -> float:
        """Menor distância perpendicular do cubo à linha que une os narizes.

        É o espaço vertical disponível abaixo do eixo das rodas: o ventre do
        veículo (fundo da caixa) precisa caber dentro desta folga, senão encalha
        na quina dos degraus durante a subida.
        """
        if not isinstance(self.terreno, PerfilEscada) or len(traj) < 2:
            return float("nan")
        theta = self.terreno.inclinacao
        n = np.array([-np.sin(theta), np.cos(theta)])   # normal à rampa dos narizes
        p0 = np.array(self.terreno.narizes()[0])
        dentro = traj[(traj[:, 0] >= p0[0]) &
                      (traj[:, 0] <= self.terreno.x_inicio + (self.terreno.num_degraus - 1) * self.terreno.piso)]
        if len(dentro) == 0:
            return float("nan")
        return float(np.min((dentro - p0) @ n))

    def _degraus_vencidos(self, cubo: np.ndarray) -> int:
        if not isinstance(self.terreno, PerfilEscada):
            return 0
        alt = float(self.terreno.altura(cubo[0])) - self.terreno.y_base
        return int(round(alt / self.terreno.espelho))


# =============================================================================
# 4. FUNÇÕES DE ALTO NÍVEL
# =============================================================================
def avaliar_projeto(
    num_raios: int,
    raio_max: float,
    espelho: float,
    piso: float,
    raio_cubo: Optional[float] = None,
    carga_por_roda_N: Optional[float] = None,
    degraus_alvo: int = 4,
) -> ResultadoMarcha:
    """Roda a marcha completa para um par (N, r_max) num degrau (E, P)."""
    if raio_cubo is None:
        raio_cubo = max(0.03, 0.30 * raio_max)
    roda = RodaRaiosCurvos(num_raios=num_raios, raio_max=raio_max, raio_cubo=raio_cubo)
    escada = PerfilEscada(espelho=espelho, piso=piso, num_degraus=degraus_alvo + 2)
    sim = SimuladorMarcha(roda, escada, carga_por_roda_N=carga_por_roda_N)
    return sim.simular(x_inicial=-0.6, degraus_alvo=degraus_alvo)


@dataclass
class ResultadoRobustez:
    """Agregado de marchas para todas as fases de aproximação de um projeto."""

    num_raios: int
    raio_max: float
    espelho: float
    piso: float
    fases: List[float]
    resultados: List[ResultadoMarcha]

    @property
    def taxa_sucesso(self) -> float:
        return sum(1 for r in self.resultados if r.sucesso) / max(1, len(self.resultados))

    @property
    def sincrona(self) -> bool:
        alcance = 2.0 * self.raio_max * float(np.sin(np.pi / self.num_raios))
        return alcance >= float(np.hypot(self.espelho, self.piso))

    @property
    def margem_sincronismo(self) -> float:
        alcance = 2.0 * self.raio_max * float(np.sin(np.pi / self.num_raios))
        return alcance - float(np.hypot(self.espelho, self.piso))

    @property
    def torque_pior_caso(self) -> float:
        return max((r.torque_pico for r in self.resultados), default=0.0)

    @property
    def queda_pior_caso(self) -> float:
        return max((r.queda_maxima for r in self.resultados), default=0.0)

    @property
    def degraus_por_volta_medio(self) -> float:
        vals = [r.degraus_por_volta for r in self.resultados if r.sucesso]
        return float(np.mean(vals)) if vals else 0.0

    def resumo(self) -> str:
        return (
            f"N={self.num_raios} r_max={self.raio_max*1000:.0f} mm (Φ{2*self.raio_max*1000:.0f} mm) "
            f"em degrau {self.espelho*1000:.0f}x{self.piso*1000:.0f} mm\n"
            f"  marcha síncrona ....... {'SIM' if self.sincrona else 'NÃO'} "
            f"(margem {self.margem_sincronismo*1000:+.1f} mm)\n"
            f"  robustez de fase ...... {self.taxa_sucesso*100:.0f}% das fases de aproximação escalam\n"
            f"  degraus por volta ..... {self.degraus_por_volta_medio:.2f}\n"
            f"  torque de pior caso ... {self.torque_pior_caso:.2f} N·m por roda\n"
            f"  queda de pior caso .... {self.queda_pior_caso*1000:.1f} mm"
        )


def avaliar_robustez(
    num_raios: int,
    raio_max: float,
    espelho: float = PARAMS.ambiente.escada.espelho_E,
    piso: float = PARAMS.ambiente.escada.piso_P,
    raio_cubo: Optional[float] = None,
    num_fases: int = 12,
    degraus_alvo: int = 3,
    carga_por_roda_N: Optional[float] = None,
) -> ResultadoRobustez:
    """Avalia a marcha para todas as fases de aproximação do primeiro nariz.

    A fase com que a roda chega ao pé da escada não é controlável pelo piloto:
    um projeto só é aceitável se escalar a partir de QUALQUER fase. Esta função
    varre a posição inicial ao longo de um passo de degrau completo.
    """
    if raio_cubo is None:
        raio_cubo = max(0.03, 0.30 * raio_max)
    passo = float(np.hypot(espelho, piso))
    fases, resultados = [], []
    for f in np.linspace(0.0, piso, num_fases, endpoint=False):
        x0 = -0.60 - float(f)
        roda = RodaRaiosCurvos(num_raios=num_raios, raio_max=raio_max, raio_cubo=raio_cubo)
        escada = PerfilEscada(espelho=espelho, piso=piso, num_degraus=degraus_alvo + 2)
        sim = SimuladorMarcha(roda, escada, carga_por_roda_N=carga_por_roda_N)
        resultados.append(sim.simular(x_inicial=x0, degraus_alvo=degraus_alvo))
        fases.append(float(f))
    return ResultadoRobustez(num_raios, raio_max, espelho, piso, fases, resultados)


def mapa_viabilidade(
    raios_mm: Sequence[float],
    lista_n: Sequence[int],
    espelho: float = PARAMS.ambiente.escada.espelho_E,
    piso: float = PARAMS.ambiente.escada.piso_P,
    degraus_alvo: int = 3,
) -> dict:
    """Varredura do espaço de projeto (N x r_max) devolvendo métricas por ponto."""
    saida = {}
    for n in lista_n:
        for r_mm in raios_mm:
            res = avaliar_projeto(n, r_mm * 1e-3, espelho, piso, degraus_alvo=degraus_alvo)
            saida[(n, r_mm)] = res
    return saida
