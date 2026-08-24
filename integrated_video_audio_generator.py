#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
  带音频的视频生成软件 - 集成版
  整合了 autowav.py + flash.py + faatt.py
  功能：
    1. 生成随机视频（基于元胞自动机+粒子系统）
    2. 生成随机音乐（基于程序化合成）
    3. 将音频和视频合并为完整视频
============================================
"""

import os
import sys
import threading
import time
import random
import subprocess
from pathlib import Path

# ==================== 检查依赖 ====================
def check_dependencies():
    """检查并报告依赖状态"""
    deps = {
        "numpy": False,
        "cv2": False,
        "torch": False,
        "sounddevice": False,
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
        import torch
        deps["torch"] = True
    except ImportError:
        pass
    
    try:
        import sounddevice
        deps["sounddevice"] = True
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

# ==================== 音频生成模块 (来自 autowav.py) ====================
class AudioGenerator:
    """封装 autowav.py 的音频生成功能"""
    
    @staticmethod
    def generate_simple_tone(freq=440, duration=5, sample_rate=44100):
        """生成简单的正弦波音频"""
        try:
            import numpy as np
        except ImportError:
            print("❌ 需要 numpy 来生成音频")
            return None
        
        t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
        # 生成带有简单包络的音调
        tone = np.sin(2 * np.pi * freq * t)
        # 应用简单的ADSR包络
        attack = int(0.05 * sample_rate)
        decay = int(0.1 * sample_rate)
        release = int(0.2 * sample_rate)
        
        envelope = np.ones_like(tone)
        # Attack
        if attack > 0:
            envelope[:attack] = np.linspace(0, 1, attack)
        # Decay
        if decay > 0:
            envelope[attack:attack+decay] = np.linspace(1, 0.7, decay)
        # Release
        if release > 0:
            envelope[-release:] = np.linspace(0.7, 0, release)
        
        tone = tone * envelope * 0.5
        return tone, sample_rate
    
    @staticmethod
    def save_wav(filepath, audio_data, sample_rate):
        """保存音频为WAV文件"""
        try:
            import numpy as np
            from scipy.io import wavfile
            # 确保数据在正确范围内
            audio_int16 = (audio_data * 32767).astype(np.int16)
            wavfile.write(filepath, sample_rate, audio_int16)
            return True
        except ImportError:
            # 如果没有scipy，使用标准库
            try:
                import wave
                import struct
                
                with wave.open(filepath, 'w') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(sample_rate)
                    
                    for s in audio_data:
                        val = max(-1, min(1, s))
                        wf.writeframes(struct.pack('<h', int(val * 32767)))
                return True
            except Exception as e:
                print(f"❌ 保存WAV失败: {e}")
                return False
        except Exception as e:
            print(f"❌ 保存WAV失败: {e}")
            return False

# ==================== 视频生成模块 (来自 flash.py 的简化版) ====================
class VideoGenerator:
    """封装视频生成功能"""
    
    @staticmethod
    def generate_video(output_path, width=640, height=480, num_frames=300, fps=30, 
                      progress_callback=None):
        """生成随机视频（简化版，不依赖PyTorch）"""
        try:
            import numpy as np
            import cv2
        except ImportError as e:
            print(f"❌ 缺少依赖: {e}")
            return False
        
        # 初始化视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not video_writer.isOpened():
            print(f"❌ 无法创建视频文件: {output_path}")
            return False
        
        print(f"🎬 开始生成视频: {output_path}")
        print(f"   分辨率: {width}x{height}, 帧数: {num_frames}, FPS: {fps}")
        
        # 初始化元胞自动机网格
        grid = np.random.randint(0, 2, (height, width), dtype=np.uint8)
        
        # 颜色调色板
        palettes = [
            # 霓虹
            np.array([[255, 0, 128], [0, 255, 255], [128, 0, 255]], dtype=np.uint8),
            # 日落
            np.array([[255, 100, 50], [255, 180, 100], [255, 50, 100]], dtype=np.uint8),
            # 海洋
            np.array([[0, 150, 255], [0, 200, 200], [100, 255, 255]], dtype=np.uint8),
        ]
        
        palette = palettes[random.randint(0, len(palettes)-1)]
        
        for i in range(num_frames):
            # 更新元胞自动机
            new_grid = np.zeros_like(grid)
            for y in range(1, height-1):
                for x in range(1, width-1):
                    neighbors = np.sum(grid[y-1:y+2, x-1:x+2]) - grid[y, x]
                    if grid[y, x] == 1:
                        new_grid[y, x] = 1 if 2 <= neighbors <= 3 else 0
                    else:
                        new_grid[y, x] = 1 if neighbors == 3 else 0
            grid = new_grid
            
            # 创建帧
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # 应用元胞自动机纹理
            for c in range(3):
                frame[:, :, c] = grid * palette[random.randint(0, len(palette)-1)][c]
            
            # 添加粒子效果
            num_particles = 20
            for _ in range(num_particles):
                x = int((np.sin(i * 0.1 + random.random()) * 0.5 + 0.5) * width)
                y = int((np.cos(i * 0.08 + random.random()) * 0.5 + 0.5) * height)
                size = random.randint(1, 4)
                color = tuple([int(c) for c in palette[random.randint(0, len(palette)-1)]])
                cv2.circle(frame, (x, y), size, color, -1)
            
            # 写入帧
            video_writer.write(frame)
            
            # 进度回调
            if progress_callback and i % 10 == 0:
                progress = int((i / num_frames) * 100)
                progress_callback(progress)
            
            if i % 50 == 0:
                print(f"   进度: {i}/{num_frames} 帧")
        
        video_writer.release()
        print(f"✅ 视频已保存: {output_path}")
        
        if progress_callback:
            progress_callback(100)
        
        return True

# ==================== 音视频合并模块 ====================
class MediaMerger:
    """合并音频和视频"""
    
    @staticmethod
    def merge_audio_video(video_path, audio_path, output_path):
        """使用ffmpeg合并音频和视频"""
        # 检查ffmpeg是否可用
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ 未找到 ffmpeg，无法合并音视频")
            print("   请安装 ffmpeg: https://ffmpeg.org/download.html")
            return False
        
        print(f"🎬 合并音视频...")
        print(f"   视频: {video_path}")
        print(f"   音频: {audio_path}")
        print(f"   输出: {output_path}")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ 合并完成: {output_path}")
                return True
            else:
                print(f"❌ 合并失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 合并失败: {e}")
            return False

# ==================== GUI 界面 ====================
class IntegratedGeneratorGUI:
    """集成生成器的GUI界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 带音频的视频生成软件 v1.0")
        self.root.geometry("800x700")
        self.root.configure(bg="#1a1a2e")
        
        self.deps = check_dependencies()
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        import tkinter as tk
        from tkinter import ttk, messagebox, scrolledtext
        
        # 标题
        title_frame = tk.Frame(self.root, bg="#1a1a2e", height=60)
        title_frame.pack(fill=tk.X, padx=10, pady=10)
        
        title_label = tk.Label(
            title_frame, 
            text="🎬 带音频的视频生成软件", 
            font=("Arial", 20, "bold"),
            bg="#1a1a2e",
            fg="#e94560"
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="集成 autowav.py + flash.py + faatt.py",
            font=("Arial", 10),
            bg="#1a1a2e",
            fg="#eee"
        )
        subtitle_label.pack()
        
        # 依赖状态
        dep_frame = tk.LabelFrame(
            self.root,
            text="📦 依赖状态",
            bg="#1a1a2e",
            fg="#e94560",
            font=("Arial", 10, "bold"),
            padx=10, pady=5
        )
        dep_frame.pack(fill=tk.X, padx=10, pady=5)
        
        dep_text = tk.Text(
            dep_frame,
            height=4,
            bg="#0d1117",
            fg="#58a6ff",
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        dep_text.pack(fill=tk.X, padx=5, pady=5)
        
        # 更新依赖信息
        dep_info = []
        for name, status in self.deps.items():
            icon = "✅" if status else "❌"
            dep_info.append(f"{icon} {name}")
        
        dep_text.config(state=tk.NORMAL)
        dep_text.insert("1.0", "\n".join(dep_info))
        dep_text.config(state=tk.DISABLED)
        
        # 视频设置
        video_frame = tk.LabelFrame(
            self.root,
            text="🎬 视频设置",
            bg="#1a1a2e",
            fg="#0f9d58",
            font=("Arial", 10, "bold"),
            padx=10, pady=5
        )
        video_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 分辨率
        res_frame = tk.Frame(video_frame, bg="#1a1a2e")
        res_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(res_frame, text="分辨率:", bg="#1a1a2e", fg="#eee", font=("Arial", 9)).pack(side=tk.LEFT)
        self.width_var = tk.StringVar(value="640")
        tk.Entry(res_frame, textvariable=self.width_var, width=6, font=("Consolas", 9)).pack(side=tk.LEFT, padx=5)
        tk.Label(res_frame, text="x", bg="#1a1a2e", fg="#eee", font=("Arial", 9)).pack(side=tk.LEFT)
        self.height_var = tk.StringVar(value="480")
        tk.Entry(res_frame, textvariable=self.height_var, width=6, font=("Consolas", 9)).pack(side=tk.LEFT, padx=5)
        
        # 帧数和FPS
        frame_frame = tk.Frame(video_frame, bg="#1a1a2e")
        frame_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(frame_frame, text="帧数:", bg="#1a1a2e", fg="#eee", font=("Arial", 9)).pack(side=tk.LEFT)
        self.frames_var = tk.StringVar(value="300")
        tk.Entry(frame_frame, textvariable=self.frames_var, width=6, font=("Consolas", 9)).pack(side=tk.LEFT, padx=5)
        
        tk.Label(frame_frame, text="FPS:", bg="#1a1a2e", fg="#eee", font=("Arial", 9)).pack(side=tk.LEFT, padx=(20, 5))
        self.fps_var = tk.StringVar(value="30")
        tk.Entry(frame_frame, textvariable=self.fps_var, width=6, font=("Consolas", 9)).pack(side=tk.LEFT, padx=5)
        
        # 音频设置
        audio_frame = tk.LabelFrame(
            self.root,
            text="🎵 音频设置",
            bg="#1a1a2e",
            fg="#f1c40f",
            font=("Arial", 10, "bold"),
            padx=10, pady=5
        )
        audio_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 频率
        freq_frame = tk.Frame(audio_frame, bg="#1a1a2e")
        freq_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(freq_frame, text="频率 (Hz):", bg="#1a1a2e", fg="#eee", font=("Arial", 9)).pack(side=tk.LEFT)
        self.freq_var = tk.StringVar(value="440")
        tk.Entry(freq_frame, textvariable=self.freq_var, width=6, font=("Consolas", 9)).pack(side=tk.LEFT, padx=5)
        
        # 时长
        duration_frame = tk.Frame(audio_frame, bg="#1a1a2e")
        duration_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(duration_frame, text="时长 (秒):", bg="#1a1a2e", fg="#eee", font=("Arial", 9)).pack(side=tk.LEFT)
        self.duration_var = tk.StringVar(value="10")
        tk.Entry(duration_frame, textvariable=self.duration_var, width=6, font=("Consolas", 9)).pack(side=tk.LEFT, padx=5)
        
        # 输出路径
        output_frame = tk.LabelFrame(
            self.root,
            text="💾 输出设置",
            bg="#1a1a2e",
            fg="#3498db",
            font=("Arial", 10, "bold"),
            padx=10, pady=5
        )
        output_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 输出目录
        dir_frame = tk.Frame(output_frame, bg="#1a1a2e")
        dir_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(dir_frame, text="输出目录:", bg="#1a1a2e", fg="#eee", font=("Arial", 9)).pack(side=tk.LEFT)
        self.output_dir_var = tk.StringVar(value=str(Path(__file__).resolve().parent / "output"))
        tk.Entry(dir_frame, textvariable=self.output_dir_var, width=40, font=("Consolas", 9)).pack(side=tk.LEFT, padx=5)
        tk.Button(dir_frame, text="浏览", command=self.browse_dir, bg="#3498db", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
        
        # 按钮区域
        button_frame = tk.Frame(self.root, bg="#1a1a2e")
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Button(button_frame, text="🎬 仅生成视频", command=self.generate_video_only, 
                 bg="#e94560", fg="white", font=("Arial", 10, "bold"), 
                 padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="🎵 仅生成音频", command=self.generate_audio_only,
                 bg="#f1c40f", fg="white", font=("Arial", 10, "bold"),
                 padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="🎬🎵 生成完整视频", command=self.generate_complete_video,
                 bg="#0f9d58", fg="white", font=("Arial", 10, "bold"),
                 padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.root,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)
        
        # 日志输出
        log_frame = tk.LabelFrame(
            self.root,
            text="📋 输出日志",
            bg="#1a1a2e",
            fg="#aaa",
            font=("Arial", 10, "bold"),
            padx=10, pady=5
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=12,
            wrap=tk.WORD,
            bg="#0d1117",
            fg="#8b949e",
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 状态栏
        self.status_var = tk.StringVar(value="✅ 就绪 — 设置参数后点击生成按钮")
        status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            bg="#16213e",
            fg="#eee",
            font=("Arial", 9),
            anchor=tk.W,
            relief=tk.SUNKEN,
            padx=10,
            pady=5
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def browse_dir(self):
        """浏览输出目录"""
        from tkinter import filedialog
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if dir_path:
            self.output_dir_var.set(dir_path)
    
    def log(self, message):
        """添加日志"""
        import time
        import tkinter as tk
        self.log_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_var.set(value)
        self.root.update_idletasks()
    
    def generate_video_only(self):
        """仅生成视频"""
        if not self.deps["numpy"] or not self.deps["cv2"]:
            messagebox.showerror("错误", "缺少依赖: numpy 和 opencv-python")
            return
        
        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
            num_frames = int(self.frames_var.get())
            fps = int(self.fps_var.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return
        
        output_dir = Path(self.output_dir_var.get())
        output_dir.mkdir(parents=True, exist_ok=True)
        video_path = str(output_dir / "generated_video.mp4")
        
        self.status_var.set("🎬 正在生成视频...")
        self.log(f"开始生成视频: {video_path}")
        
        def do_generate():
            from tkinter import messagebox
            
            def progress_callback(progress):
                self.update_progress(progress)
            
            success = VideoGenerator.generate_video(
                video_path, width, height, num_frames, fps, progress_callback
            )
            
            if success:
                self.log(f"✅ 视频已保存: {video_path}")
                self.status_var.set(f"✅ 视频生成完成: {video_path}")
                messagebox.showinfo("完成", f"视频已保存:\n{video_path}")
            else:
                self.log("❌ 视频生成失败")
                self.status_var.set("❌ 视频生成失败")
        
        thread = threading.Thread(target=do_generate, daemon=True)
        thread.start()
    
    def generate_audio_only(self):
        """仅生成音频"""
        if not self.deps["numpy"]:
            messagebox.showerror("错误", "缺少依赖: numpy")
            return
        
        try:
            freq = float(self.freq_var.get())
            duration = float(self.duration_var.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return
        
        output_dir = Path(self.output_dir_var.get())
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = str(output_dir / "generated_audio.wav")
        
        self.status_var.set("🎵 正在生成音频...")
        self.log(f"开始生成音频: {audio_path}")
        
        def do_generate():
            from tkinter import messagebox
            try:
                import numpy as np
                
                self.log(f"   频率: {freq} Hz, 时长: {duration} 秒")
                self.update_progress(10)
                
                audio_data, sample_rate = AudioGenerator.generate_simple_tone(freq, duration)
                self.update_progress(50)
                
                if audio_data is not None:
                    success = AudioGenerator.save_wav(audio_path, audio_data, sample_rate)
                    self.update_progress(100)
                    
                    if success:
                        self.log(f"✅ 音频已保存: {audio_path}")
                        self.status_var.set(f"✅ 音频生成完成: {audio_path}")
                        messagebox.showinfo("完成", f"音频已保存:\n{audio_path}")
                    else:
                        self.log("❌ 音频保存失败")
                        self.status_var.set("❌ 音频保存失败")
                else:
                    self.log("❌ 音频生成失败")
                    self.status_var.set("❌ 音频生成失败")
            except Exception as e:
                self.log(f"❌ 错误: {e}")
                self.status_var.set("❌ 音频生成失败")
        
        thread = threading.Thread(target=do_generate, daemon=True)
        thread.start()
    
    def generate_complete_video(self):
        """生成带音频的完整视频"""
        # 检查依赖
        if not self.deps["numpy"] or not self.deps["cv2"]:
            messagebox.showerror("错误", "缺少依赖: numpy 和 opencv-python (用于视频生成)")
            return
        
        # 先生成视频
        self.log("=" * 50)
        self.log("开始生成完整视频 (视频 + 音频)")
        self.log("=" * 50)
        
        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
            num_frames = int(self.frames_var.get())
            fps = int(self.fps_var.get())
            freq = float(self.freq_var.get())
            duration = float(self.duration_var.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return
        
        output_dir = Path(self.output_dir_var.get())
        output_dir.mkdir(parents=True, exist_ok=True)
        video_path = str(output_dir / "temp_video.mp4")
        audio_path = str(output_dir / "temp_audio.wav")
        final_path = str(output_dir / "final_video_with_audio.mp4")
        
        self.status_var.set("🎬🎵 正在生成完整视频...")
        
        def do_generate():
            from tkinter import messagebox
            
            # 步骤1: 生成视频
            self.log("步骤 1/4: 生成视频...")
            self.update_progress(0)
            
            def progress_callback(progress):
                self.update_progress(progress * 0.5)  # 视频占50%进度
            
            video_success = VideoGenerator.generate_video(
                video_path, width, height, num_frames, fps, progress_callback
            )
            
            if not video_success:
                self.log("❌ 视频生成失败")
                self.status_var.set("❌ 视频生成失败")
                return
            
            self.log(f"✅ 视频已生成: {video_path}")
            self.update_progress(50)
            
            # 步骤2: 生成音频
            self.log("步骤 2/4: 生成音频...")
            try:
                import numpy as np
                
                audio_data, sample_rate = AudioGenerator.generate_simple_tone(freq, duration)
                
                if audio_data is not None:
                    AudioGenerator.save_wav(audio_path, audio_data, sample_rate)
                    self.log(f"✅ 音频已生成: {audio_path}")
                else:
                    self.log("❌ 音频生成失败")
                    self.status_var.set("❌ 音频生成失败")
                    return
            except Exception as e:
                self.log(f"❌ 音频生成失败: {e}")
                self.status_var.set("❌ 音频生成失败")
                return
            
            self.update_progress(70)
            
            # 步骤3: 合并音视频
            self.log("步骤 3/4: 合并音视频...")
            merger = MediaMerger()
            merge_success = merger.merge_audio_video(video_path, audio_path, final_path)
            
            if not merge_success:
                self.log("⚠️ 自动合并失败，但视频和音频文件已单独生成")
                self.log(f"   视频: {video_path}")
                self.log(f"   音频: {audio_path}")
                self.log("   你可以手动使用 ffmpeg 合并这两个文件")
                self.status_var.set("⚠️ 合并失败，但文件已生成")
                self.update_progress(100)
                return
            
            self.update_progress(90)
            
            # 步骤4: 清理临时文件
            self.log("步骤 4/4: 清理临时文件...")
            try:
                os.remove(video_path)
                os.remove(audio_path)
                self.log("✅ 临时文件已清理")
            except Exception as e:
                self.log(f"⚠️ 清理临时文件失败: {e}")
            
            self.update_progress(100)
            self.log("=" * 50)
            self.log(f"✅ 完整视频已生成: {final_path}")
            self.log("=" * 50)
            self.status_var.set(f"✅ 完整视频已生成: {final_path}")
            
            messagebox.showinfo("完成", f"带音频的视频已生成!\n\n文件路径:\n{final_path}")
        
        thread = threading.Thread(target=do_generate, daemon=True)
        thread.start()

# ==================== 主程序入口 ====================
def main():
    """主程序入口"""
    import tkinter as tk
    from tkinter import messagebox
    
    print("=" * 60)
    print("   🎬 带音频的视频生成软件 v1.0")
    print("   整合 autowav.py + flash.py + faatt.py")
    print("=" * 60)
    
    # 检查依赖
    deps = check_dependencies()
    print("\n依赖检查结果:")
    for name, status in deps.items():
        icon = "✅" if status else "❌"
        print(f"   {icon} {name}")
    
    missing = [name for name, status in deps.items() if not status]
    if missing:
        print(f"\n⚠️ 缺少依赖: {', '.join(missing)}")
        print("请安装缺少的依赖:")
        print(f"   pip install {' '.join(missing)}")
        
        if "tkinter" in missing:
            print("\n❌ tkinter 未安装，无法启动GUI")
            print("   请安装 python3-tk (Linux) 或使用完整Python安装 (Windows/Mac)")
            return
    
    # 启动GUI
    root = tk.Tk()
    app = IntegratedGeneratorGUI(root)
    
    def on_closing():
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
