# utils/math_utils.py

import math
import numpy as np
from typing import Tuple, Optional


def angle_diff(a1: float, a2: float) -> float:
    """Szögek különbsége -180 és +180 között."""
    d = a2 - a1
    while d > 180:
        d -= 360
    while d < -180:
        d += 360
    return d


def smooth_ellipse(
    current: Optional[Tuple],
    target: Optional[Tuple],
    alpha: float
) -> Optional[Tuple]:
    """
    Két ellipszis közötti interpoláció.

    Formátum: ((cx, cy), (w, h), angle)
    """
    if current is None:
        return target
    if target is None:
        return current

    (cx1, cy1), (w1, h1), a1 = current
    (cx2, cy2), (w2, h2), a2 = target

    cx = cx1 * (1 - alpha) + cx2 * alpha
    cy = cy1 * (1 - alpha) + cy2 * alpha
    w  = w1  * (1 - alpha) + w2  * alpha
    h  = h1  * (1 - alpha) + h2  * alpha
    a  = a1 + angle_diff(a1, a2) * alpha

    return ((cx, cy), (w, h), a)


def ema(prev: float, new: float, alpha: float) -> float:
    """Exponenciális mozgóátlag."""
    return prev * (1.0 - alpha) + new * alpha


def clip(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, value))


def safe_hypot(x1: float, y1: float, x2: float, y2: float) -> float:
    try:
        return math.hypot(x2 - x1, y2 - y1)
    except Exception:
        return 0.0