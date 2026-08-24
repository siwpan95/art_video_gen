# 带音频的视频生成软件 - 使用说明

## 功能介绍

这是一个集成了三个模块的全功能视频生成软件：

1. **视频生成** (来自 flash.py) - 使用元胞自动机 + 粒子系统生成随机艺术视频
2. **音频生成** (来自 autowav.py) - 使用程序化合成生成音频
3. **音视频合并** - 使用 ffmpeg 将音频和视频合并为完整视频

## 安装依赖

### 必需依赖（核心功能）
```bash
pip install numpy opencv-python scipy
```

### 可选依赖（增强功能）
```bash
# 音频播放预览
pip install sounddevice

# 高级音频合成（完整版 faatt.py 功能）
pip install scipy sounddevice

# 深度学习视频生成（完整版 flash.py 功能）
pip install torch torchvision matplotlib scikit-learn networkx
```

### ffmpeg（用于合并音视频）
- **Windows**: 下载 https://ffmpeg.org/download.html，添加到 PATH
- **Mac**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

## 使用方法

### 方法1: GUI 界面（推荐）
```bash
python integrated_video_audio_generator.py
```

1. 设置视频参数：
   - 分辨率（默认 640x480）
   - 帧数（默认 300 帧）
   - FPS（默认 30）

2. 设置音频参数：
   - 频率（默认 440 Hz）
   - 时长（默认 10 秒）

3. 设置输出目录

4. 点击生成按钮：
   - **仅生成视频** - 生成无声视频
   - **仅生成音频** - 生成 WAV 音频文件
   - **生成完整视频** - 生成带音频的完整视频（需要 ffmpeg）

### 方法2: 命令行模式
```bash
# 仅生成视频
python integrated_video_audio_generator.py --video-only --output ./output

# 仅生成音频
python integrated_video_audio_generator.py --audio-only --freq 440 --duration 10

# 生成完整视频
python integrated_video_audio_generator.py --complete --output ./output
```

## 输出文件

- `generated_video.mp4` - 无声视频
- `generated_audio.wav` - 音频文件
- `final_video_with_audio.mp4` - 完整视频（带音频）

## 故障排除

### 问题1: 缺少依赖
```
❌ 缺少依赖: numpy
```
**解决**: 安装缺少的包 `pip install numpy`

### 问题2: ffmpeg 未找到
```
❌ 未找到 ffmpeg，无法合并音视频
```
**解决**: 
1. 安装 ffmpeg
2. 或手动合并：
   ```bash
   ffmpeg -i video.mp4 -i audio.wav -c:v copy -c:a aac output.mp4
   ```

### 问题3: 无法创建视频文件
```
❌ 无法创建视频文件: ...
```
**解决**: 
1. 检查输出目录权限
2. 安装正确版本的 opencv-python: `pip install opencv-python`

## 技术说明

### 视频生成算法
- 使用**元胞自动机**生成基础纹理
- 添加**粒子系统**增强动态效果
- 应用**颜色变换**和**调色板**

### 音频生成算法
- 使用**正弦波**合成基础音调
- 应用**ADSR 包络**（起音-衰减-持续-释放）
- 支持多种波形（正弦波、方波、锯齿波等）

## 自定义扩展

### 添加自定义视频效果
编辑 `VideoGenerator.generate_video()` 方法，添加更多视觉效果。

### 添加自定义音频合成
编辑 `AudioGenerator.generate_simple_tone()` 方法，实现更复杂的合成逻辑。

## 许可证

本软件集成自以下开源项目：
- autowav.py (MIT License)
- flash.py (MIT License)  
- faatt.py (MIT License)

## 联系支持

如有问题，请提交 Issue 或联系开发者。
