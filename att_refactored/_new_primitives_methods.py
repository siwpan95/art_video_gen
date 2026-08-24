"""
新效果模式的视频生成方法 — 集成 pywallpaper 原语
追加到 att_model.py 末尾（在测试代码之前）
"""

    # ===================== 频谱柱形图 =====================
    @staticmethod
    def _gen_bars(video_writer, w, h, num_frames, fps,
                     palette_name, speed,
                     audio_features=None, audio_reactive=0.5, progress_callback=None):
        """频谱柱形图效果 —— 使用 BarsEffect。
        音频驱动：音量→柱高，低音→颜色偏移
        """
        import numpy as np
        import cv2

        try:
            from effects_engine.primitives import BarsEffect
        except ImportError:
            print("[ERR] effects_engine.primitives 模块未找到")
            return False

        # 创建效果实例
        effect = BarsEffect(w, h, config={'count': 64, 'direction': 'up', 'gap': 2})

        # 预计算调色板颜色
        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        palette_colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        for i in range(num_frames):
            # 创建帧
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color

            # 音频特征
            feat = None
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                # 转换为音频特征字典
                audio_dict = {
                    'volume': feat.get('volume', 0.0),
                    'spectrum': feat.get('spectrum', np.zeros(64)),
                    'bass': feat.get('bass', 0.0),
                    'treble': feat.get('treble', 0.0),
                    'onset': feat.get('onset', 0.0),
                }
            else:
                audio_dict = None

            # 渲染效果
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
        """波形曲线效果 —— 使用 WaveformEffect。
        音频驱动：音量→振幅，频率→曲线密度
        """
        import numpy as np
        import cv2

        try:
            from effects_engine.primitives import WaveformEffect
        except ImportError:
            print("[ERR] effects_engine.primitives 模块未找到")
            return False

        # 创建效果实例
        effect = WaveformEffect(w, h, config={'lines': 3, 'points': 200, 'amplitude': 100, 'line_width': 2})

        # 预计算调色板颜色
        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        palette_colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        for i in range(num_frames):
            # 创建帧
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color

            # 音频特征
            feat = None
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                audio_dict = {
                    'volume': feat.get('volume', 0.0),
                    'spectrum': feat.get('spectrum', np.zeros(64)),
                    'bass': feat.get('bass', 0.0),
                    'treble': feat.get('treble', 0.0),
                }
            else:
                audio_dict = None

            # 渲染效果
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
        """漩涡/螺旋粒子效果 —— 使用 VortexEffect。
        音频驱动：音量→旋转速度，低音→粒子大小
        """
        import numpy as np
        import cv2

        try:
            from effects_engine.primitives import VortexEffect
        except ImportError:
            print("[ERR] effects_engine.primitives 模块未找到")
            return False

        # 创建效果实例
        effect = VortexEffect(w, h, config={'count': 150, 'twist': 1.0, 'speed': 1.0, 'element_size': 3})

        # 预计算调色板颜色
        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        palette_colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        for i in range(num_frames):
            # 创建帧
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color

            # 音频特征
            feat = None
            if audio_features and i < len(audio_features):
                feat = audio_features[i]
                audio_dict = {
                    'volume': feat.get('volume', 0.0),
                    'bass': feat.get('bass', 0.0),
                }
            else:
                audio_dict = None

            # 渲染效果
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
        """脉冲/涟漪效果 —— 使用 PulseEffect。
        音频驱动：音量→触发概率，频率→涟漪密度
        """
        import numpy as np
        import cv2

        try:
            from effects_engine.primitives import PulseEffect
        except ImportError:
            print("[ERR] effects_engine.primitives 模块未找到")
            return False

        # 创建效果实例（使用 ripple 模式）
        effect = PulseEffect(w, h, config={'mode': 'ripple', 'max_radius': 300, 'speed': 3.0, 'count': 2, 'trigger': 'audio'})

        # 预计算调色板颜色
        palette_info = VIDEO_PALETTES.get(palette_name, VIDEO_PALETTES["霓虹"])
        palette_colors = np.array(palette_info["colors"], dtype=np.uint8)
        bg_color = np.array(palette_info["bg"], dtype=np.uint8)

        for i in range(num_frames):
            # 创建帧
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            frame[:, :] = bg_color

            # 音频特征
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

            # 渲染效果
            effect.render(frame, audio_dict, palette_colors, time_val=i * 0.033, dt=1.0/fps)

            video_writer.write(frame)

            if progress_callback and i % 10 == 0:
                progress_callback(int((i / num_frames) * 100))
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧 (脉冲数: {len(effect._pulses)})")

        print(f"[OK] 脉冲涟漪视频已保存")
        return True
