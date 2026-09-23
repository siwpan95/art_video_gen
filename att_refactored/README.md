# 带音频的视频生成软件 (MVVM 架构) — 增强版

## ✨ 功能概览

- 🎬 **11 种视频效果**：元胞自动机、渐变流动、几何图形、分形图案、噪声纹理、脉冲波纹、频谱可视化、反应扩散、Perlin流动场、L系统分形、**CA引擎(66种配方)**
- 🎨 **16 色调色板** + **动态HSV颜色系统** (HueFlow/Energy/Rainbow)
- 🎵 **音频生成**：6种波形 (sine/square/triangle/sawtooth/white_noise/pink_noise) + 7种和弦
- 🎚️ **音频驱动**：画面随音频节奏动态变化 + **增强音频映射** (响应曲线/平滑阻尼)
- 🔐 **加密后处理**：签名水印 → 有损压缩 → AES-256-GCM 加密
- ⚡ **Numba JIT 加速**：安装 numba 后自动启用，大幅提升渲染速度
- 🎧 **Librosa 增强**：安装 librosa 后自动使用精准节拍/起音检测
- 🧬 **CA引擎集成**：66种数学公式驱动的细胞自动机配方（来自 draw 项目）
- 🎨 **颜色工具**：HSV流动渐变、能量映射、彩虹色（来自 pywallpaper 项目）

## 项目结构

```
att_refactored/
├── att_model.py          # Model 层 - 业务逻辑 (~2100行, 11种效果)
├── att_view.py           # View 层 - GUI 界面
├── att_viewmodel.py      # ViewModel 层 - 事件处理
├── att_crypto.py         # 加密/压缩/水印模块
├── att_crypto_dialog.py  # 加密后处理对话框
├── att_main.py           # 主入口
├── ca_engine.py          # [集成] CA渲染引擎 (来自 draw 项目)
├── ca_recipes.py         # [集成] CA配方管理 (来自 draw 项目)
├── color_utils.py        # [集成] 动态颜色工具 (来自 pywallpaper 项目)
├── ca_effects/           # [集成] 66个CA配方 JSON 文件
├── output/               # 输出目录
├── test_mvvm.py          # 测试文件
├── README.md
└── __init__.py
```

## MVVM 架构说明

### Model 层 (att_model.py)
**职责**：业务逻辑和数据模型

包含：
- `check_dependencies()` - 依赖检查
- `AudioGenerator` - 音频生成器（6波形 + 7和弦 + ADSR包络）
- `VideoGenerator` - 视频生成器（10效果 + 音频驱动 + 反应扩散/流动场/L系统）
- `MediaMerger` - 音视频合并器（FFmpeg）
- `GenerationConfig` - 生成配置数据模型
- `VIDEO_PALETTES` - 16色调色板
- **Numba JIT 加速函数** - `_numba_ca_step`, `_numba_gs_step`

### 新增效果说明

| 效果 | 描述 | 音频联动 | 来源 |
|------|------|----------|------|
| **反应扩散** | Gray-Scott 化学模拟，产生珊瑚/斑图有机纹理 | 音量→反应速率，低频→馈送率，节拍→重新播种 | — |
| **流动场** | Perlin噪声驱动的粒子流场，烟雾般的有机运动 | 音量→粒子速度，低频→流场扭曲 | — |
| **L系统分形** | 分形树/龙曲线/Sierpinski/Koch雪花四种模式 | 音量→生长速度，低频→分支角度 | — |
| **CA引擎** | 66种数学公式驱动的细胞自动机，含GameOfLife/Lenia/BZ反应等 | 节拍→切换配方，音量→演化速度，低频→颜色偏移 | draw项目 |

## 安装依赖

```bash
# 核心依赖（必需）
pip install numpy opencv-python scipy

# 可选加速（强烈推荐！显著提升渲染速度）
pip install numba

# 可选增强音频分析（更精准的节拍检测）
pip install librosa

# 可选加密后处理
pip install cryptography

# 一键安装所有可选依赖
pip install numba librosa cryptography
```

## 运行方法

### 方法 1：直接运行主入口
```bash
cd <PATH>
python att_main.py
```

### 方法 2：作为模块运行
```bash
cd D:/allin
python -m tools.art_video_gen.att_refactored.att_main
```

## 使用示例

```python
# 仅使用 Model 层（无 GUI）
from att_model import AudioGenerator, VideoGenerator, VIDEO_PALETTES

# 生成和弦音频
audio_data, sample_rate = AudioGenerator.generate_chord(
    wave_type="sine", root_freq=440, chord_type="大三和弦",
    duration=10, volume=0.5
)
AudioGenerator.save_wav("output.wav", audio_data, sample_rate)

# 生成反应扩散视频
VideoGenerator.generate_video(
    "output.mp4", 640, 480, 300, 30,
    palette_name="紫罗兰", effect_mode="反应扩散"
)

# 生成流动场视频（音频驱动）
VideoGenerator.generate_video(
    "output.mp4", 640, 480, 300, 30,
    palette_name="暮光", effect_mode="流动场",
    audio_path="music.wav", audio_reactive=0.7
)
```

## 文件说明

| 文件 | 行数 | 职责 |
|------|------|------|
| att_model.py | ~2100 | 业务逻辑和数据模型（11效果+加速+CA引擎） |
| att_view.py | ~530 | GUI 界面 |
| att_viewmodel.py | ~570 | 事件处理和状态管理 |
| att_crypto.py | ~690 | 加密/压缩/水印模块 |
| ca_engine.py | ~260 | CA渲染引擎核心（来自 draw 项目） |
| ca_recipes.py | ~40 | CA配方管理 |
| color_utils.py | ~135 | 动态颜色工具（来自 pywallpaper 项目） |
| att_main.py | ~78 | 主入口和组装 |

## 与原文件对比

**原文件** (`integrated_video_audio_generator.py`)：
- 单文件，所有代码混合
- ~750 行
- 7种视频效果

**MVVM 增强版**：
- 5 个模块文件，职责分离
- ~1900 行（模型层丰富）
- 10种视频效果 + Numba加速 + Librosa节拍检测 + 16色调色板
- 易于维护、测试和扩展

## 许可证

MIT License

## 版本

v2.0.0 (MVVM 增强版)
