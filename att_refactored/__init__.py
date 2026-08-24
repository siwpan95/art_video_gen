#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
  带音频的视频生成软件 - MVVM 架构
  
  这是一个 Python 包，包含以下模块：
  - att_model.py:      Model 层（业务逻辑）
  - att_view.py:       View 层（GUI 界面）
  - att_viewmodel.py:  ViewModel 层（事件处理）
  - att_main.py:       主入口文件
============================================
"""

__version__ = "1.0.0"
__author__ = "AI Assistant"
__description__ = "带音频的视频生成软件 (MVVM 架构)"

# 导出主要类
from .att_model import (
    check_dependencies,
    AudioGenerator,
    VideoGenerator,
    MediaMerger,
    GenerationConfig
)

from .att_view import IntegratedGeneratorView
from .att_viewmodel import IntegratedViewModel

__all__ = [
    # Model
    "check_dependencies",
    "AudioGenerator",
    "VideoGenerator",
    "MediaMerger",
    "GenerationConfig",
    # View
    "IntegratedGeneratorView",
    # ViewModel
    "IntegratedViewModel",
]
