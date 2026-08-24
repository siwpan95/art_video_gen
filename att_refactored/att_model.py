#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
  Model 层 (Model Layer)
  带音频的视频生成软件 - 业务逻辑和数据模型

  职责：
  - 音频生成逻辑（多种波形 + 和弦 + 效果）
  - 视频生成逻辑（多种效果 + 丰富参数 + 音频驱动）
  - 音视频合并逻辑
  - 依赖检查
============================================
"""

import os
import sys
import random
import subprocess
import math
from pathlib import Path

# CA 引擎支持（可选，从 draw 项目集成）
try:
    from ca_recipes import load_ca_recipes, get_ca_recipe_names
    _CA_RECIPES_AVAILABLE = True
except ImportError:
    _CA_RECIPES_AVAILABLE = False

# ==================== 可选加速：numba JIT ====================
_NUMBA_AVAILABLE = False
_njit = None
try:
    from numba import njit as _njit
    _NUMBA_AVAILABLE = True
    print("[OK] numba JIT acceleration enabled")
except ImportError:
    # 提供一个什么都不做的装饰器作为降级
    def _njit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator if args and callable(args[0]) else decorator


# ==================== 依赖检查 ====================
def check_dependencies():
    """检查并报告依赖状态"""
    deps = {
        "numpy": False,
        "cv2": False,
        "scipy": False,
        "tkinter": False,
    }

    try:
        import numpy
        deps["numpy"] = True
    except ImportError:
        pass

    try:
        import cv2
        deps["cv2"] = True
    except ImportError:
        pass

    try:
        from scipy.io import wavfile
        deps["scipy"] = True
    except ImportError:
        pass

    try:
        import tkinter
        deps["tkinter"] = True
    except ImportError:
        pass

    return deps


# ==================== 调色板定义 ====================
VIDEO_PALETTES = {
    # ===== 原有 8 种 =====
    "霓虹": {
        "colors": [[255, 0, 128], [0, 255, 255], [128, 0, 255]],
        "bg": [10, 5, 20]
    },
    "日落": {
        "colors": [[255, 100, 50], [255, 180, 100], [255, 50, 100]],
        "bg": [30, 10, 15]
    },
    "海洋": {
        "colors": [[0, 150, 255], [0, 200, 200], [100, 255, 255]],
        "bg": [5, 15, 30]
    },
    "森林": {
        "colors": [[50, 200, 50], [100, 255, 100], [0, 150, 50]],
        "bg": [5, 20, 5]
    },
    "岩浆": {
        "colors": [[255, 50, 0], [255, 150, 0], [255, 80, 20]],
        "bg": [30, 5, 0]
    },
    "星空": {
        "colors": [[200, 220, 255], [100, 150, 255], [255, 240, 200]],
        "bg": [2, 2, 15]
    },
    "极光": {
        "colors": [[0, 255, 100], [50, 200, 255], [150, 255, 200]],
        "bg": [0, 10, 20]
    },
    "赛博朋克": {
        "colors": [[255, 0, 255], [0, 255, 255], [255, 255, 0]],
        "bg": [5, 0, 15]
    },
    # ===== 新增 8 种（色彩理论） =====
    "紫罗兰": {
        "colors": [[138, 43, 226], [218, 112, 214], [75, 0, 130]],
        "bg": [8, 3, 20]
    },
    "秋天": {
        "colors": [[210, 105, 30], [244, 164, 96], [139, 69, 19]],
        "bg": [20, 10, 5]
    },
    "薄荷": {
        "colors": [[152, 255, 152], [0, 250, 154], [60, 179, 113]],
        "bg": [5, 15, 8]
    },
    "暮光": {
        "colors": [[72, 61, 139], [123, 104, 238], [255, 140, 0]],
        "bg": [10, 8, 25]
    },
    "金属": {
        "colors": [[192, 192, 192], [169, 169, 169], [220, 220, 220]],
        "bg": [20, 20, 22]
    },
    "热带": {
        "colors": [[255, 69, 0], [0, 206, 209], [255, 215, 0]],
        "bg": [15, 8, 5]
    },
    "薰衣草": {
        "colors": [[230, 230, 250], [147, 112, 219], [216, 191, 216]],
        "bg": [12, 8, 20]
    },
    "暗物质": {
        "colors": [[0, 255, 255], [255, 0, 255], [57, 255, 20]],
        "bg": [3, 1, 5]
    },
}

EFFECT_MODES = ["元胞自动机", "渐变流动", "几何图形", "分形图案", "噪声纹理", "脉冲波纹", "频谱可视化",
                "反应扩散", "流动场", "L系统分形", "CA引擎", "粒子系统",
                "公式驱动", "流体模拟", "频谱柱形图", "波形曲线",
                "漩涡效果", "脉冲涟漪",
                # 组合效果（多效果叠加）
                "渐变+粒子", "流体+几何", "频谱+漩涡", "分形+噪声"]


# ==================== Numba 加速辅助函数 ====================
if _NUMBA_AVAILABLE:
    import numpy as _np

    @_njit(cache=True)
    def _numba_ca_step(grid, h, w):
        """Numba 加速的元胞自动机单步更新"""
        neighbors = _np.zeros((h, w), dtype=_np.uint8)
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                n = (int(grid[y-1, x-1]) + int(grid[y-1, x]) + int(grid[y-1, x+1]) +
                     int(grid[y, x-1]) + int(grid[y, x+1]) +
                     int(grid[y+1, x-1]) + int(grid[y+1, x]) + int(grid[y+1, x+1]))
                neighbors[y, x] = n
        new_grid = _np.zeros((h, w), dtype=_np.uint8)
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if grid[y, x] == 1:
                    new_grid[y, x] = 1 if (neighbors[y, x] == 2 or neighbors[y, x] == 3) else 0
                else:
                    new_grid[y, x] = 1 if neighbors[y, x] == 3 else 0
        return new_grid

    @_njit(cache=True)
    def _numba_gs_step(U, V, Du, Dv, F, K, dt):
        """Numba 加速的 Gray-Scott 反应扩散单步更新"""
        h, w = U.shape
        new_U = _np.zeros_like(U)
        new_V = _np.zeros_like(V)
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                # 拉普拉斯算子（5点差分）
                Lu = (U[y-1, x] + U[y+1, x] + U[y, x-1] + U[y, x+1] - 4.0 * U[y, x])
                Lv = (V[y-1, x] + V[y+1, x] + V[y, x-1] + V[y, x+1] - 4.0 * V[y, x])

                uvv = U[y, x] * V[y, x] * V[y, x]
                du = Du * Lu - uvv + F * (1.0 - U[y, x])
                dv = Dv * Lv + uvv - (F + K) * V[y, x]

                new_U[y, x] = max(0.0, min(1.0, U[y, x] + du * dt))
                new_V[y, x] = max(0.0, min(1.0, V[y, x] + dv * dt))

        # 边界复制
        new_U[0, :] = new_U[1, :]
        new_U[-1, :] = new_U[-2, :]
        new_U[:, 0] = new_U[:, 1]
        new_U[:, -1] = new_U[:, -2]
        new_V[0, :] = new_V[1, :]
        new_V[-1, :] = new_V[-2, :]
        new_V[:, 0] = new_V[:, 1]
        new_V[:, -1] = new_V[:, -2]

        return new_U, new_V


# ==================== 配置类 ====================
class GenerationConfig:
    """生成配置（数据模型）"""

    def __init__(self):
        # 视频参数
        self.width = 640
        self.height = 480
        self.num_frames = 300
        self.fps = 30
        self.codec = "mp4v"
        self.palette = "霓虹"
        self.particle_count = 20
        self.animation_speed = 1.0
        self.video_bitrate = "medium"
        self.effect_mode = "元胞自动机"
        self.audio_path = ""          # 音频驱动文件
        self.audio_reactive = 0.5     # 音频驱动强度 0~1

        # 音频参数
        self.wave_type = "sine"
        self.freq = 440
        self.duration = 10
        self.volume = 0.5
        self.sample_rate = 44100
        self.channels = 1
        self.chord_type = "无"

        # 加密/压缩配置
        self.crypto_enabled = False           # 是否启用后处理
        self.crypto_signature = "FullstackDev"  # 英文签名
        self.crypto_compress = "medium"       # 压缩预设
        self.crypto_password = ""              # 加密密码（空=随机密钥）
        self.crypto_bomb = False              # 是否生成压缩炸弹
        self.last_video_path = ""             # 最近生成的视频路径

        # 输出（以脚本所在目录为基准的绝对路径）
        self.output_dir = str(Path(__file__).parent / "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def to_dict(self):
        """转为字典（用于保存配置）"""
        return {
            "width": self.width,
            "height": self.height,
            "num_frames": self.num_frames,
            "fps": self.fps,
            "codec": self.codec,
            "palette": self.palette,
            "particle_count": self.particle_count,
            "animation_speed": self.animation_speed,
            "video_bitrate": self.video_bitrate,
            "effect_mode": self.effect_mode,
            "audio_path": self.audio_path,
            "audio_reactive": self.audio_reactive,
            "wave_type": self.wave_type,
            "freq": self.freq,
            "duration": self.duration,
            "volume": self.volume,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "chord_type": self.chord_type,
            "output_dir": self.output_dir,
            "crypto_enabled": self.crypto_enabled,
            "crypto_signature": self.crypto_signature,
            "crypto_compress": self.crypto_compress,
            "crypto_password": self.crypto_password,
            "crypto_bomb": self.crypto_bomb,
            "last_video_path": self.last_video_path,
        }

    def from_dict(self, data):
        """从字典加载（用于读取配置）"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


# ==================== 音频生成器 ====================
class AudioGenerator:
    """音频生成器 - 支持 6 种波形 + 7 种和弦 + 立体声"""

    # 和弦定义 (根音 + 叠加音 频率倍率)
    CHORDS = {
        "大三和弦": [1.0, 1.25, 1.5],          # C-E-G (纯律大三度)
        "小三和弦": [1.0, 1.2, 1.5],           # C-Eb-G
        "增和弦":   [1.0, 1.25, 1.6],          # C-E-G#
        "减和弦":   [1.0, 1.2, 1.44],          # C-Eb-Gb
        "五和弦":   [1.0, 1.5],                  # C-G (power chord)
        "大七和弦": [1.0, 1.25, 1.5, 1.875],  # C-E-G-B
        "属七和弦": [1.0, 1.25, 1.5, 1.8],    # C-E-G-Bb
    }

    @staticmethod
    def generate_wave(wave_type="sine", freq=440, duration=10,
                      sample_rate=44100, volume=0.5, channels=1):
        """
        生成基础波形音频

        Returns:
            tuple: (audio_data, sample_rate)
        """
        try:
            import numpy as np
        except ImportError:
            print("[ERR] 缺少 numpy，无法生成音频")
            return None, 0

        samples = int(duration * sample_rate)
        t = np.linspace(0, duration, samples, dtype=np.float32)

        # 生成基础波形
        if wave_type == "sine":
            wave = np.sin(2.0 * np.pi * freq * t)
        elif wave_type == "square":
            wave = np.sign(np.sin(2.0 * np.pi * freq * t))
        elif wave_type == "triangle":
            wave = 2.0 * np.abs(2.0 * (t * freq - np.floor(t * freq + 0.5))) - 1.0
        elif wave_type == "sawtooth":
            wave = 2.0 * (t * freq - np.floor(t * freq + 0.5))
        elif wave_type == "white_noise":
            wave = np.random.uniform(-1.0, 1.0, samples)
        elif wave_type == "pink_noise":
            # Voss-McCartney 算法生成粉红噪声
            white = np.random.uniform(-1.0, 1.0, samples)
            pink = np.zeros_like(white)
            n_rows = len(white)
            n_cols = 16  # 足够多的行叠加
            array = np.random.randn(n_cols, n_rows)
            yt = np.zeros(n_rows)
            for i in range(n_cols):
                yt += array[i] / (i + 1)
            yt = yt / n_cols
            wave = yt[:samples]
            wave = wave / (np.max(np.abs(wave)) + 1e-8)
        else:
            print(f"[WARN] 未知波形: {wave_type}，使用 sine")
            wave = np.sin(2.0 * np.pi * freq * t)

        # ADSR 包络（避免爆音和点击音）
        envelope = AudioGenerator._make_adsr(samples, sample_rate)
        wave = wave * envelope * volume

        # 声道处理
        if channels == 2:
            # 立体声：轻微左右延迟制造宽度
            delay_samples = int(0.005 * sample_rate)  # 5ms 延迟
            left = wave.copy()
            right = np.zeros_like(wave)
            right[delay_samples:] = wave[:-delay_samples] * 0.7
            audio_data = np.column_stack((left, right))
        else:
            audio_data = wave.reshape(-1, 1)

        return audio_data, sample_rate

    @staticmethod
    def _make_adsr(samples, sample_rate):
        """生成 ADSR 包络"""
        import numpy as np
        attack = int(0.02 * sample_rate)    # 20ms
        decay = int(0.1 * sample_rate)       # 100ms
        sustain_level = 0.7
        release = int(0.15 * sample_rate)    # 150ms

        envelope = np.ones(samples, dtype=np.float32)
        # Attack
        envelope[:attack] = np.linspace(0, 1, attack)
        # Decay
        decay_end = attack + decay
        envelope[attack:decay_end] = np.linspace(1, sustain_level, decay)
        # Sustain (已设为 1.0，上面已预设)
        # Release
        release_start = samples - release
        if release_start > 0:
            envelope[release_start:] = np.linspace(sustain_level, 0, release)

        return envelope

    @staticmethod
    def generate_chord(wave_type="sine", root_freq=440, chord_type="大三和弦",
                       duration=10, sample_rate=44100, volume=0.5, channels=1):
        """生成和弦音频（多个频率叠加）"""
        try:
            import numpy as np
        except ImportError:
            print("[ERR] 缺少 numpy")
            return None, 0

        if chord_type not in AudioGenerator.CHORDS:
            print(f"[WARN] 未知和弦: {chord_type}，使用大三和弦")
            chord_type = "大三和弦"

        ratios = AudioGenerator.CHORDS[chord_type]
        samples = int(duration * sample_rate)
        audio_data = np.zeros(samples, dtype=np.float32)

        for r in ratios:
            freq = root_freq * r
            wave, _ = AudioGenerator.generate_wave(
                wave_type, freq, duration, sample_rate, volume / len(ratios), channels
            )
            if wave is not None:
                audio_data += wave[:, 0]

        # 归一化
        audio_data = audio_data / (np.max(np.abs(audio_data)) + 1e-8) * volume

        if channels == 2:
            delay_samples = int(0.005 * sample_rate)
            left = audio_data.copy()
            right = np.zeros_like(audio_data)
            right[delay_samples:] = audio_data[:-delay_samples] * 0.7
            audio_data = np.column_stack((left, right))

        return audio_data, sample_rate

    @staticmethod
    def save_wav(filepath, audio_data, sample_rate):
        """保存音频为 WAV 文件"""
        try:
            from scipy.io import wavfile
            import numpy as np
            # 转为 16-bit PCM
            audio_int16 = (audio_data * 32767).astype(np.int16)
            wavfile.write(filepath, sample_rate, audio_int16)
            print(f"[OK] 音频已保存: {filepath}")
            return True
        except Exception as e:
            print(f"[ERR] 保存音频失败: {e}")
            return False


# ==================== 帧混合工具函数 ====================
def blend_frames(frame1, frame2, blend_mode="add", alpha=0.5):
    """
    混合两帧图像

    Args:
        frame1: 底图层 (numpy array, uint8)
        frame2: 叠加层 (numpy array, uint8)
        blend_mode: 混合模式 ("add", "multiply", "screen", "overlay", "alpha")
        alpha: 叠加层透明度 (0.0~1.0)

    Returns:
        blended: 混合后的帧 (numpy array, uint8)
    """
    import numpy as np

    # 转换为 float32 进行计算
    f1 = frame1.astype(np.float32) / 255.0
    f2 = frame2.astype(np.float32) / 255.0

    if blend_mode == "add":
        # 相加混合（变亮）
        result = np.clip(f1 + f2 * alpha, 0.0, 1.0)

    elif blend_mode == "multiply":
        # 相乘混合（变暗）
        result = f1 * f2

    elif blend_mode == "screen":
        # 滤色混合（保留较亮部分）
        result = 1.0 - (1.0 - f1) * (1.0 - f2 * alpha)

    elif blend_mode == "overlay":
        # 叠加混合
        mask = f1 < 0.5
        result = np.where(mask, 2.0 * f1 * f2, 1.0 - 2.0 * (1.0 - f1) * (1.0 - f2))

    elif blend_mode == "alpha":
        # Alpha 混合
        result = f1 * (1.0 - alpha) + f2 * alpha

    else:
        # 默认：相加
        result = np.clip(f1 + f2 * alpha, 0.0, 1.0)

    return (result * 255).astype(np.uint8)


def create_effect_frame_generator(effect_mode, w, h, palette_name, speed, particle_count):
    """
    创建效果帧生成器（用于多效果叠加）

    Returns:
        generator: 一个函数，输入 frame_index，输出渲染的帧
    """
    import numpy as np

    # 这里需要返回一个新的帧生成器
    # 由于原有代码是在循环内渲染，我们需要提取渲染逻辑
    # 这是一个简化版本，实际实现需要重构各效果生成器

    palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
    colors = np.array(palette_info["colors"], dtype=np.float32)
    bg = np.array(palette_info["bg"], dtype=np.uint8)

    def generator(frame_index, audio_feature=None):
        """生成单帧"""
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :] = bg

        # 这里需要根据 effect_mode 调用对应的渲染逻辑
        # 由于代码复杂度，这里先返回基础帧
        # 完整实现需要重构 _gen_* 方法

        return frame

    return generator


# ==================== 视频生成器（支持音频驱动）====================
class VideoGenerator:
    """
    视频生成器 - 支持 10 种效果模式 + 音频驱动 + Numba加速
    音频驱动原理：
      1. 分析音频文件，提取每帧的音频特征（音量、频谱、节拍）
      2. 生成视频时，根据当前帧的音频特征调制画面参数
    新增效果：反应扩散(Gray-Scott)、Perlin流动场、L系统分形
    """

    @staticmethod
    def analyze_audio(audio_path, num_frames, fps):
        """
        分析音频文件，提取每帧的音频特征

        增强版：如果安装了 librosa，则使用其精准的节拍/起音检测算法；
        否则回退到基于频谱通量的基础检测。

        Args:
            audio_path:  音频文件路径（WAV 格式）
            num_frames:  视频总帧数
            fps:         视频帧率

        Returns:
            list[dict] | None: 每帧的音频特征，包含：
                - "volume":  float 0~1, RMS 音量
                - "spectrum": np.array, FFT 频谱（n_bins,)
                - "bass":   float 0~1, 低音能量（0~200Hz 近似）
                - "mid":    float 0~1, 中音能量（200~2000Hz）
                - "treble": float 0~1, 高音能量（2000Hz+）
                - "onset":  float 0~1, 节拍强度（频谱通量 / librosa onset）
                - "beat":   bool, 是否检测到节拍
                - "tempo":  float, 估计的 BPM（librosa 专属，否则 0）
                - "beat_frames": list[int], 节拍所在帧号（librosa 专属）
        """
        try:
            import numpy as np
            from scipy.io import wavfile

            sr, audio = wavfile.read(audio_path)
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1)  # 立体声转单声道
            audio_f32 = audio.astype(np.float32)
            audio_f32 = audio_f32 / (np.max(np.abs(audio_f32)) + 1e-8)  # 归一化

            samples_per_frame = sr / fps
            features = []
            n_bins = 32  # FFT 频段数量
            prev_spectrum = np.zeros(n_bins)

            # ===== 尝试使用 librosa 增强节拍检测 =====
            librosa_onsets = None
            librosa_beats = None
            bpm_est = 0.0
            try:
                import librosa
                # 重新加载音频（librosa 需要 float）
                y, sr_lib = librosa.load(audio_path, sr=None, mono=True)
                # 计算 onset 强度包络
                onset_env = librosa.onset.onset_strength(y=y, sr=sr_lib)
                # 估计节拍位置
                tempo, beat_frames_lib = librosa.beat.beat_track(
                    onset_envelope=onset_env, sr=sr_lib)
                bpm_est = float(tempo)
                # 将节拍位置映射到视频帧
                beat_times = librosa.frames_to_time(beat_frames_lib, sr=sr_lib)
                librosa_beats = [int(t * fps) for t in beat_times
                                 if 0 <= int(t * fps) < num_frames]
                # 将 onset 包络映射到帧
                onset_times = librosa.frames_to_time(
                    np.arange(len(onset_env)), sr=sr_lib)
                librosa_onsets = np.interp(
                    np.arange(num_frames) / fps,
                    onset_times,
                    onset_env
                )
                # 归一化 onset
                if librosa_onsets.max() > 0:
                    librosa_onsets = librosa_onsets / librosa_onsets.max()
                print(f"[AUDIO] [librosa] 检测到 BPM: {bpm_est:.1f}, "
                      f"节拍数: {len(librosa_beats)}")
            except ImportError:
                print("   [INFO]  librosa 未安装，使用基础频谱通量节拍检测")
                pass
            except Exception as e_lib:
                print(f"   [WARN]  librosa 分析失败 ({e_lib})，使用基础检测")
                pass

            # ===== 逐帧提取特征 =====
            for i in range(num_frames):
                start = int(i * samples_per_frame)
                end = int((i + 1) * samples_per_frame)
                chunk = audio_f32[start:end]
                if len(chunk) == 0:
                    chunk = np.zeros(max(1, int(samples_per_frame)))

                # RMS 音量
                volume = float(np.sqrt(np.mean(chunk ** 2)))

                # FFT 频谱
                fft = np.fft.rfft(chunk * np.hanning(len(chunk)),
                                  n=int(2 ** np.ceil(np.log(max(len(chunk), 1)))))
                mag = np.abs(fft)
                # 分成 n_bins 个频段
                bin_size = max(1, len(mag) // n_bins)
                spectrum = np.array([
                    float(np.mean(mag[i * bin_size:(i + 1) * bin_size]))
                    for i in range(n_bins)
                ])
                spectrum = spectrum / (np.max(spectrum) + 1e-8)

                # 频段能量
                bass = float(np.mean(spectrum[:n_bins // 4]))
                mid = float(np.mean(spectrum[n_bins // 4:n_bins * 2 // 3]))
                treble = float(np.mean(spectrum[n_bins * 2 // 3:]))

                # 节拍检测：优先使用 librosa，回退到频谱通量
                if librosa_onsets is not None:
                    onset = float(librosa_onsets[i])
                else:
                    onset = float(np.mean(np.abs(spectrum - prev_spectrum)))
                    onset = min(1.0, onset * 5.0)

                beat = (librosa_beats is not None and i in librosa_beats) or \
                       (librosa_beats is None and onset > 0.3)

                prev_spectrum = spectrum.copy()

                features.append({
                    "volume":  min(1.0, volume * 5.0),
                    "spectrum": spectrum,
                    "bass":    min(1.0, bass * 3.0),
                    "mid":      min(1.0, mid * 3.0),
                    "treble":  min(1.0, treble * 3.0),
                    "onset":   min(1.0, onset),
                    "beat":     beat,
                    "tempo":    bpm_est,
                    "beat_frames": librosa_beats or [],
                })

            return features

        except Exception as e:
            print(f"[WARN] 音频分析失败: {e}")
            import traceback; traceback.print_exc()
            return None

    @staticmethod
    def generate_video(output_path, width=640, height=480, num_frames=300, fps=30,
                      codec="mp4v", palette_name="霓虹", particle_count=20,
                      animation_speed=1.0, effect_mode="元胞自动机",
                      audio_path=None, audio_reactive=0.5, progress_callback=None):
        """
        生成视频（按效果模式分发，支持音频驱动）

        Args:
            output_path:      输出视频路径
            width:            视频宽度
            height:           视频高度
            num_frames:       帧数
            fps:              帧率
            codec:            编码器
            palette_name:     调色板名称
            particle_count:   粒子数量（元胞自动机模式用）
            animation_speed:  动画速度倍率
            effect_mode:      效果模式，见 EFFECT_MODES
            audio_path:       音频文件路径（用于音频驱动，可选）
            audio_reactive:   音频驱动强度 0.0~1.0
            progress_callback: 进度回调函数

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        try:
            import numpy as np
            import cv2
        except ImportError as e:
            print(f"[ERR] 缺少依赖: {e}")
            return False

        # ========== 音频分析（如提供了音频文件）==========
        audio_features = None
        if audio_path and os.path.exists(audio_path):
            print(f"[AUDIO] 分析音频文件: {audio_path}")
            audio_features = VideoGenerator.analyze_audio(audio_path, num_frames, fps)
            if audio_features:
                print(f"   [OK] 音频分析完成，共 {len(audio_features)} 帧特征")
                print(f"   [MIXER] 音频驱动强度: {audio_reactive:.2f}")
            else:
                print(f"   [WARN] 音频分析失败，将不使用音频驱动")

        # 统一：打开视频写入器
        fourcc = cv2.VideoWriter_fourcc(*codec) if codec != "mp4v" else cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not video_writer.isOpened():
            print(f"[ERR] 无法创建视频文件: {output_path} (编码器 {codec} 可能不支持)")
            print("   尝试回退到 mp4v 编码器...")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            if not video_writer.isOpened():
                print(f"[ERR] 回退也失败")
                return False

        print(f"[VIDEO] 开始生成视频: {output_path}")
        print(f"   模式: {effect_mode} | 分辨率: {width}x{height} | 帧数: {num_frames} | FPS: {fps}")
        print(f"   调色板: {palette_name} | 速度: {animation_speed}x")
        if audio_features:
            print(f"   [AUDIO] 音频驱动: 已启用 (强度 {audio_reactive:.2f})")

        # 根据效果模式分发
        ok = False
        try:
            if effect_mode == "元胞自动机":
                ok = VideoGenerator._gen_ca(
                    video_writer, width, height, num_frames, fps,
                    palette_name, particle_count, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "渐变流动":
                ok = VideoGenerator._gen_gradient(
                    video_writer, width, height, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "几何图形":
                ok = VideoGenerator._gen_geometric(
                    video_writer, width, height, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "分形图案":
                ok = VideoGenerator._gen_fractal(
                    video_writer, width, height, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "噪声纹理":
                ok = VideoGenerator._gen_noise(
                    video_writer, width, height, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "脉冲波纹":
                ok = VideoGenerator._gen_pulse(
                    video_writer, width, height, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "频谱可视化":
                ok = VideoGenerator._gen_spectrum(
                    video_writer, width, height, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "反应扩散":
                ok = VideoGenerator._gen_reaction_diffusion(
                    video_writer, width, height, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "流动场":
                ok = VideoGenerator._gen_flow_field(
                    video_writer, width, height, num_frames, fps,
                    palette_name, particle_count, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "L系统分形":
                ok = VideoGenerator._gen_lsystem(
                    video_writer, width, height, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "CA引擎":
                ok = VideoGenerator._gen_ca_engine(
                    video_writer, width, height, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "粒子系统":
                ok = VideoGenerator._gen_particle_system(
                    video_writer, width, height, num_frames, fps,
                    palette_name, particle_count, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "公式驱动":
                ok = VideoGenerator._gen_formula(
                    video_writer, width, height, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "流体模拟":
                ok = VideoGenerator._gen_fluid(
                    video_writer, width, height, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "频谱柱形图":
                # 导入独立模块中的函数
                try:
                    from effects_video_gen import gen_bars
                    ok = gen_bars(
                        video_writer, width, height, num_frames, fps,
                        palette_name, animation_speed,
                        audio_features, audio_reactive, progress_callback
                    )
                except ImportError:
                    print("[ERR] effects_video_gen 模块未找到")
                    ok = False
            elif effect_mode == "波形曲线":
                try:
                    from effects_video_gen import gen_waveform
                    ok = gen_waveform(
                        video_writer, width, height, num_frames, fps,
                        palette_name, animation_speed,
                        audio_features, audio_reactive, progress_callback
                    )
                except ImportError:
                    print("[ERR] effects_video_gen 模块未找到")
                    ok = False
            elif effect_mode == "漩涡效果":
                try:
                    from effects_video_gen import gen_vortex
                    ok = gen_vortex(
                        video_writer, width, height, num_frames, fps,
                        palette_name, animation_speed,
                        audio_features, audio_reactive, progress_callback
                    )
                except ImportError:
                    print("[ERR] effects_video_gen 模块未找到")
                    ok = False
            elif effect_mode == "脉冲涟漪":
                try:
                    from effects_video_gen import gen_pulse
                    ok = gen_pulse(
                        video_writer, width, height, num_frames, fps,
                        palette_name, animation_speed,
                        audio_features, audio_reactive, progress_callback
                    )
                except ImportError:
                    print("[ERR] effects_video_gen 模块未找到")
                    ok = False

            # ==================== 组合效果（多效果叠加）====================
            elif effect_mode == "渐变+粒子":
                ok = VideoGenerator._gen_gradient_particle(
                    video_writer, w, h, num_frames, fps,
                    palette_name, particle_count, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "流体+几何":
                ok = VideoGenerator._gen_fluid_geometric(
                    video_writer, w, h, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "频谱+漩涡":
                ok = VideoGenerator._gen_spectrum_vortex(
                    video_writer, w, h, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            elif effect_mode == "分形+噪声":
                ok = VideoGenerator._gen_fractal_noise(
                    video_writer, w, h, num_frames, fps,
                    palette_name, animation_speed,
                    audio_features, audio_reactive, progress_callback
                )
            else:
                print(f"[ERR] 未知效果模式: {effect_mode}")
                return False
        finally:
            video_writer.release()

        if ok and progress_callback:
            progress_callback(100)

        return ok

    # ===================== 元胞自动机 + 粒子 =====================
    @staticmethod
    def _gen_ca(video_writer, w, h, num_frames, fps,
                 palette_name, particle_count, speed,
                 audio_features=None, audio_reactive=0.5, progress_callback=None):
        """元胞自动机 + 粒子。音频驱动：音量→粒子大小，低音→颜色亮度，节拍→粒子密度"""
        import numpy as np
        import cv2

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        palette_colors = np.array(palette_info["colors"], dtype=np.float32)
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        grid = np.random.randint(0, 2, (h, w), dtype=np.uint8)
        phases   = np.random.uniform(0, 2 * np.pi, particle_count)
        freq_x   = np.random.uniform(0.05, 0.15, particle_count) * speed
        freq_y   = np.random.uniform(0.03, 0.12, particle_count) * speed
        sizes    = np.random.randint(1, 5, particle_count)

        for i in range(num_frames):
            vol  = 1.0
            bass = 0.0
            beat_boost = 1.0
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                vol  = 1.0 + feat["volume"] * audio_reactive * 2.0
                bass = feat["bass"] * audio_reactive
                beat_boost = 1.0 + feat["onset"] * audio_reactive * 1.5

            # 更新 CA（使用 numba 加速或向量化版本）
            if _NUMBA_AVAILABLE:
                grid = _numba_ca_step(grid, h, w)
            else:
                neighbors = np.zeros_like(grid, dtype=np.uint8)
                neighbors[1:-1, 1:-1] = (
                    grid[0:-2, 0:-2] + grid[0:-2, 1:-1] + grid[0:-2, 2:] +
                    grid[1:-1, 0:-2] + grid[1:-1, 2:] +
                    grid[2:, 0:-2] + grid[2:, 1:-1] + grid[2:, 2:]
                )
                new_grid = np.zeros_like(grid)
                alive = (grid == 1) & ((neighbors == 2) | (neighbors == 3))
                born  = (grid == 0) & (neighbors == 3)
                new_grid[alive | born] = 1
                grid = new_grid

            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color

            ca_mask = grid.astype(bool)
            if np.any(ca_mask):
                ci = int(bass * len(palette_colors)) % len(palette_colors)
                color = np.clip(palette_colors[ci] * (1.0 + bass * 0.8), 0, 255).astype(np.uint8)
                for c in range(3):
                    frame[:, :, c][ca_mask] = color[c]

            active_particles = min(int(particle_count * beat_boost), particle_count)
            for p in range(min(active_particles, 100)):
                val_x = ((np.sin(i * freq_x[p] + phases[p]) * 0.5 + 0.5) * (w - 10))
                px = int(val_x) + 5
                val_y = ((np.cos(i * freq_y[p] + phases[p] * 0.7) * 0.5 + 0.5) * (h - 10))
                py = int(val_y) + 5
                sz = max(1, int(sizes[p] * vol))
                col_raw = palette_colors[p % len(palette_colors)]
                col = tuple([min(255, int(c * (1.0 + bass))) for c in col_raw])
                cv2.circle(frame, (px, py), sz, col, -1)
                cv2.circle(frame, (px, py), sz + 2, col, 1)

            video_writer.write(frame)
            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 视频已保存")
        return True

    # ===================== CA 引擎（配方驱动） =====================
    @staticmethod
    def _gen_ca_engine(video_writer, w, h, num_frames, fps,
                        palette_name, speed,
                        audio_features=None, audio_reactive=0.5, progress_callback=None):
        """CA 引擎效果 —— 使用 ca_engine.py 加载 JSON 配方。
        音频驱动：音量→演化速度，低音→颜色偏移，节拍→重置网格
        """
        import numpy as np
        import cv2

        try:
            from ca_engine import CARenderEngine
        except ImportError:
            print("[ERR] ca_engine 模块未找到")
            return False

        # 加载 CA 配方列表
        ca_dir = Path(__file__).parent / "ca_effects"
        if not ca_dir.exists():
            print(f"[ERR] ca_effects 目录不存在: {ca_dir}")
            return False

        recipe_files = sorted(ca_dir.glob("*.json"))
        if not recipe_files:
            print(f"[ERR] ca_effects 目录中没有 JSON 配方")
            return False

        total_recipes = len(recipe_files)
        print(f"[CA引擎] 找到 {total_recipes} 个配方")

        # 每个配方的帧数（循环使用配方）
        frames_per_recipe = max(60, num_frames // min(20, total_recipes))
        recipe_index = 0
        engine = None
        recipe_switch_frame = 0

        for i in range(num_frames):
            # 切换配方
            if i >= recipe_switch_frame or engine is None:
                recipe_path = str(recipe_files[recipe_index % total_recipes])
                try:
                    engine = CARenderEngine(recipe_path)
                    print(f"  [CA] 配方 {recipe_index % total_recipes + 1}/{total_recipes}: {engine.config.get('name', 'unknown')}")
                except Exception as e:
                    print(f"  [CA] 加载配方失败: {e}")
                    # 跳过此配方
                    recipe_index += 1
                    continue

                recipe_switch_frame = i + frames_per_recipe
                recipe_index += 1

            # 音频驱动参数
            vol = 1.0
            bass = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                vol = 1.0 + feat["volume"] * audio_reactive * 1.5
                bass = feat["bass"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            # 演化（音频驱动速度）
            steps = max(1, int(speed * vol * 3))
            for _ in range(steps):
                engine.step()

            # 获取颜色数组 (h, w, 3) uint8 RGB
            rgb = engine.get_color_array()

            # 调整大小以匹配视频分辨率
            if rgb.shape[0] != h or rgb.shape[1] != w:
                rgb = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_NEAREST)

            # 音频驱动颜色偏移（低音影响色相）
            if bass > 0.1:
                # 轻微颜色偏移
                shift = int(bass * 30)
                bgr = rgb[:, :, ::-1]  # RGB → BGR
                bgr = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
                bgr[:, :, 0] = (bgr[:, :, 0] + shift) % 180
                bgr = cv2.cvtColor(bgr, cv2.COLOR_HSV2BGR)
                frame = bgr
            else:
                frame = rgb[:, :, ::-1].copy()  # RGB → BGR

            # 音频节拍触发网格重置（一定概率）
            if onset > 0.8 and engine.t > 100:
                engine.reset()

            video_writer.write(frame)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧 (配方 {recipe_index}/{total_recipes})")

        print(f"[OK] CA引擎视频已保存")
        return True

    # ===================== 公式驱动 =====================
    @staticmethod
    def _gen_formula(video_writer, w, h, num_frames, fps,
                      palette_name, speed,
                      audio_features=None, audio_reactive=0.5, progress_callback=None):
        """公式驱动效果 —— 使用 FormulaEngine 生成参数曲线。
        音频驱动：音量→动画速度，低音→曲线缩放，节拍→切换模板
        """
        import numpy as np
        import cv2

        try:
            from effects_engine.formula_engine import FormulaEngine
        except ImportError:
            print("[ERR] effects_engine.formula_engine 模块未找到")
            return False

        # 可用模板列表
        TEMPLATES = ['spiral', 'cardioid', 'lissajous', 'rose', 'butterfly']
        template_index = 0
        engine = FormulaEngine()

        # 编译当前模板
        def _compile_template(name):
            params = engine.get_template_params(name)
            if not params:
                return None, None, 0, 0, 0
            fx = engine.compile_template(name, 'x')
            fy = engine.compile_template(name, 'y')
            t_min = params.get('t_min', 0)
            t_max = params.get('t_max', 6.28)
            t_step = params.get('t_step', 0.02)
            return fx, fy, t_min, t_max, t_step

        fx, fy, t_min, t_max, t_step = _compile_template(TEMPLATES[template_index])
        template_switch_frame = 0
        frames_per_template = max(90, num_frames // len(TEMPLATES))

        # 预计算调色板颜色
        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        palette_colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        for i in range(num_frames):
            # 切换模板
            if i >= template_switch_frame:
                template_index = (template_index + 1) % len(TEMPLATES)
                fx, fy, t_min, t_max, t_step = _compile_template(TEMPLATES[template_index])
                template_switch_frame = i + frames_per_template
                print(f"  [公式] 切换到模板: {TEMPLATES[template_index]}")

            # 音频驱动参数
            vol = 1.0
            bass = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                vol = 1.0 + feat["volume"] * audio_reactive * 1.5
                bass = feat["bass"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            # 创建空白帧
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color

            # 计算时间参数
            t = t_min + (i * speed * vol * t_step) % (t_max - t_min)
            n_points = int((t_max - t_min) / t_step)
            if n_points < 10:
                n_points = 100

            # 生成曲线点
            try:
                t_vals = np.linspace(t_min, t_max, n_points)
                x_vals = fx(t=t_vals)
                y_vals = fy(t=t_vals)

                # 归一化到屏幕坐标
                x_norm = (x_vals - x_vals.min()) / (x_vals.max() - x_vals.min() + 1e-8)
                y_norm = (y_vals - y_vals.min()) / (y_vals.max() - y_vals.min() + 1e-8)

                # 缩放到屏幕（留边距）
                margin = 50
                px = (x_norm * (w - 2 * margin) + margin).astype(np.int32)
                py = (y_norm * (h - 2 * margin) + margin).astype(np.int32)

                # 音频驱动：低音影响颜色
                color_index = int(bass * (len(palette_colors) - 1))
                color = tuple(palette_colors[color_index].tolist())

                # 绘制曲线
                for j in range(len(px) - 1):
                    cv2.line(frame, (px[j], py[j]), (px[j + 1], py[j + 1]), color, 2)
            except Exception as e:
                print(f"  [公式] 渲染错误: {e}")

            video_writer.write(frame)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 公式驱动视频已保存")
        return True

    # ===================== 流体模拟 =====================
    @staticmethod
    def _gen_fluid(video_writer, w, h, num_frames, fps,
                     palette_name, speed,
                     audio_features=None, audio_reactive=0.5, progress_callback=None):
        """流体模拟效果 —— 使用 FluidEngine 模拟流体动力学。
        音频驱动：音量→外力强度，低音→密度源，节拍→清空流体场
        """
        import numpy as np
        import cv2

        try:
            from effects_engine.fluid_engine import FluidEngine, COLOR_MAPS
        except ImportError:
            print("[ERR] effects_engine.fluid_engine 模块未找到")
            return False

        # 创建流体引擎（网格尺寸取较小值以提高性能）
        grid_w = max(32, w // 8)
        grid_h = max(32, h // 8)
        color_map = 'fire'  # 默认火焰颜色映射
        engine = FluidEngine(grid_w=grid_w, grid_h=grid_h, color_map=color_map)

        # 鼠标/触点位置（在网格坐标中）
        cx, cy = grid_w // 2, grid_h // 2

        for i in range(num_frames):
            # 音频驱动参数
            vol = 1.0
            bass = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                vol = 1.0 + feat["volume"] * audio_reactive * 2.0
                bass = feat["bass"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            # 施加外力（音频驱动）
            force_strength = 5.0 * vol
            fx = force_strength * np.sin(i * 0.02 * speed)
            fy = force_strength * np.cos(i * 0.02 * speed)

            # 在中心位置施加力
            engine.add_force_at(cx, cy, fx, fy, radius=3.0, dt=1.0)

            # 音频低音触发密度源
            if bass > 0.2:
                amount = bass * 0.2
                engine.add_density_at(cx, cy, amount=amount, radius=2.0)

            # 音频节拍触发清空
            if onset > 0.8:
                engine.clear()

            # 演化流体
            dt = 0.1 * speed * vol
            audio_dict = {'rms': vol * 0.5, 'bass': bass, 'energy': vol * 0.3}
            engine.step(dt, audio=audio_dict)

            # 渲染到 numpy 数组
            frame_rgb = engine.render_to_numpy(w, h)
            # render_to_numpy() 返回的是 RGB，需要转换为 BGR
            frame_bgr = frame_rgb[:, :, ::-1].copy()

            video_writer.write(frame_bgr)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧 (密度: {engine.density.mean():.3f})")

        print(f"[OK] 流体模拟视频已保存")
        return True

    # ===================== 渐变流动 =====================
    @staticmethod
    def _gen_gradient(video_writer, w, h, num_frames, fps,
                      palette_name, speed,
                      audio_features=None, audio_reactive=0.5, progress_callback=None):
        """渐变流动。音频驱动：音量→流动速度，高频→粒子数量，节拍→亮度闪烁"""
        import numpy as np
        import cv2

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.float32) / 255.0
        bg     = np.array(palette_info["bg"], dtype=np.float32) / 255.0

        Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
        X = (X / w - 0.5) * 2.0
        Y = (Y / h - 0.5) * 2.0

        for i in range(num_frames):
            vol = 1.0
            treble = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat   = audio_features[i]
                vol    = 1.0 + feat["volume"]  * audio_reactive * 1.5
                treble = feat["treble"] * audio_reactive
                onset  = feat["onset"]  * audio_reactive

            frame_f = np.zeros((h, w, 3), dtype=np.float32)
            frame_f[:, :] = bg * (1.0 + onset * 0.5)

            t = i * 0.02 * speed * vol

            n_layers = 3 + int(treble * 3)
            for layer in range(max(n_layers, 2)):
                angle = t * (0.5 + layer * 0.7)
                freq  = 2.0 + layer * 0.5
                xr = X * np.cos(angle) - Y * np.sin(angle)
                val = ((np.sin(xr * freq * np.pi + t * (1.0 + layer * 0.3)) + 1.0) * 0.5)
                val = np.clip(val, 0.0, 1.0)
                ci = layer % len(colors)
                for c in range(3):
                    frame_f[:, :, c] += val * colors[ci][c] * 0.5

            n_particles = 8 + int(treble * 20)
            for _ in range(n_particles):
                px = int((np.sin(t * 0.3 + random.random()) * 0.5 + 0.5) * (w - 1))
                py = int((np.cos(t * 0.2 + random.random()) * 0.5 + 0.5) * (h - 1))
                r = random.randint(3, 8)
                bg_col = tuple([min(1.0, float(c) + 0.3 + onset * 0.5) for c in bg])
                cv2.circle(frame_f, (px, py), r, bg_col, -1)

            frame = np.clip(frame_f * 255, 0, 255).astype(np.uint8)
            video_writer.write(frame)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 视频已保存")
        return True

    # ===================== 几何图形 =====================
    @staticmethod
    def _gen_geometric(video_writer, w, h, num_frames, fps,
                        palette_name, speed,
                        audio_features=None, audio_reactive=0.5, progress_callback=None):
        """几何图形。音频驱动：音量→图形大小，中音→旋转速度，节拍→颜色闪烁"""
        import numpy as np
        import cv2

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.float32)
        bg     = np.array(palette_info["bg"], dtype=np.uint8)

        cx, cy = w // 2, h // 2

        for i in range(num_frames):
            vol = 1.0
            mid = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat  = audio_features[i]
                vol   = 1.0 + feat["volume"] * audio_reactive * 1.5
                mid   = feat["mid"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg

            t = i * 0.01 * speed * (1.0 + mid * 0.5)

            n_shapes = 5
            for s in range(n_shapes):
                base_col = colors[s % len(colors)]
                if onset > 0.3:
                    col = np.clip(base_col * 1.8, 0, 255).astype(int)
                else:
                    col = np.clip(base_col * (0.7 + vol * 0.3), 0, 255).astype(int)
                col = tuple([int(c) for c in col])

                angle = t * (30 + s * 15) * (1.0 + mid * 0.3)
                scale = (0.3 + 0.2 * np.sin(t * 0.5 + s)) * vol
                sz = int(min(w, h) * max(scale, 0.05) * 0.3)

                ox = int(np.sin(t * 0.3 + s * 1.2) * w * 0.25)
                oy = int(np.cos(t * 0.25 + s * 0.9) * h * 0.25)
                ccx, ccy = cx + ox, cy + oy

                shape_type = s % 3
                if shape_type == 0:
                    rect_w = sz
                    rect_h = sz
                    box = cv2.boxPoints(((ccx, ccy), (rect_w, rect_h), angle))
                    box = np.int32(box)
                    cv2.drawContours(frame, [box], 0, col, 2)
                    fill_col = tuple([int(c * 0.4) for c in col])
                    cv2.fillPoly(frame, [box], fill_col)
                elif shape_type == 1:
                    r = max(sz // 2, 1)
                    cv2.circle(frame, (ccx, ccy), r, col, 2)
                    fill_col = tuple([int(c * 0.3) for c in col])
                    cv2.circle(frame, (ccx, ccy), r, fill_col, -1)
                else:
                    pts = []
                    for k in range(3):
                        a = angle * np.pi / 180.0 + k * 2.094
                        px = int(ccx + np.cos(a) * sz * 0.5)
                        py = int(ccy + np.sin(a) * sz * 0.5)
                        pts.append([px, py])
                    pts = np.array(pts, np.int32)
                    cv2.polylines(frame, [pts], True, col, 2)
                    fill_col = tuple([int(c * 0.35) for c in col])
                    cv2.fillPoly(frame, [pts], fill_col)

            video_writer.write(frame)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 视频已保存")
        return True

    # ===================== 分形图案（Julia 集） =====================
    @staticmethod
    def _gen_fractal(video_writer, w, h, num_frames, fps,
                      palette_name, speed,
                      audio_features=None, audio_reactive=0.5, progress_callback=None):
        """分形图案。音频驱动：音量→分形复杂度，高频→迭代次数，节拍→颜色翻转"""
        import numpy as np
        import cv2

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.float32) / 255.0
        bg     = np.array(palette_info["bg"], dtype=np.uint8)

        x_min, x_max = -1.8, 1.8
        y_min, y_max = -1.0, 1.0

        for i in range(num_frames):
            vol = 1.0
            bass = 0.0
            treble = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat   = audio_features[i]
                vol    = 1.0 + feat["volume"] * audio_reactive * 1.5
                bass   = feat["bass"]   * audio_reactive
                treble = feat["treble"] * audio_reactive
                onset  = feat["onset"]  * audio_reactive

            t = i * 0.008 * speed * (1.0 + bass * 0.3)

            c_mag = 0.7885 * vol
            cr = c_mag * np.cos(t)
            ci = c_mag * np.sin(t)

            x = np.linspace(x_min, x_max, w, dtype=np.float32)
            y = np.linspace(y_min, y_max, h, dtype=np.float32)
            X, Y = np.meshgrid(x, y)
            Zr = X.copy()
            Zi = Y.copy()

            max_iter = 32 + int(treble * 64)
            output = np.zeros((h, w), dtype=np.float32)
            mask = np.ones((h, w), dtype=bool)

            for it in range(max_iter):
                Zr2 = Zr * Zr
                Zi2 = Zi * Zi
                done = (Zr2 + Zi2) > 4.0
                output[mask & done] = (it / max_iter) * 255.0
                mask = mask & (~done)
                if not np.any(mask):
                    break
                new_Zr = Zr * Zr - Zi * Zi + cr
                Zi = 2.0 * Zr * Zi + ci
                Zr = new_Zr

            output[mask] = 255.0

            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg

            norm = output.astype(np.float32) / 255.0
            for c in range(3):
                shift = t * (1.0 + bass * 0.5) + c * 0.7
                if onset > 0.3:
                    cv = np.abs(np.sin(norm * np.pi * 4.0 + shift))
                else:
                    cv = np.sin(norm * np.pi * 2.0 + shift) * 0.5 + 0.5
                cv = np.clip(cv, 0.0, 1.0)
                frame[:, :, c] = (cv * colors[c % len(colors)][c] * 255).astype(np.uint8)

            video_writer.write(frame)

            if progress_callback and i % 5 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 视频已保存")
        return True

    # ===================== 噪声纹理 =====================
    @staticmethod
    def _gen_noise(video_writer, w, h, num_frames, fps,
                   palette_name, speed,
                   audio_features=None, audio_reactive=0.5, progress_callback=None):
        """噪声纹理。音频驱动：音量→噪声强度，全频段→颜色偏移，节拍→纹理密度"""
        import numpy as np
        import cv2

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg     = np.array(palette_info["bg"], dtype=np.uint8)

        grid_scale = 8
        gw, gh = max(2, w // grid_scale), max(2, h // grid_scale)

        def make_noise_frame(time_offset, vol=1.0):
            grid = np.random.rand(gh + 2, gw + 2).astype(np.float32) * vol
            up = cv2.resize(grid, (w, h), interpolation=cv2.INTER_LINEAR)
            up = cv2.GaussianBlur(up, (0, 0), max(w, h) * 0.02)
            up = (up - up.min()) / (up.max() - up.min() + 1e-8)
            return up

        prev_noise = make_noise_frame(0.0)
        next_noise = make_noise_frame(1.0)

        for i in range(num_frames):
            vol = 1.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat  = audio_features[i]
                vol   = 1.0 + feat["volume"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            alpha = (i * speed) % num_frames / num_frames
            if i % max(1, num_frames // 8) == 0:
                prev_noise = next_noise
                next_noise = make_noise_frame(i * 0.5, vol)

            noise = prev_noise * (1.0 - alpha) + next_noise * alpha
            noise = np.clip(noise, 0.0, 1.0)

            frame = np.zeros((h, w, 3), dtype=np.uint8)
            for c in range(3):
                channel = (noise * colors[c % len(colors)][c]).astype(np.uint8)
                frame[:, :, c] = channel

            # 节拍时加亮中心区域
            if onset > 0.4:
                cv2.circle(frame, (w // 2, h // 2), min(w, h) // 4,
                           tuple([min(255, int(c * 1.5)) for c in bg]), -1)

            video_writer.write(frame)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 视频已保存")
        return True

    # ===================== 脉冲波纹 =====================
    @staticmethod
    def _gen_pulse(video_writer, w, h, num_frames, fps,
                   palette_name, speed,
                   audio_features=None, audio_reactive=0.5, progress_callback=None):
        """脉冲波纹。音频驱动：音量→波纹数量，节拍→波纹速度，低音→波纹大小"""
        import numpy as np
        import cv2

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg     = np.array(palette_info["bg"], dtype=np.uint8)

        max_pulses = 10
        pulses = []  # [(cx, cy, current_radius, max_radius, color_idx)]

        for i in range(num_frames):
            vol = 1.0
            bass = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat  = audio_features[i]
                vol   = 1.0 + feat["volume"] * audio_reactive * 1.5
                bass  = feat["bass"]   * audio_reactive
                onset = feat["onset"]  * audio_reactive

            # 节拍时生成新波纹
            if onset > 0.3 or (i % max(1, int(20 / speed)) == 0):
                cx = random.randint(w // 4, 3 * w // 4)
                cy = random.randint(h // 4, 3 * h // 4)
                max_r = int(min(w, h) * (0.3 + bass * 0.5))
                ci = random.randint(0, len(colors) - 1)
                pulses.append([cx, cy, 0, max_r, ci])
                if len(pulses) > max_pulses:
                    pulses.pop(0)

            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg

            new_pulses = []
            for (cx, cy, r, max_r, ci) in pulses:
                new_r = int(r + max(1, int(speed * 8 * vol)))
                if new_r < max_r:
                    col = tuple([int(c) for c in colors[ci]])
                    thickness = max(1, 3 - int(new_r / max_r * 2))
                    cv2.circle(frame, (cx, cy), new_r, col, thickness)
                    new_pulses.append([cx, cy, new_r, max_r, ci])
                else:
                    # 波纹到达最大半径时，画一个逐渐消失的光晕
                    fade_col = tuple([min(255, int(c * 0.3)) for c in colors[ci]])
                    cv2.circle(frame, (cx, cy), max_r, fade_col, 1)

            pulses = new_pulses

            # 背景加一点粒子（音量越大越多）
            n_particles = int(vol * 5)
            for _ in range(n_particles):
                px = random.randint(0, w - 1)
                py = random.randint(0, h - 1)
                r = random.randint(1, 3)
                ci = random.randint(0, len(colors) - 1)
                col = tuple([int(c * 0.6) for c in colors[ci]])
                cv2.circle(frame, (px, py), r, col, -1)

            video_writer.write(frame)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 视频已保存")
        return True

    # ===================== 频谱可视化 =====================
    @staticmethod
    def _gen_spectrum(video_writer, w, h, num_frames, fps,
                      palette_name, speed,
                      audio_features=None, audio_reactive=0.5, progress_callback=None):
        """
        频谱可视化：类似音乐播放器的频谱柱状图 + 曲线
        必须提供 audio_features，否则退化为随机噪声纹理
        """
        import numpy as np
        import cv2

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg     = np.array(palette_info["bg"], dtype=np.uint8)

        n_bars = 32  # 频谱柱数量
        bar_w = max(1, w // (n_bars + 2))
        gap = max(1, bar_w // 10)

        for i in range(num_frames):
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg

            spectrum = None
            onset = 0.0
            bass = 0.0
            if audio_features and i < len(audio_features):
                spectrum = audio_features[i]["spectrum"]
                onset    = audio_features[i]["onset"]    * audio_reactive
                bass     = audio_features[i]["bass"]     * audio_reactive
            else:
                # 无音频时退化为随机频谱
                spectrum = np.random.rand(n_bars) * 0.3

            if spectrum is None:
                spectrum = np.random.rand(n_bars) * 0.3

            # 画频谱柱（从下往上）
            for b in range(min(n_bars, len(spectrum))):
                x = (b + 1) * bar_w
                bar_h = int(spectrum[b] * h * 0.9)
                bar_h = max(2, bar_h)
                # 颜色随频段变化
                col = tuple([int(c) for c in colors[b % len(colors)]])
                cv2.rectangle(frame, (x, h), (x + bar_w - gap, h - bar_h), col, -1)
                # 顶部高亮
                if bar_h > 4:
                    highlight = tuple([min(255, int(c * 1.5)) for c in col])
                    cv2.rectangle(frame, (x, h - bar_h), (x + bar_w - gap, h - bar_h + 3), highlight, -1)

            # 画频谱曲线（叠加）
            pts = []
            for b in range(min(n_bars, len(spectrum))):
                x = int((b + 1) * bar_w + bar_w // 2)
                y = int(h - spectrum[b] * h * 0.9)
                pts.append([x, y])

            if len(pts) > 2:
                pts = np.array(pts, np.int32)
                col = tuple([int(c * 0.7) for c in colors[0]])
                cv2.polylines(frame, [pts], False, col, 2)

            # 节拍闪烁效果
            if onset > 0.3:
                overlay = frame.copy()
                cv2.circle(overlay, (w // 2, h // 2), int(min(w, h) * 0.1 * bass * 5), (255, 255, 255), -1)
                cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)

            video_writer.write(frame)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 视频已保存")
        return True

    # ===================== 反应扩散（Gray-Scott 模型）=====================
    @staticmethod
    def _gen_reaction_diffusion(video_writer, w, h, num_frames, fps,
                                 palette_name, speed,
                                 audio_features=None, audio_reactive=0.5, progress_callback=None):
        """
        反应扩散系统（Gray-Scott 模型）
        模拟化学物质的扩散和反应，产生类似细胞分裂、珊瑚、斑图的有机图案。

        音频驱动：音量→反应速率，低频→馈送率F，高频→移除率K，节拍→重置种子
        """
        import numpy as np
        import cv2

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.float32) / 255.0
        bg = np.array(palette_info["bg"], dtype=np.float32) / 255.0

        # Gray-Scott 参数
        Du, Dv = 0.16, 0.08  # 扩散系数
        F_base, K_base = 0.035, 0.065  # 馈送率和移除率

        # 初始化化学场：U 均匀分布，V 局部种子
        U = np.ones((h, w), dtype=np.float32)
        V = np.zeros((h, w), dtype=np.float32)
        # 在中心区域放置 V 种子
        r = min(w, h) * 0.15
        cx, cy = w // 2, h // 2
        Y, X = np.ogrid[:h, :w]
        mask = (X - cx) ** 2 + (Y - cy) ** 2 < r ** 2
        U[mask] = 0.50
        V[mask] = 0.25
        # 添加随机扰动
        U += np.random.uniform(-0.01, 0.01, (h, w))
        V += np.random.uniform(-0.01, 0.01, (h, w))

        # 拉普拉斯核（5点差分）
        laplace_kernel = np.array([[0.05, 0.2, 0.05],
                                    [0.2, -1.0, 0.2],
                                    [0.05, 0.2, 0.05]], dtype=np.float32)

        for i in range(num_frames):
            vol = 1.0
            bass = 0.0
            treble = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                vol = 1.0 + feat["volume"] * audio_reactive * 2.0
                bass = feat["bass"] * audio_reactive
                treble = feat["treble"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            # 参数随音频动态调整
            F = F_base + bass * 0.03 - treble * 0.005  # 低音增加馈送
            K = K_base + treble * 0.01  # 高音增加移除
            dt = 0.3 * speed * vol  # 音频驱动时间步长

            # 节拍时重新播种
            if onset > 0.5 and i % max(1, int(30 / max(speed, 0.1))) == 0:
                sx = random.randint(w // 4, 3 * w // 4)
                sy = random.randint(h // 4, 3 * h // 4)
                rr = int(min(w, h) * 0.08 * vol)
                Y2, X2 = np.ogrid[:h, :w]
                seed_mask = (X2 - sx) ** 2 + (Y2 - sy) ** 2 < rr ** 2
                V[seed_mask] = np.clip(V[seed_mask] + 0.15 * vol, 0, 1)

            # 多步模拟（收敛更好）
            n_steps = max(1, int(vol * 1.5))
            if _NUMBA_AVAILABLE:
                for _ in range(n_steps):
                    U, V = _numba_gs_step(U, V, Du, Dv, F, K, dt / n_steps)
            else:
                for _ in range(n_steps):
                    # 拉普拉斯算子
                    Lu = cv2.filter2D(U, -1, laplace_kernel)
                    Lv = cv2.filter2D(V, -1, laplace_kernel)

                    # Gray-Scott 反应项
                    uvv = U * V * V
                    du = Du * Lu - uvv + F * (1.0 - U)
                    dv = Dv * Lv + uvv - (F + K) * V

                    U = np.clip(U + du * dt / n_steps, 0, 1)
                    V = np.clip(V + dv * dt / n_steps, 0, 1)

            # 将化学场映射到颜色
            v_norm = V.copy()
            # 使用 V 场生成颜色映射
            r_ch = np.clip(v_norm * colors[0][0] * 1.5 + bg[0], 0, 1)
            g_ch = np.clip(v_norm * colors[1 % len(colors)][1] * 1.5 + bg[1], 0, 1)
            b_ch = np.clip(v_norm * colors[2 % len(colors)][2] * 1.5 + bg[2], 0, 1)

            # U 场提供暗区纹理
            u_mask = 1.0 - U * 0.3
            r_ch *= u_mask
            g_ch *= u_mask
            b_ch *= u_mask

            frame = np.zeros((h, w, 3), dtype=np.float32)
            frame[:, :, 0] = r_ch
            frame[:, :, 1] = g_ch
            frame[:, :, 2] = b_ch

            # 节拍高亮
            if onset > 0.3:
                glow = np.exp(-((np.arange(h) - h / 2) ** 2)[:, None] / (h * 0.15) ** 2 -
                               ((np.arange(w) - w / 2) ** 2)[None, :] / (w * 0.15) ** 2)
                for c in range(3):
                    frame[:, :, c] += glow * onset * 0.6

            frame = np.clip(frame * 255, 0, 255).astype(np.uint8)
            video_writer.write(frame)

            if progress_callback and i % 5 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧 (反应扩散 F={F:.4f} K={K:.4f})")

        print(f"[OK] 视频已保存")
        return True

    # ===================== Perlin 流动场 ======================
    @staticmethod
    def _perlin_noise_2d(shape, scale=50.0, octaves=4, seed=0):
        """
        生成 2D Perlin 噪声（使用 numpy）

        Args:
            shape:   (h, w) 形状
            scale:   缩放因子（越小噪声越密）
            octaves: 八度数（叠加层数，越高细节越多）
            seed:    随机种子

        Returns:
            np.ndarray (h, w)
        """
        import numpy as np

        rng = np.random.RandomState(seed)
        h, w = shape

        def _fade(t):
            return 6 * t ** 5 - 15 * t ** 4 + 10 * t ** 3

        def _lerp(a, b, x):
            return a + x * (b - a)

        noise = np.zeros(shape, dtype=np.float32)
        amp = 1.0
        freq = 1.0

        for _ in range(octaves):
            # 网格尺寸
            grid_w = max(2, int(w * freq / scale) + 2)
            grid_h = max(2, int(h * freq / scale) + 2)
            freq_w = (grid_w - 1) / w
            freq_h = (grid_h - 1) / h

            # 随机梯度向量
            angles = rng.uniform(0, 2 * np.pi, (grid_h, grid_w))
            grad_x = np.cos(angles).astype(np.float32)
            grad_y = np.sin(angles).astype(np.float32)

            # 计算每个像素的网格坐标
            px = np.arange(w, dtype=np.float32) * freq_w
            py = np.arange(h, dtype=np.float32) * freq_h

            x0 = np.floor(px).astype(int)
            x1 = x0 + 1
            y0 = np.floor(py).astype(int)
            y1 = y0 + 1

            # 限制在边界内
            x0 = np.clip(x0, 0, grid_w - 1)
            x1 = np.clip(x1, 0, grid_w - 1)
            y0 = np.clip(y0, 0, grid_h - 1)
            y1 = np.clip(y1, 0, grid_h - 1)

            sx = _fade(px - x0)
            sy = _fade(py - y0)

            # 向量化计算
            n00 = grad_x[y0[:, None], x0[None, :]] * (px[None, :] - x0[None, :]) + \
                  grad_y[y0[:, None], x0[None, :]] * (py[:, None] - y0[:, None])
            n10 = grad_x[y0[:, None], x1[None, :]] * (px[None, :] - x1[None, :]) + \
                  grad_y[y0[:, None], x1[None, :]] * (py[:, None] - y0[:, None])
            n01 = grad_x[y1[:, None], x0[None, :]] * (px[None, :] - x0[None, :]) + \
                  grad_y[y1[:, None], x0[None, :]] * (py[:, None] - y1[:, None])
            n11 = grad_x[y1[:, None], x1[None, :]] * (px[None, :] - x1[None, :]) + \
                  grad_y[y1[:, None], x1[None, :]] * (py[:, None] - y1[:, None])

            nx0 = _lerp(n00, n10, sx[None, :])
            nx1 = _lerp(n01, n11, sx[None, :])
            layer = _lerp(nx0, nx1, sy[:, None])

            noise += layer * amp
            amp *= 0.5
            freq *= 2.0

        # 归一化到 0~1
        noise = (noise - noise.min()) / (noise.max() - noise.min() + 1e-8)
        return noise

    @staticmethod
    def _gen_flow_field(video_writer, w, h, num_frames, fps,
                         palette_name, particle_count, speed,
                         audio_features=None, audio_reactive=0.5, progress_callback=None):
        """
        Perlin 噪声流动场粒子系统
        粒子在 Perlin 噪声定义的向量场中流动，产生有机的、烟雾般的运动。

        音频驱动：音量→粒子速度，低频→流场扭曲，高频→粒子数量，节拍→颜色闪烁
        """
        import numpy as np
        import cv2

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.float32)
        bg = np.array(palette_info["bg"], dtype=np.float32) / 255.0

        n_particles = max(50, min(particle_count * 15, 800))
        # 初始化粒子位置
        px = np.random.uniform(0, w - 1, n_particles)
        py = np.random.uniform(0, h - 1, n_particles)
        # 每个粒子的生命周期和年龄
        age = np.random.uniform(0, 1, n_particles)
        lifespan = np.random.uniform(0.3, 1.0, n_particles)
        # 每个粒子的颜色索引
        color_idx = np.random.randint(0, len(colors), n_particles)

        noise_seed = random.randint(0, 10000)

        for i in range(num_frames):
            vol = 1.0
            bass = 0.0
            treble = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                vol = 1.0 + feat["volume"] * audio_reactive * 2.0
                bass = feat["bass"] * audio_reactive
                treble = feat["treble"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            # 生成流场 (Perlin noise 的两个通道 = 角度)
            t_offset = i * 0.005 * speed * vol
            noise_angle = VideoGenerator._perlin_noise_2d(
                (h // 8, w // 8), scale=3.0, octaves=3,
                seed=noise_seed + int(t_offset * 100)
            )
            noise_magnitude = VideoGenerator._perlin_noise_2d(
                (h // 8, w // 8), scale=5.0, octaves=2,
                seed=noise_seed + 5000 + int(t_offset * 100)
            )

            # 放大流场到全分辨率
            angle_field = cv2.resize(noise_angle, (w, h), interpolation=cv2.INTER_LINEAR)
            mag_field = cv2.resize(noise_magnitude, (w, h), interpolation=cv2.INTER_LINEAR)

            # 角度转为方向向量
            angle_rad = angle_field * np.pi * 2.0 * (1.0 + bass * 0.5)
            fx = np.cos(angle_rad) * mag_field
            fy = np.sin(angle_rad) * mag_field

            # 更新粒子位置（采样流场）
            px_int = np.clip(px.astype(int), 0, w - 1)
            py_int = np.clip(py.astype(int), 0, h - 1)
            move_x = fx[py_int, px_int] * speed * 3.0 * vol
            move_y = fy[py_int, px_int] * speed * 3.0 * vol

            px = (px + move_x) % w
            py = (py + move_y) % h

            # 更新年龄
            age += 0.005 * speed * vol
            reset_mask = age > lifespan
            px[reset_mask] = np.random.uniform(0, w, np.sum(reset_mask))
            py[reset_mask] = np.random.uniform(0, h, np.sum(reset_mask))
            age[reset_mask] = 0
            lifespan[reset_mask] = np.random.uniform(0.3, 1.0, np.sum(reset_mask))
            color_idx[reset_mask] = np.random.randint(0, len(colors), np.sum(reset_mask))

            # 渲染帧
            frame = np.zeros((h, w, 3), dtype=np.float32)
            frame[:, :] = bg

            # 运动模糊（衰减上一帧）
            alpha = 0.15
            # 获取上一帧近似（无法直接获取，使用 bg 衰减）
            frame = frame * (1.0 - alpha)

            # 绘制粒子轨迹
            active_mask = age < lifespan
            n_active = min(np.sum(active_mask), 600)
            active_indices = np.where(active_mask)[0][:n_active]

            for idx in active_indices:
                x, y = int(px[idx]), int(py[idx])
                if 0 <= x < w and 0 <= y < h:
                    ci = color_idx[idx]
                    alpha_val = (1.0 - age[idx] / lifespan[idx]) * 0.8
                    col = colors[ci] * alpha_val / 255.0
                    # 粒子大小随年龄和音量变化
                    sz = max(1, int((1.0 - age[idx] / lifespan[idx]) * 2.5 * vol))
                    cv2.circle(frame, (x, y), sz,
                              (float(col[0]), float(col[1]), float(col[2])), -1)

            # 节拍时全屏闪白
            if onset > 0.35:
                flash = onset * 0.4
                frame = np.clip(frame + flash, 0, 1)

            frame = np.clip(frame * 255, 0, 255).astype(np.uint8)
            video_writer.write(frame)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 视频已保存")
        return True

    # ===================== L-System 分形动画 ======================
    @staticmethod
    def _gen_lsystem(video_writer, w, h, num_frames, fps,
                      palette_name, speed,
                      audio_features=None, audio_reactive=0.5, progress_callback=None):
        """
        L-System 分形动画
        基于 Lindenmayer 系统的分形生长动画，支持分形树、Koch雪花、Sierpinski等。

        音频驱动：音量→生长速度，低频→分支角度，高频→线宽，节拍→颜色变化
        """
        import numpy as np
        import cv2

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.float32)
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        # L-System 预定义
        lsystems = [
            {
                "name": "分形树",
                "axiom": "X",
                "rules": {"X": "F-[[X]+X]+F[+FX]-X", "F": "FF"},
                "angle": 25,
            },
            {
                "name": "龙曲线",
                "axiom": "FX",
                "rules": {"X": "X+YF+", "Y": "-FX-Y"},
                "angle": 90,
            },
            {
                "name": "Sierpinski",
                "axiom": "F-G-G",
                "rules": {"F": "F-G+F+G-F", "G": "GG"},
                "angle": 120,
            },
            {
                "name": "Koch雪花",
                "axiom": "F++F++F",
                "rules": {"F": "F-F++F-F"},
                "angle": 60,
            },
        ]

        def _generate_lstring(axiom, rules, iterations):
            """生成 L-System 字符串"""
            s = axiom
            for _ in range(iterations):
                s = "".join(rules.get(c, c) for c in s)
            return s

        def _draw_lsystem(frame, lstring, angle_deg, cx, cy, step, thickness, color, start_angle=-90):
            """绘制 L-System"""
            import math
            angle_rad = math.radians(start_angle)
            stack = []
            x, y = cx, cy

            for cmd in lstring:
                if cmd == 'F' or cmd == 'G':
                    nx = x + math.cos(angle_rad) * step
                    ny = y + math.sin(angle_rad) * step
                    cv2.line(frame, (int(x), int(y)), (int(nx), int(ny)),
                            color, max(1, int(thickness)))
                    x, y = nx, ny
                elif cmd == '+':
                    angle_rad += math.radians(angle_deg)
                elif cmd == '-':
                    angle_rad -= math.radians(angle_deg)
                elif cmd == '[':
                    stack.append((x, y, angle_rad))
                elif cmd == ']':
                    if stack:
                        x, y, angle_rad = stack.pop()
                # 忽略其他字符

        # 每个 L-System 展示一段时间，循环切换
        frames_per_lsys = num_frames // len(lsystems) + 1

        for i in range(num_frames):
            vol = 1.0
            bass = 0.0
            treble = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                vol = 1.0 + feat["volume"] * audio_reactive * 2.0
                bass = feat["bass"] * audio_reactive
                treble = feat["treble"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            # 选择当前 L-System
            lsys_idx = min(i // frames_per_lsys, len(lsystems) - 1)
            lsys = lsystems[lsys_idx]

            # 迭代次数随音频动态变化（3-7次迭代）
            max_iter = 7
            base_iter = min(3 + int(bass * 3 + vol * 0.5), max_iter)
            # 在 L-System 变化时使用固定迭代，变化时用音频驱动
            iter_count = base_iter

            # 在帧内部分生成（模拟生长）
            progress = min(1.0, (i % frames_per_lsys) / (frames_per_lsys * 0.5))
            effective_iter = max(1, int(iter_count * progress))

            lstring = _generate_lstring(lsys["axiom"], lsys["rules"], effective_iter)

            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color

            # 颜色随节拍变化
            ci = (lsys_idx + int(onset * 3)) % len(colors)
            color = tuple([int(c) for c in colors[ci]])
            # 分支颜色渐变
            color2 = tuple([int(c) for c in colors[(ci + 1) % len(colors)]])

            # 绘制参数
            cx, cy = w // 2, h - 20
            step = min(w, h) * 0.02 * (1.0 + bass * 0.3)
            thickness = max(1, 1 + bass * 3 + treble * 2)
            angle = lsys["angle"] + bass * 10 - treble * 5  # 角度动态变化

            _draw_lsystem(frame, lstring, angle, cx, cy, step, thickness, color)

            # 第二层叠加（不同颜色，轻微偏移）
            if len(lstring) < 10000:
                color_blend = tuple([int((c1 + c2) // 2) for c1, c2 in zip(color, color2)])
                step2 = step * 0.8
                _draw_lsystem(frame, lstring[:min(len(lstring), 5000)],
                            angle * 1.1, cx, cy - 10, step2,
                            max(1, thickness // 2), color_blend)

            # 节拍闪烁
            if onset > 0.3:
                overlay = np.zeros_like(frame)
                cv2.circle(overlay, (w // 2, h // 2), int(min(w, h) * 0.15), (255, 255, 255), -1)
                cv2.addWeighted(overlay, onset * 0.3, frame, 1.0, 0, frame)

            # 显示当前系统名称
            cv2.putText(frame, f"L-System: {lsys['name']} (iter={effective_iter})",
                       (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            video_writer.write(frame)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧 ({lsys['name']}, iter={effective_iter})")

        print(f"[OK] 视频已保存")
        return True

    # ===================== CA引擎（64种细胞自动机配方）=====================
    @staticmethod
    def _gen_ca_engine(video_writer, w, h, num_frames, fps,
                        palette_name, speed,
                        audio_features=None, audio_reactive=0.5, progress_callback=None):
        """
        CA引擎效果：集成 draw 项目的 64+ 种细胞自动机配方
        使用数学公式驱动的连续细胞自动机引擎，支持：
        - Game of Life、反应扩散、Lenia、BZ反应、DLA 等
        - 音频驱动：节拍→自动切换配方，音量→演化步数，低频→颜色偏移

        需要 ca_effects/ 目录下的 JSON 配方文件。
        """
        import numpy as np
        import cv2

        # 加载 CA 引擎
        try:
            from ca_engine import CARenderEngine
        except ImportError:
            print("[ERR] ca_engine 模块未找到，请确保 ca_engine.py 在模块路径中")
            return False

        # 加载配方列表
        ca_effects_dir = Path(__file__).parent / "ca_effects"
        if not ca_effects_dir.exists():
            print(f"[ERR] CA配方目录不存在: {ca_effects_dir}")
            return False

        recipes = {}
        try:
            recipes = load_ca_recipes(str(ca_effects_dir))
        except Exception as e:
            print(f"[ERR] 加载CA配方失败: {e}")
            return False

        if not recipes:
            print("[ERR] 没有找到CA配方文件")
            return False

        recipe_names = sorted(recipes.keys())
        print(f"[CA引擎] 已加载 {len(recipes)} 个CA配方")

        # 为适配视频尺寸，限制渲染分辨率为 max(h/2, h)
        ca_h = min(h, max(h // 2, 64))
        ca_w = min(w, max(w // 2, 64))
        ca_h = (ca_h // 8) * 8  # 保证 8 的倍数
        ca_w = (ca_w // 8) * 8

        engine = None
        current_recipe_idx = -1
        recipe_frames = 0
        frames_per_recipe = max(30, num_frames // min(len(recipes), 5))  # 每种配方至少30帧

        def _switch_recipe(idx):
            """切换到指定索引的配方"""
            nonlocal engine, recipe_frames
            recipe_frames = 0
            name = recipe_names[idx]
            path = recipes[name]
            try:
                # 创建新的引擎并覆盖尺寸参数
                import json
                with open(path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                config['grid']['width'] = ca_w
                config['grid']['height'] = ca_h

                # 通过临时文件加载
                import tempfile
                tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
                json.dump(config, tmp)
                tmp.close()

                engine = CARenderEngine(tmp.name)
                os.unlink(tmp.name)
                print(f"[CA引擎] 切换配方: {name}")
                return True
            except Exception as e:
                print(f"[CA引擎] 加载配方 '{name}' 失败: {e}")
                return False

        # 初始加载第一个配方
        if not _switch_recipe(0):
            return False

        # 使用 OpenCV 的颜色偏移（模拟调色板效果）
        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        palette_colors = np.array(palette_info["colors"], dtype=np.float32)

        for i in range(num_frames):
            vol = 1.0
            bass = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                vol = 1.0 + feat["volume"] * audio_reactive * 2.0
                bass = feat["bass"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            # 配方轮换：按时间或在强节拍时切换
            recipe_frames += 1
            should_switch = (recipe_frames >= frames_per_recipe) or \
                            (onset > 0.7 and recipe_frames > 15)
            if should_switch:
                next_idx = (current_recipe_idx + 1) % len(recipes)
                if _switch_recipe(next_idx):
                    current_recipe_idx = next_idx

            # 演化（步数与音量相关）
            steps = max(1, int(vol * speed * 2))
            engine.step_n(steps)

            # 获取颜色帧
            ca_frame = engine.get_color_array()  # (h, w, 3) uint8 RGB

            # 缩放到目标尺寸
            ca_frame = cv2.resize(ca_frame, (w, h), interpolation=cv2.INTER_LINEAR)

            # 应用颜色偏移（基于音频 + 调色板）
            ca_float = ca_frame.astype(np.float32)
            color_shift = palette_colors[0] * bass * 0.3  # 低频→颜色偏移
            for c in range(3):
                ca_float[:, :, c] = np.clip(ca_float[:, :, c] + color_shift[c], 0, 255)

            # 节拍闪烁
            if onset > 0.4:
                flash = onset * 60
                ca_float = np.clip(ca_float + flash, 0, 255)

            frame = ca_float.astype(np.uint8)
            video_writer.write(frame)

            # 在帧上叠加配方名
            if i % 30 == 0:
                name = recipe_names[current_recipe_idx] if current_recipe_idx >= 0 else "???"
                cv2.putText(frame, name, (8, h - 8), cv2.FONT_HERSHEY_SIMPLEX,
                           0.4, (200, 200, 200), 1)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                name = recipe_names[current_recipe_idx] if current_recipe_idx >= 0 else "???"
                print(f"   进度: {i}/{num_frames} 帧 (配方: {name})")

        print(f"[OK] 视频已保存")
        return True

    # ===================== 粒子系统 =====================
    @staticmethod
    def _gen_particle_system(video_writer, w, h, num_frames, fps,
                                palette_name, particle_count, speed,
                                audio_features=None, audio_reactive=0.5, progress_callback=None):
        """
        粒子系统效果：使用 particles/ 模块的 ParticleSystem 渲染粒子动画。
        支持多种预设（火焰、烟花、雨、雪、漩涡等）。
        音频驱动：音量→粒子速度/大小，低音→颜色亮度，节拍→粒子爆发
        """
        import math, random
        import numpy as np

        from particles.particle_core import (
            ParticleSystem, Emitter, ForceField,
            EmitterShape, gradient_to_curve, create_fireworks_emitters,
        )
        from particles.renderer import render_particles_to_frame

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        color_tuples = [tuple(int(c) for c in palette_info["colors"][i])
                        for i in range(len(palette_info["colors"]))]
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        ps = ParticleSystem(max_particles=max(particle_count * 10, 2000))

        # 重力
        ps.add_force_field(ForceField(field_type='gravity', strength=200.0))

        # 随机额外力场
        if random.random() > 0.4:
            ft = random.choice(['vortex', 'turbulence', 'wind'])
            if ft == 'vortex':
                ps.add_force_field(ForceField(
                    field_type='vortex', x=w/2, y=h/2,
                    strength=3.0 * speed, vortex_clockwise=random.choice([True, False]),
                ))
            elif ft == 'turbulence':
                ps.add_force_field(ForceField(
                    field_type='turbulence', strength=2.0 * speed,
                ))
            else:
                ps.add_force_field(ForceField(
                    field_type='wind', strength=80.0 * speed,
                ))

        # 主发射器（多个，随机位置+颜色）
        n_emitters = max(1, min(4, len(color_tuples)))
        for ei in range(n_emitters):
            cx = w * (0.2 + 0.6 * random.random())
            cy = h * (0.2 + 0.6 * random.random())
            color = color_tuples[ei % len(color_tuples)]
            shape = EmitterShape(
                shape_type=random.choice(['point', 'circle', 'sphere', 'rectangle']),
                radius=min(w, h) * random.uniform(0.05, 0.15),
            )
            em = Emitter(
                x=cx, y=cy,
                rate=particle_count * 0.5,
                spread=math.pi * random.uniform(0.3, 0.8),
                direction=math.pi * random.uniform(0, 2),
                speed=100.0 * speed,
                life=2.0 + random.random() * 2.0,
                size=3.0, color=color,
                color_over_lifetime=gradient_to_curve([
                    color,
                    tuple(min(255, int(c*1.3)) for c in color),
                    (min(255, color[0]//2), min(255, color[1]//2), min(255, color[2]//2)),
                ]),
                size_over_lifetime=[(0.0, 4.0), (0.5, 2.0), (1.0, 0.5)],
                trail_enabled=(random.random() > 0.5),
                trail_length=random.randint(6, 15),
                shape=shape,
            )
            ps.add_emitter(em)

        # 底部火焰发射器
        fire_color = color_tuples[0]
        fire_em = Emitter(
            x=w/2, y=h,
            rate=particle_count * 0.8,
            spread=0.4, direction=-math.pi/2,
            speed=120.0 * speed,
            life=1.5 + random.random(),
            size=3.5, color=fire_color,
            color_over_lifetime=gradient_to_curve([
                (255, 255, 200), fire_color,
                (min(255, fire_color[0]//2), min(255, fire_color[1]//2), min(255, fire_color[2]//2)),
                (30, 10, 5),
            ]),
            size_over_lifetime=[(0.0, 5.0), (0.2, 3.0), (1.0, 0.3)],
            trail_enabled=True, trail_length=10,
        )
        ps.add_emitter(fire_em)

        # 烟花爆发计时
        fireworks_interval = max(30, int(fps * 1.5))
        firework_emitters = create_fireworks_emitters(w/2, h/2)

        for i in range(num_frames):
            vol = 1.0
            bass = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                vol = 1.0 + feat["volume"] * audio_reactive * 2.0
                bass = feat["bass"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            # 节拍时触发烟花爆发
            if (onset > 0.4 or i % fireworks_interval == 0) and i > 10:
                fx = random.randint(int(w*0.2), int(w*0.8))
                fy = random.randint(int(h*0.2), int(h*0.6))
                for fe in firework_emitters:
                    fe.x = fx
                    fe.y = fy
                    fe.rate = 200.0 * vol
                    burst_particles = fe.emit(dt=0.0)
                    for bp in burst_particles:
                        if len(ps.particles) < ps.max_particles:
                            ps.particles.append(bp)
                    fe.rate = 0  # 单次爆发

            # 更新粒子系统
            adt = 1.0 / fps * speed * vol
            audio_data = None
            if audio_features and i < len(audio_features):
                audio_data = {
                    'rms': audio_features[i]["volume"],
                    'bass': bass,
                    'onset': onset,
                }
            ps.update(adt, audio_data)

            # 渲染帧
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color
            render_particles_to_frame(
                frame, ps.particles,
                blend_mode='additive',
                smooth_trail=True, glow_radius=2,
            )

            # 节拍闪烁
            if onset > 0.4:
                try:
                    import cv2
                    cv2.circle(frame, (w//2, h//2),
                              int(min(w, h) * 0.1 * bass * 5),
                              (255, 255, 255), -1)
                except ImportError:
                    pass

            video_writer.write(frame)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧 (粒子数: {ps.get_particle_count()})")

        print(f"[OK] 粒子系统视频已保存")
        return True

    # ===================== 公式驱动 =====================
    @staticmethod
    def _gen_formula(video_writer, w, h, num_frames, fps,
                             palette_name, speed,
                             audio_features=None, audio_reactive=0.5, progress_callback=None):
        """
        公式驱动效果：使用 effects_engine/formula_engine.py 的数学表达式渲染图案。
        支持多种内置模板（spiral, cardioid, lissajous, rose, butterfly 等）。
        音频驱动：音量→公式参数，频率→颜色映射。
        """
        import math, random
        import numpy as np

        from effects_engine.formula_engine import FormulaEngine

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.float32)
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        engine = FormulaEngine()
        template_names = list(engine.TEMPLATES.keys())
        chosen = random.choice(template_names)
        template = engine.get_template_params(chosen)

        x_func = engine.compile_template(chosen, 'x')
        y_func = engine.compile_template(chosen, 'y')

        t_min = template.get('t_min', 0)
        t_max = template.get('t_max', 12.56)
        t_step = template.get('t_step', 0.05)
        t_vals = np.arange(t_min, t_max, t_step)
        n_pts = len(t_vals)

        x_static = x_func(t=t_vals)
        y_static = y_func(t=t_vals)

        for i in range(num_frames):
            vol = 1.0
            bass = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                vol = 1.0 + feat["volume"] * audio_reactive * 1.5
                bass = feat["bass"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            scale = 1.0 + vol * 0.3
            rot = (i * 0.005 * speed) % (2 * math.pi)
            color_off = (i * 0.002 * speed) % 1.0

            cos_r = math.cos(rot)
            sin_r = math.sin(rot)
            x_rot = (x_static * cos_r - y_static * sin_r) * scale
            y_rot = (x_static * sin_r + y_static * cos_r) * scale

            pts_x = ((x_rot + 1.0) * 0.5 * w).astype(np.int32)
            pts_y = ((y_rot + 1.0) * 0.5 * h).astype(np.int32)

            mask = (pts_x >= 0) & (pts_x < w) & (pts_y >= 0) & (pts_y < h)
            pts_x = pts_x[mask]
            pts_y = pts_y[mask]

            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color

            n_valid = len(pts_x)
            col_off = int(color_off * len(colors)) % len(colors)

            for pi in range(n_valid - 1):
                x0, y0 = int(pts_x[pi]), int(pts_y[pi])
                x1, y1 = int(pts_x[pi + 1]), int(pts_y[pi + 1])
                ci = (pi + col_off) % len(colors)
                cr, cg, cb = int(colors[ci][0]), int(colors[ci][1]), int(colors[ci][2])
                thickness = max(1, int(1 + vol * 2))
                # 简化绘制：直接画点
                for dx2 in range(-thickness, thickness + 1):
                    for dy2 in range(-thickness, thickness + 1):
                        nx, ny = x0 + dx2, y0 + dy2
                        if 0 <= nx < w and 0 <= ny < h:
                            frame[ny, nx, 0] = min(255, cr)
                            frame[ny, nx, 1] = min(255, cg)
                            frame[ny, nx, 2] = min(255, cb)

            if onset > 0.3:
                cx2, cy2 = w // 2, h // 2
                try:
                    import cv2
                    cv2.circle(frame, (cx2, cy2), int(min(w, h) * 0.1 * bass * 5),
                              (255, 255, 255), -1)
                except ImportError:
                    pass

            video_writer.write(frame)
            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧 (模板: {chosen})")

        print(f"[OK] 公式驱动视频已保存")
        return True

    # ===================== 流体模拟 =====================
    @staticmethod
    def _gen_fluid(video_writer, w, h, num_frames, fps,
                           palette_name, speed,
                           audio_features=None, audio_reactive=0.5, progress_callback=None):
        """
        流体模拟效果：使用 effects_engine/fluid_engine.py 的 Stable Fluids 算法。
        """
        import math, random
        import numpy as np

        from effects_engine.fluid_engine import FluidEngine, COLOR_MAPS

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        grid_w = max(32, w // 4)
        grid_h = max(32, h // 4)
        color_map = random.choice(list(COLOR_MAPS.keys()))
        fluid = FluidEngine(grid_w=grid_w, grid_h=grid_h, color_map=color_map)

        cx = grid_w // 2
        cy = grid_h // 2
        fluid.add_density_at(cx, cy, amount=0.5, radius=grid_w * 0.1)

        for i in range(num_frames):
            vol = 1.0
            bass = 0.0
            onset = 0.0
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                vol = 1.0 + feat["volume"] * audio_reactive * 2.0
                bass = feat["bass"] * audio_reactive
                onset = feat["onset"] * audio_reactive

            if random.random() < 0.1 + vol * 0.2:
                fx = random.randint(1, grid_w - 2)
                fy = random.randint(1, grid_h - 2)
                fluid.add_density_at(fx, fy, amount=0.05 * vol, radius=2.0)

            if onset > 0.4:
                fx = random.randint(1, grid_w - 2)
                fy = random.randint(1, grid_h - 2)
                fluid.add_density_at(fx, fy, amount=0.2 * vol, radius=grid_w * 0.05)

            force_x = math.sin(i * 0.01 * speed) * 3.0 * vol
            force_y = math.cos(i * 0.008 * speed) * 3.0 * vol
            fluid.add_force_at(cx, cy, force_x, force_y, radius=grid_w * 0.08, dt=1.0 / fps)

            fluid.step(dt=1.0 / fps * speed, audio=None)

            frame_rgb = fluid.render_to_numpy(w, h)
            if frame_rgb is not None:
                final = np.zeros((h, w, 3), dtype=np.uint8)
                final[:, :] = bg_color
                # 简化叠加
                for y in range(h):
                    for x in range(w):
                        f = frame_rgb[y, x].astype(np.float32)
                        if f[0] > 10 or f[1] > 10 or f[2] > 10:
                            a = min(1.0, (f[0] + f[1] + f[2]) / (3.0 * 255.0))
                        else:
                            a = 0.0
                        final[y, x, 0] = int(bg_color[0] * (1.0 - a) + f[0] * a)
                        final[y, x, 1] = int(bg_color[1] * (1.0 - a) + f[1] * a)
                        final[y, x, 2] = int(bg_color[2] * (1.0 - a) + f[2] * a)
                video_writer.write(final)
            else:
                video_writer.write(np.zeros((h, w, 3), dtype=np.uint8))

            if progress_callback and i % 5 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 流体模拟视频已保存")
        return True

    # ===================== 组合效果：渐变+粒子 =====================
    @staticmethod
    def _gen_gradient_particle(video_writer, w, h, num_frames, fps,
                                palette_name, particle_count, speed,
                                audio_features=None, audio_reactive=0.5, progress_callback=None):
        """渐变流动 + 粒子系统（多效果叠加）"""
        import numpy as np
        import cv2
        import math
        import random

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.float32) / 255.0
        bg = np.array(palette_info["bg"], dtype=np.float32) / 255.0

        # 初始化粒子
        particles = []
        for _ in range(particle_count * 2):  # 更多粒子
            particles.append({
                'x': random.uniform(0, w),
                'y': random.uniform(0, h),
                'vx': random.uniform(-2, 2) * speed,
                'vy': random.uniform(-2, 2) * speed,
                'size': random.randint(2, 8),
                'color_idx': random.randint(0, len(colors) - 1)
            })

        Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
        X = (X / w - 0.5) * 2.0
        Y = (Y / h - 0.5) * 2.0

        for i in range(num_frames):
            # 渲染渐变背景
            frame_f = np.zeros((h, w, 3), dtype=np.float32)
            frame_f[:, :] = bg

            vol = 1.0
            if audio_features and i < len(audio_features):
                vol = 1.0 + audio_features[i]["volume"] * audio_reactive * 1.5

            t = i * 0.02 * speed * vol

            # 渐变流动
            for layer in range(3):
                angle = t * (0.5 + layer * 0.7)
                freq = 2.0 + layer * 0.5
                xr = X * np.cos(angle) - Y * np.sin(angle)
                val = ((np.sin(xr * freq * np.pi + t * (1.0 + layer * 0.3)) + 1.0) * 0.5)
                val = np.clip(val, 0.0, 1.0)
                ci = layer % len(colors)
                for c in range(3):
                    frame_f[:, :, c] += val * colors[ci][c] * 0.3

            # 添加粒子叠加层
            particle_frame = np.zeros((h, w, 3), dtype=np.float32)
            for p in particles:
                px = int(p['x'])
                py = int(p['y'])
                if 0 <= px < w and 0 <= py < h:
                    col = colors[p['color_idx']]
                    cv2.circle(particle_frame, (px, py), p['size'], (float(col[0]), float(col[1]), float(col[2])), -1)

                # 更新粒子位置
                p['x'] += p['vx']
                p['y'] += p['vy']
                if p['x'] < 0 or p['x'] >= w:
                    p['vx'] *= -1
                if p['y'] < 0 or p['y'] >= h:
                    p['vy'] *= -1

            # 混合渐变背景和粒子层
            blended = blend_frames(
                (frame_f * 255).astype(np.uint8),
                (particle_frame * 255).astype(np.uint8),
                blend_mode="add",
                alpha=0.6
            )

            video_writer.write(blended)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 渐变+粒子 组合视频已保存")
        return True

    # ===================== 组合效果：流体+几何 =====================
    @staticmethod
    def _gen_fluid_geometric(video_writer, w, h, num_frames, fps,
                               palette_name, speed,
                               audio_features=None, audio_reactive=0.5, progress_callback=None):
        """流体模拟 + 几何图形（多效果叠加）"""
        import numpy as np
        import cv2
        import random

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg = np.array(palette_info["bg"], dtype=np.uint8)

        # 流体模拟初始化
        grid = np.zeros((h, w), dtype=np.float32)
        velocity = np.zeros((h, w, 2), dtype=np.float32)

        cx, cy = w // 2, h // 2

        for i in range(num_frames):
            # 更新流体
            grid = np.roll(grid, 1, axis=0) * 0.99
            grid = np.roll(grid, 1, axis=1) * 0.99

            # 添加扰动
            grid[cx-10:cx+10, cy-10:cy+10] += 1.0

            # 渲染流体层
            fluid_frame = np.zeros((h, w, 3), dtype=np.uint8)
            fluid_frame[:, :] = bg

            # 使用颜色映射显示流体
            grid_norm = np.clip(grid * 255, 0, 255).astype(np.uint8)
            for c in range(3):
                fluid_frame[:, :, c] = grid_norm * (colors[0][c] / 255.0)

            # 添加几何图形叠加层
            geo_frame = np.zeros((h, w, 3), dtype=np.uint8)

            vol = 1.0
            if audio_features and i < len(audio_features):
                vol = 1.0 + audio_features[i]["volume"] * audio_reactive

            # 绘制旋转几何图形
            angle = i * 0.02 * speed
            num_shapes = 3
            for s in range(num_shapes):
                shape_angle = angle + s * (2 * 3.14159 / num_shapes)
                dist = 100 + s * 50
                sx = int(cx + dist * np.cos(shape_angle))
                sy = int(cy + dist * np.sin(shape_angle))
                size = int(30 * vol)
                col = tuple([int(c) for c in colors[s % len(colors)]])
                cv2.circle(geo_frame, (sx, sy), size, col, 2)

            # 混合流体和几何层
            blended = blend_frames(
                fluid_frame,
                geo_frame,
                blend_mode="screen",
                alpha=0.7
            )

            video_writer.write(blended)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 流体+几何 组合视频已保存")
        return True

    # ===================== 组合效果：频谱+漩涡 =====================
    @staticmethod
    def _gen_spectrum_vortex(video_writer, w, h, num_frames, fps,
                               palette_name, speed,
                               audio_features=None, audio_reactive=0.5, progress_callback=None):
        """频谱可视化 + 漩涡效果（多效果叠加）"""
        import numpy as np
        import cv2
        import random

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg = np.array(palette_info["bg"], dtype=np.uint8)

        cx, cy = w // 2, h // 2

        for i in range(num_frames):
            # 渲染频谱层
            spectrum_frame = np.zeros((h, w, 3), dtype=np.uint8)
            spectrum_frame[:, :] = bg

            spectrum = None
            if audio_features and i < len(audio_features):
                spectrum = audio_features[i]["spectrum"]

            if spectrum is None:
                spectrum = np.random.rand(32) * 0.3

            # 绘制频谱柱
            n_bars = 32
            bar_w = max(1, w // (n_bars + 2))
            for b in range(min(n_bars, len(spectrum))):
                x = (b + 1) * bar_w
                bar_h = int(spectrum[b] * h * 0.9)
                bar_h = max(2, bar_h)
                col = tuple([int(c) for c in colors[b % len(colors)]])
                cv2.rectangle(spectrum_frame, (x, h), (x + bar_w - 1, h - bar_h), col, -1)

            # 添加漩涡叠加层
            vortex_frame = np.zeros((h, w, 3), dtype=np.uint8)

            t = i * 0.01 * speed
            n_particles = 100
            for p in range(n_particles):
                angle = t + p * (2 * 3.14159 / n_particles)
                radius = 50 + (p % 10) * 20
                px = int(cx + radius * np.cos(angle) * (1.0 + 0.3 * np.sin(t * 0.5)))
                py = int(cy + radius * np.sin(angle) * (1.0 + 0.3 * np.cos(t * 0.5)))
                size = 3
                col = tuple([int(c * 0.8) for c in colors[p % len(colors)]])
                cv2.circle(vortex_frame, (px, py), size, col, -1)

            # 混合频谱和漩涡层
            blended = blend_frames(
                spectrum_frame,
                vortex_frame,
                blend_mode="add",
                alpha=0.5
            )

            video_writer.write(blended)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 频谱+漩涡 组合视频已保存")
        return True

    # ===================== 组合效果：分形+噪声 =====================
    @staticmethod
    def _gen_fractal_noise(video_writer, w, h, num_frames, fps,
                              palette_name, speed,
                              audio_features=None, audio_reactive=0.5, progress_callback=None):
        """分形图案 + 噪声纹理（多效果叠加）"""
        import numpy as np
        import cv2
        import random
        import math

        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        colors = np.array(palette_info["colors"], dtype=np.float32) / 255.0
        bg = np.array(palette_info["bg"], dtype=np.float32) / 255.0

        for i in range(num_frames):
            # 渲染分形层
            fractal_frame = np.zeros((h, w, 3), dtype=np.float32)
            fractal_frame[:, :] = bg

            t = i * 0.005 * speed

            # 简化分形：使用多重噪声
            Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
            X = X / w
            Y = Y / h

            for octave in range(4):
                freq = 2 ** octave
                noise = np.sin(X * freq * 10 + t) * np.cos(Y * freq * 10 + t * 0.7)
                noise = (noise + 1.0) * 0.5
                ci = octave % len(colors)
                for c in range(3):
                    fractal_frame[:, :, c] += noise * colors[ci][c] * 0.25

            fractal_frame = np.clip(fractal_frame, 0.0, 1.0)

            # 添加噪声叠加层
            noise_frame = np.random.rand(h, w, 3).astype(np.float32) * 0.3

            # 混合分形和噪声层
            blended = blend_frames(
                (fractal_frame * 255).astype(np.uint8),
                (noise_frame * 255).astype(np.uint8),
                blend_mode="overlay",
                alpha=0.4
            )

            video_writer.write(blended)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")

        print(f"[OK] 分形+噪声 组合视频已保存")
        return True


# ==================== 音视频合并器 ====================
class MediaMerger:
    """音视频合并器 - 使用 ffmpeg"""

    @staticmethod
    def merge_audio_video(video_path, audio_path, output_path, bitrate="medium"):
        """
        合并音频和视频

        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出文件路径
            bitrate:    视频码率 ("low", "medium", "high", "ultra")

        Returns:
            bool: 成功返回 True，失败返回 False
        """
        bitrate_map = {
            "low": "1000k",
            "medium": "2500k",
            "high": "5000k",
            "ultra": "8000k",
        }
        br = bitrate_map.get(bitrate, "2500k")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:v", br,
            "-shortest",
            output_path
        ]

        try:
            print(f"[VIDEO] 合并音视频...")
            print(f"   视频: {video_path}")
            print(f"   音频: {audio_path}")
            print(f"   输出: {output_path}")
            print(f"   码率: {br}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )

            if result.returncode == 0:
                print(f"[OK] 合并成功: {output_path}")
                return True
            else:
                print(f"[ERR] 合并失败 (ffmpeg 错误):")
                print(result.stderr[-500:])
                return False

        except FileNotFoundError:
            print("[ERR] 未找到 ffmpeg，请先安装 ffmpeg 并添加到 PATH")
            print("   或者：你可以手动使用命令合并：")
            print(f"   ffmpeg -i {video_path} -i {audio_path} -c:v copy -c:a aac {output_path}")
            return False
        except Exception as e:
            print(f"[ERR] 合并失败: {e}")
            return False

    # ===================== 频谱柱形图 =====================
    @staticmethod
    def _gen_bars(video_writer, w, h, num_frames, fps,
                     palette_name, speed,
                     audio_features=None, audio_reactive=0.5, progress_callback=None):
        """频谱柱形图效果 —— 使用 BarsEffect（从 pywallpaper 集成）"""
        import numpy as np
        import cv2
        try:
            from effects_engine.primitives import BarsEffect
        except ImportError:
            print("[ERR] effects_engine.primitives 模块未找到")
            return False

        effect = BarsEffect(w, h, config={'count': 64, 'direction': 'up', 'gap': 2})
        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        palette_colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        for i in range(num_frames):
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color
            feat = None
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                audio_dict = {
                    'volume': feat.get('volume', 0.0),
                    'spectrum': feat.get('spectrum', np.zeros(64)),
                    'bass': feat.get('bass', 0.0),
                }
            else:
                audio_dict = None
            effect.render(frame, audio_dict, palette_colors, time_val=i * 0.033)
            video_writer.write(frame)
            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")
        print(f"[OK] 频谱柱形图视频已保存")
        return True

    # ===================== 波形曲线 =====================
    @staticmethod
    def _gen_waveform(video_writer, w, h, num_frames, fps,
                         palette_name, speed,
                         audio_features=None, audio_reactive=0.5, progress_callback=None):
        """波形曲线效果 —— 使用 WaveformEffect（从 pywallpaper 集成）"""
        import numpy as np
        import cv2
        try:
            from effects_engine.primitives import WaveformEffect
        except ImportError:
            print("[ERR] effects_engine.primitives 模块未找到")
            return False

        effect = WaveformEffect(w, h, config={'lines': 3, 'points': 200, 'amplitude': 100, 'line_width': 2})
        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        palette_colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        for i in range(num_frames):
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color
            feat = None
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                audio_dict = {
                    'volume': feat.get('volume', 0.0),
                    'spectrum': feat.get('spectrum', np.zeros(64)),
                }
            else:
                audio_dict = None
            effect.render(frame, audio_dict, palette_colors, time_val=i * 0.033)
            video_writer.write(frame)
            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")
        print(f"[OK] 波形曲线视频已保存")
        return True

    # ===================== 漩涡效果 =====================
    @staticmethod
    def _gen_vortex(video_writer, w, h, num_frames, fps,
                       palette_name, speed,
                       audio_features=None, audio_reactive=0.5, progress_callback=None):
        """漩涡/螺旋粒子效果 —— 使用 VortexEffect（从 pywallpaper 集成）"""
        import numpy as np
        import cv2
        try:
            from effects_engine.primitives import VortexEffect
        except ImportError:
            print("[ERR] effects_engine.primitives 模块未找到")
            return False

        effect = VortexEffect(w, h, config={'count': 150, 'twist': 1.0, 'speed': 1.0, 'element_size': 3})
        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        palette_colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        for i in range(num_frames):
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color
            feat = None
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                audio_dict = {
                    'volume': feat.get('volume', 0.0),
                    'bass': feat.get('bass', 0.0),
                }
            else:
                audio_dict = None
            effect.render(frame, audio_dict, palette_colors, time_val=i * 0.033)
            video_writer.write(frame)
            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")
        print(f"[OK] 漩涡效果视频已保存")
        return True

    # ===================== 脉冲涟漪 =====================
    @staticmethod
    def _gen_pulse(video_writer, w, h, num_frames, fps,
                      palette_name, speed,
                      audio_features=None, audio_reactive=0.5, progress_callback=None):
        """脉冲/涟漪效果 —— 使用 PulseEffect（从 pywallpaper 集成）"""
        import numpy as np
        import cv2
        try:
            from effects_engine.primitives import PulseEffect
        except ImportError:
            print("[ERR] effects_engine.primitives 模块未找到")
            return False

        effect = PulseEffect(w, h, config={'mode': 'ripple', 'max_radius': 300, 'speed': 3.0, 'count': 2, 'trigger': 'audio'})
        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        palette_colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        for i in range(num_frames):
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color
            feat = None
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                audio_dict = {
                    'volume': feat.get('volume', 0.0),
                    'spectrum': feat.get('spectrum', np.zeros(64)),
                    'bass': feat.get('bass', 0.0),
                }
            else:
                audio_dict = None
            effect.render(frame, audio_dict, palette_colors, time_val=i * 0.033, dt=1.0/fps)
            video_writer.write(frame)
            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧 (脉冲数: {len(effect._pulses)})")
        print(f"[OK] 脉冲涟漪视频已保存")
        return True


# ==================== 测试代码 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("   [VIDEO] 音视频生成器 Model 层测试")
    print("=" * 60)

    deps = check_dependencies()
    print(f"\n依赖检查结果:")
    for name, status in deps.items():
        icon = "[OK]" if status else "[ERR]"
        print(f"   {icon} {name}")

    print(f"\n可用调色板({len(VIDEO_PALETTES)}): {list(VIDEO_PALETTES.keys())}")
    print(f"可用视频效果模式({len(EFFECT_MODES)}): {EFFECT_MODES}")
    print(f"CA引擎: {'已加载' if _CA_RECIPES_AVAILABLE else '未加载'}")

    # 测试音频生成
    if deps["numpy"]:
        print(f"\n--- 测试音频生成（多种波形）---")
        for wavetype in ["sine", "square", "triangle", "sawtooth", "white_noise"]:
            data, sr = AudioGenerator.generate_wave(wave_type=wavetype, freq=440, duration=1)
            print(f"   {wavetype}: {'[OK]' if data is not None else '[ERR]'}")

        print(f"\n--- 测试和弦生成 ---")
        for chord in AudioGenerator.CHORDS.keys():
            data, sr = AudioGenerator.generate_chord(root_freq=440, chord_type=chord, duration=1)
            print(f"   {chord}: {'[OK]' if data is not None else '[ERR]'}")

    # 测试视频生成（极短测试）
    if deps["numpy"] and deps["cv2"]:
        print(f"\n--- 测试视频生成（1 秒，所有效果模式）---")
        for mode in EFFECT_MODES:
            ok = VideoGenerator.generate_video(
                output_path=f"./test_{mode}.mp4",
                width=320, height=240,
                num_frames=10,
                fps=10,
                effect_mode=mode,
                progress_callback=None
            )
            print(f"   {mode}: {'[OK]' if ok else '[ERR]'}")

    print(f"\n=" * 60)
    print("测试完成")
    print("=" * 60)
