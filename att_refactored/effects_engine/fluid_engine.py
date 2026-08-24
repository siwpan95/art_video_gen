"""
流体模拟引擎 — 简化的 Stable Fluids 算法
从 pywallpaper/engine/primitives/fluid.py 复制并适配到当前项目。
禁止跨项目调用，所有代码自包含。
"""

import numpy as np
from PIL import Image


# ================================================================
#  颜色映射
# ================================================================

def _fire_color(v: float) -> tuple:
    """火焰颜色映射 (黑→红→橙→黄→白)"""
    v = max(0.0, min(1.0, v))
    if v < 0.25:
        return (int(255 * v * 4), 0, 0)
    elif v < 0.5:
        return (255, int(255 * (v - 0.25) * 4), 0)
    elif v < 0.75:
        return (255, 255, int(255 * (v - 0.5) * 4))
    else:
        return (255, 255, 255)


def _ocean_color(v: float) -> tuple:
    """海洋颜色映射 (深蓝→蓝→青)"""
    v = max(0.0, min(1.0, v))
    b = int(100 + 155 * v)
    g = int(80 + 175 * v)
    return (0, g, b)


def _rainbow_color(v: float) -> tuple:
    """彩虹颜色映射"""
    v = max(0.0, min(1.0, v))
    h = v * 300  # 0~300 度色相
    import colorsys
    try:
        r, g, b = colorsys.hsv_to_rgb(h / 360, 0.8, 0.7 + v * 0.3)
        return (int(r * 255), int(g * 255), int(b * 255))
    except ImportError:
        # 简化彩虹
        if h < 60:
            return (255, int(h * 4.25), 0)
        elif h < 120:
            return (int((120 - h) * 4.25), 255, 0)
        elif h < 180:
            return (0, 255, int((h - 120) * 4.25))
        elif h < 240:
            return (0, int((240 - h) * 4.25), 255)
        else:
            return (int((h - 240) * 4.25), 0, 255)


COLOR_MAPS = {
    'fire': _fire_color,
    'ocean': _ocean_color,
    'rainbow': _rainbow_color,
}


# ================================================================
#  FluidEngine — 流体模拟核心
# ================================================================

class FluidEngine:
    """
    简化的 Stable Fluids 流体模拟。

    算法步骤：
    1. 施加外力（add force）
    2. 平流（advect velocity & density）
    3. 扩散（diffuse velocity & density）
    4. 投影（project velocity to be divergence-free）
    5. 边界处理（boundary conditions）
    """

    def __init__(self, grid_w: int = 64, grid_h: int = 64,
                 viscosity: float = 0.000001, diffusion: float = 0.0001,
                 color_map: str = 'fire'):
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.viscosity = viscosity
        self.diffusion = diffusion
        self.color_map_name = color_map
        self.color_map = COLOR_MAPS.get(color_map, _fire_color)

        # 密度场（dye）
        self.density = np.zeros((grid_h, grid_w), dtype=np.float32)

        # 速度场（u: x方向, v: y方向）
        self.u = np.zeros((grid_h, grid_w), dtype=np.float32)
        self.v = np.zeros((grid_h, grid_w), dtype=np.float32)

        # 临时数组
        self._tmp = np.zeros((grid_h, grid_w), dtype=np.float32)
        self._divergence = np.zeros((grid_h, grid_w), dtype=np.float32)
        self._pressure = np.zeros((grid_h, grid_w), dtype=np.float32)

        # 音频调制状态
        self.force_strength = 5.0
        self.audio_funcs = {}

        # 图像缓存
        self._pil_img = Image.new('RGB', (grid_w, grid_h))
        self._pixels = self._pil_img.load()

    def set_audio_modulation(self, audio_funcs: dict):
        """
        设置音频调制函数。

        audio_funcs 格式：
        {
            'force_x': lambda audio: audio['rms'] * 10,
            'force_y': lambda audio: audio['bass'] * 8,
            'source':  lambda audio: audio['rms'] * 0.1,
        }
        """
        self.audio_funcs = audio_funcs

    def add_force_at(self, cx: float, cy: float, fx: float, fy: float,
                     radius: float = 3.0, dt: float = 1.0):
        """在指定位置施加力"""
        w, h = self.grid_w, self.grid_h
        for dy in range(-int(radius), int(radius) + 1):
            for dx in range(-int(radius), int(radius) + 1):
                if dx * dx + dy * dy <= radius * radius:
                    x, y = int(cx + dx), int(cy + dy)
                    if 0 <= x < w and 0 <= y < h:
                        self.u[y, x] += fx * dt
                        self.v[y, x] += fy * dt

    def add_density_at(self, cx: float, cy: float, amount: float = 0.1,
                        radius: float = 2.0):
        """在指定位置添加密度"""
        w, h = self.grid_w, self.grid_h
        for dy in range(-int(radius), int(radius) + 1):
            for dx in range(-int(radius), int(radius) + 1):
                if dx * dx + dy * dy <= radius * radius:
                    x, y = int(cx + dx), int(cy + dy)
                    if 0 <= x < w and 0 <= y < h:
                        self.density[y, x] += amount

    def step(self, dt: float, audio: dict = None):
        """
        执行一步流体模拟。

        Args:
            dt:    时间步长
            audio: 音频数据字典（可选，用于调制）
        """
        # 1. 施加外力（含音频调制）
        self._apply_force(dt, audio)

        # 2. 平流速度场
        self._advect_velocity(dt)

        # 3. 扩散速度场
        self._diffuse_velocity(dt)

        # 4. 投影（使速度场无散）
        self._project()

        # 5. 平流密度场
        self._advect_density(dt)

        # 6. 扩散密度场
        self._diffuse_density(dt)

        # 7. 边界处理
        self._apply_boundary()

    def _apply_force(self, dt: float, audio: dict):
        """施加外力（中心位置 + 音频调制）"""
        w, h = self.grid_w, self.grid_h
        cx, cy = w // 2, h // 2

        fx = self.force_strength
        fy = self.force_strength

        # 音频调制
        if audio and self.audio_funcs:
            for param, func in self.audio_funcs.items():
                try:
                    val = func(audio)
                    if param == 'force_x':
                        fx = val
                    elif param == 'force_y':
                        fy = val
                    elif param == 'source':
                        self.add_density_at(cx, cy, amount=val)
                except Exception:
                    pass

        self.add_force_at(cx, cy, fx * dt, fy * dt)

    def _advect_velocity(self, dt: float):
        """平流速度场（semi-Lagrangian）"""
        w, h = self.grid_w, self.grid_h

        # 创建坐标网格
        x = np.arange(w, dtype=np.float32)
        y = np.arange(h, dtype=np.float32)
        X, Y = np.meshgrid(x, y)

        # 回溯位置
        src_x = X - self.u * dt
        src_y = Y - self.v * dt

        # 限制在网格内
        src_x = np.clip(src_x, 0, w - 1.0001)
        src_y = np.clip(src_y, 0, h - 1.0001)

        # 双线性插值
        x0 = np.floor(src_x).astype(np.int32)
        x1 = x0 + 1
        y0 = np.floor(src_y).astype(np.int32)
        y1 = y0 + 1

        wx = src_x - x0
        wy = src_y - y0

        x0 = np.clip(x0, 0, w - 1)
        x1 = np.clip(x1, 0, w - 1)
        y0 = np.clip(y0, 0, h - 1)
        y1 = np.clip(y1, 0, h - 1)

        # 插值 u
        self._tmp[:, :] = self.u[:, :]
        self.u[:, :] = (
            self._tmp[y0, x0] * (1 - wx) * (1 - wy) +
            self._tmp[y0, x1] * wx * (1 - wy) +
            self._tmp[y1, x0] * (1 - wx) * wy +
            self._tmp[y1, x1] * wx * wy
        )

        # 插值 v
        self._tmp[:, :] = self.v[:, :]
        self.v[:, :] = (
            self._tmp[y0, x0] * (1 - wx) * (1 - wy) +
            self._tmp[y0, x1] * wx * (1 - wy) +
            self._tmp[y1, x0] * (1 - wx) * wy +
            self._tmp[y1, x1] * wx * wy
        )

    def _diffuse_velocity(self, dt: float):
        """扩散速度场（Jacobi 迭代）"""
        w, h = self.grid_w, self.grid_h
        a = dt * self.viscosity * w * h

        for _ in range(20):  # Jacobi 迭代次数
            self._tmp[:, :] = self.u[:, :]
            self.u[1:-1, 1:-1] = (
                self._tmp[1:-1, 1:-1] +
                a * (
                    self._tmp[1:-1, 2:] + self._tmp[1:-1, :-2] +
                    self._tmp[2:, 1:-1] + self._tmp[:-2, 1:-1]
                )
            ) / (1 + 4 * a)

            self._tmp[:, :] = self.v[:, :]
            self.v[1:-1, 1:-1] = (
                self._tmp[1:-1, 1:-1] +
                a * (
                    self._tmp[1:-1, 2:] + self._tmp[1:-1, :-2] +
                    self._tmp[2:, 1:-1] + self._tmp[:-2, 1:-1]
                )
            ) / (1 + 4 * a)

    def _project(self):
        """投影（使速度场无散）"""
        w, h = self.grid_w, self.grid_h

        # 计算散度
        self._divergence[1:-1, 1:-1] = (
            -0.5 * (
                self.u[1:-1, 2:] - self.u[1:-1, :-2] +
                self.v[2:, 1:-1] - self.v[:-2, 1:-1]
            )
        )

        # 求解压力（Jacobi 迭代）
        self._pressure[:, :] = 0

        for _ in range(20):
            self._tmp[:, :] = self._pressure[:, :]
            self._pressure[1:-1, 1:-1] = (
                self._divergence[1:-1, 1:-1] +
                self._tmp[1:-1, 2:] + self._tmp[1:-1, :-2] +
                self._tmp[2:, 1:-1] + self._tmp[:-2, 1:-1]
            ) / 4

        # 减去压力梯度
        self.u[1:-1, 1:-1] -= 0.5 * (
            self._pressure[1:-1, 2:] - self._pressure[1:-1, :-2]
        )
        self.v[1:-1, 1:-1] -= 0.5 * (
            self._pressure[2:, 1:-1] - self._pressure[:-2, 1:-1]
        )

    def _advect_density(self, dt: float):
        """平流密度场"""
        w, h = self.grid_w, self.grid_h

        x = np.arange(w, dtype=np.float32)
        y = np.arange(h, dtype=np.float32)
        X, Y = np.meshgrid(x, y)

        src_x = X - self.u * dt
        src_y = Y - self.v * dt

        src_x = np.clip(src_x, 0, w - 1.0001)
        src_y = np.clip(src_y, 0, h - 1.0001)

        x0 = np.floor(src_x).astype(np.int32)
        x1 = x0 + 1
        y0 = np.floor(src_y).astype(np.int32)
        y1 = y0 + 1

        wx = src_x - x0
        wy = src_y - y0

        x0 = np.clip(x0, 0, w - 1)
        x1 = np.clip(x1, 0, w - 1)
        y0 = np.clip(y0, 0, h - 1)
        y1 = np.clip(y1, 0, h - 1)

        self._tmp[:, :] = self.density[:, :]
        self.density[:, :] = (
            self._tmp[y0, x0] * (1 - wx) * (1 - wy) +
            self._tmp[y0, x1] * wx * (1 - wy) +
            self._tmp[y1, x0] * (1 - wx) * wy +
            self._tmp[y1, x1] * wx * wy
        )

    def _diffuse_density(self, dt: float):
        """扩散密度场"""
        w, h = self.grid_w, self.grid_h
        a = dt * self.diffusion * w * h

        for _ in range(20):
            self._tmp[:, :] = self.density[:, :]
            self.density[1:-1, 1:-1] = (
                self._tmp[1:-1, 1:-1] +
                a * (
                    self._tmp[1:-1, 2:] + self._tmp[1:-1, :-2] +
                    self._tmp[2:, 1:-1] + self._tmp[:-2, 1:-1]
                )
            ) / (1 + 4 * a)

    def _apply_boundary(self):
        """边界处理（将速度归零）"""
        self.u[0, :] = 0
        self.u[-1, :] = 0
        self.u[:, 0] = 0
        self.u[:, -1] = 0

        self.v[0, :] = 0
        self.v[-1, :] = 0
        self.v[:, 0] = 0
        self.v[:, -1] = 0

        # 密度边界（Neumann 条件）
        self.density[0, :] = self.density[1, :]
        self.density[-1, :] = self.density[-2, :]
        self.density[:, 0] = self.density[:, 1]
        self.density[:, -1] = self.density[:, -2]

    def render_to_image(self, width: int, height: int) -> 'Image.Image':
        """
        将流体场渲染到 PIL Image。

        Args:
            width:  输出图像宽度
            height: 输出图像高度

        Returns:
            PIL RGB Image
        """
        # 归一化密度场到 0~1
        d = self.density
        d_min = d.min()
        d_max = d.max()
        if d_max - d_min > 1e-8:
            d_norm = (d - d_min) / (d_max - d_min)
        else:
            d_norm = d * 0.0

        # 应用颜色映射
        for y in range(self.grid_h):
            for x in range(self.grid_w):
                v = float(d_norm[y, x])
                r, g, b = self.color_map(v)
                self._pixels[x, y] = (r, g, b)

        # 缩放到目标尺寸
        if width != self.grid_w or height != self.grid_h:
            return self._pil_img.resize((width, height), Image.LANCZOS)
        return self._pil_img.copy()

    def render_to_numpy(self, width: int, height: int) -> 'np.ndarray':
        """
        将流体场渲染到 numpy 数组（RGB，供 OpenCV 使用）。

        Returns:
            (height, width, 3) uint8 numpy 数组
        """
        import cv2
        pil_img = self.render_to_image(width, height)
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    def clear(self):
        """清空流体场"""
        self.density[:, :] = 0.0
        self.u[:, :] = 0.0
        self.v[:, :] = 0.0
        self._pressure[:, :] = 0.0
