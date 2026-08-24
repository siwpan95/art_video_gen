#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
  Crypto & Compression Module (att_crypto.py)
  视频加密/压缩/签名水印模块
  
  功能：
  - 英文签名水印叠加（OpenCV 烧入像素）
  - 有损压缩（FFmpeg 重新编码 / OpenCV 降级编码）
  - AES-256-GCM 对称加密（先压缩后加密）
  - 解密工具
  - 可选：压缩炸弹包装（zlib 高倍率）
============================================
"""

import os
import sys
import json
import base64
import hashlib
import secrets
import subprocess
import zlib
import struct
from pathlib import Path


# ==================== 配置类 ====================
class CryptoConfig:
    """加密/压缩配置"""

    def __init__(self):
        self.signature_text = "FullstackDev"   # 英文签名（修改为你自己的）
        self.signature_pos = "bottom-right"     # 位置
        self.signature_size = 0.8               # 字体大小倍率
        self.signature_opacity = 0.6            # 水印透明度 0~1
        self.compress_preset = "medium"         # 压缩预设：low, medium, high, ultra
        self.encrypt_cipher = "AES-256-GCM"    # 加密算法
        self.compression_bomb = False           # 是否启用压缩炸弹包装
        self.key_derivation_iterations = 100000 # PBKDF2 迭代次数

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    def from_dict(self, data):
        for k, v in data.items():
            if hasattr(self, k):
                setattr(self, k, v)


# ==================== 密钥管理 ====================
def generate_key(password=None, salt=None, iterations=100000):
    """
    生成 AES-256 密钥
    
    Returns:
        tuple: (key[32 bytes], salt[16 bytes])
    """
    if salt is None:
        salt = secrets.token_bytes(16)

    if password:
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
            32
        )
    else:
        key = secrets.token_bytes(32)

    return key, salt


def save_key_file(key, salt, filepath):
    """保存密钥到 JSON 文件（base64 编码）"""
    data = {
        "version": "1.0",
        "cipher": "AES-256-GCM",
        "key": base64.b64encode(key).decode("ascii"),
        "salt": base64.b64encode(salt).decode("ascii"),
        "note": "KEEP THIS FILE SECRET — Required for decryption."
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[OK] 密钥已保存: {filepath}")
    return True


def load_key_file(filepath):
    """从文件加载密钥"""
    with open(filepath, "r") as f:
        data = json.load(f)
    key = base64.b64decode(data["key"])
    salt = base64.b64decode(data["salt"])
    return key, salt


# ==================== AES-256-GCM 加密/解密 ====================
class AESCipher:
    """
    AES-256-GCM 对称加密（文件级）

    文件格式（加密输出）：
    ┌────────────┬────────────┬─────────────────┬────────────┐
    │ nonce (12B)│ header(4B)│ ciphertext (...) │ tag (16B)  │
    └────────────┴────────────┴─────────────────┴────────────┘
    """

    @staticmethod
    def check_dependency():
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            return True
        except ImportError:
            return False

    @staticmethod
    def _get_cipher_module():
        """延迟导入 cryptography 库"""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        return Cipher, algorithms, modes, default_backend

    @staticmethod
    def encrypt_file(input_path, output_path, key, chunk_size=64 * 1024):
        """
        加密文件（AES-256-GCM，流式处理）

        Args:
            input_path:  输入文件（压缩后的视频）
            output_path: 输出加密文件 (.bin)
            key:         32 字节密钥
            chunk_size:  分块大小

        Returns:
            bool: 成功返回 True
        """
        Cipher, algorithms, modes, default_backend = AESCipher._get_cipher_module()

        nonce = secrets.token_bytes(12)  # GCM 推荐 12 字节 nonce

        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()

        try:
            with open(input_path, "rb") as fin:
                with open(output_path, "wb") as fout:
                    # 写入 nonce (12B) + 4B 保留位（对齐 16 字节）
                    fout.write(nonce)
                    fout.write(b"\x00\x00\x00\x00")

                    while True:
                        chunk = fin.read(chunk_size)
                        if not chunk:
                            break
                        encrypted_chunk = encryptor.update(chunk)
                        fout.write(encrypted_chunk)

                    # 最终化，获取 tag
                    encryptor.finalize()
                    tag = encryptor.tag  # 16 字节
                    fout.write(tag)

            fsize = os.path.getsize(output_path)
            print(f"[OK] 加密完成: {output_path}")
            print(f"   文件大小: {fsize / 1024:.1f} KB")
            print(f"   Nonce: {nonce.hex()[:16]}... | Tag: {tag.hex()[:16]}...")
            return True

        except Exception as e:
            print(f"[ERR] 加密失败: {e}")
            import traceback; traceback.print_exc()
            return False

    @staticmethod
    def decrypt_file(input_path, output_path, key, chunk_size=64 * 1024):
        """
        解密文件（AES-256-GCM）

        Args:
            input_path:  输入加密文件
            output_path: 输出解密文件
            key:         32 字节密钥
            chunk_size:  分块大小

        Returns:
            bool: 成功返回 True
        """
        Cipher, algorithms, modes, default_backend = AESCipher._get_cipher_module()

        try:
            with open(input_path, "rb") as fin:
                # 读取 nonce (12B) + 4B 保留
                nonce_and_pad = fin.read(16)
                nonce = nonce_and_pad[:12]

                # 读取其余内容，最后 16 字节是 tag
                rest = fin.read()
                if len(rest) < 16:
                    print("[ERR] 加密文件格式错误（太小）")
                    return False
                tag = rest[-16:]
                ciphertext = rest[:-16]

            # 解密
            cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
            decryptor = cipher.decryptor()

            with open(output_path, "wb") as fout:
                decrypted = decryptor.update(ciphertext)
                fout.write(decrypted)
                decryptor.finalize()

            print(f"[OK] 解密完成: {output_path}")
            return True

        except Exception as e:
            print(f"[ERR] 解密失败: {e}")
            import traceback; traceback.print_exc()
            return False


# ==================== 签名水印（OpenCV 烧入） ====================
def add_signature_watermark(input_path, output_path, signature_text,
                             position="bottom-right", font_scale=0.8,
                             opacity=0.6, color=(255, 255, 255)):
    """
    在视频帧上叠加英文签名水印（烧入像素，不可去除）

    Args:
        input_path:     输入视频路径
        output_path:    输出视频路径
        signature_text: 英文签名文本
        position:       位置 (bottom-right/left, top-right/left)
        font_scale:     字体大小倍率
        opacity:        背景不透明度 0~1
        color:          文字 RGB 颜色

    Returns:
        bool: 成功返回 True
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("[ERR] 缺少 opencv-python，跳過水印")
        return False

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"[ERR] 无法打开视频: {input_path}")
        return False

    fps = max(1, int(cap.get(cv2.CAP_PROP_FPS)))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = max(0.3, font_scale)
    thickness = max(1, int(scale * 2))
    (text_w, text_h), baseline = cv2.getTextSize(signature_text, font, scale, thickness)

    # 位置
    margin = 20
    pos = position.lower().replace("_", "-")
    if "bottom" in pos and "right" in pos:
        x, y = w - text_w - margin, h - margin
    elif "bottom" in pos and "left" in pos:
        x, y = margin, h - margin
    elif "top" in pos and "right" in pos:
        x, y = w - text_w - margin, text_h + margin
    elif "top" in pos and "left" in pos:
        x, y = margin, text_h + margin
    else:
        x, y = w - text_w - margin, h - margin

    print(f"[SIGN]  添加签名水印: '{signature_text}' @ {position}")
    print(f"   视频: {w}x{h} | {fps}fps | ~{total} 帧")

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 半透明背景框
        bg_x1, bg_y1 = x - 6, y - text_h - 4
        bg_x2, bg_y2 = x + text_w + 6, y + 4
        overlay = frame.copy()
        cv2.rectangle(overlay, (bg_x1, bg_y1), (bg_x2, bg_y2), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 1.0 - opacity * 0.4, frame, opacity * 0.4, 0, frame)

        # 签名文字
        cv2.putText(frame, signature_text, (x, y), font, scale, color, thickness, cv2.LINE_AA)

        out.write(frame)
        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"   水印进度: {frame_idx}/{total}")

    cap.release()
    out.release()
    print(f"[OK] 水印添加完成: {output_path}")
    return True


# ==================== 有损压缩 ====================
def lossy_compress(input_path, output_path, preset="medium", use_ffmpeg=True):
    """
    有损压缩视频

    优先使用 FFmpeg (libx264)，失败时回退到 OpenCV 重新编码

    Returns:
        bool: 成功返回 True
    """
    preset_map = {
        "low":    {"crf": "35", "preset": "ultrafast"},
        "medium": {"crf": "28", "preset": "medium"},
        "high":   {"crf": "23", "preset": "slow"},
        "ultra":  {"crf": "18", "preset": "veryslow"},
    }
    params = preset_map.get(preset, preset_map["medium"])

    print(f"[PACK] 有损压缩 (预设: {preset}, CRF: {params['crf']})")

    # 尝试 FFmpeg
    if use_ffmpeg:
        ok = _compress_ffmpeg(input_path, output_path, params)
        if ok:
            return True
        print("[WARN]  FFmpeg 失败，回退到 OpenCV 重新编码...")

    # 回退：OpenCV 重新编码（会降低质量）
    return _compress_opencv(input_path, output_path, quality=preset)


def _compress_ffmpeg(input_path, output_path, params):
    """使用 FFmpeg 压缩"""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-c:v", "libx264",
        "-crf", params["crf"],
        "-preset", params["preset"],
        "-c:a", "aac",
        "-b:a", "128k",
        output_path
    ]
    print(f"   运行 FFmpeg...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=600
        )
        if result.returncode == 0:
            _print_compress_ratio(input_path, output_path)
            return True
        else:
            print(f"   [ERR] FFmpeg 返回码 {result.returncode}")
            print(f"   {result.stderr[-400:]}")
            return False
    except FileNotFoundError:
        print("   [ERR] 未找到 ffmpeg（请安装 FFmpeg 并添加到 PATH）")
        return False
    except subprocess.TimeoutExpired:
        print("   [ERR] FFmpeg 超时（视频太长）")
        return False
    except Exception as e:
        print(f"   [ERR] FFmpeg 异常: {e}")
        return False


def _compress_opencv(input_path, output_path, quality="medium"):
    """
    OpenCV 有损重新编码（降级参数模拟有损压缩）
    """
    try:
        import cv2
    except ImportError:
        print("[ERR] 缺少 opencv-python，无法压缩")
        return False

    quality_map = {"low": 30, "medium": 50, "high": 70, "ultra": 85}
    jpeg_quality = quality_map.get(quality, 50)

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"[ERR] 无法打开: {input_path}")
        return False

    fps = max(1, int(cap.get(cv2.CAP_PROP_FPS)))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    print(f"   OpenCV 重新编码（质量≈JPEG q={jpeg_quality}）...")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # 模拟有损：JPEG 压缩再解压
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality])
        frame_lossy = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        out.write(frame_lossy)

    cap.release()
    out.release()
    _print_compress_ratio(input_path, output_path)
    print(f"[OK] OpenCV 压缩完成: {output_path}")
    return True


def _print_compress_ratio(input_path, output_path):
    orig = os.path.getsize(input_path)
    new = os.path.getsize(output_path)
    if orig == 0:
        return
    ratio = new / orig * 100
    print(f"   原始: {orig / 1024 / 1024:.2f} MB → 压缩后: {new / 1024 / 1024:.2f} MB ({ratio:.1f}%)")


# ==================== 压缩炸弹（zlib 多轮压缩） ====================
def create_compression_bomb(input_path, output_path, layers=3):
    """
    创建压缩炸弹（zlib 多轮压缩后包装成 ZIP）

    [WARN] 警告：此文件解压时可能耗尽系统资源！
    仅用于安全研究/压力测试！

    Args:
        input_path:  输入文件（已加密的 .bin）
        output_path: 输出 .zip 路径
        layers:      zlib 压缩轮数

    Returns:
        bool
    """
    print(f"[BOMB] 创建压缩炸弹（{layers} 层 zlib 压缩）...")
    print(f"[WARN]  警告：解压此文件可能导致系统崩溃！仅用于研究目的！")

    try:
        import zipfile
        with open(input_path, "rb") as f:
            data = f.read()

        orig_kb = len(data) / 1024
        print(f"   输入大小: {orig_kb:.1f} KB")

        # 多轮 zlib 压缩
        for layer in range(layers):
            compressed = zlib.compress(data, level=9)
            new_kb = len(compressed) / 1024
            ratio = new_kb / max(1, orig_kb) * 100 if layer == 0 else len(compressed) / 1024
            print(f"   第 {layer + 1} 层: {len(data)/1024:.1f} KB → {new_kb:.1f} KB")
            data = compressed

        # 包装成 ZIP（单一文件）
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_STORED) as zf:
            zf.writestr("encrypted_video.bin", data)

        final_kb = os.path.getsize(output_path) / 1024
        print(f"[OK] 压缩炸弹已创建: {output_path} ({final_kb:.1f} KB)")
        print(f"   [WARN] 解压需要极其谨慎！")
        return True

    except Exception as e:
        print(f"[ERR] 创建压缩炸弹失败: {e}")
        return False


# ==================== 主工作流程 ====================
def process_video(input_video_path, output_dir=None, config=None,
                  password=None, progress_callback=None):
    """
    主处理流水线：

    流程：
      1. 添加签名水印（OpenCV 烧入）
      2. 有损压缩（FFmpeg / OpenCV）
      3. AES-256-GCM 加密（先压缩后加密）
      4. (可选) 压缩炸弹包装

    Args:
        input_video_path: 输入视频路径
        output_dir:       输出目录（None = 输入文件同目录）
        config:           CryptoConfig 实例
        password:         可选密码（用于派生密钥）
        progress_callback: 进度回调 function(percent)

    Returns:
        dict: {"watermarked", "compressed", "encrypted", "key_file", "bomb"[optional]}
    """
    if config is None:
        config = CryptoConfig()

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")  # 原 D:\allin 已失效
    os.makedirs(output_dir, exist_ok=True)

    stem = Path(input_video_path).stem
    print("\n" + "=" * 60)
    print("   [CRYPTO] 视频加密/压缩处理流水线")
    print("=" * 60)

    results = {}
    current_file = input_video_path

    # ---- Step 1: 签名水印 ----
    print(f"\n[1/4] 添加英文签名水印...")
    watermarked_path = str(Path(output_dir) / f"{stem}_signed.mp4")
    ok = add_signature_watermark(
        current_file, watermarked_path,
        signature_text=config.signature_text,
        position=config.signature_pos,
        font_scale=config.signature_size,
        opacity=config.signature_opacity
    )
    if ok:
        results["watermarked"] = watermarked_path
        current_file = watermarked_path
    else:
        print("   [WARN]  水印失败，跳过，继续使用原始文件")
        watermarked_path = current_file

    if progress_callback:
        progress_callback(20)

    # ---- Step 2: 有损压缩 ----
    print(f"\n[2/4] 有损压缩（预设: {config.compress_preset}）...")
    compressed_path = str(Path(output_dir) / f"{stem}_compressed.mp4")
    ok = lossy_compress(current_file, compressed_path, preset=config.compress_preset)
    if ok:
        results["compressed"] = compressed_path
        current_file = compressed_path
    else:
        print("   [WARN]  压缩失败，继续使用当前文件")

    if progress_callback:
        progress_callback(50)

    # ---- Step 3: AES 加密 ----
    print(f"\n[3/4] AES-256-GCM 加密...")
    if not AESCipher.check_dependency():
        print("[ERR] 缺少 cryptography 库，请运行: pip install cryptography")
        print("   跳過加密步骤")
    else:
        key, salt = generate_key(password, iterations=config.key_derivation_iterations)
        encrypted_path = str(Path(output_dir) / f"{stem}_encrypted.bin")
        ok = AESCipher.encrypt_file(current_file, encrypted_path, key)
        if ok:
            results["encrypted"] = encrypted_path
            current_file = encrypted_path

            # 保存密钥文件
            key_path = str(Path(output_dir) / f"{stem}_key.json")
            save_key_file(key, salt, key_path)
            results["key_file"] = key_path
        else:
            print("   [WARN]  加密失败")

    if progress_callback:
        progress_callback(80)

    # ---- Step 4: 压缩炸弹（可选）----
    if config.compression_bomb and "encrypted" in results:
        print(f"\n[4/4] 创建压缩炸弹...")
        bomb_path = str(Path(output_dir) / f"{stem}_bomb.zip")
        ok = create_compression_bomb(results["encrypted"], bomb_path)
        if ok:
            results["bomb"] = bomb_path

    if progress_callback:
        progress_callback(100)

    print("\n" + "=" * 60)
    print("[OK] 处理完成！输出文件：")
    print("=" * 60)
    for k, v in results.items():
        label = {
            "watermarked": "水印版（可播放）  ",
            "compressed":  "压缩版（可播放）  ",
            "encrypted":   "加密版（不可播放） ",
            "key_file":    "密钥文件          ",
            "bomb":        "压缩炸弹（危险！）",
        }.get(k, k)
        print(f"   {label}: {v}")

    return results


def decrypt_video(encrypted_path, key_file_path, output_path):
    """
    解密视频（从加密文件还原为 MP4）

    Args:
        encrypted_path:   加密文件 (.bin)
        key_file_path:    密钥文件 (.json)
        output_path:      解密输出路径 (.mp4)

    Returns:
        bool
    """
    print("[DECRYPT] 解密视频...")
    if not os.path.exists(encrypted_path):
        print(f"[ERR] 加密文件不存在: {encrypted_path}")
        return False
    if not os.path.exists(key_file_path):
        print(f"[ERR] 密钥文件不存在: {key_file_path}")
        return False

    key, salt = load_key_file(key_file_path)
    return AESCipher.decrypt_file(encrypted_path, output_path, key)


# ==================== CLI 入口 ====================
if __name__ == "__main__":
    import argparse

    print("=" * 60)
    print("  [CRYPTO] 视频加密/压缩/签名工具 (att_crypto)")
    print("=" * 60)

    parser = argparse.ArgumentParser(description="视频加密/压缩/签名工具")
    parser.add_argument("input", nargs="?", help="输入视频文件路径")
    parser.add_argument("-o", "--output-dir", default=None, help="输出目录")
    parser.add_argument("-s", "--signature", default="FullstackDev", help="英文签名文本")
    parser.add_argument("-p", "--preset", default="medium",
                        choices=["low", "medium", "high", "ultra"],
                        help="压缩预设（low=小文件, ultra=高画质）")
    parser.add_argument("-k", "--password", default=None,
                        help="AES 密钥密码（可选，不填则随机生成密钥）")
    parser.add_argument("-b", "--bomb", action="store_true",
                        help="启用压缩炸弹包装（危险！仅用于研究）")
    parser.add_argument("--decrypt", action="store_true",
                        help="解密模式（需要 --encrypted 和 --keyfile）")
    parser.add_argument("--encrypted", default=None, help="加密文件路径（解密模式）")
    parser.add_argument("--keyfile", default=None, help="密钥文件路径（解密模式）")
    parser.add_argument("--outfile", default=None, help="输出文件路径（解密模式）")

    args = parser.parse_args()

    # 解密模式
    if args.decrypt:
        if not args.encrypted or not args.keyfile:
            print("[ERR] 解密模式需要 --encrypted 和 --keyfile 参数")
            parser.print_help()
            sys.exit(1)
        out = args.outfile or args.encrypted.replace(".bin", "_decrypted.mp4")
        ok = decrypt_video(args.encrypted, args.keyfile, out)
        sys.exit(0 if ok else 1)

    # 加密模式
    if not args.input:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(args.input):
        print(f"[ERR] 输入文件不存在: {args.input}")
        sys.exit(1)

    config = CryptoConfig()
    config.signature_text = args.signature
    config.compress_preset = args.preset
    config.compression_bomb = args.bomb

    results = process_video(args.input, args.output_dir, config, args.password)

    print(f"\n[NOTE] 使用说明：")
    print(f"  - 水印版/压缩版可直接用播放器播放")
    print(f"  - 加密版需要解密后才能播放：")
    print(f"    python att_crypto.py --decrypt --encrypted <file> --keyfile <key.json>")
    sys.exit(0)
