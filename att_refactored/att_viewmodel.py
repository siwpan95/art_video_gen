#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
  ViewModel 层 (ViewModel Layer)
  带音频的视频生成软件 - 事件处理和状态管理
  
  职责：
  - 处理 View 的事件（按钮点击等）
  - 调用 Model 层的方法
  - 更新 View 的状态（进度、日志、状态栏）
  - 管理生成状态
============================================
"""

import os
import re
import threading
from datetime import datetime
from pathlib import Path

# 导入 Model 层
from att_model import (
    check_dependencies,
    AudioGenerator,
    VideoGenerator,
    MediaMerger,
    GenerationConfig,
    VIDEO_PALETTES,
)
# 导入加密模块
try:
    import att_crypto
    from att_crypto_dialog import show_crypto_dialog
except ImportError:
    att_crypto = None
    show_crypto_dialog = None


class IntegratedViewModel:
    """视图模型 - 连接 View 和 Model"""
    
    def __init__(self, view):
        """
        初始化 ViewModel
        
        Args:
            view: View 层实例
        """
        self.view = view
        self.model = None
        
        # 依赖状态
        self.deps = check_dependencies()
        
        # 生成配置
        self.config = GenerationConfig()
        
        # 生成状态
        self.is_generating = False
        
        # 绑定 View 的事件回调
        self._bind_callbacks()
        
        # 更新 View 的初始状态
        self._init_view()
    
    def _bind_callbacks(self):
        """绑定 View 的事件回调"""
        self.view.on_generate_video = self.generate_video_only
        self.view.on_generate_audio = self.generate_audio_only
        self.view.on_generate_complete = self.generate_complete_video
        self.view.on_browse_dir = self.browse_dir
        self.view.on_crypto_process = self.launch_crypto_dialog
    
    def _init_view(self):
        """初始化 View 的显示状态"""
        # 更新依赖状态显示
        self.view.update_dependencies(self.deps)
        
        # 更新配置到 View
        self._update_view_from_config()
        
        # 初始日志
        self.view.log("=" * 60)
        self.view.log("   [VIDEO] 音视频生成器 v3.0 (MVVM 架构 - 音画联动版)")
        self.view.log("   支持: 音频驱动 | 7种视频效果 | 多种波形 | 和弦 | 调色板 | 加密后处理")
        self.view.log("=" * 60)
        self.view.log(f"依赖检查结果:")
        for name, status in self.deps.items():
            icon = "[OK]" if status else "[ERR]"
            self.view.log(f"   {icon} {name}")
        self.view.log("=" * 60)
    
    def _update_view_from_config(self):
        """从配置更新 View 的显示"""
        config_dict = self.config.to_dict()
        
        # 视频参数
        self.view.width_var.set(str(config_dict["width"]))
        self.view.height_var.set(str(config_dict["height"]))
        self.view.frames_var.set(str(config_dict["num_frames"]))
        self.view.fps_var.set(str(config_dict["fps"]))
        self.view.codec_var.set(config_dict["codec"])
        self.view.palette_var.set(config_dict["palette"])
        self.view.particle_var.set(str(config_dict["particle_count"]))
        self.view.speed_var.set(str(config_dict["animation_speed"]))
        self.view.vbitrate_var.set(config_dict["video_bitrate"])
        self.view.effect_mode_var.set(config_dict["effect_mode"])
        self.view.audio_path_var.set(config_dict.get("audio_path", ""))
        self.view.audio_reactive_var.set(config_dict.get("audio_reactive", 0.5))
        
        # 音频参数
        self.view.wave_type_var.set(config_dict["wave_type"])
        self.view.freq_var.set(str(config_dict["freq"]))
        self.view.duration_var.set(str(config_dict["duration"]))
        self.view.volume_var.set(str(int(config_dict["volume"] * 100)))
        self.view.sample_rate_var.set(str(config_dict["sample_rate"]))
        self.view.channels_var.set("1 (单声道)" if config_dict["channels"] == 1 else "2 (立体声)")
        self.view.chord_var.set(config_dict["chord_type"])
        
        # 输出目录
        self.view.output_dir_var.set(config_dict["output_dir"])
    
    def _update_config_from_view(self):
        """从 View 更新配置"""
        video_settings = self.view.get_video_settings()
        audio_settings = self.view.get_audio_settings()
        output_dir = self.view.get_output_dir()
        
        if video_settings:
            self.config.width = video_settings["width"]
            self.config.height = video_settings["height"]
            self.config.num_frames = video_settings["num_frames"]
            self.config.fps = video_settings["fps"]
            self.config.codec = video_settings["codec"]
            self.config.palette = video_settings["palette"]
            self.config.particle_count = video_settings["particle_count"]
            self.config.animation_speed = video_settings["animation_speed"]
            self.config.video_bitrate = video_settings["video_bitrate"]
            self.config.effect_mode   = video_settings.get("effect_mode", "元胞自动机")
            self.config.audio_path     = video_settings.get("audio_path", "")
            self.config.audio_reactive = video_settings.get("audio_reactive", 0.5)
        
        if audio_settings:
            self.config.wave_type = audio_settings["wave_type"]
            self.config.freq = audio_settings["freq"]
            self.config.duration = audio_settings["duration"]
            self.config.volume = audio_settings["volume"]
            self.config.sample_rate = audio_settings["sample_rate"]
            self.config.channels = audio_settings["channels"]
            self.config.chord_type = audio_settings["chord_type"]
        
        if output_dir:
            self.config.output_dir = str(output_dir)
    
    # ==================== 动态命名 ====================
    @staticmethod
    def _sanitize_filename(name):
        """清理文件名中的非法字符"""
        return re.sub(r'[\\/:*?"<>|]', '_', name)
    
    def _build_video_filename(self, video_settings):
        """
        构建视频文件名
        格式: video_{效果}_{调色板}_{宽}x{高}_{帧数}f_{fps}fps_{时间戳}.mp4
        示例: video_元胞自动机_极光_640x480_300f_30fps_20260617_213000.mp4
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        effect = self._sanitize_filename(video_settings.get("effect_mode", "未知效果"))
        palette = self._sanitize_filename(video_settings.get("palette", "默认"))
        width = video_settings.get("width", 640)
        height = video_settings.get("height", 480)
        frames = video_settings.get("num_frames", 300)
        fps = video_settings.get("fps", 30)
        return f"video_{effect}_{palette}_{width}x{height}_{frames}f_{fps}fps_{ts}.mp4"
    
    def _build_audio_filename(self, audio_settings):
        """
        构建音频文件名
        格式: audio_{波形}_{频率}Hz_{时长}s_{时间戳}.wav
        示例: audio_sine_440Hz_10s_20260617_213000.wav
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        wave = self._sanitize_filename(audio_settings.get("wave_type", "未知波形"))
        freq = audio_settings.get("freq", 440)
        dur = audio_settings.get("duration", 10)
        chord = audio_settings.get("chord_type", "无")
        chord_suffix = f"_{self._sanitize_filename(chord)}" if chord != "无" else ""
        return f"audio_{wave}_{freq}Hz_{dur}s{chord_suffix}_{ts}.wav"
    
    def _build_complete_filename(self, video_settings):
        """
        构建完整视频文件名
        格式: {效果}_{调色板}_{宽}x{高}_{时间戳}.mp4
        示例: CA引擎_极光_640x480_20260617_213000.mp4
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        effect = self._sanitize_filename(video_settings.get("effect_mode", "未知效果"))
        palette = self._sanitize_filename(video_settings.get("palette", "默认"))
        width = video_settings.get("width", 640)
        height = video_settings.get("height", 480)
        return f"{effect}_{palette}_{width}x{height}_{ts}.mp4"
    
    # ==================== 加密后处理 ====================
    def launch_crypto_dialog(self):
        """启动加密后处理对话框"""
        if show_crypto_dialog is None:
            self.view.show_error("错误", "加密对话框模块未找到！")
            return
        self.view.log("[CRYPTO] 启动加密后处理对话框...")
        show_crypto_dialog(self.view.root, self)
    
    def _crypto_post_process(self, video_path):
        """
        生成完成后的自动加密后处理
        由 generate_video_only / generate_complete_video 末尾调用
        """
        if not self.config.crypto_enabled:
            return
        if not att_crypto:
            self.view.log("[WARN]  att_crypto 模块未加载，跳过加密后处理")
            return

        self.view.log("[CRYPTO] 开始自动加密后处理...")
        self.view.update_status("[CRYPTO] 正在加密/压缩后处理...")

        def _worker():
            try:
                from att_crypto import CryptoConfig, process_video
                cfg = CryptoConfig()
                cfg.signature_text = self.config.crypto_signature
                cfg.compress_preset = self.config.crypto_compress
                cfg.compression_bomb = self.config.crypto_bomb

                password = self.config.crypto_password or None
                output_dir = self.config.output_dir

                self.view.log(f"   视频: {video_path}")
                self.view.log(f"   签名: {cfg.signature_text} | 压缩: {cfg.compress_preset}")

                results = process_video(
                    video_path,
                    output_dir=output_dir,
                    config=cfg,
                    password=password,
                    progress_callback=None
                )

                self.view.log("[OK] 加密后处理完成！")
                for k, v in results.items():
                    self.view.log(f"   {k}: {v}")
                self.view.update_status("[OK] 加密后处理完成")

                # 更新最后处理的视频路径
                if "encrypted" in results:
                    self.config.last_video_path = results["encrypted"]
                elif "compressed" in results:
                    self.config.last_video_path = results["compressed"]

            except Exception as e:
                self.view.log(f"[ERR] 加密后处理失败: {e}")
                self.view.update_status("[ERR] 加密后处理失败")
                import traceback; traceback.print_exc()

        threading.Thread(target=_worker, daemon=True).start()
    
    # ==================== 事件处理 ====================
    def browse_dir(self):
        """浏览输出目录"""
        from tkinter import filedialog
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            self.config.output_dir = dir_path
            self.view.set_output_dir(dir_path)
            self.view.log(f"输出目录已更新: {dir_path}")
    
    def generate_video_only(self):
        """仅生成视频"""
        if self.is_generating:
            self.view.show_warning("警告", "正在生成中，请等待...")
            return
        
        # 检查依赖
        if not self.deps["numpy"] or not self.deps["cv2"]:
            self.view.show_error("错误", "缺少依赖: numpy 和 opencv-python")
            return
        
        # 获取配置
        video_settings = self.view.get_video_settings()
        if not video_settings:
            return
        
        output_dir = Path(self.view.get_output_dir())
        output_dir.mkdir(parents=True, exist_ok=True)
        video_path = str(output_dir / self._build_video_filename(video_settings))
        
        # 更新状态
        self.is_generating = True
        self.view.update_status("[VIDEO] 正在生成视频...")
        self.view.log(f"开始生成视频: {video_path}")
        self.view.log(f"   编码器: {video_settings['codec']}, 主题: {video_settings['palette']}, "
                     f"粒子: {video_settings['particle_count']}, 速度: {video_settings['animation_speed']}x")
        
        def do_generate():
            try:
                def progress_callback(progress):
                    self.view.update_progress(progress)
                
                success = VideoGenerator.generate_video(
                    video_path, 
                    video_settings["width"],
                    video_settings["height"],
                    video_settings["num_frames"],
                    video_settings["fps"],
                    video_settings["codec"],
                    video_settings["palette"],
                    video_settings["particle_count"],
                    video_settings["animation_speed"],
                    video_settings["effect_mode"],
                    video_settings.get("audio_path", ""),
                    video_settings.get("audio_reactive", 0.5),
                    progress_callback
                )
                
                if success:
                    self.view.log(f"[OK] 视频已保存: {video_path}")
                    self.view.update_status(f"[OK] 视频生成完成: {video_path}")
                    self.view.show_info("完成", f"视频已保存:\n{video_path}")
                    # 自动加密后处理
                    self._crypto_post_process(video_path)
                else:
                    self.view.log("[ERR] 视频生成失败")
                    self.view.update_status("[ERR] 视频生成失败")
            except Exception as e:
                self.view.log(f"[ERR] 错误: {e}")
                self.view.update_status("[ERR] 视频生成失败")
            finally:
                self.is_generating = False
        
        thread = threading.Thread(target=do_generate, daemon=True)
        thread.start()
    
    def generate_audio_only(self):
        """仅生成音频"""
        if self.is_generating:
            self.view.show_warning("警告", "正在生成中，请等待...")
            return
        
        # 检查依赖
        if not self.deps["numpy"]:
            self.view.show_error("错误", "缺少依赖: numpy")
            return
        
        # 获取配置
        audio_settings = self.view.get_audio_settings()
        if not audio_settings:
            return
        
        output_dir = Path(self.view.get_output_dir())
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = str(output_dir / self._build_audio_filename(audio_settings))
        
        # 更新状态
        self.is_generating = True
        self.view.update_status("[AUDIO] 正在生成音频...")
        self.view.log(f"开始生成音频: {audio_path}")
        self.view.log(f"   波形: {audio_settings['wave_type']}, 频率: {audio_settings['freq']} Hz, "
                     f"时长: {audio_settings['duration']} 秒")
        self.view.log(f"   音量: {audio_settings['volume']*100:.0f}%, "
                     f"采样率: {audio_settings['sample_rate']} Hz, "
                     f"通道: {audio_settings['channels']}, 和弦: {audio_settings['chord_type']}")
        
        def do_generate():
            try:
                self.view.update_progress(10)
                
                # 判断是生成单音还是和弦
                if audio_settings["chord_type"] != "无":
                    audio_data, sample_rate = AudioGenerator.generate_chord(
                        wave_type=audio_settings["wave_type"],
                        root_freq=audio_settings["freq"],
                        chord_type=audio_settings["chord_type"],
                        duration=audio_settings["duration"],
                        sample_rate=audio_settings["sample_rate"],
                        volume=audio_settings["volume"],
                        channels=audio_settings["channels"]
                    )
                else:
                    audio_data, sample_rate = AudioGenerator.generate_wave(
                        wave_type=audio_settings["wave_type"],
                        freq=audio_settings["freq"],
                        duration=audio_settings["duration"],
                        sample_rate=audio_settings["sample_rate"],
                        volume=audio_settings["volume"],
                        channels=audio_settings["channels"]
                    )
                
                self.view.update_progress(60)
                
                if audio_data is not None:
                    success = AudioGenerator.save_wav(audio_path, audio_data, sample_rate)
                    self.view.update_progress(100)
                    
                    if success:
                        self.view.log(f"[OK] 音频已保存: {audio_path}")
                        self.view.update_status(f"[OK] 音频生成完成: {audio_path}")
                        self.view.show_info("完成", f"音频已保存:\n{audio_path}")
                    else:
                        self.view.log("[ERR] 音频保存失败")
                        self.view.update_status("[ERR] 音频保存失败")
                else:
                    self.view.log("[ERR] 音频生成失败")
                    self.view.update_status("[ERR] 音频生成失败")
            except Exception as e:
                self.view.log(f"[ERR] 错误: {e}")
                self.view.update_status("[ERR] 音频生成失败")
            finally:
                self.is_generating = False
        
        thread = threading.Thread(target=do_generate, daemon=True)
        thread.start()
    
    def generate_complete_video(self):
        """生成带音频的完整视频"""
        if self.is_generating:
            self.view.show_warning("警告", "正在生成中，请等待...")
            return
        
        # 检查依赖
        if not self.deps["numpy"] or not self.deps["cv2"]:
            self.view.show_error("错误", "缺少依赖: numpy 和 opencv-python (用于视频生成)")
            return
        
        # 获取配置
        video_settings = self.view.get_video_settings()
        audio_settings = self.view.get_audio_settings()
        if not video_settings or not audio_settings:
            return
        
        output_dir = Path(self.view.get_output_dir())
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_video_path = str(output_dir / f"_temp_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
        temp_audio_path = str(output_dir / f"_temp_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
        final_path = str(output_dir / self._build_complete_filename(video_settings))
        
        # 更新状态
        self.is_generating = True
        self.view.log("=" * 50)
        self.view.log("开始生成完整视频 (视频 + 音频)")
        self.view.log("=" * 50)
        self.view.update_status("[VIDEO][AUDIO] 正在生成完整视频...")
        
        def do_generate():
            try:
                # 步骤1: 生成视频
                self.view.log("步骤 1/4: 生成视频...")
                self.view.update_progress(0)
                
                def video_progress_callback(progress):
                    self.view.update_progress(progress * 0.4)  # 视频占40%进度
                
                video_success = VideoGenerator.generate_video(
                    temp_video_path,
                    video_settings["width"],
                    video_settings["height"],
                    video_settings["num_frames"],
                    video_settings["fps"],
                    video_settings["codec"],
                    video_settings["palette"],
                    video_settings["particle_count"],
                    video_settings["animation_speed"],
                    video_settings["effect_mode"],
                    video_settings.get("audio_path", ""),
                    video_settings.get("audio_reactive", 0.5),
                    video_progress_callback
                )
                
                if not video_success:
                    self.view.log("[ERR] 视频生成失败")
                    self.view.update_status("[ERR] 视频生成失败")
                    return
                
                self.view.log(f"[OK] 视频已生成: {temp_video_path}")
                self.view.update_progress(40)
                
                # 步骤2: 生成音频
                self.view.log("步骤 2/4: 生成音频...")
                try:
                    if audio_settings["chord_type"] != "无":
                        audio_data, sample_rate = AudioGenerator.generate_chord(
                            wave_type=audio_settings["wave_type"],
                            root_freq=audio_settings["freq"],
                            chord_type=audio_settings["chord_type"],
                            duration=audio_settings["duration"],
                            sample_rate=audio_settings["sample_rate"],
                            volume=audio_settings["volume"],
                            channels=audio_settings["channels"]
                        )
                    else:
                        audio_data, sample_rate = AudioGenerator.generate_wave(
                            wave_type=audio_settings["wave_type"],
                            freq=audio_settings["freq"],
                            duration=audio_settings["duration"],
                            sample_rate=audio_settings["sample_rate"],
                            volume=audio_settings["volume"],
                            channels=audio_settings["channels"]
                        )
                    
                    if audio_data is not None:
                        AudioGenerator.save_wav(temp_audio_path, audio_data, sample_rate)
                        self.view.log(f"[OK] 音频已生成: {temp_audio_path}")
                    else:
                        self.view.log("[ERR] 音频生成失败")
                        self.view.update_status("[ERR] 音频生成失败")
                        return
                except Exception as e:
                    self.view.log(f"[ERR] 音频生成失败: {e}")
                    self.view.update_status("[ERR] 音频生成失败")
                    return
                
                self.view.update_progress(60)
                
                # 步骤3: 合并音视频
                self.view.log("步骤 3/4: 合并音视频...")
                merger = MediaMerger()
                merge_success = merger.merge_audio_video(
                    temp_video_path, temp_audio_path, final_path,
                    bitrate=video_settings["video_bitrate"]
                )
                
                if not merge_success:
                    self.view.log("[WARN] 自动合并失败，但视频和音频文件已单独生成")
                    self.view.log(f"   视频: {temp_video_path}")
                    self.view.log(f"   音频: {temp_audio_path}")
                    self.view.log("   你可以手动使用 ffmpeg 合并这两个文件")
                    self.view.update_status("[WARN] 合并失败，但文件已生成")
                    self.view.update_progress(100)
                    return
                
                self.view.update_progress(80)
                
                # 步骤4: 清理临时文件
                self.view.log("步骤 4/4: 清理临时文件...")
                try:
                    os.remove(temp_video_path)
                    os.remove(temp_audio_path)
                    self.view.log("[OK] 临时文件已清理")
                except Exception as e:
                    self.view.log(f"[WARN] 清理临时文件失败: {e}")
                
                self.view.update_progress(100)
                self.view.log("=" * 50)
                self.view.log(f"[OK] 完整视频已生成: {final_path}")
                self.view.log("=" * 50)
                self.view.update_status(f"[OK] 完整视频已生成: {final_path}")
                
                self.view.show_info("完成", f"带音频的视频已生成!\n\n文件路径:\n{final_path}")
                
                # 自动加密后处理
                self._crypto_post_process(final_path)
                
            except Exception as e:
                self.view.log(f"[ERR] 错误: {e}")
                self.view.update_status("[ERR] 生成失败")
            finally:
                self.is_generating = False
        
        thread = threading.Thread(target=do_generate, daemon=True)
        thread.start()
    
    # ==================== 配置管理 ====================
    def save_config(self, filepath):
        """
        保存配置到文件
        
        Args:
            filepath: 配置文件路径
        """
        import json
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)
            self.view.log(f"配置已保存: {filepath}")
            return True
        except Exception as e:
            self.view.log(f"[ERR] 保存配置失败: {e}")
            return False
    
    def load_config(self, filepath):
        """
        从文件加载配置
        
        Args:
            filepath: 配置文件路径
        """
        import json
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.config = GenerationConfig()
            self.config.from_dict(data)
            self._update_view_from_config()
            self.view.log(f"配置已加载: {filepath}")
            return True
        except Exception as e:
            self.view.log(f"[ERR] 加载配置失败: {e}")
            return False
    

if __name__ == "__main__":
    import tkinter as tk
    from att_view import IntegratedGeneratorView
    
    print("Testing ViewModel Layer...")
    
    root = tk.Tk()
    view = IntegratedGeneratorView(root)
    viewmodel = IntegratedViewModel(view)
    
    print("ViewModel initialized successfully!")
    print("View and ViewModel are now connected.")
    
    root.mainloop()
