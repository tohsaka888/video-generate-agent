"""
场景处理工具模块
提供分镜脚本处理、图片生成等功能
"""

import json
import os
from typing import List, Dict, Any
from utils.comfyui import generate_image


def setup_output_directories() -> Dict[str, str]:
    """设置输出目录结构（扁平化）"""
    directories = {
        "output_dir": "output",
        "images_dir": "output/images",
        "audio_dir": "output/audio", 
        "srt_dir": "output/srt",
    }
    
    # 创建所有必要的目录
    for dir_path in directories.values():
        os.makedirs(dir_path, exist_ok=True)
    
    return directories


def read_content_file(content_file: str = "output/content.txt") -> str:
    """读取小说内容文件"""
    if not os.path.exists(content_file):
        raise FileNotFoundError(f"内容文件不存在: {content_file}")
    
    with open(content_file, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if not content:
        raise ValueError("内容文件为空")
    
    return content


def save_scenes_scripts(scenes_scripts: List[Dict[str, Any]], output_file: str = "output/scenes.json") -> str:
    """保存分镜脚本到JSON文件"""
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(scenes_scripts, f, ensure_ascii=False, indent=2)
    
    return f"分镜脚本已保存到: {output_file}"


def load_scenes_scripts(json_file: str = "output/scenes.json") -> List[Dict[str, Any]]:
    """加载分镜脚本文件"""
    if not os.path.exists(json_file):
        raise FileNotFoundError(f"分镜脚本文件不存在: {json_file}")
    
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_scene_image(scene_data: Dict[str, Any], images_dir: str = "output/images") -> bool:
    """生成单个场景图片"""
    scene_id = scene_data.get("scene_id", 1)
    image_prompt = scene_data.get("image_prompt", "").strip()
    
    if not image_prompt:
        print(f"警告: 场景 {scene_id} 缺少图片提示词")
        return False
    
    # 确保图片目录存在
    os.makedirs(images_dir, exist_ok=True)
    
    image_path = os.path.join(images_dir, f"scene_{scene_id}.png")
    
    try:
        result = generate_image(prompt_text=image_prompt, save_path=image_path)
        return result and os.path.exists(image_path)
    except Exception as e:
        print(f"生成场景 {scene_id} 图片失败: {e}")
        return False


def batch_generate_images(scenes_scripts: List[Dict[str, Any]], images_dir: str = "output/images") -> Dict[str, Any]:
    """批量生成场景图片"""
    os.makedirs(images_dir, exist_ok=True)
    
    results = []
    success_count = 0
    
    for scene_data in scenes_scripts:
        success = generate_scene_image(scene_data, images_dir)
        results.append(success)
        if success:
            success_count += 1
    
    return {
        "total_scenes": len(scenes_scripts),
        "success_count": success_count,
        "failed_count": len(scenes_scripts) - success_count,
        "success_rate": f"{(success_count/len(scenes_scripts)*100):.1f}%" if scenes_scripts else "0%"
    }


def validate_scene_data(scene_data: Dict[str, Any]) -> bool:
    """简单验证场景数据的完整性"""
    required_fields = ["scene_id", "script", "image_prompt"]
    
    for field in required_fields:
        if field not in scene_data or not scene_data[field]:
            return False
    
    return True


def clean_scenes_data(scenes_scripts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """清理和标准化场景数据"""
    cleaned_scenes = []
    
    for i, scene in enumerate(scenes_scripts):
        if not validate_scene_data(scene):
            print(f"警告: 场景 {i+1} 数据不完整，跳过")
            continue
        
        # 标准化场景数据
        cleaned_scene = {
            "scene_id": scene.get("scene_id", i+1),
            "script": scene.get("script", "").strip(),
            "image_prompt": scene.get("image_prompt", "").strip()
        }
        
        cleaned_scenes.append(cleaned_scene)
    
    return cleaned_scenes
