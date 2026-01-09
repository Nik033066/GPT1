from __future__ import annotations

from dataclasses import dataclass
import math
import random
from random import Random
from typing import Iterable, Iterator

DEFAULT_FPS = 60
MIN_MOVEMENT_TIME_MS = 80
MAX_MOVEMENT_TIME_MS = 800


def _min_jerk(s: float) -> float:
    return (10 * s**3) - (15 * s**4) + (6 * s**5)


def _spring_settle(x1: float, y1: float, steps: int = 8) -> list[tuple[float, float]]:
    pts = []
    k, c = 0.5, 0.4
    dx = random.uniform(-3.0, 3.0)
    dy = random.uniform(-3.0, 3.0)
    vx, vy = 0.0, 0.0
    dt = 0.6
    
    for _ in range(steps):
        ax = (-k * dx) - (c * vx)
        ay = (-k * dy) - (c * vy)
        vx += ax * dt
        vy += ay * dt
        dx += vx * dt
        dy += vy * dt
        pts.append((x1 + dx, y1 + dy))
        
    pts.append((x1, y1))
    return pts


def _fitts_mt(d: float, w: float, a: float = 0.05, b: float = 0.12) -> float:
    w_eff = max(6.0, w)
    mt = a + b * math.log2((d / w_eff) + 1.0)
    min_sec = MIN_MOVEMENT_TIME_MS / 1000.0
    max_sec = MAX_MOVEMENT_TIME_MS / 1000.0
    return max(min_sec, min(max_sec, mt))


@dataclass
class PathResult:
    points: list[tuple[float, float]]
    total_time_ms: float
    delay_per_step_ms: float


def _path_pts(
    x0: float, y0: float, x1: float, y1: float, w: float,
    seed: int | None = None, fps: int = DEFAULT_FPS,
) -> PathResult:
    if seed is None:
        seed = random.randrange(1 << 30)
    rnd = Random(seed)

    dx = x1 - x0
    dy = y1 - y0
    d = math.hypot(dx, dy)
    
    mt = _fitts_mt(d, w)
    total_time_ms = mt * 1000.0
    
    steps = max(8, int(mt * fps))
    steps = min(steps, 150)
    delay_per_step_ms = total_time_ms / steps if steps > 0 else 0

    px, py = (-dy, dx)
    p_len = math.hypot(px, py) or 1.0
    px /= p_len
    py /= p_len

    bulge = rnd.uniform(-1.0, 1.0) * min(30.0, 0.15 * d)

    pts: list[tuple[float, float]] = []
    for i in range(steps + 1):
        s = i / steps
        m = _min_jerk(s)
        
        base_x = x0 + dx * m
        base_y = y0 + dy * m

        curve = bulge * math.sin(math.pi * m)
        
        jitter_scale = (1.0 - m) * 2.0
        jx = rnd.gauss(0.0, 0.4) * jitter_scale
        jy = rnd.gauss(0.0, 0.4) * jitter_scale

        x = base_x + px * curve + jx
        y = base_y + py * curve + jy
        pts.append((x, y))

    settle_pts = _spring_settle(x1, y1)
    pts.extend(settle_pts)
    
    settle_time_ms = len(settle_pts) * 12.0
    total_time_ms += settle_time_ms
    
    return PathResult(points=pts, total_time_ms=total_time_ms, delay_per_step_ms=delay_per_step_ms)


@dataclass
class Cur:
    x: float = 0.0
    y: float = 0.0

    def set(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def move(self, x: float, y: float, w: float, seed: int | None = None) -> Iterable[tuple[float, float]]:
        result = _path_pts(self.x, self.y, x, y, w, seed=seed)
        self.x, self.y = x, y
        return result.points
    
    def move_timed(self, x: float, y: float, w: float, seed: int | None = None, fps: int = DEFAULT_FPS) -> PathResult:
        result = _path_pts(self.x, self.y, x, y, w, seed=seed, fps=fps)
        self.x, self.y = x, y
        return result

    def iter_timed(self, x: float, y: float, w: float, seed: int | None = None, fps: int = DEFAULT_FPS) -> Iterator[tuple[float, float, float]]:
        result = _path_pts(self.x, self.y, x, y, w, seed=seed, fps=fps)
        self.x, self.y = x, y
        
        n_main = len(result.points) - 9
        
        for i, (px, py) in enumerate(result.points):
            delay = result.delay_per_step_ms if i < n_main else 12.0
            yield (px, py, delay)
