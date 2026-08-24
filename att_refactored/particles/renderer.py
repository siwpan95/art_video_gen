"""
粒子渲染器 — 直接渲染到 numpy 数组（OpenCV BGR 格式）
适配当前项目的 cv2.VideoWriter 管道。
"""

import math
import numpy as np


# ================================================================
#  拖尾曲线辅助（Catmull-Rom 平滑）
# ================================================================

def _catmull_rom_points(points: list, num_segments: int = 4) -> list:
    if len(points) < 2:
        return [(int(p[0]), int(p[1])) for p in points]
    result = []
    pts = [points[0]] + list(points) + [points[-1]]
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i-1], pts[i], pts[i+1], pts[i+2]
        for j in range(num_segments):
            t = j / num_segments
            t2 = t * t
            t3 = t2 * t
            f0 = -0.5*t3 + t2 - 0.5*t
            f1 =  1.5*t3 - 2.5*t2 + 1.0
            f2 = -1.5*t3 + 2.0*t2 + 0.5*t
            f3 =  0.5*t3 - 0.5*t2
            x = f0*p0[0] + f1*p1[0] + f2*p2[0] + f3*p3[0]
            y = f0*p0[1] + f1*p1[1] + f2*p2[1] + f3*p3[1]
            result.append((int(x), int(y)))
    result.append((int(points[-1][0]), int(points[-1][1])))
    return result


# ================================================================
#  将粒子系统渲染到 numpy 帧（BGR 格式，供 cv2 使用）
# ================================================================

def render_particles_to_frame(frame: np.ndarray, particles: list,
                                  blend_mode: str = 'normal',
                                  smooth_trail: bool = True,
                                  trail_segments: int = 4,
                                  glow_radius: int = 0):
    """
    将粒子系统渲染到视频帧（numpy BGR 数组）。

    Args:
        frame        : (h, w, 3) uint8 BGR numpy 数组（由 cv2 使用）
        particles    : Particle 对象列表（particles.particle_core.Particle）
        blend_mode   : 'normal' | 'additive' | 'screen'
        smooth_trail : 是否用 Catmull-Rom 平滑拖尾
        trail_segments: 拖尾平滑细分数
        glow_radius   : 光晕半径（0 = 不绘制）

    Returns:
        修改后的 frame（原地修改，也返回引用）
    """
    h, w = frame.shape[:2]

    if blend_mode == 'normal':
        _render_normal(frame, particles, h, w,
                       smooth_trail, trail_segments, glow_radius)
    else:
        _render_blended(frame, particles, h, w, blend_mode,
                          smooth_trail, trail_segments, glow_radius)
    return frame


def _render_normal(frame, particles, h, w,
                     smooth_trail, trail_segments, glow_radius):
    """标准 alpha 混合渲染（原地修改 frame）"""
    for p in particles:
        if not p.is_alive():
            continue
        x, y = int(p.x), int(p.y)
        alpha = max(0.0, min(1.0, p.alpha))

        # 光晕
        if glow_radius > 0 and alpha > 0.01:
            gr = max(1, int(p.size * alpha) + glow_radius)
            _draw_circle_aa(frame, x, y, gr, p.color, alpha * 0.2, h, w)

        # 粒子主体
        sz = max(1, int(p.size * alpha))
        if sz > 0 and 0 <= x < w and 0 <= y < h:
            _draw_circle_aa(frame, x, y, sz, p.color, alpha, h, w)

        # 拖尾
        if p.trail_enabled and len(p.trail_history) >= 2:
            _render_trail(frame, p, h, w, smooth_trail, trail_segments)


def _render_blended(frame, particles, h, w,
                      blend_mode, smooth_trail, trail_segments, glow_radius):
    """Additive / Screen 混合渲染（使用 float32 中间层）"""
    # 创建 float32 中间层
    layer = np.zeros((h, w, 3), dtype=np.float32)

    for p in particles:
        if not p.is_alive():
            continue
        x, y = int(p.x), int(p.y)
        alpha_val = max(0.0, min(1.0, p.alpha))
        r = int(p.color[0] * alpha_val)
        g = int(p.color[1] * alpha_val)
        b = int(p.color[2] * alpha_val)
        sz = max(1, int(p.size * alpha_val))

        # 光晕
        if glow_radius > 0:
            gsz = sz + glow_radius
            ga = alpha_val * 0.3
            _draw_circle_aa_float(layer, x, y, gsz, (r, g, b), ga, h, w)

        # 粒子
        _draw_circle_aa_float(layer, x, y, sz, (r, g, b), alpha_val, h, w)

        # 拖尾
        if p.trail_enabled and len(p.trail_history) >= 2:
            _render_trail_float(layer, p, h, w, smooth_trail, trail_segments, alpha_val)

    # 混合到原帧
    base_f = frame.astype(np.float32)
    if blend_mode == 'additive':
        result = np.clip(base_f + layer, 0, 255)
    else:  # screen
        base_n = base_f / 255.0
        layer_n = np.clip(layer / 255.0, 0, 1)
        result = (1.0 - (1.0 - base_n) * (1.0 - layer_n)) * 255.0
        result = np.clip(result, 0, 255)
    frame[:, :] = result.astype(np.uint8)


def _draw_circle_aa(frame, cx, cy, r, color_rgb, alpha, h, w):
    """在 BGR frame 上绘制抗锯齿圆盘（原地修改）"""
    # color_rgb → BGR
    cr, cg, cb = color_rgb[0], color_rgb[1], color_rgb[2]
    b, g, r = cb, cg, cr

    x0 = max(0, cx - r - 1)
    x1 = min(w, cx + r + 2)
    y0 = max(0, cy - r - 1)
    y1 = min(h, cy + r + 2)

    for py in range(y0, y1):
        for px in range(x0, x1):
            dist = math.sqrt((px - cx)**2 + (py - cy)**2)
            if dist <= r * 0.8:
                # 中心完全不透明
                frame[py, px, 0] = int(b * alpha + frame[py, px, 0] * (1 - alpha))
                frame[py, px, 1] = int(g * alpha + frame[py, px, 1] * (1 - alpha))
                frame[py, px, 2] = int(r * alpha + frame[py, px, 2] * (1 - alpha))
            elif dist <= r:
                # 边缘抗锯齿
                edge_alpha = alpha * (1.0 - (dist - r * 0.8) / (r * 0.2))
                edge_alpha = max(0.0, min(1.0, edge_alpha))
                frame[py, px, 0] = int(b * edge_alpha + frame[py, px, 0] * (1 - edge_alpha))
                frame[py, px, 1] = int(g * edge_alpha + frame[py, px, 1] * (1 - edge_alpha))
                frame[py, px, 2] = int(r * edge_alpha + frame[py, px, 2] * (1 - edge_alpha))


def _draw_circle_aa_float(layer, cx, cy, r, color_rgb, alpha, h, w):
    """在 float32 layer 上绘制圆盘"""
    cr, cg, cb = color_rgb[0], color_rgb[1], color_rgb[2]

    x0 = max(0, cx - r - 1)
    x1 = min(w, cx + r + 2)
    y0 = max(0, cy - r - 1)
    y1 = min(h, cy + r + 2)

    for py in range(y0, y1):
        for px in range(x0, x1):
            dist = math.sqrt((px - cx)**2 + (py - cy)**2)
            if dist <= r:
                a = alpha * max(0.0, 1.0 - dist / r)
                layer[py, px, 0] += cr * a
                layer[py, px, 1] += cg * a
                layer[py, px, 2] += cb * a


def _render_trail(frame, p, h, w, smooth_trail, trail_segments):
    """渲染拖尾到 BGR frame（原地修改）"""
    points = p.get_trail_points()
    if len(points) < 2:
        return
    if smooth_trail and len(points) >= 3:
        pts = _catmull_rom_points(points, trail_segments)
    else:
        pts = [(int(pt[0]), int(pt[1])) for pt in points]

    n = len(pts)
    cr, cg, cb = p.color[0], p.color[1], p.color[2]
    for i in range(n - 1):
        t = i / max(n - 1, 1)
        trail_alpha = (t ** 0.7) * p.alpha
        r = int(cr * trail_alpha)
        g = int(cg * trail_alpha)
        b = int(cb * trail_alpha)
        x0, y0 = pts[i]
        x1, y1 = pts[i+1]
        _draw_line_aa(frame, x0, y0, x1, y1, (b, g, r), trail_alpha, h, w)


def _render_trail_float(layer, p, h, w, smooth_trail, trail_segments, alpha_val):
    """渲染拖尾到 float32 layer"""
    points = p.get_trail_points()
    if len(points) < 2:
        return
    if smooth_trail and len(points) >= 3:
        pts = _catmull_rom_points(points, trail_segments)
    else:
        pts = [(int(pt[0]), int(pt[1])) for pt in points]

    n = len(pts)
    cr, cg, cb = p.color[0], p.color[1], p.color[2]
    for i in range(n - 1):
        t = i / max(n - 1, 1)
        a = (t ** 0.7) * alpha_val
        x0, y0 = pts[i]
        x1, y1 = pts[i+1]
        _draw_line_float(layer, x0, y0, x1, y1, (cr, cg, cb), a, h, w)


def _draw_line_aa(frame, x0, y0, x1, y1, color_bgr, alpha, h, w):
    """绘制抗锯齿线段（BGR frame，原地修改）"""
    b, g, r = color_bgr
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        if 0 <= x0 < w and 0 <= y0 < h:
            frame[y0, x0, 0] = int(b * alpha + frame[y0, x0, 0] * (1 - alpha))
            frame[y0, x0, 1] = int(g * alpha + frame[y0, x0, 1] * (1 - alpha))
            frame[y0, x0, 2] = int(r * alpha + frame[y0, x0, 2] * (1 - alpha))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def _draw_line_float(layer, x0, y0, x1, y1, color_rgb, alpha, h, w):
    """绘制线段到 float32 layer"""
    cr, cg, cb = color_rgb
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        if 0 <= x0 < w and 0 <= y0 < h:
            layer[y0, x0, 0] += cr * alpha
            layer[y0, x0, 1] += cg * alpha
            layer[y0, x0, 2] += cb * alpha
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


# ================================================================
#  Bloom 后处理（直接操作 numpy 数组）
# ================================================================

def apply_bloom(frame: np.ndarray, radius: int = 12,
                  strength: float = 0.5, threshold: int = 160) -> np.ndarray:
    """
    对视频帧做 Bloom 辉光后处理。

    Args:
        frame     : (h, w, 3) uint8 BGR numpy 数组
        radius    : 高斯模糊半径
        strength  : 亮部提取强度
        threshold : 亮部阈值

    Returns:
        处理后的新帧（不修改原帧）
    """
    try:
        import cv2
        # 提取亮部
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, bright_mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        bright = cv2.bitwise_and(frame, frame, mask=bright_mask)
        # 高斯模糊
        blurred = cv2.GaussianBlur(bright, (0, 0), radius)
        # Screen blend
        result = cv2.addWeighted(frame, 1.0, blurred, strength, 0)
        return result
    except ImportError:
        return frame
