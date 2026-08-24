"""
CA 配方管理模块 —— 扫描 ca_effects/ 目录加载 JSON 配方
从 draw/recipes.py 适配
"""

import json
from pathlib import Path


def load_ca_recipes(effects_dir, progress_callback=None):
    """扫描目录下所有 .json 配方，返回 {名称: 文件路径}

    Args:
        effects_dir: ca_effects 目录路径
        progress_callback: 可选回调 callback(current, total, filename)

    Returns:
        dict: {配方名称: 完整文件路径}
    """
    effects_dir = Path(effects_dir)
    if not effects_dir.exists():
        print(f"[CA配方] 目录不存在: {effects_dir}")
        return {}

    json_files = sorted(effects_dir.glob('*.json'))
    total = len(json_files)
    recipes = {}
    for i, fpath in enumerate(json_files):
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            name = data.get('name', fpath.stem)
            recipes[name] = str(fpath)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[CA配方] 跳过 {fpath.name}: {e}")
        if progress_callback:
            progress_callback(i + 1, total, fpath.name)
    return recipes


def get_ca_recipe_names(effects_dir):
    """仅获取配方名称列表（轻量）"""
    recipes = load_ca_recipes(effects_dir)
    return sorted(recipes.keys())
