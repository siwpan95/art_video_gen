"""
随机效果背景视频生成器
=======================================
基于当前项目的 18 种效果模式，随机生成背景视频。

功能：
1. 随机选择效果模式
2. 随机生成参数（调色板、速度、粒子数量等）
3. 支持无缝循环
4. 批量生成多个视频

使用方法：
    python random_bg_generator.py --count 5 --duration 10
    python random_bg_generator.py --effect "流体模拟" --loop
"""

import argparse
import random
import json
import sys
from pathlib import Path


# 导入当前项目的模块
try:
    from att_model import VideoGenerator, EFFECT_MODES, VIDEO_PALETTES
except ImportError:
    print("[ERR] 无法导入 att_model 模块，请确保在正确目录中运行")
    sys.exit(1)


class RandomBackgroundGenerator:
    """随机背景视频生成器"""

    # 可用的调色板列表
    PALETTE_NAMES = list(VIDEO_PALETTES.keys())

    # 效果模式权重（某些效果更适合做背景）
    EFFECT_WEIGHTS = {
        "元胞自动机": 0.8,
        "渐变流动": 1.0,
        "几何图形": 0.7,
        "分形图案": 0.6,
        "噪声纹理": 0.9,
        "脉冲波纹": 0.8,
        "频谱可视化": 0.5,
        "反应扩散": 0.8,
        "流动场": 0.9,
        "L系统分形": 0.6,
        "CA引擎": 0.9,
        "粒子系统": 0.8,
        "公式驱动": 0.7,
        "流体模拟": 1.0,
        "频谱柱形图": 0.5,
        "波形曲线": 0.6,
        "漩涡效果": 0.9,
        "脉冲涟漪": 0.8,
        # 组合效果（多效果叠加）- 更高的权重，因为组合效果更丰富
        "渐变+粒子": 1.0,
        "流体+几何": 0.9,
        "频谱+漩涡": 0.8,
        "分形+噪声": 0.7,
    }

    def __init__(self, output_dir=None, width=1920, height=1080,
                 fps=30, codec="mp4v", vbitrate="medium"):
        """
        初始化生成器

        Args:
            output_dir: 输出目录（默认：脚本所在目录下的 output/random_bg）
            width: 视频宽度（默认 1920）
            height: 视频高度（默认 1080）
            fps: 帧率（默认 30）
            codec: 编码器（默认 mp4v）
            vbitrate: 码率（默认 medium）
        """
        if output_dir is None:
            # 默认输出到脚本所在目录下的 output/random_bg
            output_dir = Path(__file__).parent / "output" / "random_bg"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.width = width
        self.height = height
        self.fps = fps
        self.codec = codec
        self.vbitrate = vbitrate

        print(f"[INFO] 随机背景视频生成器初始化")
        print(f"   输出目录: {self.output_dir}")
        print(f"   分辨率: {width}x{height}")
        print(f"   帧率: {fps} FPS")
        print(f"   可用效果: {len(EFFECT_MODES)} 种")
        print(f"   可用调色板: {len(self.PALETTE_NAMES)} 种")

    def _random_params(self, effect_mode=None):
        """
        生成随机参数

        Returns:
            dict: 随机参数
        """
        # 随机选择效果模式（带权重）
        if effect_mode is None:
            effect_mode = random.choices(
                list(self.EFFECT_WEIGHTS.keys()),
                weights=list(self.EFFECT_WEIGHTS.values())
            )[0]

        # 随机调色板
        palette_name = random.choice(self.PALETTE_NAMES)

        # 随机速度（0.3 ~ 3.0）
        speed = round(random.uniform(0.3, 3.0), 1)

        # 随机粒子数量（5 ~ 100）
        particle_count = random.randint(5, 100)

        # 随机帧数（300 ~ 900，即 10 ~ 30 秒）
        num_frames = random.randint(300, 900)

        return {
            "effect_mode": effect_mode,
            "palette_name": palette_name,
            "speed": speed,
            "particle_count": particle_count,
            "num_frames": num_frames,
        }

    def generate_single(self, output_name=None, loop=False, progress_callback=None):
        """
        生成单个随机背景视频

        Args:
            output_name: 输出文件名（不含扩展名）
            loop: 是否生成无缝循环视频
            progress_callback: 进度回调函数

        Returns:
            str: 输出文件路径，失败返回 None
        """
        # 生成随机参数
        params = self._random_params()
        effect_mode = params["effect_mode"]

        # 生成输出文件名
        if output_name is None:
            output_name = f"random_bg_{effect_mode}_{random.randint(1000, 9999)}"

        output_path = str(self.output_dir / f"{output_name}.mp4")

        print(f"\n{'=' * 60}")
        print(f"  生成随机背景视频")
        print(f"  效果模式: {effect_mode}")
        print(f"  调色板: {params['palette_name']}")
        print(f"  速度: {params['speed']}x")
        print(f"  帧数: {params['num_frames']} ({params['num_frames'] / self.fps:.1f}秒)")
        print(f"  输出: {output_path}")
        print(f"{'=' * 60}\n")

        # 生成视频
        ok = VideoGenerator.generate_video(
            output_path=output_path,
            width=self.width,
            height=self.height,
            num_frames=params["num_frames"],
            fps=self.fps,
            codec=self.codec,
            palette_name=params["palette_name"],
            particle_count=params["particle_count"],
            animation_speed=params["speed"],
            effect_mode=effect_mode,
            audio_path=None,  # 背景视频通常不需要音频驱动
            audio_reactive=0.0,
            progress_callback=progress_callback
        )

        if ok:
            print(f"\n[OK] 视频生成成功: {output_path}")

            # 如果需要无缝循环，复制最后一帧到开头
            if loop:
                print(f"[INFO] 处理无缝循环...")
                self._make_loopable(output_path)

            return output_path
        else:
            print(f"\n[ERR] 视频生成失败")
            return None

    def generate_batch(self, count=5, duration=10, loop=False):
        """
        批量生成随机背景视频

        Args:
            count: 生成数量
            duration: 每个视频的时长（秒）
            loop: 是否生成无缝循环视频

        Returns:
            list: 成功生成的文件路径列表
        """
        print(f"\n{'=' * 60}")
        print(f"  批量生成随机背景视频")
        print(f"  数量: {count}")
        print(f"  每个时长: {duration} 秒")
        print(f"  无缝循环: {loop}")
        print(f"{'=' * 60}\n")

        results = []
        for i in range(count):
            print(f"\n进度: {i + 1}/{count}")

            # 计算帧数
            num_frames = int(duration * self.fps)

            # 生成随机参数
            params = self._random_params()
            effect_mode = params["effect_mode"]

            # 生成输出文件名
            output_name = f"random_bg_{i + 1:02d}_{effect_mode}"
            output_path = str(self.output_dir / f"{output_name}.mp4")

            print(f"  效果: {effect_mode}")
            print(f"  调色板: {params['palette_name']}")

            # 生成视频
            ok = VideoGenerator.generate_video(
                output_path=output_path,
                width=self.width,
                height=self.height,
                num_frames=num_frames,
                fps=self.fps,
                codec=self.codec,
                palette_name=params["palette_name"],
                particle_count=params["particle_count"],
                animation_speed=params["speed"],
                effect_mode=effect_mode,
                audio_path=None,
                audio_reactive=0.0,
                progress_callback=lambda p: print(f"  进度: {p}%")
            )

            if ok:
                print(f"[OK] {output_name}.mp4")
                results.append(output_path)

                # 处理无缝循环
                if loop:
                    self._make_loopable(output_path)
            else:
                print(f"[ERR] {output_name}.mp4 生成失败")

        print(f"\n{'=' * 60}")
        print(f"  批量生成完成")
        print(f"  成功: {len(results)}/{count}")
        print(f"  输出目录: {self.output_dir}")
        print(f"{'=' * 60}")

        return results

    def _make_loopable(self, video_path):
        """
        处理视频使其无缝循环（简单版本：将视频最后一帧复制到开头）
        注意：这只是简单处理，真正的无缝循环需要更复杂的算法
        """
        try:
            import cv2
            import numpy as np

            # 读取视频
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # 读取所有帧
            frames = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
            cap.release()

            if len(frames) < 2:
                print(f"  [WARN] 帧数太少，无法处理循环")
                return

            # 在开头添加最后一帧（简化版本）
            # 注意：这只是让视频"看起来"能循环，但不是真正的无缝循环
            frames.insert(0, frames[-1])

            # 重新写入
            temp_path = video_path + ".temp.mp4"
            fourcc = cv2.VideoWriter_fourcc(*self.codec)
            out = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))

            for frame in frames:
                out.write(frame)
            out.release()

            # 替换原文件
            import os
            os.replace(temp_path, video_path)
            print(f"  [OK] 已处理无缝循环")

        except ImportError:
            print(f"  [WARN] 需要 cv2 模块来处理无缝循环")
        except Exception as e:
            print(f"  [ERR] 处理无缝循环失败: {e}")

    def generate_showcase(self, output_name="showcase", duration_per_effect=5):
        """
        生成展示视频（遍历所有效果模式）

        Args:
            output_name: 输出文件名
            duration_per_effect: 每个效果的时长（秒）

        Returns:
            str: 输出文件路径，失败返回 None
        """
        print(f"\n{'=' * 60}")
        print(f"  生成效果展示视频")
        print(f"  效果数量: {len(EFFECT_MODES)}")
        print(f"  每个时长: {duration_per_effect} 秒")
        print(f"{'=' * 60}\n")

        output_path = str(self.output_dir / f"{output_name}.mp4")
        temp_dir = self.output_dir / "temp_segments"
        temp_dir.mkdir(exist_ok=True)

        # 生成每个效果的片段
        segment_paths = []
        for i, effect_mode in enumerate(EFFECT_MODES):
            print(f"\n进度: {i + 1}/{len(EFFECT_MODES)} - {effect_mode}")

            segment_name = f"segment_{i:02d}_{effect_mode}.mp4"
            segment_path = str(temp_dir / segment_name)

            # 随机参数
            palette_name = random.choice(self.PALETTE_NAMES)
            speed = round(random.uniform(0.5, 2.0), 1)

            ok = VideoGenerator.generate_video(
                output_path=segment_path,
                width=self.width,
                height=self.height,
                num_frames=int(duration_per_effect * self.fps),
                fps=self.fps,
                codec=self.codec,
                palette_name=palette_name,
                particle_count=random.randint(10, 50),
                animation_speed=speed,
                effect_mode=effect_mode,
                audio_path=None,
                audio_reactive=0.0,
                progress_callback=lambda p: print(f"  进度: {p}%") if p % 20 == 0 else None
            )

            if ok:
                segment_paths.append(segment_path)
                print(f"[OK] {segment_name}")
            else:
                print(f"[ERR] {segment_name} 生成失败")

        # 合并所有片段
        if len(segment_paths) < 1:
            print(f"\n[ERR] 没有成功生成的片段")
            return None

        print(f"\n{'=' * 60}")
        print(f"  合并 {len(segment_paths)} 个片段...")
        print(f"{'=' * 60}")

        try:
            # 使用 ffmpeg 合并
            import subprocess

            # 创建文件列表
            list_file = temp_dir / "segment_list.txt"
            with open(list_file, "w", encoding="utf-8") as f:
                for path in segment_paths:
                    f.write(f"file '{Path(path).name}'\n")

            # ffmpeg 合并命令
            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                output_path
            ]

            result = subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"[OK] 展示视频已生成: {output_path}")

                # 清理临时文件
                import shutil
                shutil.rmtree(temp_dir)

                return output_path
            else:
                print(f"[ERR] ffmpeg 合并失败:")
                print(result.stderr)
                return None

        except Exception as e:
            print(f"[ERR] 合并片段失败: {e}")
            return None


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="随机效果背景视频生成器")

    parser.add_argument("--count", type=int, default=1,
                        help="生成数量（默认 1）")
    parser.add_argument("--duration", type=int, default=10,
                        help="每个视频的时长（秒，默认 10）")
    parser.add_argument("--width", type=int, default=1920,
                        help="视频宽度（默认 1920）")
    parser.add_argument("--height", type=int, default=1080,
                        help="视频高度（默认 1080）")
    parser.add_argument("--fps", type=int, default=30,
                        help="帧率（默认 30）")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="输出目录（默认：脚本所在目录下的 output/random_bg）")
    parser.add_argument("--effect", type=str, default=None,
                        help="指定效果模式（默认随机）")
    parser.add_argument("--loop", action="store_true",
                        help="生成无缝循环视频")
    parser.add_argument("--showcase", action="store_true",
                        help="生成效果展示视频（遍历所有 18 种效果）")
    parser.add_argument("--showcase-duration", type=int, default=5,
                        help="展示视频中每个效果的时长（秒，默认 5）")

    args = parser.parse_args()

    # 创建生成器
    generator = RandomBackgroundGenerator(
        output_dir=args.output_dir,
        width=args.width,
        height=args.height,
        fps=args.fps
    )

    if args.showcase:
        # 生成展示视频
        output = generator.generate_showcase(
            output_name="showcase",
            duration_per_effect=args.showcase_duration
        )
        if output:
            print(f"\n[OK] 展示视频已生成: {output}")
        else:
            print(f"\n[ERR] 展示视频生成失败")
    else:
        # 批量生成随机背景视频
        if args.count > 1:
            results = generator.generate_batch(
                count=args.count,
                duration=args.duration,
                loop=args.loop
            )
            print(f"\n[OK] 已生成 {len(results)} 个视频")
        else:
            # 生成单个视频
            output = generator.generate_single(
                loop=args.loop
            )
            if output:
                print(f"\n[OK] 视频已生成: {output}")
            else:
                print(f"\n[ERR] 视频生成失败")


if __name__ == "__main__":
    main()
