#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本 - 验证 MVVM 架构
"""

import sys
import os

def test_imports():
    """测试导入各层"""
    print("=" * 60)
    print("测试 1: 导入各层")
    print("=" * 60)
    
    try:
        # 测试 Model 层导入
        print("\n[1/4] 测试 Model 层导入...")
        from att_model import (
            check_dependencies,
            AudioGenerator,
            VideoGenerator,
            MediaMerger,
            GenerationConfig
        )
        print("✅ Model 层导入成功")
        print("    - check_dependencies")
        print("    - AudioGenerator")
        print("    - VideoGenerator")
        print("    - MediaMerger")
        print("    - GenerationConfig")
    except ImportError as e:
        print(f"❌ Model 层导入失败: {e}")
        return False
    
    try:
        # 测试 View 层导入
        print("\n[2/4] 测试 View 层导入...")
        from att_view import IntegratedGeneratorView
        print("✅ View 层导入成功")
        print("    - IntegratedGeneratorView")
    except ImportError as e:
        print(f"❌ View 层导入失败: {e}")
        return False
    
    try:
        # 测试 ViewModel 层导入
        print("\n[3/4] 测试 ViewModel 层导入...")
        from att_viewmodel import IntegratedViewModel
        print("✅ ViewModel 层导入成功")
        print("    - IntegratedViewModel")
    except ImportError as e:
        print(f"❌ ViewModel 层导入失败: {e}")
        return False
    
    try:
        # 测试主入口导入
        print("\n[4/4] 测试主入口导入...")
        from att_main import main
        print("✅ 主入口导入成功")
        print("    - main()")
    except ImportError as e:
        print(f"❌ 主入口导入失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有层导入测试通过!")
    print("=" * 60)
    return True


def test_model_layer():
    """测试 Model 层功能"""
    print("\n" + "=" * 60)
    print("测试 2: Model 层功能")
    print("=" * 60)
    
    from att_model import check_dependencies, GenerationConfig
    
    # 测试依赖检查
    print("\n[1/2] 测试依赖检查...")
    deps = check_dependencies()
    print(f"依赖状态:")
    for name, status in deps.items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {name}")
    print("✅ 依赖检查功能正常")
    
    # 测试配置模型
    print("\n[2/2] 测试配置模型...")
    config = GenerationConfig()
    print(f"默认配置:")
    print(f"  视频: {config.width}x{config.height}, {config.num_frames} 帧, {config.fps} FPS")
    print(f"  音频: {config.freq} Hz, {config.duration} 秒")
    print(f"  输出: {config.output_dir}")
    
    # 测试 to_dict 和 from_dict
    config_dict = config.to_dict()
    new_config = GenerationConfig.from_dict(config_dict)
    assert new_config.width == config.width
    print("✅ 配置模型功能正常")
    
    print("\n" + "=" * 60)
    print("✅ Model 层功能测试通过!")
    print("=" * 60)
    return True


def test_viewmodel_layer():
    """测试 ViewModel 层（无头模式）"""
    print("\n" + "=" * 60)
    print("测试 3: ViewModel 层（无头模式）")
    print("=" * 60)
    
    try:
        # 创建无头 Tkinter root
        print("\n[1/2] 创建测试环境...")
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # 隐藏窗口
        
        # 创建 View
        print("[2/2] 测试 ViewModel 初始化...")
        from att_view import IntegratedGeneratorView
        from att_viewmodel import IntegratedViewModel
        
        view = IntegratedGeneratorView(root)
        viewmodel = IntegratedViewModel(view)
        
        print("✅ ViewModel 初始化成功")
        print("   - View 已创建")
        print("   - ViewModel 已创建")
        print("   - 事件回调已绑定")
        
        # 销毁窗口
        root.destroy()
        
        print("\n" + "=" * 60)
        print("✅ ViewModel 层测试通过!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ ViewModel 层测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_structure():
    """测试文件结构"""
    print("\n" + "=" * 60)
    print("测试 4: 文件结构")
    print("=" * 60)
    
    expected_files = [
        "att_model.py",
        "att_view.py",
        "att_viewmodel.py",
        "att_main.py",
        "__init__.py"
    ]
    
    all_exist = True
    for filename in expected_files:
        filepath = os.path.join(os.path.dirname(__file__), filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"✅ {filename:<25} ({size:,} bytes)")
        else:
            print(f"❌ {filename:<25} (缺失)")
            all_exist = False
    
    if all_exist:
        print("\n" + "=" * 60)
        print("✅ 文件结构测试通过!")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("❌ 文件结构测试失败!")
        print("=" * 60)
        return False


def main():
    """主测试函数"""
    print("\n")
    print("=" * 60)
    print("   MVVM 架构验证测试")
    print("=" * 60)
    print("\n工作目录:", os.path.dirname(os.path.abspath(__file__)))
    
    # 切换工作目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 运行测试
    tests = [
        ("导入测试", test_imports),
        ("Model 层功能测试", test_model_layer),
        ("ViewModel 层测试", test_viewmodel_layer),
        ("文件结构测试", test_file_structure)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 发生异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 输出测试报告
    print("\n" + "=" * 60)
    print("   测试报告")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}  {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"总计: {passed + failed} 测试")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print("=" * 60)
    
    if failed == 0:
        print("\n🎉 所有测试通过! MVVM 架构验证成功!")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查上面的错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
