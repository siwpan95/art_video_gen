"""
粒子系统核心模块 v3.0 — 全功能增强版
从 D:/allin/tools/particle 复制并适配到当前项目
禁止跨项目调用，所有代码自包含。
"""

import numpy as np
import random
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable, Dict, Any


# ================================================================
#  曲线/插值辅助函数
# ================================================================

def lerp_color(c1: Tuple[int, int, int],
               c2: Tuple[int, int, int],
               t: float) -> Tuple[int, int, int]:
    """颜色线性插值 (t: 0~1)"""
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def evaluate_curve(curve: List[Tuple[float, float]], t: float) -> float:
    """计算曲线在 t 处的值（线性插值）"""
    if not curve:
        return 1.0
    if len(curve) == 1:
        return curve[0][1]
    if t <= curve[0][0]:
        return curve[0][1]
    if t >= curve[-1][0]:
        return curve[-1][1]
    for i in range(len(curve) - 1):
        t0, v0 = curve[i]
        t1, v1 = curve[i + 1]
        if t0 <= t <= t1:
            s = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return v0 + (v1 - v0) * s
    return curve[-1][1]


def evaluate_color_curve(curve: List[Tuple[float, Tuple[int, int, int]]],
                         t: float) -> Tuple[int, int, int]:
    """计算颜色曲线在 t 处的值"""
    if not curve:
        return (255, 255, 255)
    if len(curve) == 1:
        return curve[0][1]
    if t <= curve[0][0]:
        return curve[0][1]
    if t >= curve[-1][0]:
        return curve[-1][1]
    for i in range(len(curve) - 1):
        t0, c0 = curve[i]
        t1, c1 = curve[i + 1]
        if t0 <= t <= t1:
            s = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return lerp_color(c0, c1, s)
    return curve[-1][1]


def evaluate_curve_vel(curve: List[Tuple[float, Tuple[float, float]]],
                       t: float) -> Tuple[float, float]:
    """计算速度倍率曲线在 t 处的值"""
    if not curve:
        return (1.0, 1.0)
    if len(curve) == 1:
        return curve[0][1]
    if t <= curve[0][0]:
        return curve[0][1]
    if t >= curve[-1][0]:
        return curve[-1][1]
    for i in range(len(curve) - 1):
        t0, v0 = curve[i]
        t1, v1 = curve[i + 1]
        if t0 <= t <= t1:
            s = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return (v0[0] + (v1[0] - v0[0]) * s,
                    v0[1] + (v1[1] - v0[1]) * s)
    return curve[-1][1]


# ================================================================
#  发射形状模块（Shape Module）
# ================================================================

@dataclass
class EmitterShape:
    """
    发射器形状 — 控制粒子的初始位置和发射方向
    支持的形状：
    - point      : 点发射（默认）
    - sphere     : 球形表面或体内发射
    - cone       : 锥形发射
    - circle     : 圆形边缘或面内发射
    - rectangle  : 矩形区域内发射
    - edge       : 边缘线段发射
    """
    shape_type: str = 'point'  # point | sphere | cone | circle | rectangle | edge

    # --- 形状参数 ---
    radius: float = 10.0
    height: float = 20.0
    width: float = 40.0
    rect_height: float = 30.0
    edge_length: float = 30.0
    edge_angle: float = 0.0

    # --- 控制参数 ---
    emit_from_shell: bool = False
    emit_from_volume: bool = True
    randomize_direction: bool = True

    def sample_position(self, base_x: float, base_y: float,
                        speed: float, spread: float) -> Tuple[float, float, float, float]:
        handlers = {
            'point': self._sample_point,
            'sphere': self._sample_sphere,
            'cone': self._sample_cone,
            'circle': self._sample_circle,
            'rectangle': self._sample_rectangle,
            'edge': self._sample_edge,
        }
        handler = handlers.get(self.shape_type, self._sample_point)
        return handler(base_x, base_y, speed, spread)

    def _sample_point(self, bx, by, speed, spread):
        angle = random.uniform(-spread, spread)
        vx = speed * math.cos(angle)
        vy = speed * math.sin(angle)
        return bx, by, vx, vy

    def _sample_sphere(self, bx, by, speed, spread):
        r = self.radius
        if self.emit_from_shell:
            angle_2d = random.uniform(0, 2 * math.pi)
            px = bx + r * math.cos(angle_2d)
            py = by + r * math.sin(angle_2d)
        else:
            angle_2d = random.uniform(0, 2 * math.pi)
            dist = r * math.sqrt(random.uniform(0, 1))
            px = bx + dist * math.cos(angle_2d)
            py = by + dist * math.sin(angle_2d)
        dx = px - bx
        dy = py - by
        dist = math.sqrt(dx*dx + dy*dy) if (dx*dx + dy*dy) > 1e-6 else 1.0
        if self.randomize_direction:
            base_angle = math.atan2(dy, dx)
            angle = base_angle + random.uniform(-spread, spread)
        else:
            angle = random.uniform(-spread, spread)
        vx = speed * math.cos(angle)
        vy = speed * math.sin(angle)
        return px, py, vx, vy

    def _sample_cone(self, bx, by, speed, spread):
        r_at_base = self.radius
        h = self.height
        cone_angle = random.uniform(0, 2 * math.pi)
        r_sample = r_at_base * math.sqrt(random.uniform(0, 1))
        px = bx + r_sample * math.cos(cone_angle)
        py = by + h
        dx = px - bx
        dy = py - by
        dist = math.sqrt(dx*dx + dy*dy) if (dx*dx + dy*dy) > 1e-6 else 1.0
        if self.randomize_direction:
            base_angle = math.atan2(dy, dx)
            angle = base_angle + random.uniform(-spread * 0.5, spread * 0.5)
        else:
            angle = math.pi / 2 + random.uniform(-spread, spread)
        vx = speed * math.cos(angle)
        vy = speed * math.sin(angle)
        return px, py, vx, vy

    def _sample_circle(self, bx, by, speed, spread):
        r = self.radius
        if self.emit_from_shell:
            angle_2d = random.uniform(0, 2 * math.pi)
            px = bx + r * math.cos(angle_2d)
            py = by + r * math.sin(angle_2d)
        else:
            angle_2d = random.uniform(0, 2 * math.pi)
            dist = r * math.sqrt(random.uniform(0, 1))
            px = bx + dist * math.cos(angle_2d)
            py = by + dist * math.sin(angle_2d)
        if self.randomize_direction:
            base_angle = random.uniform(0, 2 * math.pi)
            angle = base_angle + random.uniform(-spread, spread)
        else:
            angle = random.uniform(-spread, spread)
        vx = speed * math.cos(angle)
        vy = speed * math.sin(angle)
        return px, py, vx, vy

    def _sample_rectangle(self, bx, by, speed, spread):
        hw = self.width / 2
        hh = self.rect_height / 2
        px = bx + random.uniform(-hw, hw)
        py = by + random.uniform(-hh, hh)
        angle = random.uniform(-spread, spread)
        vx = speed * math.cos(angle)
        vy = speed * math.sin(angle)
        return px, py, vx, vy

    def _sample_edge(self, bx, by, speed, spread):
        half_len = self.edge_length / 2
        cos_a = math.cos(self.edge_angle)
        sin_a = math.sin(self.edge_angle)
        offset = random.uniform(-half_len, half_len)
        px = bx + offset * cos_a
        py = by + offset * sin_a
        angle = random.uniform(-spread, spread)
        vx = speed * math.cos(angle)
        vy = speed * math.sin(angle)
        return px, py, vx, vy


# ================================================================
#  Particle  — 单个粒子（v3.0 全功能版）
# ================================================================

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    color: Tuple[int, int, int]
    alpha: float = 1.0
    rotation: float = 0.0
    angular_velocity: float = 0.0
    mass: float = 1.0
    color_over_lifetime: Optional[List[Tuple[float, Tuple[int, int, int]]]] = None
    size_over_lifetime: Optional[List[Tuple[float, float]]] = None
    velocity_over_lifetime: Optional[List[Tuple[float, Tuple[float, float]]]] = None
    trail_enabled: bool = False
    trail_history: List[Tuple[float, float]] = field(default_factory=list)
    trail_max_length: int = 10

    def is_alive(self) -> bool:
        return self.life > 0.0

    def update(self, dt: float):
        if self.velocity_over_lifetime:
            t = max(0.0, min(1.0, 1.0 - self.life / self.max_life))
            vx_mult, vy_mult = evaluate_curve_vel(self.velocity_over_lifetime, t)
            self.vx *= (0.95 + 0.05 * vx_mult)
            self.vy *= (0.95 + 0.05 * vy_mult)
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.trail_enabled and self.trail_max_length > 0:
            self.trail_history.append((self.x, self.y))
            if len(self.trail_history) > self.trail_max_length:
                self.trail_history.pop(0)
        self.rotation += self.angular_velocity * dt
        self.life -= dt / self.max_life
        if self.color_over_lifetime:
            t = max(0.0, min(1.0, 1.0 - self.life / self.max_life))
            self.color = evaluate_color_curve(self.color_over_lifetime, t)
        if self.size_over_lifetime:
            t = max(0.0, min(1.0, 1.0 - self.life / self.max_life))
            self.size = evaluate_curve(self.size_over_lifetime, t)
        self.alpha = max(0.0, self.life)

    def enable_trail(self, length: int = 10):
        self.trail_enabled = True
        self.trail_max_length = length
        self.trail_history = [(self.x, self.y)]

    def get_trail_points(self) -> List[Tuple[float, float]]:
        points = list(self.trail_history)
        points.append((self.x, self.y))
        return points


# ================================================================
#  力场（增强版）
# ================================================================

class ForceField:
    def __init__(self, field_type: str = 'gravity',
                 x: float = 0.0, y: float = 0.0,
                 strength: float = 1.0,
                 noise_scale: float = 50.0,
                 noise_strength: float = 1.0,
                 noise_octaves: int = 2,
                 vortex_clockwise: bool = True,
                 vortex_falloff: float = 0.01,
                 turb_scale: float = 30.0,
                 turb_strength: float = 2.0,
                 magnet_polarity: float = 1.0,
                 magnet_range: float = 200.0,
                 ):
        self.field_type = field_type
        self.x = x
        self.y = y
        self.strength = strength
        self.noise_scale = noise_scale
        self.noise_strength = noise_strength
        self.noise_octaves = noise_octaves
        self.vortex_clockwise = vortex_clockwise
        self.vortex_falloff = vortex_falloff
        self.turb_scale = turb_scale
        self.turb_strength = turb_strength
        self.magnet_polarity = magnet_polarity
        self.magnet_range = magnet_range
        self._noise_time_offset = random.uniform(0, 1000)

    def get_force(self, px: float, py: float, time: float = 0.0) -> Tuple[float, float]:
        handlers = {
            'gravity': self._force_gravity,
            'wind': self._force_wind,
            'attraction': self._force_attraction,
            'noise': self._force_noise,
            'vortex': self._force_vortex,
            'turbulence': self._force_turbulence,
            'magnet': self._force_magnet,
        }
        handler = handlers.get(self.field_type)
        if handler:
            return handler(px, py, time)
        return (0.0, 0.0)

    def _force_gravity(self, px, py, t):
        return (0.0, self.strength)

    def _force_wind(self, px, py, t):
        return (self.strength, 0.0)

    def _force_attraction(self, px, py, t):
        dx = self.x - px
        dy = self.y - py
        dist_sq = dx * dx + dy * dy
        if dist_sq < 1e-6:
            return (0.0, 0.0)
        dist = math.sqrt(dist_sq)
        force_mag = self.strength / (1.0 + dist * 0.01)
        return (force_mag * dx / dist, force_mag * dy / dist)

    def _force_noise(self, px, py, t):
        sx = self.noise_scale
        t_val = t + self._noise_time_offset
        fx_total, fy_total = 0.0, 0.0
        for octave in range(max(1, self.noise_octaves)):
            freq = 2.0 ** octave / sx
            amp = self.noise_strength / (2.0 ** octave)
            nx = px * freq + t_val * 0.5 + octave * 10.0
            ny = py * freq + t_val * 0.3 + octave * 7.0
            fx_total += amp * math.sin(nx) * math.cos(ny * 0.7)
            fy_total += amp * math.cos(ny) * math.sin(nx * 0.7)
        return (fx_total, fy_total)

    def _force_vortex(self, px, py, t):
        dx = px - self.x
        dy = py - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1e-6:
            return (0.0, 0.0)
        direction = 1.0 if self.vortex_clockwise else -1.0
        tx = -dy / dist
        ty = dx / dist
        falloff = math.exp(-dist * self.vortex_falloff)
        mag = self.strength * falloff * direction
        return (mag * tx, mag * ty)

    def _force_turbulence(self, px, py, t):
        sx = self.turb_scale
        t_val = t + self._noise_time_offset * 1.7
        fx, fy = 0.0, 0.0
        for i in range(3):
            freq = (3.0 + i * 2.0) / sx
            amp = self.turb_strength / (1.5 ** i)
            phase = t_val * (2.0 + i) + i * 13.37
            fx += amp * math.sin(px * freq * (1 + i * 0.3) + phase)
            fy += amp * math.cos(py * freq * (1 + i * 0.4) + phase * 1.3)
            fx += amp * 0.5 * math.cos(py * freq * 0.7 + phase * 0.9)
            fy += amp * 0.5 * math.sin(px * freq * 0.8 + phase * 1.1)
        return (fx, fy)

    def _force_magnet(self, px, py, t):
        dx = self.x - px
        dy = self.y - py
        dist_sq = dx * dx + dy * dy
        dist = math.sqrt(dist_sq)
        if dist < 1e-6 or dist > self.magnet_range:
            return (0.0, 0.0)
        direction = self.magnet_polarity
        range_factor = 1.0 - (dist / self.magnet_range)
        force_mag = self.strength * direction * range_factor / (1.0 + dist_sq * 0.0001)
        return (force_mag * dx / dist, force_mag * dy / dist)

    def set_position(self, x: float, y: float):
        self.x = x
        self.y = y


# ================================================================
#  Emitter  — 粒子发射器
# ================================================================

class Emitter:
    def __init__(self,
                 x: float, y: float,
                 rate: float = 10.0,
                 spread: float = 0.5,
                 direction: float = 0.0,
                 speed: float = 1.0,
                 life: float = 1.0,
                 size: float = 1.0,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 rotation_range: Tuple[float, float] = (0.0, 0.0),
                 angular_velocity_range: Tuple[float, float] = (0.0, 0.0),
                 mass_range: Tuple[float, float] = (1.0, 1.0),
                 color_over_lifetime=None,
                 size_over_lifetime=None,
                 velocity_over_lifetime=None,
                 shape: Optional[EmitterShape] = None,
                 trail_enabled: bool = False,
                 trail_length: int = 8,
                 ):
        self.x = x
        self.y = y
        self.rate = rate
        self.spread = spread
        self.direction = direction
        self.speed = speed
        self.life = life
        self.size = size
        self.color = color
        self.rotation_range = rotation_range
        self.angular_velocity_range = angular_velocity_range
        self.mass_range = mass_range
        self.color_over_lifetime = color_over_lifetime
        self.size_over_lifetime = size_over_lifetime
        self.velocity_over_lifetime = velocity_over_lifetime
        self.shape = shape or EmitterShape('point')
        self.trail_enabled = trail_enabled
        self.trail_length = trail_length
        self.accumulated_time = 0.0

    def emit(self, dt: float,
             audio_data: Optional[dict] = None,
             current_time: float = 0.0) -> List[Particle]:
        self.accumulated_time += dt
        current_rate = self.rate
        if audio_data:
            energy = audio_data.get('rms', 1.0)
            current_rate *= (1.0 + energy * 2.0)

        num_to_emit = int(self.accumulated_time * current_rate)
        self.accumulated_time -= num_to_emit / current_rate if current_rate > 0 else 0.0

        new_particles = []
        for _ in range(num_to_emit):
            px, py, vx, vy = self.shape.sample_position(
                self.x, self.y, self.speed, self.spread
            )
            if self.direction != 0.0:
                cos_a = math.cos(self.direction)
                sin_a = math.sin(self.direction)
                vx, vy = vx * cos_a - vy * sin_a, vx * sin_a + vy * cos_a

            rotation = random.uniform(*self.rotation_range)
            angular_velocity = random.uniform(*self.angular_velocity_range)
            mass = random.uniform(*self.mass_range)

            p = Particle(
                x=px, y=py,
                vx=vx, vy=vy,
                life=1.0, max_life=self.life,
                size=self.size, color=self.color,
                alpha=1.0,
                rotation=rotation, angular_velocity=angular_velocity,
                mass=mass,
                color_over_lifetime=self.color_over_lifetime,
                size_over_lifetime=self.size_over_lifetime,
                velocity_over_lifetime=self.velocity_over_lifetime,
            )
            if self.trail_enabled:
                p.enable_trail(self.trail_length)
            new_particles.append(p)
        return new_particles

    def set_position(self, x: float, y: float):
        self.x = x
        self.y = y


# ================================================================
#  ParticleSystem  — 粒子系统管理器
# ================================================================

class ParticleSystem:
    def __init__(self, max_particles: int = 1000):
        self.max_particles = max_particles
        self.particles: List[Particle] = []
        self.emitters: List[Emitter] = []
        self.force_fields: List[ForceField] = []
        self._time = 0.0

    def add_emitter(self, emitter: Emitter):
        self.emitters.append(emitter)

    def add_force_field(self, force_field: ForceField):
        self.force_fields.append(force_field)

    def update(self, dt: float, audio_data: Optional[dict] = None):
        self._time += dt
        for emitter in self.emitters:
            new_particles = emitter.emit(dt, audio_data, self._time)
            for p in new_particles:
                if len(self.particles) < self.max_particles:
                    self.particles.append(p)

        alive_particles = []
        for p in self.particles:
            if not p.is_alive():
                continue
            for ff in self.force_fields:
                fx, fy = ff.get_force(p.x, p.y, self._time)
                p.vx += (fx / p.mass) * dt
                p.vy += (fy / p.mass) * dt
            p.update(dt)
            if p.is_alive():
                alive_particles.append(p)
        self.particles = alive_particles

    def clear(self):
        self.particles.clear()

    def get_particle_count(self) -> int:
        return len(self.particles)

    @property
    def time(self) -> float:
        return self._time


# ================================================================
#  便利预设曲线 / 工厂函数
# ================================================================

def gradient_to_curve(colors: List[Tuple[int, int, int]],
                      num_samples: int = 8) -> List[Tuple[float, Tuple[int, int, int]]]:
    n = len(colors)
    if n == 0:
        return []
    if n == 1:
        return [(0.0, colors[0])]
    curve = []
    for i in range(n - 1):
        t0 = i / (n - 1)
        t1 = (i + 1) / (n - 1)
        curve.append((t0, colors[i]))
        if i < n - 2:
            t_mid = (t0 + t1) / 2
            mid_color = lerp_color(colors[i], colors[i + 1], 0.5)
            curve.append((t_mid, mid_color))
    curve.append((1.0, colors[-1]))
    return curve


def create_fire_emitter(x: float, y: float, rate: float = 50.0) -> Emitter:
    return Emitter(
        x=x, y=y, rate=rate,
        spread=0.3, direction=math.pi/2,  # 向上
        speed=80.0, life=2.0,
        size=3.0, color=(255, 160, 30),
        color_over_lifetime=gradient_to_curve([
            (255, 255, 200), (255, 160, 30), (255, 60, 10), (80, 20, 5)
        ]),
        size_over_lifetime=[(0.0, 4.0), (0.3, 2.0), (1.0, 0.5)],
        trail_enabled=True, trail_length=8,
    )


def create_fireworks_emitters(cx: float, cy: float) -> List[Emitter]:
    """创建烟花效果（爆炸式发射）"""
    emitters = []
    colors = [(255, 200, 50), (50, 150, 255), (255, 50, 150),
               (100, 255, 100), (255, 255, 100)]
    for i in range(5):
        angle = 2 * math.pi * i / 5
        em = Emitter(
            x=cx, y=cy,
            rate=0,  # 手动触发
            spread=0.1, direction=angle,
            speed=150.0 + i * 10, life=1.5 + i * 0.2,
            size=2.5, color=colors[i],
            color_over_lifetime=gradient_to_curve([
                colors[i], (255, 255, 255), (100, 100, 100)
            ]),
            trail_enabled=True, trail_length=12,
        )
        emitters.append(em)
    return emitters


def create_rain_emitter(w: float, h: float, rate: float = 80.0) -> Emitter:
    return Emitter(
        x=w/2, y=0,
        rate=rate, spread=1.0,
        direction=math.pi/2,  # 向下
        speed=300.0, life=1.5,
        size=2.0, color=(150, 200, 255),
    )


def create_snow_emitter(w: float, h: float, rate: float = 40.0) -> Emitter:
    return Emitter(
        x=w/2, y=0,
        rate=rate, spread=1.5,
        direction=math.pi/2,
        speed=50.0, life=4.0,
        size=3.0, color=(240, 240, 255),
    )
