"""
新效果模式的视频生成方法 — 从 pywallpaper 原语集成
供 att_model.py 导入使用
"""

import numpy as np
import math
import random


def gen_bars(video_writer, w, h, num_frames, fps,
             palette_name, speed,
             audio_features=None, audio_reactive=0.5, progress_callback=None):
    """频谱柱形图效果"""
    try:
        from effects_engine.primitives import BarsEffect
    except ImportError:
        print("[ERR] effects_engine.primitives 模块未找到")
        return False

    effect = BarsEffect(w, h, config={'count': 64, 'direction': 'up', 'gap': 2})

    from att_model import VIDEO_PALETTES
    palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
    palette_colors = np.array(palette_info["colors"], dtype=np.uint8)
    bg_color = np.array(palette_info["bg"], dtype=np.uint8)

    for i in range(num_frames):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :] = bg_color

        audio_dict = None
        if audio_features and i < len(audio_features):
            feat = audio_features[i]
            audio_dict = {
                'volume': feat.get('volume', 0.0),
                'spectrum': feat.get('spectrum', np.zeros(64)),
                'bass': feat.get('bass', 0.0),
            }

        effect.render(frame, audio_dict, palette_colors, time_val=i * 0.033)
        video_writer.write(frame)

        if progress_callback and i % 10 == 0:
            progress_callback(int((i / num_frames) * 100))
        if i % 50 == 0:
            print(f"   进度: {i}/{num_frames} 帧")

    print("[OK] 频谱柱形图视频已保存")
    return True


def gen_waveform(video_writer, w, h, num_frames, fps,
                palette_name, speed,
                audio_features=None, audio_reactive=0.5, progress_callback=None):
    """波形曲线效果"""
    try:
        from effects_engine.primitives import WaveformEffect
    except ImportError:
        print("[ERR] effects_engine.primitives 模块未找到")
        return False

    effect = WaveformEffect(w, h, config={'lines': 3, 'points': 200, 'amplitude': 100, 'line_width': 2})

    from att_model import VIDEO_PALETTES
    palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
    palette_colors = np.array(palette_info["colors"], dtype=np.uint8)
    bg_color = np.array(palette_info["bg"], dtype=np.uint8)

    for i in range(num_frames):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :] = bg_color

        audio_dict = None
        if audio_features and i < len(audio_features):
            feat = audio_features[i]
            audio_dict = {
                'volume': feat.get('volume', 0.0),
                'spectrum': feat.get('spectrum', np.zeros(64)),
            }

        effect.render(frame, audio_dict, palette_colors, time_val=i * 0.033)
        video_writer.write(frame)

        if progress_callback and i % 10 == 0:
            progress_callback(int((i / num_frames) * 100))
        if i % 50 == 0:
            print(f"   进度: {i}/{num_frames} 帧")

    print("[OK] 波形曲线视频已保存")
    return True


def gen_vortex(video_writer, w, h, num_frames, fps,
              palette_name, speed,
              audio_features=None, audio_reactive=0.5, progress_callback=None):
    """漩涡/螺旋粒子效果"""
    try:
        from effects_engine.primitives import VortexEffect
    except ImportError:
        print("[ERR] effects_engine.primitives 模块未找到")
        return False

    effect = VortexEffect(w, h, config={'count': 150, 'twist': 1.0, 'speed': 1.0, 'element_size': 3})

    from att_model import VIDEO_PALETTES
    palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
    palette_colors = np.array(palette_info["colors"], dtype=np.uint8)
    bg_color = np.array(palette_info["bg"], dtype=np.uint8)

    for i in range(num_frames):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :] = bg_color

        audio_dict = None
        if audio_features and i < len(audio_features):
            feat = audio_features[i]
            audio_dict = {
                'volume': feat.get('volume', 0.0),
                'bass': feat.get('bass', 0.0),
            }

        effect.render(frame, audio_dict, palette_colors, time_val=i * 0.033)
        video_writer.write(frame)

        if progress_callback and i % 10 == 0:
            progress_callback(int((i / num_frames) * 100))
        if i % 50 == 0:
            print(f"   进度: {i}/{num_frames} 帧")

    print("[OK] 漩涡效果视频已保存")
    return True


def gen_pulse(video_writer, w, h, num_frames, fps,
             palette_name, speed,
             audio_features=None, audio_reactive=0.5, progress_callback=None):
    """脉冲/涟漪效果"""
    try:
        from effects_engine.primitives import PulseEffect
    except ImportError:
        print("[ERR] effects_engine.primitives 模块未找到")
        return False

    effect = PulseEffect(w, h, config={'mode': 'ripple', 'max_radius': 300, 'speed': 3.0, 'count': 2, 'trigger': 'audio'})

    from att_model import VIDEO_PALETTES
    palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
    palette_colors = np.array(palette_info["colors"], dtype=np.uint8)
    bg_color = np.array(palette_info["bg"], dtype=np.uint8)

    for i in range(num_frames):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :] = bg_color

        audio_dict = None
        if audio_features and i < len(audio_features):
            feat = audio_features[i]
            audio_dict = {
                'volume': feat.get('volume', 0.0),
                'spectrum': feat.get('spectrum', np.zeros(64)),
                'bass': feat.get('bass', 0.0),
            }

        effect.render(frame, audio_dict, palette_colors, time_val=i * 0.033, dt=1.0/fps)
        video_writer.write(frame)

        if progress_callback and i % 10 == 0:
            progress_callback(int((i / num_frames) * 100))
        if i % 50 == 0:
            print(f"   进度: {i}/{num_frames} 帧 (脉冲数: {len(effect._pulses)})")

    print("[OK] 脉冲涟漪视频已保存")
    return True
