# ATT — 集成音视频生成器

> 仓库：<https://gitee.com/siwpan/art_video_gen> ｜ 许可：MIT（见 [LICENSE](LICENSE)）

元胞自动机 + 粒子系统生成随机艺术视频，程序化合成音频，ffmpeg 合并。

## 功能

- **视频生成** — 元胞自动机 / 粒子系统生成抽象视觉
- **音频生成** — 程序化音频合成，与视觉同步
- **音视频合并** — ffmpeg 自动合并视频 + 音频
- **GUI 界面** — Tkinter 参数调节面板
- **MVVM 重构版** — att_refactored/ 子目录为架构升级版

## 快速开始

```bash
# 安装依赖
pip install numpy opencv-python scipy

# 安装 ffmpeg (Windows)
# 下载 ffmpeg 并加入 PATH 环境变量

# GUI 模式
python integrated_video_audio_generator.py

# MVVM 重构版
python att_refactored/att_main.py
```

## 项目结构

```
att/
├── integrated_video_audio_generator.py   # 主程序 (GUI + 视频+音频+合并)
├── INTEGRATED_USAGE.md                   # 详细使用手册
├── att_refactored/                       # MVVM 架构重构版
│   ├── att_main.py      # 主入口
│   ├── att_model.py     # 业务逻辑
│   ├── att_view.py      # GUI 界面
│   ├── att_viewmodel.py # 事件处理
│   └── att_crypto.py    # 加密/压缩模块
└── output/              # 输出目录
```

## 依赖

- Python >= 3.8
- numpy, opencv-python, scipy, tkinter
- ffmpeg (外部)
