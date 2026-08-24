"""
效果原语模块 — 从 pywallpaper/engine/primitives/ 适配
使用 numpy 直接渲染（兼容 OpenCV），杜绝跨项目调用。
"""

import math
import random
import numpy as np


# ================================================================
#  工具函数
# ================================================================

def _apply_color(index, total, energy, palette_colors):
    """从调色板获取颜色（音频驱动）"""
    if palette_colors is None:
        return (255, 255, 255)
    ci = int((index / total + energy * 0.5) * len(palette_colors)) % len(palette_colors)
    return tuple(palette_colors[ci].tolist())


def _draw_rect_bgr(frame, x, y, w, h, color):
    """在 BGR 帧上绘制矩形（in-place）"""
    h_f, w_f = frame.shape[:2]
    x0 = max(0, int(x))
    y0 = max(0, int(y))
    x1 = min(w_f, int(x + w))
    y1 = min(h_f, int(y + h))
    if x0 < x1 and y0 < y1:
        frame[y0:y1, x0:x1] = color[::-1]  # RGB → BGR


def _draw_circle_bgr(frame, cx, cy, r, color):
    """在 BGR 帧上绘制圆形（in-place，简单版本）"""
    h_f, w_f = frame.shape[:2]
    r_int = max(1, int(r))
    for dy in range(-r_int, r_int + 1):
        for dx in range(-r_int, r_int + 1):
            if dx * dx + dy * dy <= r_int * r_int:
                px = int(cx) + dx
                py = int(cy) + dy
                if 0 <= px < w_f and 0 <= py < h_f:
                    frame[py, px] = color[::-1]  # RGB → BGR


def _draw_line_bgr(frame, x0, y0, x1, y1, color, width=1):
    """在 BGR 帧上绘制线段（Bresenham 简化版）"""
    h_f, w_f = frame.shape[:2]
    color_bgr = color[::-1]  # RGB → BGR
    
    # 使用 cv2 如果可用
    try:
        import cv2
        cv2.line(frame, (int(x0), int(y0)), (int(x1), int(y1)), color_bgr, width)
    except ImportError:
        # 降级：简单 Bresenham
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            if 0 <= x0 < w_f and 0 <= y0 < h_f:
                frame[y0, x0] = color_bgr
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
#  BarsPrimitive — 频谱柱形图
# ================================================================

class BarsEffect:
    """频谱柱形图效果（适配 numpy BGR 数组）。
    
    配置：
        count: int          柱数（默认 64）
        direction: str      'up'/'down'/'left'/'right'/'center_v'/'center_h'
        gap: int           柱间距（默认 2）
        round_caps: bool   圆角（默认 False）
    """

    def __init__(self, w, h, config=None):
        config = config or {}
        self.w = w
        self.h = h
        self.count = config.get('count', 64)
        self.direction = config.get('direction', 'up')
        self.gap = config.get('gap', 2)
        self.round_caps = config.get('round_caps', False)

    def render(self, frame, audio_features, palette_colors, time_val=0):
        """渲染一帧。
        
        Args:
            frame: (h, w, 3) uint8 BGR numpy 数组
            audio_features: 音频特征字典（包含 spectrum, volume, bass 等）
            palette_colors: 调色板颜色数组
            time_val: 时间值（用于动画）
        """
        n = self.count
        
        if self.direction in ('up', 'down', 'center_v'):
            bar_w = max(1, self.w / n - self.gap)
            for i in range(n):
                # 获取音频能量（使用 spectrum）
                if audio_features and 'spectrum' in audio_features:
                    spectrum = audio_features['spectrum']
                    energy = spectrum[i % len(spectrum)] if i < len(spectrum) else 0.0
                else:
                    energy = 0.5 + 0.5 * math.sin(time_val * 0.1 + i * 0.1)
                
                h_val = energy * self.h
                color = _apply_color(i, n, energy, palette_colors)
                
                if self.direction == 'up':
                    x0 = i * (bar_w + self.gap)
                    y0 = self.h - h_val
                    _draw_rect_bgr(frame, x0, y0, bar_w, h_val, color)
                elif self.direction == 'down':
                    x0 = i * (bar_w + self.gap)
                    y0 = 0
                    _draw_rect_bgr(frame, x0, y0, bar_w, h_val, color)
                elif self.direction == 'center_v':
                    half_h = h_val / 2
                    x0 = i * (bar_w + self.gap)
                    mid_y = self.h / 2
                    _draw_rect_bgr(frame, x0, mid_y - half_h, bar_w, half_h, color)
                    _draw_rect_bgr(frame, x0, mid_y, bar_w, half_h, color)
                    
        else:  # 'left'/'right'/'center_h'
            bar_h = max(1, self.h / n - self.gap)
            for i in range(n):
                if audio_features and 'spectrum' in audio_features:
                    spectrum = audio_features['spectrum']
                    energy = spectrum[i % len(spectrum)] if i < len(spectrum) else 0.0
                else:
                    energy = 0.5 + 0.5 * math.sin(time_val * 0.1 + i * 0.1)
                
                w_val = energy * self.w
                color = _apply_color(i, n, energy, palette_colors)
                
                if self.direction == 'right':
                    y0 = i * (bar_h + self.gap)
                    _draw_rect_bgr(frame, 0, y0, w_val, bar_h, color)
                elif self.direction == 'left':
                    y0 = i * (bar_h + self.gap)
                    _draw_rect_bgr(frame, self.w - w_val, y0, w_val, bar_h, color)
                elif self.direction == 'center_h':
                    half_w = w_val / 2
                    y0 = i * (bar_h + self.gap)
                    mid_x = self.w / 2
                    _draw_rect_bgr(frame, mid_x - half_w, y0, half_w, bar_h, color)
                    _draw_rect_bgr(frame, mid_x, y0, half_w, bar_h, color)


# ================================================================
#  WaveformPrimitive — 波形曲线
# ================================================================

class WaveformEffect:
    """波形曲线效果（适配 numpy BGR 数组）。
    
    配置：
        lines: int          曲线数量（默认 2）
        points: int         每条曲线点数（默认 200）
        amplitude: float    振幅（默认 150）
        frequency: float    空间频率（默认 0.05）
        line_width: int     线宽（默认 2）
    """

    def __init__(self, w, h, config=None):
        config = config or {}
        self.w = w
        self.h = h
        self.line_count = config.get('lines', config.get('count', 2))
        self.points = config.get('points', 200)
        self.amplitude = min(config.get('amplitude', 150), min(w, h) // 2)
        self.frequency = config.get('frequency', 0.05)
        self.line_width = config.get('line_width', 2)

    def render(self, frame, audio_features, palette_colors, time_val=0):
        """渲染一帧波形曲线。"""
        mid_y = self.h / 2
        
        for li in range(self.line_count):
            pts = []
            for i in range(self.points):
                x = (i / (self.points - 1)) * self.w
                
                # 音频驱动：使用 spectrum 或默认正弦波
                if audio_features and 'spectrum' in audio_features:
                    spectrum = audio_features['spectrum']
                    band_idx = int((i / self.points) * len(spectrum))
                    energy = spectrum[band_idx] if band_idx < len(spectrum) else 0.0
                else:
                    energy = 0.5
                
                phase = li * 0.5 + time_val * (2.0 + li)
                y = mid_y + math.sin(i * self.frequency + phase) * (30 + energy * self.amplitude)
                pts.append((x, y))
            
            color = _apply_color(li, self.line_count, 0, palette_colors)
            
            # 绘制曲线
            for pi in range(len(pts) - 1):
                _draw_line_bgr(frame, pts[pi][0], pts[pi][1],
                               pts[pi + 1][0], pts[pi + 1][1],
                               color, self.line_width)


# ================================================================
#  VortexPrimitive — 漩涡/螺旋粒子
# ================================================================

class VortexEffect:
    """漩涡/螺旋粒子效果（适配 numpy BGR 数组）。
    
    配置：
        count: int            粒子数量（默认 150）
        radius_min: float     最小半径（默认 50）
        radius_step: float    半径步进（默认 5）
        twist: float          扭曲度（默认 1.0）
        speed: float          旋转速度（默认 1.0）
        element_size: float   粒子大小（默认 3）
        size_scale: float     粒子大小缩放（默认 5.0）
    """

    def __init__(self, w, h, config=None):
        config = config or {}
        self.w = w
        self.h = h
        self.count = config.get('count', 150)
        self.r_min = min(config.get('radius', {}).get('min', 50), min(w, h) // 3)
        self.r_step = config.get('radius', {}).get('step', 5)
        self.twist = config.get('twist', 1.0)
        self.speed = config.get('speed', 1.0)
        self.elem_size = config.get('element_size', 3)
        self.size_scale = config.get('size_scale', 5.0)
        
        # 中心点
        self.cx = self.w / 2
        self.cy = self.h / 2

    def render(self, frame, audio_features, palette_colors, time_val=0):
        """渲染一帧漩涡效果。"""
        n = self.count
        
        for i in range(n):
            angle = (i / n) * math.pi * 2 * self.twist + time_val * self.speed
            r = self.r_min + (i % 32) * self.r_step + math.sin(time_val * 2 + i) * 20
            
            # 音频驱动
            if audio_features and 'volume' in audio_features:
                energy = audio_features['volume']
                r *= (1.0 + energy * 0.5)
            else:
                energy = 0.5
            
            x = self.cx + math.cos(angle) * r
            y = self.cy + math.sin(angle) * r
            
            color = _apply_color(i, n, energy, palette_colors)
            sz = self.elem_size + energy * self.size_scale
            
            _draw_circle_bgr(frame, x, y, sz, color)


# ================================================================
#  PulsePrimitive — 脉冲/涟漪/声纳
# ================================================================

class PulseEffect:
    """脉冲/涟漪/声纳效果（适配 numpy BGR 数组）。
    
    配置：
        mode: str         'ripple'/'sonar'/'ring_pulse'/'spectrum_ripples'
        max_radius: float  最大扩散半径（默认 400）
        speed: float       扩散速度（默认 2.0）
        count: int         每次创建的脉冲数（默认 1）
        trigger: str       'audio'/'random'/'beat'
        line_width: int    线宽（默认 2）
    """

    def __init__(self, w, h, config=None):
        config = config or {}
        self.w = w
        self.h = h
        self.mode = config.get('mode', 'ripple')
        self.max_radius = min(config.get('max_radius', 400), min(w, h) // 2)
        self.speed = config.get('speed', 2.0)
        self.count = config.get('count', 1)
        self.trigger = config.get('trigger', 'audio')
        self.threshold = config.get('trigger_threshold', 0.3)
        self.line_width = config.get('line_width', 2)
        
        self._pulses = []
        self._timer = 0.0
        self._seeded = False
        
        # 中心点
        self.cx = self.w / 2
        self.cy = self.h / 2

    def _should_fire(self, audio_features, dt):
        """判断是否应该触发新脉冲"""
        self._timer += dt
        
        if audio_features and 'spectrum' in audio_features:
            spectrum = audio_features['spectrum']
            avg_e = sum(spectrum) / len(spectrum) if len(spectrum) > 0 else 0.0
            
            if self.trigger == 'audio' and avg_e > self.threshold:
                return random.random() < avg_e
            elif self.trigger == 'beat':
                bass = sum(spectrum[:4]) / 4 if len(spectrum) >= 4 else 0.0
                if bass > self.threshold and self._timer > 0.1:
                    self._timer = 0.0
                    return True
        
        if self.trigger == 'random' and random.random() < self.threshold * 0.05:
            return True
        
        return False

    def _spawn_pulses(self, audio_features):
        """创建新脉冲"""
        if self.mode == 'ripple':
            for _ in range(self.count):
                self._pulses.append({
                    'x': random.random() * self.w,
                    'y': random.random() * self.h,
                    'radius': 0,
                    'band': random.randint(0, 63),
                })
        elif self.mode == 'sonar':
            for _ in range(self.count):
                self._pulses.append({
                    'radius': 0,
                    'angle': random.uniform(0, math.pi * 2),
                    'band': random.randint(0, 63),
                })
        elif self.mode == 'ring_pulse':
            for _ in range(self.count):
                self._pulses.append({
                    'radius': 0,
                    'band': random.randint(0, 63),
                    'born': 0,  # 简化：不使用 global_time
                })
        elif self.mode == 'spectrum_ripples':
            if audio_features and 'spectrum' in audio_features:
                spectrum = audio_features['spectrum']
                for i in range(min(self.count, len(spectrum))):
                    if spectrum[i] > 0.2:
                        self._pulses.append({'radius': 0, 'band': i})

    def _update_pulses(self):
        """更新所有脉冲"""
        for p in self._pulses[:]:
            p['radius'] += self.speed
            if p['radius'] > self.max_radius:
                self._pulses.remove(p)

    def _seed_initial(self):
        """首次更新时预置脉冲"""
        if self._seeded:
            return
        self._seeded = True
        
        if self.mode in ('ripple', 'spectrum_ripples'):
            for _ in range(max(1, self.count)):
                self._pulses.append({
                    'x': random.random() * self.w,
                    'y': random.random() * self.h,
                    'radius': random.uniform(0, self.max_radius * 0.5),
                    'band': random.randint(0, 63),
                })
        elif self.mode == 'ring_pulse':
            for _ in range(max(1, self.count)):
                self._pulses.append({
                    'radius': random.uniform(0, self.max_radius * 0.5),
                    'band': random.randint(0, 63),
                    'born': 0,
                })
        elif self.mode == 'sonar':
            for _ in range(max(1, self.count)):
                self._pulses.append({
                    'radius': random.uniform(0, self.max_radius * 0.3),
                    'angle': random.uniform(0, math.pi * 2),
                    'band': random.randint(0, 63),
                })

    def render(self, frame, audio_features, palette_colors, time_val=0, dt=0.033):
        """渲染一帧脉冲效果。"""
        # 预置脉冲
        self._seed_initial()
        
        # 触发新脉冲
        if self._should_fire(audio_features, dt):
            self._spawn_pulses(audio_features)
        
        # 更新脉冲
        self._update_pulses()
        
        # 渲染脉冲
        if self.mode == 'sonar':
            # 背景网格圆（简化：只画圆点）
            for r in range(50, int(self.max_radius), 80):
                for i in range(36):
                    a = (i / 36) * math.pi * 2
                    x = self.cx + math.cos(a) * r
                    y = self.cy + math.sin(a) * r
                    if 0 <= int(x) < self.w and 0 <= int(y) < self.h:
                        frame[int(y), int(x)] = (30, 30, 30)  # 深灰色
            
            for p in self._pulses:
                a_ratio = 1 - p['radius'] / self.max_radius
                if a_ratio <= 0:
                    continue
                hue = p['angle'] / (math.pi * 2)
                color = _apply_color(int(hue * 64), 64, 0.5, palette_colors)
                x1 = self.cx + math.cos(p['angle']) * p['radius']
                y1 = self.cy + math.sin(p['angle']) * p['radius']
                x2 = self.cx + math.cos(p['angle'] + 0.1) * p['radius']
                y2 = self.cy + math.sin(p['angle'] + 0.1) * p['radius']
                _draw_line_bgr(frame, x1, y1, x2, y2, color, self.line_width)
                
        elif self.mode == 'ring_pulse':
            for p in self._pulses:
                a_ratio = 1 - p['radius'] / self.max_radius
                if a_ratio <= 0:
                    continue
                hue = (p['band'] / 64 + time_val * 0.05) % 1.0
                color = _apply_color(int(hue * 64), 64, 0.5, palette_colors)
                for i in range(72):
                    ang = (i / 72) * math.pi * 2
                    r = p['radius'] + math.sin(ang * 8 + time_val * 5) * 5
                    x1 = self.cx + math.cos(ang) * r
                    y1 = self.cy + math.sin(ang) * r
                    x2 = self.cx + math.cos(ang + 0.1) * r
                    y2 = self.cy + math.sin(ang + 0.1) * r
                    _draw_line_bgr(frame, x1, y1, x2, y2, color, 1)
                    
        elif self.mode in ('ripple', 'spectrum_ripples'):
            for p in self._pulses:
                a_ratio = 1 - p['radius'] / self.max_radius
                if a_ratio <= 0:
                    continue
                px = p.get('x', self.cx)
                py = p.get('y', self.cy)
                hue = (p['band'] / 64 + time_val * 0.1) % 1.0
                color = _apply_color(int(hue * 64), 64, 0.5, palette_colors)
                for i in range(36):
                    ang = (i / 36) * math.pi * 2
                    r = p['radius'] + math.sin(ang * 5 + time_val * 4) * 5
                    x1 = px + math.cos(ang) * r
                    y1 = py + math.sin(ang) * r
                    x2 = px + math.cos(ang + 0.2) * r
                    y2 = py + math.sin(ang + 0.2) * r
                    _draw_line_bgr(frame, x1, y1, x2, y2, color, self.line_width)


# ================================================================
#  DrawingPrimitive — 自由绘制
# ================================================================

class DrawingEffect:
    """自由绘制效果（命令序列）。
    
    配置：
        commands: list  绘制命令列表
                      每个命令: {'shape': 'circle'/'rect'/'line'/'polygon',
                                 'x': 100, 'y': 100, ...}
    """

    def __init__(self, w, h, config=None):
        config = config or {}
        self.w = w
        self.h = h
        self.commands = config.get('commands', [])
        
        # 简化：只支持基本形状
        self.SUPPORTED_SHAPES = ('circle', 'rect', 'line', 'polygon')

    def render(self, frame, audio_features, palette_colors, time_val=0):
        """执行绘制命令。"""
        for cmd in self.commands:
            shape = cmd.get('shape', 'circle')
            if shape not in self.SUPPORTED_SHAPES:
                continue
            
            # 获取颜色
            color_val = cmd.get('color', [255, 255, 255])
            if isinstance(color_val, dict) and 'audio' in color_val:
                # 音频驱动颜色（简化）
                if audio_features and 'volume' in audio_features:
                    vol = audio_features['volume']
                    color_val = [int(c * vol) for c in color_val.get('default', [255, 255, 255])]
            color = tuple(color_val[:3]) if isinstance(color_val, list) else (255, 255, 255)
            
            if shape == 'circle':
                x = cmd.get('x', self.w // 2)
                y = cmd.get('y', self.h // 2)
                r = cmd.get('radius', 10)
                fill = cmd.get('fill', True)
                if fill:
                    _draw_circle_bgr(frame, x, y, r, color)
                # 简化：outline 暂不实现
                
            elif shape == 'rect':
                x1 = cmd.get('x1', 0)
                y1 = cmd.get('y1', 0)
                x2 = cmd.get('x2', 100)
                y2 = cmd.get('y2', 100)
                fill = cmd.get('fill', True)
                if fill:
                    _draw_rect_bgr(frame, x1, y1, x2 - x1, y2 - y1, color)
                    
            elif shape == 'line':
                x1 = cmd.get('x1', 0)
                y1 = cmd.get('y1', 0)
                x2 = cmd.get('x2', 100)
                y2 = cmd.get('y2', 100)
                width = cmd.get('width', 1)
                _draw_line_bgr(frame, x1, y1, x2, y2, color, width)
                
            # polygon 简化：暂不实现
