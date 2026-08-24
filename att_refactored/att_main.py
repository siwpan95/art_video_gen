#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
  主入口文件 (Main Entry Point)
  带音频的视频生成软件 - MVVM 架构
  
  职责：
  - 组装 MVVM 组件
  - 创建 View 和 ViewModel 实例
  - 启动主事件循环
============================================
"""

import sys
import tkinter as tk
from tkinter import messagebox

# 导入 MVVM 组件
from att_view import IntegratedGeneratorView
from att_viewmodel import IntegratedViewModel


def main():
    """主程序入口"""
    print("=" * 60)
    print("   [VIDEO] 音视频生成器 v2.0 (MVVM 架构 - 增强版)")
    print("   多种波形 | 和弦 | 调色板 | 丰富参数")
    print("=" * 60)
    
    # 检查 tkinter 是否可用
    try:
        import tkinter
    except ImportError:
        print("[ERR] tkinter 未安装，无法启动GUI")
        print("   请安装 python3-tk (Linux) 或使用完整Python安装 (Windows/Mac)")
        return
    
    # 创建 Tkinter 根窗口
    root = tk.Tk()
    
    # 创建 View（视图层）
    print("\n[1/3] 初始化 View 层...")
    view = IntegratedGeneratorView(root)
    
    # 创建 ViewModel（视图模型层）
    print("[2/3] 初始化 ViewModel 层...")
    viewmodel = IntegratedViewModel(view)
    
    # ViewModel 会自动绑定到 View 的事件回调
    print("[3/3] 绑定 MVVM 组件...")
    
    print("\n[OK] MVVM 架构组装完成!")
    print("=" * 60)
    print("启动 GUI...")
    print("=" * 60)
    
    # 定义关闭事件
    def on_closing():
        print("\n正在关闭应用程序...")
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 启动主事件循环
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n用户中断 (Ctrl+C)")
    except Exception as e:
        print(f"\n[ERR] 发生错误: {e}")
        messagebox.showerror("错误", f"发生未知错误:\n{e}")
    
    print("\n应用程序已退出。")


if __name__ == "__main__":
    main()
