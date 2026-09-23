"""Small SVG geometry helpers shared by the logo and the curriculum tree."""
from __future__ import annotations

import math

Point = tuple[float, float]


def bez(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    u = 1 - t
    return (
        u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
        u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
    )


def bez_tan(p0: Point, p1: Point, p2: Point, p3: Point, t: float) -> Point:
    u = 1 - t
    dx = 3 * u * u * (p1[0] - p0[0]) + 6 * u * t * (p2[0] - p1[0]) + 3 * t * t * (p3[0] - p2[0])
    dy = 3 * u * u * (p1[1] - p0[1]) + 6 * u * t * (p2[1] - p1[1]) + 3 * t * t * (p3[1] - p2[1])
    n = math.hypot(dx, dy) or 1.0
    return dx / n, dy / n


def tapered(p0: Point, p1: Point, p2: Point, p3: Point, w0: float, w1: float,
            n: int = 36, ease: float = 1.0, shift: float = 0.0) -> str:
    """
    Filled outline of a cubic curve whose thickness goes w0 -> w1.
    `shift` slides the ribbon sideways (used for highlight strips).
    """
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        x, y = bez(p0, p1, p2, p3, t)
        tx, ty = bez_tan(p0, p1, p2, p3, t)
        nx, ny = -ty, tx
        w = (w0 + (w1 - w0) * (t ** ease)) / 2
        x += nx * shift
        y += ny * shift
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    pts = left + right[::-1]
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"


def stroke_d(p0: Point, p1: Point, p2: Point, p3: Point) -> str:
    return (f"M{p0[0]:.1f} {p0[1]:.1f}C{p1[0]:.1f} {p1[1]:.1f} "
            f"{p2[0]:.1f} {p2[1]:.1f} {p3[0]:.1f} {p3[1]:.1f}")


def leaf_d(length: float, width: float) -> str:
    """Pointed leaf with its base at (0,0) and its tip at (0,-length)."""
    l, w = length, width / 2 * 1.33
    return (f"M0 0C{w:.1f} {-l * 0.2:.1f} {w:.1f} {-l * 0.68:.1f} 0 {-l:.1f}"
            f"C{-w:.1f} {-l * 0.68:.1f} {-w:.1f} {-l * 0.2:.1f} 0 0Z")


def leaf_veins(length: float, width: float) -> str:
    l, w = length, width / 2
    d = f"M0 {-l * 0.07:.1f}L0 {-l * 0.88:.1f}"
    for f in (0.3, 0.5, 0.68):
        d += f"M0 {-l * f:.1f}L{w * 0.62:.1f} {-l * (f + 0.15):.1f}"
        d += f"M0 {-l * f:.1f}L{-w * 0.62:.1f} {-l * (f + 0.15):.1f}"
    return d


def angle_of(vx: float, vy: float) -> float:
    """Rotation (deg) that turns an 'up' pointing leaf toward vector (vx, vy)."""
    return math.degrees(math.atan2(vx, -vy))


def rotate(vx: float, vy: float, deg: float) -> Point:
    a = math.radians(deg)
    return vx * math.cos(a) - vy * math.sin(a), vx * math.sin(a) + vy * math.cos(a)
