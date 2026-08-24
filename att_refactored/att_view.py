#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
  View 层 (View Layer)
  带音频的视频生成软件 - GUI 界面
  
  职责：
  - 构建 UI 组件
  - 显示数据和状态
  - 定义事件回调接口（由 ViewModel 绑定）
  - 不处理业务逻辑
============================================
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from pathlib import Path


class IntegratedGeneratorView:
    """主界面视图 - 只负责 UI 布局和显示"""
    
    def __init__(self, root):
        """
        初始化视图
        
        Args:
            root: Tkinter 根窗口
        """
        self.root = root
        self.root.title("[VIDEO] 音视频生成器 v3.0 (MVVM) — 音画联动版")
        self.root.geometry("850x1050")
        self.root.configure(bg="#1a1a2e")
        self.root.minsize(800, 700)
        
        # 事件回调（由 ViewModel 绑定）
        self.on_generate_video = None
        self.on_generate_audio = None
        self.on_generate_complete = None
        self.on_browse_dir = None
        self.on_crypto_process = None
        
        # UI 组件引用（供 ViewModel 更新）
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar()
        self.log_text = None
        
        # ========== 视频输入变量 ==========
        self.width_var = tk.StringVar(value="640")
        self.height_var = tk.StringVar(value="480")
        self.frames_var = tk.StringVar(value="300")
        self.fps_var = tk.StringVar(value="30")
        self.codec_var = tk.StringVar(value="mp4v")
        self.palette_var = tk.StringVar(value="霓虹")
        self.particle_var = tk.StringVar(value="20")
        self.speed_var = tk.StringVar(value="1.0")
        self.vbitrate_var = tk.StringVar(value="medium")
        self.effect_mode_var = tk.StringVar(value="元胞自动机")
        self.audio_path_var   = tk.StringVar(value="")       # 音频驱动文件
        self.audio_reactive_var = tk.DoubleVar(value=0.5)  # 驱动强度
        
        # ========== 音频输入变量 ==========
        self.wave_type_var = tk.StringVar(value="sine")
        self.freq_var = tk.StringVar(value="440")
        self.duration_var = tk.StringVar(value="10")
        self.volume_var = tk.StringVar(value="50")
        self.sample_rate_var = tk.StringVar(value="44100")
        self.channels_var = tk.StringVar(value="1")
        self.chord_var = tk.StringVar(value="无")
        
        # ========== 输出变量 ==========
        self.output_dir_var = tk.StringVar(value=str(Path(__file__).resolve().parent / "output"))  # 原 D:\allin 已失效
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        # ==================== 标题 ====================
        title_frame = tk.Frame(self.root, bg="#1a1a2e", height=60)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        
        title_label = tk.Label(
            title_frame, 
            text="[VIDEO] 音视频生成器 v2.0",
            font=("Microsoft YaHei", 18, "bold"),
            bg="#1a1a2e",
            fg="#e94560"
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="MVVM 架构 | 18种视频效果 | 音频驱动 | 多种波形 | 16色调色板 | 加密后处理",
            font=("Microsoft YaHei", 9),
            bg="#1a1a2e",
            fg="#aaa"
        )
        subtitle_label.pack()
        
        # ==================== 依赖状态 ====================
        dep_frame = tk.LabelFrame(
            self.root,
            text="[PACK] 依赖状态",
            bg="#1a1a2e",
            fg="#e94560",
            font=("Microsoft YaHei", 9, "bold"),
            padx=8, pady=4
        )
        dep_frame.pack(fill=tk.X, padx=10, pady=3)
        
        self.dep_text = tk.Text(
            dep_frame,
            height=3,
            bg="#0d1117",
            fg="#58a6ff",
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        self.dep_text.pack(fill=tk.X, padx=4, pady=3)
        
        # ==================== 视频设置 ====================
        video_frame = tk.LabelFrame(
            self.root,
            text="[VIDEO] 视频设置",
            bg="#1a1a2e",
            fg="#0f9d58",
            font=("Microsoft YaHei", 10, "bold"),
            padx=10, pady=5
        )
        video_frame.pack(fill=tk.X, padx=10, pady=3)
        
        # 第1行：分辨率 + 帧数 + FPS
        row1 = tk.Frame(video_frame, bg="#1a1a2e")
        row1.pack(fill=tk.X, pady=2)
        
        tk.Label(row1, text="分辨率:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        tk.Entry(row1, textvariable=self.width_var, width=5, font=("Consolas", 9), bg="#0d1117", fg="#eee", insertbackground="#eee").pack(side=tk.LEFT, padx=3)
        tk.Label(row1, text="x", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        tk.Entry(row1, textvariable=self.height_var, width=5, font=("Consolas", 9), bg="#0d1117", fg="#eee", insertbackground="#eee").pack(side=tk.LEFT, padx=3)
        
        tk.Label(row1, text="  帧数:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(15, 0))
        tk.Entry(row1, textvariable=self.frames_var, width=5, font=("Consolas", 9), bg="#0d1117", fg="#eee", insertbackground="#eee").pack(side=tk.LEFT, padx=3)
        
        tk.Label(row1, text="FPS:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(15, 0))
        tk.Entry(row1, textvariable=self.fps_var, width=4, font=("Consolas", 9), bg="#0d1117", fg="#eee", insertbackground="#eee").pack(side=tk.LEFT, padx=3)
        
        # 第2行：编码器 + 调色板
        row2 = tk.Frame(video_frame, bg="#1a1a2e")
        row2.pack(fill=tk.X, pady=2)
        
        tk.Label(row2, text="编码器:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        codec_combo = ttk.Combobox(row2, textvariable=self.codec_var, values=["mp4v", "avc1", "XVID", "MJPG"], width=8, state="readonly")
        codec_combo.pack(side=tk.LEFT, padx=3)
        
        tk.Label(row2, text="  主题:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(15, 0))
        palette_combo = ttk.Combobox(row2, textvariable=self.palette_var,
            values=["霓虹", "日落", "海洋", "森林", "岩浆", "星空", "极光", "赛博朋克",
                    "紫罗兰", "秋天", "薄荷", "暮光", "金属", "热带", "薰衣草", "暗物质"],
            width=8, state="readonly")
        palette_combo.pack(side=tk.LEFT, padx=3)
        
        # 第3行：粒子数量 + 动画速度 + 码率
        row3 = tk.Frame(video_frame, bg="#1a1a2e")
        row3.pack(fill=tk.X, pady=2)
        
        tk.Label(row3, text="粒子:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        tk.Entry(row3, textvariable=self.particle_var, width=5, font=("Consolas", 9), bg="#0d1117", fg="#eee", insertbackground="#eee").pack(side=tk.LEFT, padx=3)
        
        tk.Label(row3, text="  速度:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(15, 0))
        tk.Entry(row3, textvariable=self.speed_var, width=5, font=("Consolas", 9), bg="#0d1117", fg="#eee", insertbackground="#eee").pack(side=tk.LEFT, padx=3)
        
        tk.Label(row3, text="  码率:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(15, 0))
        vbitrate_combo = ttk.Combobox(row3, textvariable=self.vbitrate_var,
            values=["low", "medium", "high", "ultra"], width=8, state="readonly")
        vbitrate_combo.pack(side=tk.LEFT, padx=3)
        
        # 第4行：效果模式
        row4 = tk.Frame(video_frame, bg="#1a1a2e")
        row4.pack(fill=tk.X, pady=2)
        
        tk.Label(row4, text="效果模式:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        effect_combo = ttk.Combobox(row4, textvariable=self.effect_mode_var,
            values=["元胞自动机", "渐变流动", "几何图形", "分形图案", "噪声纹理", "脉冲波纹", "频谱可视化",
                    "反应扩散", "流动场", "L系统分形", "CA引擎", "粒子系统",
                    "公式驱动", "流体模拟", "频谱柱形图", "波形曲线",
                    "漩涡效果", "脉冲涟漪"],
            width=14, state="readonly")
        effect_combo.pack(side=tk.LEFT, padx=3)

        # 第5行：音频驱动文件
        row5 = tk.Frame(video_frame, bg="#1a1a2e")
        row5.pack(fill=tk.X, pady=2)

        tk.Label(row5, text="驱动音频:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        tk.Entry(row5, textvariable=self.audio_path_var, width=25,
                 font=("Consolas", 8), bg="#0d1117", fg="#eee", insertbackground="#eee").pack(side=tk.LEFT, padx=3)
        tk.Button(row5, text="浏览...", command=self._browse_audio,
                   bg="#21262d", fg="#58a6ff", font=("Microsoft YaHei", 8),
                   activebackground="#30363d", activeforeground="#58a6ff",
                   relief=tk.FLAT, padx=6, pady=1).pack(side=tk.LEFT, padx=3)

        # 第6行：音频驱动强度
        row6 = tk.Frame(video_frame, bg="#1a1a2e")
        row6.pack(fill=tk.X, pady=2)

        tk.Label(row6, text="驱动强度:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        tk.Scale(row6, variable=self.audio_reactive_var, from_=0.0, to=1.0,
                 resolution=0.05, orient=tk.HORIZONTAL, length=160,
                 bg="#1a1a2e", fg="#eee", font=("Consolas", 8),
                 troughcolor="#21262d", activebackground="#e95660").pack(side=tk.LEFT, padx=3)
        tk.Label(row6, textvariable=self.audio_reactive_var, bg="#1a1a2e", fg="#e95660",
                 font=("Consolas", 8), width=4).pack(side=tk.LEFT)
        
        # ==================== 音频设置 ====================
        audio_frame = tk.LabelFrame(
            self.root,
            text="[AUDIO] 音频设置",
            bg="#1a1a2e",
            fg="#f1c40f",
            font=("Microsoft YaHei", 10, "bold"),
            padx=10, pady=5
        )
        audio_frame.pack(fill=tk.X, padx=10, pady=3)
        
        # 第1行：波形 + 和弦
        arow1 = tk.Frame(audio_frame, bg="#1a1a2e")
        arow1.pack(fill=tk.X, pady=2)
        
        tk.Label(arow1, text="波形:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        wave_combo = ttk.Combobox(arow1, textvariable=self.wave_type_var,
            values=["sine", "square", "triangle", "sawtooth", "white_noise", "pink_noise"],
            width=10, state="readonly")
        wave_combo.pack(side=tk.LEFT, padx=3)
        
        tk.Label(arow1, text="  和弦:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(15, 0))
        chord_combo = ttk.Combobox(arow1, textvariable=self.chord_var,
            values=["无", "大三和弦", "小三和弦", "增和弦", "减和弦", "五和弦", "大七和弦"],
            width=10, state="readonly")
        chord_combo.pack(side=tk.LEFT, padx=3)
        
        # 第2行：频率 + 时长
        arow2 = tk.Frame(audio_frame, bg="#1a1a2e")
        arow2.pack(fill=tk.X, pady=2)
        
        tk.Label(arow2, text="频率 (Hz):", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        tk.Entry(arow2, textvariable=self.freq_var, width=6, font=("Consolas", 9), bg="#0d1117", fg="#eee", insertbackground="#eee").pack(side=tk.LEFT, padx=3)
        
        tk.Label(arow2, text="  时长 (秒):", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(15, 0))
        tk.Entry(arow2, textvariable=self.duration_var, width=6, font=("Consolas", 9), bg="#0d1117", fg="#eee", insertbackground="#eee").pack(side=tk.LEFT, padx=3)
        
        # 第3行：音量 + 采样率 + 通道
        arow3 = tk.Frame(audio_frame, bg="#1a1a2e")
        arow3.pack(fill=tk.X, pady=2)
        
        tk.Label(arow3, text="音量:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        tk.Entry(arow3, textvariable=self.volume_var, width=5, font=("Consolas", 9), bg="#0d1117", fg="#eee", insertbackground="#eee").pack(side=tk.LEFT, padx=3)
        tk.Label(arow3, text="%", bg="#1a1a2e", fg="#888", font=("Microsoft YaHei", 8)).pack(side=tk.LEFT)
        
        tk.Label(arow3, text="  采样率:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(15, 0))
        sr_combo = ttk.Combobox(arow3, textvariable=self.sample_rate_var,
            values=["44100", "48000", "22050", "16000"], width=8, state="readonly")
        sr_combo.pack(side=tk.LEFT, padx=3)
        
        tk.Label(arow3, text="  通道:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(15, 0))
        ch_combo = ttk.Combobox(arow3, textvariable=self.channels_var,
            values=["1 (单声道)", "2 (立体声)"], width=12, state="readonly")
        ch_combo.pack(side=tk.LEFT, padx=3)
        
        # ==================== 输出设置 ====================
        output_frame = tk.LabelFrame(
            self.root,
            text="[SAVE] 输出设置",
            bg="#1a1a2e",
            fg="#3498db",
            font=("Microsoft YaHei", 10, "bold"),
            padx=10, pady=5
        )
        output_frame.pack(fill=tk.X, padx=10, pady=3)
        
        dir_frame = tk.Frame(output_frame, bg="#1a1a2e")
        dir_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(dir_frame, text="输出目录:", bg="#1a1a2e", fg="#eee", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)
        tk.Entry(dir_frame, textvariable=self.output_dir_var, width=40, font=("Consolas", 9), bg="#0d1117", fg="#eee", insertbackground="#eee").pack(side=tk.LEFT, padx=5)
        tk.Button(dir_frame, text="浏览", command=self._on_browse_dir, bg="#3498db", fg="white", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=5)
        
        # ==================== 按钮区域 ====================
        button_frame = tk.Frame(self.root, bg="#1a1a2e")
        button_frame.pack(fill=tk.X, padx=10, pady=8)
        
        tk.Button(
            button_frame, 
            text="[VIDEO] 仅生成视频", 
            command=self._on_generate_video,
            bg="#e94560", 
            fg="white", 
            font=("Microsoft YaHei", 10, "bold"), 
            padx=18, 
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame, 
            text="[AUDIO] 仅生成音频", 
            command=self._on_generate_audio,
            bg="#f1c40f", 
            fg="#1a1a2e", 
            font=("Microsoft YaHei", 10, "bold"),
            padx=18, 
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame, 
            text="[VIDEO][AUDIO] 生成完整视频", 
            command=self._on_generate_complete,
            bg="#0f9d58", 
            fg="white", 
            font=("Microsoft YaHei", 10, "bold"),
            padx=18, 
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            button_frame, 
            text="[CRYPTO] 后处理", 
            command=self._on_crypto_process,
            bg="#9b59b6", 
            fg="white", 
            font=("Microsoft YaHei", 10, "bold"),
            padx=18, 
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        # ==================== 进度条 ====================
        self.progress_bar = ttk.Progressbar(
            self.root,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, padx=10, pady=3)
        
        # ==================== 日志输出 ====================
        log_frame = tk.LabelFrame(
            self.root,
            text="[LOG] 输出日志",
            bg="#1a1a2e",
            fg="#aaa",
            font=("Microsoft YaHei", 10, "bold"),
            padx=10, pady=5
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=3)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            wrap=tk.WORD,
            bg="#0d1117",
            fg="#8b949e",
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # ==================== 状态栏 ====================
        self.status_var.set("[OK] 就绪 — 设置参数后点击生成按钮")
        status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            bg="#16213e",
            fg="#eee",
            font=("Microsoft YaHei", 9),
            anchor=tk.W,
            relief=tk.SUNKEN,
            padx=10,
            pady=4
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    # ==================== 事件处理（转发给 ViewModel）====================
    def _on_generate_video(self):
        if self.on_generate_video:
            self.on_generate_video()
    
    def _on_generate_audio(self):
        if self.on_generate_audio:
            self.on_generate_audio()
    
    def _on_generate_complete(self):
        if self.on_generate_complete:
            self.on_generate_complete()
    
    def _on_browse_dir(self):
        if self.on_browse_dir:
            self.on_browse_dir()
        else:
            dir_path = filedialog.askdirectory(title="选择输出目录")
            if dir_path:
                self.output_dir_var.set(dir_path)
    
    # ==================== 供 ViewModel 调用的方法 ====================
    def update_dependencies(self, deps):
        dep_info = []
        for name, status in deps.items():
            icon = "[OK]" if status else "[ERR]"
            dep_info.append(f"{icon} {name}")
        
        self.dep_text.config(state=tk.NORMAL)
        self.dep_text.delete("1.0", tk.END)
        self.dep_text.insert("1.0", "  ".join(dep_info))
        self.dep_text.config(state=tk.DISABLED)
    
    def log(self, message):
        import time
        self.log_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def update_progress(self, value):
        self.progress_var.set(value)
        self.root.update_idletasks()
    
    def update_status(self, message):
        self.status_var.set(message)
    
    def get_video_settings(self):
        """获取视频设置"""
        try:
            return {
                "width": int(self.width_var.get()),
                "height": int(self.height_var.get()),
                "num_frames": int(self.frames_var.get()),
                "fps": int(self.fps_var.get()),
                "codec": self.codec_var.get(),
                "palette": self.palette_var.get(),
                "particle_count": int(self.particle_var.get()),
                "animation_speed": float(self.speed_var.get()),
                "video_bitrate": self.vbitrate_var.get(),
                "effect_mode": self.effect_mode_var.get(),
                "audio_path": self.audio_path_var.get().strip(),
                "audio_reactive": float(self.audio_reactive_var.get()),
            }
        except ValueError as e:
            self.show_error("错误", f"请输入有效的视频设置数字: {e}")
            return None
    
    def get_audio_settings(self):
        """获取音频设置"""
        try:
            # 解析通道数
            ch_str = self.channels_var.get()
            channels = 1 if "1" in ch_str else 2
            
            return {
                "wave_type": self.wave_type_var.get(),
                "freq": float(self.freq_var.get()),
                "duration": float(self.duration_var.get()),
                "volume": float(self.volume_var.get()) / 100.0,
                "sample_rate": int(self.sample_rate_var.get()),
                "channels": channels,
                "chord_type": self.chord_var.get(),
            }
        except ValueError as e:
            self.show_error("错误", f"请输入有效的音频设置数字: {e}")
            return None
    
    def get_output_dir(self):
        from pathlib import Path
        return Path(self.output_dir_var.get())
    
    def set_output_dir(self, path):
        self.output_dir_var.set(str(path))
    
    def _browse_audio(self):
        """浏览并选择音频驱动文件"""
        path = filedialog.askopenfilename(
            title="选择音频驱动文件（WAV 格式）",
            filetypes=[("WAV 文件", "*.wav"), ("所有文件", "*.*")]
        )
        if path:
            self.audio_path_var.set(path)
            self.log(f"[AUDIO] 音频驱动文件已选择: {path}")
    
    def show_error(self, title, message):
        self.root.after(0, lambda: messagebox.showerror(title, message))
    
    def show_info(self, title, message):
        self.root.after(0, lambda: messagebox.showinfo(title, message))
    
    def show_warning(self, title, message):
        self.root.after(0, lambda: messagebox.showwarning(title, message))
    
    def check_dependency(self, deps, required):
        missing = [dep for dep in required if not deps.get(dep, False)]
        if missing:
            self.show_error("错误", f"缺少依赖: {', '.join(missing)}")
            return False
        return True

    
    def _on_crypto_process(self):
        """启动加密后处理对话框"""
        if self.on_crypto_process:
            self.on_crypto_process()
    

if __name__ == "__main__":
    root = tk.Tk()
    view = IntegratedGeneratorView(root)
    
    def test_callback():
        print("Button clicked!")
    
    view.on_generate_video = test_callback
    view.on_generate_audio = test_callback
    view.on_generate_complete = test_callback
    
    view.log("测试日志消息")
    view.update_status("测试状态")
    view.update_progress(50)
    
    test_deps = {
        "numpy": True,
        "cv2": True,
        "scipy": True,
        "tkinter": True,
    }
    view.update_dependencies(test_deps)
    
    root.mainloop()
