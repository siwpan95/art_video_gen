#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密/压缩后处理对话框
从 att_view.py 中调用，收集用户设置后回调 ViewModel 处理方法。
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path


def show_crypto_dialog(parent, viewmodel):
    """
    显示加密后处理对话框

    Args:
        parent:    父窗口 (tk.Tk 或 tk.Toplevel)
        viewmodel: IntegratedViewModel 实例（用于回调处理）
    """
    dlg = tk.Toplevel(parent)
    dlg.title("[CRYPTO] 视频加密 / 压缩后处理")
    dlg.geometry("520x420")
    dlg.configure(bg="#1a1a2e")
    dlg.resizable(False, False)
    dlg.transient(parent)
    dlg.grab_set()

    # ============ 标题 ============
    tk.Label(
        dlg, text="[CRYPTO] 视频加密 / 压缩后处理",
        font=("Microsoft YaHei", 13, "bold"),
        bg="#1a1a2e", fg="#e94560"
    ).pack(pady=(12, 4))

    tk.Label(
        dlg,
        text="对已有视频进行：签名水印 → 有损压缩 → AES-256 加密",
        font=("Microsoft YaHei", 8),
        bg="#1a1a2e", fg="#888"
    ).pack(pady=(0, 10))

    # ============ 输入文件 ============
    file_frame = tk.Frame(dlg, bg="#1a1a2e")
    file_frame.pack(fill=tk.X, padx=18, pady=4)

    tk.Label(file_frame, text="视频文件:", bg="#1a1a2e", fg="#eee",
             font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)

    file_var = tk.StringVar()
    # 尝试自动填入最近生成的视频
    try:
        from att_viewmodel import IntegratedViewModel
        # viewmodel 会传入，直接用
        last = viewmodel.config.last_video_path
        if last and Path(last).exists():
            file_var.set(last)
    except Exception:
        pass

    entry_file = tk.Entry(file_frame, textvariable=file_var,
                          font=("Consolas", 9), bg="#0d1117", fg="#eee",
                          insertbackground="#eee", width=32)
    entry_file.pack(side=tk.LEFT, padx=4)

    def _browse():
        p = filedialog.askopenfilename(
            title="选择要处理的视频",
            filetypes=[("MP4 文件", "*.mp4"), ("所有文件", "*.*")]
        )
        if p:
            file_var.set(p)

    tk.Button(file_frame, text="浏览...", command=_browse,
               bg="#21262d", fg="#58a6ff", font=("Microsoft YaHei", 8),
               activebackground="#30363d",
               relief=tk.FLAT, padx=6, pady=2).pack(side=tk.LEFT)

    # ============ 签名设置 ============
    sig_frame = tk.LabelFrame(dlg, text="[EDIT] 英文签名水印",
                               bg="#1a1a2e", fg="#0f9d58",
                               font=("Microsoft YaHei", 9, "bold"),
                               padx=8, pady=4)
    sig_frame.pack(fill=tk.X, padx=14, pady=(4, 2))

    sig_inner = tk.Frame(sig_frame, bg="#1a1a2e")
    sig_inner.pack(fill=tk.X, padx=4, pady=2)

    tk.Label(sig_inner, text="签名文本:", bg="#1a1a2e", fg="#ccc",
             font=("Microsoft YaHei", 8)).pack(side=tk.LEFT)

    sig_var = tk.StringVar(value=viewmodel.config.crypto_signature or "FullstackDev")
    tk.Entry(sig_inner, textvariable=sig_var, width=18,
             font=("Consolas", 9), bg="#0d1117", fg="#eee",
             insertbackground="#eee").pack(side=tk.LEFT, padx=4)

    tk.Label(sig_inner, text="  位置:", bg="#1a1a2e", fg="#ccc",
             font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=(8, 2))

    sig_pos_var = tk.StringVar(value="bottom-right")
    ttk.Combobox(sig_inner, textvariable=sig_pos_var,
                   values=["bottom-right", "bottom-left", "top-right", "top-left"],
                   width=12, state="readonly").pack(side=tk.LEFT)

    # ============ 压缩设置 ============
    comp_frame = tk.LabelFrame(dlg, text="[PACK] 有损压缩",
                                bg="#1a1a2e", fg="#3498db",
                                font=("Microsoft YaHei", 9, "bold"),
                                padx=8, pady=4)
    comp_frame.pack(fill=tk.X, padx=14, pady=2)

    comp_inner = tk.Frame(comp_frame, bg="#1a1a2e")
    comp_inner.pack(fill=tk.X, padx=4, pady=2)

    tk.Label(comp_inner, text="压缩预设:", bg="#1a1a2e", fg="#ccc",
             font=("Microsoft YaHei", 8)).pack(side=tk.LEFT)

    comp_var = tk.StringVar(value=viewmodel.config.crypto_compress or "medium")
    ttk.Combobox(comp_inner, textvariable=comp_var,
                   values=["low", "medium", "high", "ultra"],
                   width=10, state="readonly").pack(side=tk.LEFT, padx=4)

    tk.Label(comp_inner, text="(low=小文件, ultra=高画质)",
             bg="#1a1a2e", fg="#666",
             font=("Microsoft YaHei", 7)).pack(side=tk.LEFT, padx=(6, 0))

    # ============ 加密设置 ============
    enc_frame = tk.LabelFrame(dlg, text="[KEY] AES-256-GCM 加密",
                               bg="#1a1a2e", fg="#f1c40f",
                               font=("Microsoft YaHei", 9, "bold"),
                               padx=8, pady=4)
    enc_frame.pack(fill=tk.X, padx=14, pady=2)

    enc_inner1 = tk.Frame(enc_frame, bg="#1a1a2e")
    enc_inner1.pack(fill=tk.X, padx=4, pady=2)

    tk.Label(enc_inner1, text="加密密码:", bg="#1a1a2e", fg="#ccc",
             font=("Microsoft YaHei", 8)).pack(side=tk.LEFT)

    pwd_var = tk.StringVar(value=viewmodel.config.crypto_password or "")
    entry_pwd = tk.Entry(enc_inner1, textvariable=pwd_var, width=22,
                          font=("Consolas", 9), bg="#0d1117", fg="#eee",
                          insertbackground="#eee", show="*")
    entry_pwd.pack(side=tk.LEFT, padx=4)

    tk.Label(enc_inner1, text="(留空=随机密钥)",
             bg="#1a1a2e", fg="#666",
             font=("Microsoft YaHei", 7)).pack(side=tk.LEFT, padx=(4, 0))

    enc_inner2 = tk.Frame(enc_frame, bg="#1a1a2e")
    enc_inner2.pack(fill=tk.X, padx=4, pady=(0, 2))

    bomb_var = tk.BooleanVar(value=viewmodel.config.crypto_bomb or False)
    tk.Checkbutton(enc_inner2, text="[BOMB] 生成压缩炸弹（仅用于安全研究！）",
                  variable=bomb_var,
                  bg="#1a1a2e", fg="#e94560",
                  font=("Microsoft YaHei", 8),
                  selectcolor="#1a1a2e",
                  activebackground="#1a1a2e").pack(side=tk.LEFT, padx=(0, 4))

    # ============ 进度条 ============
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(dlg, variable=progress_var,
                                     maximum=100, mode='determinate',
                                     length=480)
    progress_bar.pack(padx=18, pady=(6, 2))

    status_var = tk.StringVar(value="就绪")
    tk.Label(dlg, textvariable=status_var,
              bg="#1a1a2e", fg="#aaa",
              font=("Consolas", 8)).pack()

    # ============ 按钮 ============
    btn_frame = tk.Frame(dlg, bg="#1a1a2e")
    btn_frame.pack(pady=(6, 12))

    # ---- 处理 ----
    def _do_process():
        video_path = file_var.get().strip()
        if not video_path or not Path(video_path).exists():
            messagebox.showerror("错误", "请选择有效的视频文件！", parent=dlg)
            return

        # 更新 config（持久化）
        viewmodel.config.crypto_signature = sig_var.get()
        viewmodel.config.crypto_compress = comp_var.get()
        viewmodel.config.crypto_password = pwd_var.get()
        viewmodel.config.crypto_bomb = bomb_var.get()

        # 构造 CryptoConfig
        try:
            from att_crypto import CryptoConfig
        except ImportError:
            messagebox.showerror("错误", "att_crypto.py 模块未找到！", parent=dlg)
            return

        cfg = CryptoConfig()
        cfg.signature_text = sig_var.get()
        cfg.signature_pos = sig_pos_var.get()
        cfg.compress_preset = comp_var.get()
        cfg.compression_bomb = bomb_var.get()

        password = pwd_var.get() or None

        def _callback(pct):
            progress_var.set(pct)
            dlg.update_idletasks()

        def _worker():
            try:
                from att_crypto import process_video
                status_var.set("处理中，请稍候...")
                dlg.update_idletasks()

                results = process_video(
                    video_path,
                    output_dir=str(Path(__file__).resolve().parent / "output"),  # 原 D:\allin 已失效
                    config=cfg,
                    password=password,
                    progress_callback=_callback
                )

                status_var.set("[OK] 处理完成！")
                # 显示结果
                msg = "处理完成！输出文件：\n"
                for k, v in results.items():
                    label = {
                        "watermarked": "水印版（可播放）  ",
                        "compressed":  "压缩版（可播放）  ",
                        "encrypted":   "加密版（不可播放）",
                        "key_file":    "密钥文件          ",
                        "bomb":        "压缩炸弹（危险！） ",
                    }.get(k, k)
                    msg += f"\n  {label}: {v}"
                messagebox.showinfo("完成", msg, parent=dlg)

                # 保存配置
                try:
                    viewmodel.config.last_video_path = video_path
                except Exception:
                    pass

            except Exception as e:
                status_var.set(f"[ERR] 错误: {e}")
                messagebox.showerror("错误", str(e), parent=dlg)
                import traceback; traceback.print_exc()

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    tk.Button(
        btn_frame, text="[RUN] 开始处理",
        command=_do_process,
        bg="#0f9d58", fg="white",
        font=("Microsoft YaHei", 10, "bold"),
        padx=20, pady=6
    ).pack(side=tk.LEFT, padx=8)

    # ---- 关闭 ----
    def _close():
        dlg.grab_release()
        dlg.destroy()

    tk.Button(
        btn_frame, text="关闭",
        command=_close,
        bg="#21262d", fg="#ccc",
        font=("Microsoft YaHei", 9),
        padx=16, pady=6
    ).pack(side=tk.LEFT, padx=8)

    dlg.wait_window()
