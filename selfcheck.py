#!/usr/bin/env python3
"""无头自检：程序化音频生成 / WAV 往返 / 小尺寸视频写入读回。

只 import 纯逻辑类（AudioGenerator / VideoGenerator），不会创建 Tkinter 窗口。
运行：python selfcheck.py
"""
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def fail(msg):
    print(f"FAIL: {msg}")
    raise SystemExit(1)


def main():
    # 项目内部会用 emoji 打印进度，GBK 控制台下需切到 UTF-8 才不会抛 UnicodeEncodeError
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import numpy as np

    try:
        import integrated_video_audio_generator as proj
    except Exception as exc:  # pragma: no cover
        fail(f"导入入口模块失败: {exc}")

    deps = proj.check_dependencies()
    for name in ("numpy", "cv2"):
        if not deps.get(name):
            fail(f"缺少依赖: {name}")

    # ---------- 1. 音频：频率 + ADSR 包络 ----------
    sample_rate, duration, freq = 8000, 0.5, 440
    tone, sr = proj.AudioGenerator.generate_simple_tone(freq, duration, sample_rate)
    if tone is None or sr != sample_rate:
        fail("generate_simple_tone 未返回音频或采样率不符")
    if tone.shape != (int(sample_rate * duration),):
        fail(f"音频长度不符: {tone.shape}")
    if abs(float(tone[0])) > 1e-6 or abs(float(tone[-1])) > 1e-6:
        fail("ADSR 包络首尾未归零")
    if float(np.max(np.abs(tone))) > 0.5 + 1e-6:
        fail("音频幅度超出 0.5 上限")
    spectrum = np.abs(np.fft.rfft(tone))
    peak_hz = float(np.fft.rfftfreq(len(tone), 1.0 / sr)[int(np.argmax(spectrum))])
    if abs(peak_hz - freq) > 5:
        fail(f"主频不符: 期望 {freq}Hz，实测 {peak_hz:.1f}Hz")

    # ---------- 2. WAV 16-bit 往返 ----------
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "tone.wav"
        if not proj.AudioGenerator.save_wav(str(wav_path), tone, sr):
            fail("save_wav 返回 False")
        with wave.open(str(wav_path), "rb") as wf:
            if (wf.getnchannels(), wf.getsampwidth(), wf.getframerate()) != (1, 2, sr):
                fail("WAV 头信息不符（应为 mono/16-bit/采样率）")
            if wf.getnframes() != len(tone):
                fail(f"WAV 帧数不符: {wf.getnframes()} != {len(tone)}")
            raw = wf.readframes(wf.getnframes())
        written = np.frombuffer(raw, dtype="<i2")
        expected = (tone * 32767).astype(np.int16)
        max_diff = int(np.max(np.abs(written.astype(np.int32) - expected.astype(np.int32))))
        if max_diff > 1:
            fail(f"WAV 采样值往返偏差过大: {max_diff} LSB")

        # ---------- 3. 视频：写入 3 帧并读回 ----------
        video_path = Path(tmp) / "tiny.mp4"
        try:
            ok = proj.VideoGenerator.generate_video(
                str(video_path), width=32, height=32, num_frames=3, fps=5
            )
        except Exception as exc:
            fail(f"generate_video 抛异常: {exc!r}")
        if not ok or not video_path.is_file() or video_path.stat().st_size == 0:
            fail("视频文件未生成")
        import cv2

        cap = cv2.VideoCapture(str(video_path))
        try:
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            ok_read, frame = cap.read()
        finally:
            cap.release()
        if (frames, width, height) != (3, 32, 32):
            fail(f"视频读回参数不符: frames={frames}, {width}x{height}")
        if not ok_read or frame is None or frame.shape != (32, 32, 3):
            fail("视频首帧无法解码")

    print(
        "selfcheck ok: 440Hz 音调/ADSR 包络、WAV 16-bit 采样往返、"
        "32x32 三帧 OpenCV 视频写入并读回"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
