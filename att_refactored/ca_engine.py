"""
CA 渲染引擎核心模块 —— 与 Pygame 解耦版本
用于 att_refactored 视频生成器集成。
从 draw/engine.py 适配，改进公式编译逻辑（稳健嵌套 if-else 转换）。
"""

import json
import re

import numpy as np
from scipy.ndimage import convolve


class CARenderEngine:
    """连续细胞自动机渲染引擎。

    通过 JSON 配方配置，支持：
    - 数学公式初始化网格
    - 数学公式演化规则
    - 数学公式颜色映射
    - 周期循环重置
    - 可配置邻域核
    """

    def __init__(self, config_path=None):
        self._compile_cache = {}
        self.config = {}
        self.grid = None
        self.rule_func = None
        self.color_funcs = {}
        self.t = 0
        self.w, self.h = 0, 0
        self.wrap = True
        self.kernel = None
        self.fps = 30
        self.steps_per_frame = 1
        self.x_grid = None
        self.y_grid = None
        self.cycle_steps = 0
        self.init_func = None
        self.init_expr = None
        self._total_cycles = 0
        if config_path is not None:
            self.load_config(config_path)

    # ================================================================
    #  配置加载
    # ================================================================
    def load_config(self, path):
        """热插拔入口：从 JSON 加载完整配方"""
        with open(path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        g = self.config['grid']
        self.w, self.h = g['width'], g['height']
        self.wrap = g.get('wrap', True)

        init_expr = g['initial']['expression']
        self.init_expr = init_expr
        self.init_func = self._compile(init_expr, ['x', 'y', 'i', 'j', 'random'])
        self._reset_grid()

        ev = self.config['evolution']
        var_names = ev.get('variables', ['c', 'sum_n', 'avg_n', 'x', 'y', 't'])
        self.rule_func = self._compile(ev['rule'], var_names)

        col = self.config['color']
        self.color_funcs = {}
        for channel in ['red', 'green', 'blue']:
            expr = col.get(channel, '0.0')
            self.color_funcs[channel] = self._compile(expr, ['v', 'x', 'y'])

        nb = self.config.get('neighborhood', {})
        radius = nb.get('radius', 1)
        size = 2 * radius + 1
        self.kernel = np.ones((size, size), dtype=np.float32)
        self.kernel[radius, radius] = 0

        tick = self.config.get('tick', {})
        self.fps = tick.get('fps', 30)
        self.steps_per_frame = tick.get('steps_per_frame', 1)

        cycle = self.config.get('cycle', {})
        self.cycle_steps = cycle.get('steps', 0)

        self.t = 0
        self._total_cycles = 0
        self._build_coordinate_grids()

    def _build_coordinate_grids(self):
        self.x_grid = np.broadcast_to(
            np.linspace(0, 1, self.w, endpoint=False, dtype=np.float64).reshape(1, -1),
            (self.h, self.w)
        ).copy()
        self.y_grid = np.broadcast_to(
            np.linspace(0, 1, self.h, endpoint=False, dtype=np.float64).reshape(-1, 1),
            (self.h, self.w)
        ).copy()

    # ================================================================
    #  公式编译器（改进版 — 从 draw 项目集成健壮逻辑）
    # ================================================================
    _IF_ELSE_PAT = re.compile(r'\bif\b|\belse\b')

    @classmethod
    def _ifelse_to_where(cls, expr: str) -> str:
        """稳健地将 Python 三元表达式转换为 NumPy where()。

        逐层剥离：先找最内层（括号深度最大）的 if-else 替换为 where()，
        然后逐层向外，彻底解决嵌套 if-else 的误匹配问题。
        """
        for _ in range(10):
            tokens = []
            for m in cls._IF_ELSE_PAT.finditer(expr):
                pos = m.start()
                depth = expr[:pos].count('(') - expr[:pos].count(')')
                tokens.append((pos, m.group(), depth))

            pairs = []
            i = 0
            while i < len(tokens):
                if tokens[i][1] == 'if':
                    if_depth = tokens[i][2]
                    j = i + 1
                    while j < len(tokens):
                        if tokens[j][1] == 'else' and tokens[j][2] == if_depth:
                            pairs.append((tokens[i][0], tokens[j][0], if_depth))
                            i = j + 1
                            break
                        j += 1
                    else:
                        i += 1
                else:
                    i += 1

            if not pairs:
                break

            pairs.sort(key=lambda x: (x[2], x[0]), reverse=True)
            if_pos, else_pos, depth = pairs[0]

            left = 0
            for k in range(if_pos - 1, -1, -1):
                d = expr[:k].count('(') - expr[:k].count(')')
                if d < depth:
                    left = k + 1
                    break

            scan_start = else_pos + 5
            false_right = len(expr)
            paren_depth = 0
            for k in range(scan_start, len(expr)):
                ch = expr[k]
                if ch == '(':
                    paren_depth += 1
                elif ch == ')':
                    if paren_depth > 0:
                        paren_depth -= 1
                    else:
                        false_right = k
                        break
                elif ch == ',' and paren_depth == 0:
                    false_right = k
                    break

            sub = expr[left:false_right]
            inner_if = sub.index(' if ')
            inner_else = sub.index(' else ')
            true_val = sub[:inner_if].strip()
            condition = sub[inner_if + 4:inner_else].strip()
            false_val = sub[inner_else + 6:].strip()

            replacement = f'where({condition}, {true_val}, {false_val})'
            expr = expr[:left] + replacement + expr[false_right:]

        return expr

    @staticmethod
    def _convert_logic_ops(expr: str) -> str:
        """将 Python 逻辑运算符 and/or/not 转换为 NumPy &/|/~。"""
        _KW_RE = re.compile(r'\band\b|\bor\b')
        while True:
            m = re.search(r'\bnot\b', expr)
            if not m:
                break
            start, end = m.start(), m.end()
            kw_positions = {kw.start() for kw in _KW_RE.finditer(expr)}
            right_boundary = len(expr)
            depth = 0
            for i in range(end, len(expr)):
                ch = expr[i]
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    if depth == 0:
                        right_boundary = i
                        break
                    depth -= 1
                elif ch == ',' and depth == 0:
                    right_boundary = i
                    break
                elif i in kw_positions and depth == 0:
                    right_boundary = i
                    break
            operand = expr[end:right_boundary].strip()
            expr = expr[:start] + f'logical_not({operand})' + expr[right_boundary:]

        while True:
            m = re.search(r'\band\b|\bor\b', expr)
            if not m:
                break
            start, end = m.start(), m.end()
            op = m.group()
            kw_positions = {kw.start() for kw in re.finditer(r'\band\b|\bor\b', expr)}
            left_boundary = 0
            depth = 0
            for i in range(start - 1, -1, -1):
                ch = expr[i]
                if ch == ')':
                    depth += 1
                elif ch == '(':
                    if depth == 0:
                        left_boundary = i + 1
                        break
                    depth -= 1
                elif ch == ',' and depth == 0:
                    left_boundary = i + 1
                    break
                elif i in kw_positions and depth == 0:
                    kw_m = re.match(r'\band\b|\bor\b', expr[i:])
                    left_boundary = i + (kw_m.end() if kw_m else 3)
                    break
            left = expr[left_boundary:start].strip()
            right_boundary = len(expr)
            depth = 0
            for i in range(end, len(expr)):
                ch = expr[i]
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    if depth == 0:
                        right_boundary = i
                        break
                    depth -= 1
                elif ch == ',' and depth == 0:
                    right_boundary = i
                    break
                elif i in kw_positions and depth == 0:
                    right_boundary = i
                    break
            right = expr[end:right_boundary].strip()
            new_op = '&' if op == 'and' else '|'
            replacement = f'({left}) {new_op} ({right})'
            expr = expr[:left_boundary] + replacement + expr[right_boundary:]

        return expr

    def _compile(self, expr, var_names):
        cache_key = (expr, tuple(var_names))
        if cache_key in self._compile_cache:
            return self._compile_cache[cache_key]

        # Python if-else → where() 转换（稳健版）
        processed = self._ifelse_to_where(expr)

        # min/max → minimum/maximum
        processed = re.sub(r'\bmin\(', 'minimum(', processed)
        processed = re.sub(r'\bmax\(', 'maximum(', processed)

        # and/or/not → NumPy &/|/~ （添加括号保护优先级）
        processed = self._convert_logic_ops(processed)

        func = self._compile_numeric(processed)
        self._compile_cache[cache_key] = func
        return func

    def _compile_numeric(self, processed):
        ns = {
            'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
            'exp': np.exp, 'log': np.log, 'sqrt': np.sqrt,
            'abs': np.abs, 'pi': np.pi, 'e': np.e,
            'minimum': np.minimum, 'maximum': np.maximum,
            'where': np.where, 'clip': np.clip,
            'logical_not': np.logical_not,
            'floor': np.floor, 'ceil': np.ceil, 'round': np.round,
            'int': lambda x: np.floor(x).astype(np.float64),  # int(x) → floor(x)
            'random': lambda *a: np.random.random(a[0] if a else None),
        }

        def func(**kwargs):
            first_arr = next((v for v in kwargs.values()
                              if isinstance(v, np.ndarray) and v.ndim == 2), None)
            if first_arr is not None:
                ns['random'] = lambda *a: np.random.random(first_arr.shape)
            else:
                ns['random'] = lambda *a: np.random.random()
            try:
                result = eval(processed, {"__builtins__": {}}, {**ns, **kwargs})
                return np.asarray(result, dtype=np.float64)
            except KeyboardInterrupt:
                raise
            except Exception:
                return np.float64(0.0)
        return func

    # ================================================================
    #  网格操作
    # ================================================================
    def _reset_grid(self):
        self.grid = np.zeros((self.h, self.w), dtype=np.float32)
        for i in range(self.h):
            for j in range(self.w):
                x = j / self.w
                y = i / self.h
                val = self.init_func(x=x, y=y, i=i, j=j, random=np.random.random)
                self.grid[i, j] = np.clip(val, 0.0, 1.0)

    def reset(self):
        self._reset_grid()
        self.t = 0
        self._total_cycles = 0

    # ================================================================
    #  演化
    # ================================================================
    def step(self):
        if self.cycle_steps > 0 and self.t >= self.cycle_steps:
            self._reset_grid()
            self.t = 0
            self._total_cycles += 1
            return

        mode = 'wrap' if self.wrap else 'constant'
        sum_n = convolve(self.grid, self.kernel, mode=mode, cval=0.0)
        avg_n = sum_n / self.kernel.sum()

        val = self.rule_func(
            c=self.grid, sum_n=sum_n, avg_n=avg_n,
            x=self.x_grid, y=self.y_grid, t=np.float64(self.t),
            i=self.y_grid * self.h, j=self.x_grid * self.w
        )
        val = np.asarray(val, dtype=np.float32)
        if val.shape != (self.h, self.w):
            val = np.broadcast_to(val.ravel()[0:1], (self.h, self.w)).astype(np.float32)
        self.grid = np.clip(val, 0.0, 1.0)
        self.t += 1

    def step_n(self, n):
        for _ in range(n):
            self.step()

    def get_grid_stats(self):
        return {
            'min': float(self.grid.min()),
            'max': float(self.grid.max()),
            'mean': float(self.grid.mean()),
            'std': float(self.grid.std()),
            'alive': float((self.grid > 0.01).mean()),
        }

    # ================================================================
    #  颜色映射
    # ================================================================
    def _eval_channel(self, func, v):
        ch = func(v=v, x=self.x_grid, y=self.y_grid)
        ch = np.asarray(ch, dtype=np.float64)
        if ch.shape != (self.h, self.w):
            ch = np.broadcast_to(ch.ravel()[0:1], (self.h, self.w)).astype(np.float64)
        return np.clip(ch, 0.0, 1.0)

    def get_color_array(self):
        """返回形状 (h, w, 3) 的 uint8 RGB 数组（与 OpenCV 兼容）"""
        v = self.grid.astype(np.float64)
        r = self._eval_channel(self.color_funcs['red'], v)
        g = self._eval_channel(self.color_funcs['green'], v)
        b = self._eval_channel(self.color_funcs['blue'], v)
        arr = np.zeros((self.h, self.w, 3), dtype=np.uint8)
        arr[:, :, 0] = (r * 255).astype(np.uint8)
        arr[:, :, 1] = (g * 255).astype(np.uint8)
        arr[:, :, 2] = (b * 255).astype(np.uint8)
        return arr

    def get_color_bgr(self):
        """返回 OpenCV BGR 格式 (h, w, 3) uint8"""
        rgb = self.get_color_array()
        return rgb[:, :, ::-1].copy()
