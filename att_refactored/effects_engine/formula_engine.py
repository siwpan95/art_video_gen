"""
公式引擎 — 安全求值数学表达式（基于 asteval）
从 pywallpaper/engine/formula_engine.py 复制并适配到当前项目。
禁止跨项目调用，所有代码自包含。
"""

import re
import numpy as np

try:
    from asteval import Interpreter
    _HAS_ASTEVAL = True
except ImportError:
    _HAS_ASTEVAL = False
    print("[WARN] asteval 未安装，公式引擎将使用 eval()（安全性较低）")


class FormulaEngine:
    """
    公式引擎 — 支持音频数据驱动公式参数

    使用示例：
        engine = FormulaEngine()

        # 编译公式
        func = engine.compile("sin(t) * cos(t)", ['t'])

        # 执行公式
        t_vals = np.linspace(0, 2*np.pi, 100)
        result = func(t=t_vals)

        # 使用音频变量
        engine.set_audio(audio_spectrum=np.array([...]), audio_energy=0.5)
        result = engine.evaluate("sin(t) * audio.energy", t=0.5)
    """

    # 内置公式模板库
    TEMPLATES = {
        'spiral': {
            'x': 't * cos(t)',
            'y': 't * sin(t)',
            't_min': 0,
            't_max': 12.56,
            't_step': 0.1,
        },
        'cardioid': {
            'x': 'cos(t) * (1 + cos(t))',
            'y': 'sin(t) * (1 + cos(t))',
            't_min': 0,
            't_max': 6.28,
            't_step': 0.05,
        },
        'lissajous': {
            'x': 'cos(3*t)',
            'y': 'sin(2*t)',
            't_min': 0,
            't_max': 6.28,
            't_step': 0.02,
        },
        'rose': {
            'x': 'cos(3*t) * cos(t)',
            'y': 'cos(3*t) * sin(t)',
            't_min': 0,
            't_max': 6.28,
            't_step': 0.02,
        },
        'helix': {
            'x': 'cos(t)',
            'y': 'sin(t)',
            'z': 't * 0.1',
            't_min': 0,
            't_max': 12.56,
            't_step': 0.05,
        },
        'butterfly': {
            'x': 'sin(t) * (exp(cos(t)) - 2*cos(4*t) - sin(t/12)**5)',
            'y': 'cos(t) * (exp(cos(t)) - 2*cos(4*t) - sin(t/12)**5)',
            't_min': 0,
            't_max': 12.56,
            't_step': 0.02,
        },
    }

    def __init__(self):
        self._interp = None
        if _HAS_ASTEVAL:
            self._interp = Interpreter()
        self._compiled = {}  # 缓存编译后的公式
        self._audio = {}  # 音频数据

    def compile(self, expression: str, variables: list):
        """
        编译公式表达式。

        Args:
            expression: 数学表达式字符串
            variables:  变量名列表

        Returns:
            可调用函数：接收关键字参数为变量值，返回计算结果
        """
        if _HAS_ASTEVAL and self._interp:
            # 使用 asteval 安全编译
            code = self._interp.parse(expression)
            def _func(**kwargs):
                ns = dict(kwargs)
                self._interp.symtable.update(ns)
                return self._interp.run(code)
            return _func
        else:
            # 降级：使用 eval（注意安全性）
            def _func(**kwargs):
                ns = dict(kwargs)
                # 添加 numpy 函数到命名空间
                ns.update({
                    'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
                    'arcsin': np.arcsin, 'arccos': np.arccos, 'arctan': np.arctan,
                    'exp': np.exp, 'log': np.log, 'sqrt': np.sqrt,
                    'abs': abs, 'pi': np.pi, 'e': np.e,
                    'np': np, 'min': min, 'max': max,
                })
                return eval(expression, {'__builtins__': {}}, ns)
            return _func

    def evaluate(self, expression: str, **variables):
        """
        求值公式表达式。

        Args:
            expression: 数学表达式字符串
            **variables: 变量值（关键字参数）

        Returns:
            计算结果（标量或 numpy 数组）
        """
        func = self.compile(expression, list(variables.keys()))
        return func(**variables)

    def compile_template(self, template_name: str, param: str):
        """
        编译内置模板的某个参数。

        Args:
            template_name: 模板名称（在 TEMPLATES 中）
            param:         参数名（如 'x', 'y'）

        Returns:
            编译后的可调用函数
        """
        if template_name not in self.TEMPLATES:
            raise ValueError(f"未知模板: {template_name}")
        template = self.TEMPLATES[template_name]
        if param not in template:
            raise ValueError(f"模板 {template_name} 中没有参数: {param}")
        return self.compile(template[param], ['t'])

    def get_template_params(self, template_name: str) -> dict:
        """获取模板的全部参数"""
        return self.TEMPLATES.get(template_name, {})

    def add_template(self, name: str, config: dict):
        """添加自定义模板"""
        self.TEMPLATES[name] = config

    def set_audio(self, **audio_data):
        """
        设置音频数据（供公式中的 audio.* 变量使用）

        示例：
            engine.set_audio(
                spectrum=np.array([...]),
                energy=0.5,
                rms=0.3,
                band_energy=lambda idx: spectrum[idx],
            )
        """
        self._audio.update(audio_data)

    def evaluate_with_audio(self, expression: str, t: float, audio: dict):
        """
        在音频数据上下文中求值公式。

        Args:
            expression: 数学表达式字符串
            t:          时间变量
            audio:      音频数据字典（包含 spectrum, energy, rms 等）

        Returns:
            计算结果
        """
        # 构建命名空间
        ns = {
            't': t,
            'audio': audio,
            'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
            'exp': np.exp, 'log': np.log, 'sqrt': np.sqrt,
            'abs': abs, 'pi': np.pi,
            'np': np,
        }
        # 添加音频辅助函数
        if 'spectrum' in audio:
            spectrum = audio['spectrum']
            ns['audio_spectrum'] = spectrum
            ns['audio_band'] = lambda idx: spectrum[int(idx)] if idx < len(spectrum) else 0.0
        if 'energy' in audio:
            ns['audio_energy'] = audio['energy']
        if 'rms' in audio:
            ns['audio_rms'] = audio['rms']

        if _HAS_ASTEVAL and self._interp:
            self._interp.symtable.update(ns)
            code = self._interp.parse(expression)
            return self._interp.run(code)
        else:
            return eval(expression, {'__builtins__': {}}, ns)


def evaluate_curve(curve, t: float) -> float:
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
