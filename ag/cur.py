from __future__ import annotations

from dataclasses import dataclass
import math
import random
from random import Random
from typing import Iterable


def _min_jerk(s: float) -> float:
    """
    Calcola la posizione normalizzata (0-1) lungo una traiettoria a minimo scossone (Minimum Jerk).
    Usa un polinomio di quinto grado: 10t^3 - 15t^4 + 6t^5.
    Questo minimizza la derivata terza della posizione (Jerk), massimizzando la naturalezza del movimento umano.
    """
    return (10 * s**3) - (15 * s**4) + (6 * s**5)


def _spring_settle(x1: float, y1: float, steps: int = 8) -> list[tuple[float, float]]:
    """
    Simula l'assestamento finale del cursore usando un sistema massa-molla smorzato (Mass-Spring-Damper).
    Equazione differenziale discretizzata: F = -kx - cv.
    Questo aggiunge un micro-movimento di 'overshoot' e correzione, matematicamente coerente con la fisiologia umana.
    """
    pts = []
    # Parametri fisici ottimizzati per stabilità
    k = 0.5  # Rigidità molla
    c = 0.4  # Smorzamento
    
    # Stato iniziale (piccolo errore simulato per innescare la correzione)
    dx = random.uniform(-3.0, 3.0)
    dy = random.uniform(-3.0, 3.0)
    vx, vy = 0.0, 0.0
    
    dt = 0.6 # Time step simulato
    
    for _ in range(steps):
        # Accelerazione
        ax = (-k * dx) - (c * vx)
        ay = (-k * dy) - (c * vy)
        
        # Integrazione velocità
        vx += ax * dt
        vy += ay * dt
        
        # Integrazione posizione
        dx += vx * dt
        dy += vy * dt
        
        pts.append((x1 + dx, y1 + dy))
        
    pts.append((x1, y1)) # Convergenza finale garantita
    return pts


def _fitts_mt(d: float, w: float, a: float = 0.05, b: float = 0.12) -> float:
    """
    Calcola il tempo di movimento previsto secondo la Legge di Fitts (Shannon formulation).
    MT = a + b * log2(D/W + 1)
    
    Args:
        d: Distanza dal target.
        w: Larghezza del target.
        a: Intercetta (tempo di reazione/elaborazione).
        b: Pendenza (inverso della larghezza di banda del sistema motorio umano).
    """
    w_eff = max(6.0, w)
    mt = a + b * math.log2((d / w_eff) + 1.0)
    # Clamp per evitare tempi troppo lunghi o nulli in automazione
    return max(0.12, min(1.2, mt))


def _path_pts(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    w: float,
    seed: int | None = None,
) -> list[tuple[float, float]]:
    """
    Genera una sequenza di punti (x, y) che simulano il movimento del mouse umano.
    Combina Fitts' Law per la durata e Minimum Jerk per la velocità, aggiungendo
    archi di controllo (Bézier-like) e rumore gaussiano per realismo.
    """
    if seed is None:
        seed = random.randrange(1 << 30)
    rnd = Random(seed)

    dx = x1 - x0
    dy = y1 - y0
    d = math.hypot(dx, dy)
    mt = _fitts_mt(d, w)

    # Frequenza di aggiornamento simulata (60Hz o più per fluidità)
    dt = 1 / 120.0 
    steps = int(mt / dt)
    steps = max(15, min(120, steps))

    # Vettore perpendicolare per l'arco
    px, py = (-dy, dx)
    p_len = math.hypot(px, py) or 1.0
    px /= p_len
    py /= p_len

    # "Bulge": deviazione dalla linea retta (arco naturale del braccio)
    bulge = rnd.uniform(-1.0, 1.0) * min(30.0, 0.15 * d)

    pts: list[tuple[float, float]] = []
    for i in range(steps + 1):
        s = i / steps
        m = _min_jerk(s)
        
        # Posizione base sulla retta
        base_x = x0 + dx * m
        base_y = y0 + dy * m

        # Aggiunta arco
        curve = bulge * math.sin(math.pi * m)
        
        # Tremolio naturale (decresce verso il target per precisione)
        jitter_scale = (1.0 - m) * 2.0
        jx = rnd.gauss(0.0, 0.4) * jitter_scale
        jy = rnd.gauss(0.0, 0.4) * jitter_scale

        x = base_x + px * curve + jx
        y = base_y + py * curve + jy
        pts.append((x, y))

    # Sostituisci l'assegnazione diretta con la fase di assestamento fisico
    pts.extend(_spring_settle(x1, y1))
    return pts


@dataclass
class Cur:
    x: float = 0.0
    y: float = 0.0

    def set(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def move(self, x: float, y: float, w: float, seed: int | None = None) -> Iterable[tuple[float, float]]:
        pts = _path_pts(self.x, self.y, x, y, w, seed=seed)
        self.x, self.y = x, y
        return pts
