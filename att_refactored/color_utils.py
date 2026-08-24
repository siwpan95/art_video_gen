"""
颜色工具模块 —— 从 pywallpaper 集成
提供动态颜色生成：HSV 流动、能量映射、彩虹色、通用数学工具
"""

import math


# ==================== HSV → RGB ====================
def hsv_to_rgb(h: float, s: float, v: float):
    """HSV 转 RGB，h/s/v 范围 [0, 1]，返回 (R, G, B) 0-255"""
    h = h * 6.0
    i = int(h)
    f = h - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return (int(r * 255), int(g * 255), int(b * 255))


# ==================== 动态颜色生成 ====================
class DynamicColor:
    """动态颜色生成器集合（静态方法）"""

    @staticmethod
    def hsv_flow(index, total, time, hue_range=(0.0, 0.7), speed=0.1, sat=0.8, val=0.9):
        """HSV 流动渐变：色相在元素间 + 时间上流动"""
        hue_min, hue_max = hue_range
        frac = index / max(total, 1)
        hue = (frac * (hue_max - hue_min) + hue_min + time * speed) % 1.0
        return hsv_to_rgb(hue, sat, val)

    @staticmethod
    def energy_color(energy, hue_offset=0.0):
        """根据音频能量映射颜色（蓝→紫→红）"""
        hue = (0.7 - energy * 0.5 + hue_offset) % 1.0
        saturation = 0.8
        value = 0.3 + energy * 0.7
        return hsv_to_rgb(hue, saturation, value)

    @staticmethod
    def rainbow(time, speed=0.05, sat=0.8, val=0.9):
        """彩虹色：色相随时间循环"""
        hue = (time * speed) % 1.0
        return hsv_to_rgb(hue, sat, val)

    @staticmethod
    def hsv_palette(index, total, time, hue_shift=0.0, sat=0.75, val=0.85):
        """生成完整的 HSV 调色板（index 从 0 到 total-1）"""
        colors = []
        for i in range(total):
            hue = ((i / total) + time * 0.03 + hue_shift) % 1.0
            colors.append(list(hsv_to_rgb(hue, sat, val)))
        return colors


# ==================== 数学工具 ====================
def lerp(a, b, t):
    """线性插值"""
    return a + (b - a) * t


def clamp(value, min_val, max_val):
    """数值钳制"""
    return max(min_val, min(max_val, value))


def smooth_damp(current, target, velocity, smooth_time, max_speed=float('inf'), dt=0.016):
    """平滑阻尼过渡 (Unity-like SmoothDamp)"""
    smooth_time = max(0.0001, smooth_time)
    omega = 2.0 / smooth_time
    x = omega * dt
    exp = 1.0 / (1.0 + x + 0.48 * x * x + 0.235 * x * x * x)
    change = current - target
    max_change = max_speed * smooth_time
    change = clamp(change, -max_change, max_change)
    target_new = current - change
    temp = (velocity + omega * change) * dt
    velocity = (velocity - omega * temp) * exp
    output = target_new + (change + temp) * exp
    if (target_new - current > 0) == (output > target_new):
        output = target_new
        velocity = (output - target_new) / dt
    return output, velocity


def map_range(value, in_min, in_max, out_min, out_max):
    """将值从一个范围映射到另一个范围"""
    if in_max == in_min:
        return out_min
    t = (value - in_min) / (in_max - in_min)
    return out_min + t * (out_max - out_min)


# ==================== 增强音频映射 ====================
def audio_map_value(audio_feature, target_min=0.0, target_max=1.0,
                     response_curve="linear", smoothing=0.0, prev_value=0.0):
    """
    将音频特征值映射到目标范围，支持响应曲线和平滑。

    Args:
        audio_feature: 原始音频特征值 (0~1)
        target_min:    输出最小值
        target_max:    输出最大值
        response_curve: 响应曲线 ("linear", "sqrt", "square", "exp")
        smoothing:      平滑系数 (0=不平滑, 0.9=很平滑)
        prev_value:     上一帧值（用于平滑）

    Returns:
        float: 映射后的值
    """
    # 响应曲线
    v = clamp(audio_feature, 0.0, 1.0)
    if response_curve == "sqrt":
        v = math.sqrt(v)
    elif response_curve == "square":
        v = v * v
    elif response_curve == "exp":
        v = math.exp(v * 2.0 - 2.0)  # 平滑的指数曲线

    # 范围映射
    result = target_min + v * (target_max - target_min)

    # 平滑
    if smoothing > 0:
        result = prev_value * smoothing + result * (1.0 - smoothing)

    return result
