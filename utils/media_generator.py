"""
媒体生成工具模块
包含图片和音频生成的通用函数，支持并发处理
"""
import os
import json
import concurrent.futures
from typing import List, Dict, Any, Tuple
from utils.comfyui import generate_image
from utils.tts import generate_audio_for_script


class MediaGenerationResult:
    """媒体生成结果类"""
    def __init__(self):
        self.generated_images = []
        self.failed_images = []
        self.generated_audio = []
        self.generated_srt = []
        self.failed_audio = []
    
    def add_image_success(self, filename: str):
        """添加成功生成的图片"""
        self.generated_images.append(filename)
    
    def add_image_failure(self, filename: str, error: str = ""):
        """添加生成失败的图片"""
        error_msg = f"{filename}" + (f" (错误: {error})" if error else "")
        self.failed_images.append(error_msg)
    
    def add_audio_success(self, audio_file: str, srt_file: str):
        """添加成功生成的音频和字幕"""
        self.generated_audio.append(audio_file)
        self.generated_srt.append(srt_file)
    
    def add_audio_failure(self, audio_file: str, srt_file: str, error: str = ""):
        """添加生成失败的音频和字幕"""
        error_msg = f"{audio_file} / {srt_file}" + (f" (错误: {error})" if error else "")
        self.failed_audio.append(error_msg)
    
    def get_statistics(self, total_count: int) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_scenes": total_count,
            "image_success": len(self.generated_images),
            "image_failed": len(self.failed_images),
            "audio_success": len(self.generated_audio),
            "audio_failed": len(self.failed_audio),
            "image_success_rate": (len(self.generated_images) / total_count * 100) if total_count > 0 else 0,
            "audio_success_rate": (len(self.generated_audio) / total_count * 100) if total_count > 0 else 0
        }


def validate_scenes_scripts(scenes_scripts: List[Dict]) -> List[Dict]:
    """
    验证场景脚本数据的有效性，确保音色类型正确
    
    Args:
        scenes_scripts: 场景脚本列表
    
    Returns:
        验证并修正后的场景脚本列表
    """
    valid_voice_types = {"male", "female", "narrator"}
    
    for scene in scenes_scripts:
        voice_type = scene.get("voice_type", "narrator")
        if voice_type not in valid_voice_types:
            print(f"警告：场景 {scene.get('scene_index')} 的音色类型 '{voice_type}' 无效，已调整为 'narrator'")
            scene["voice_type"] = "narrator"
    
    return scenes_scripts


def load_scenes_scripts(json_path: str) -> Tuple[List[Dict], str]:
    """
    加载场景脚本配置文件
    
    Args:
        json_path: JSON文件路径
    
    Returns:
        (场景脚本列表, 错误信息)，如果成功则错误信息为空字符串
    """
    if not os.path.exists(json_path):
        return [], f"❌ 未找到 {json_path}，请先生成分镜和脚本"
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            scenes_scripts = json.load(f)
        
        if not scenes_scripts:
            return [], f"❌ {json_path} 为空"
        
        # 验证和修正数据
        scenes_scripts = validate_scenes_scripts(scenes_scripts)
        return scenes_scripts, ""
        
    except json.JSONDecodeError as e:
        return [], f"❌ JSON文件格式错误: {str(e)}"
    except Exception as e:
        return [], f"❌ 读取文件失败: {str(e)}"


def generate_single_image(item: Dict, images_dir: str) -> Dict[str, Any]:
    """
    生成单个图片
    
    Args:
        item: 场景配置项
        images_dir: 图片输出目录
    
    Returns:
        生成结果字典
    """
    try:
        scene_index = item.get("scene_index")
        scene_content = item.get("scene_prompt", "").strip()
        image_path = os.path.join(images_dir, f"scene_{scene_index}.png")
        
        print(f"🎨 正在生成第{scene_index}张图片...")
        result = generate_image(prompt_text=scene_content, save_path=image_path)
        
        if result and os.path.exists(image_path):
            print(f"✅ 第{scene_index}张图片生成成功: scene_{scene_index}.png")
            return {
                "success": True, 
                "file": f"scene_{scene_index}.png", 
                "index": scene_index
            }
        else:
            print(f"❌ 第{scene_index}张图片生成失败")
            return {
                "success": False, 
                "file": f"scene_{scene_index}.png", 
                "index": scene_index, 
                "error": "生成失败"
            }
    except Exception as e:
        print(f"❌ 第{scene_index}张图片生成异常: {str(e)}")
        return {
            "success": False, 
            "file": f"scene_{scene_index}.png", 
            "index": scene_index, 
            "error": str(e)
        }


def generate_single_audio(item: Dict, audio_dir: str, srt_dir: str, temp_dir: str) -> Dict[str, Any]:
    """
    生成单个音频和字幕
    
    Args:
        item: 场景配置项
        audio_dir: 音频输出目录
        srt_dir: 字幕输出目录
        temp_dir: 临时文件目录
    
    Returns:
        生成结果字典
    """
    try:
        scene_index = item.get("scene_index")
        script_content = item.get("scene_script", "").strip()
        voice_type = item.get("voice_type", "narrator")
        audio_path = os.path.join(audio_dir, f"audio_{scene_index}.mp3")
        srt_path = os.path.join(srt_dir, f"srt_{scene_index}.srt")
        
        print(f"🎵 正在生成第{scene_index}个音频文件（音色：{voice_type}）...")
        
        # 创建临时脚本文件
        tmp_script_path = os.path.join(temp_dir, f"tmp_script_{scene_index}.txt")
        with open(tmp_script_path, "w", encoding="utf-8") as ftmp:
            ftmp.write(script_content)
        
        # 生成音频和字幕
        result = generate_audio_for_script(tmp_script_path, audio_path, srt_path, voice_type=voice_type)
        
        # 清理临时文件
        if os.path.exists(tmp_script_path):
            os.remove(tmp_script_path)
        
        if "已生成音频和字幕文件" in result or "音频和字幕生成完成" in result:
            print(f"✅ 第{scene_index}个音频和字幕生成成功")
            return {
                "success": True, 
                "audio": f"audio_{scene_index}.mp3", 
                "srt": f"srt_{scene_index}.srt", 
                "index": scene_index
            }
        else:
            print(f"❌ 第{scene_index}个音频生成失败")
            return {
                "success": False, 
                "audio": f"audio_{scene_index}.mp3", 
                "srt": f"srt_{scene_index}.srt", 
                "index": scene_index, 
                "error": "生成失败"
            }
    except Exception as e:
        # 确保清理临时文件
        tmp_script_path = os.path.join(temp_dir, f"tmp_script_{scene_index}.txt")
        if os.path.exists(tmp_script_path):
            os.remove(tmp_script_path)
        
        print(f"❌ 第{scene_index}个音频生成异常: {str(e)}")
        return {
            "success": False, 
            "audio": f"audio_{scene_index}.mp3", 
            "srt": f"srt_{scene_index}.srt", 
            "index": scene_index, 
            "error": str(e)
        }


def generate_media_concurrent(scenes_scripts: List[Dict], output_dirs: Dict[str, str], 
                            max_workers: int = 4) -> MediaGenerationResult:
    """
    并发生成图片和音频
    
    Args:
        scenes_scripts: 场景脚本列表
        output_dirs: 输出目录字典，包含 images_dir, audio_dir, srt_dir, temp_dir
        max_workers: 最大并发数
    
    Returns:
        MediaGenerationResult: 生成结果
    """
    result = MediaGenerationResult()
    
    # 确保所有输出目录存在
    for dir_path in output_dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    print(f"🚀 开始并发生成{len(scenes_scripts)}个场景的图片和音频...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有图片生成任务
        image_futures = [
            executor.submit(generate_single_image, item, output_dirs["images_dir"]) 
            for item in scenes_scripts
        ]
        
        # 提交所有音频生成任务
        audio_futures = [
            executor.submit(generate_single_audio, item, 
                          output_dirs["audio_dir"], 
                          output_dirs["srt_dir"], 
                          output_dirs["temp_dir"]) 
            for item in scenes_scripts
        ]
        
        # 收集图片生成结果
        for future in concurrent.futures.as_completed(image_futures):
            try:
                task_result = future.result()
                if task_result["success"]:
                    result.add_image_success(task_result["file"])
                else:
                    error_info = task_result.get("error", "未知错误")
                    result.add_image_failure(task_result["file"], error_info)
            except Exception as e:
                result.add_image_failure("unknown_file", str(e))
        
        # 收集音频生成结果
        for future in concurrent.futures.as_completed(audio_futures):
            try:
                task_result = future.result()
                if task_result["success"]:
                    result.add_audio_success(task_result["audio"], task_result["srt"])
                else:
                    error_info = task_result.get("error", "未知错误")
                    result.add_audio_failure(task_result["audio"], task_result["srt"], error_info)
            except Exception as e:
                result.add_audio_failure("unknown_audio", "unknown_srt", str(e))
    
    return result


def generate_media_report(chapter_num: int, result: MediaGenerationResult, 
                         total_scenes: int) -> str:
    """
    生成媒体文件生成结果报告
    
    Args:
        chapter_num: 章节号
        result: 生成结果
        total_scenes: 总场景数
    
    Returns:
        格式化的报告字符串
    """
    stats = result.get_statistics(total_scenes)
    
    report = f"""
📊 第{chapter_num}章媒体文件并发生成完成报告:
==========================================
🖼️ 图片生成统计:
- 总场景数: {stats['total_scenes']}
- 成功生成: {stats['image_success']}张
- 生成失败: {stats['image_failed']}张
- 成功率: {stats['image_success_rate']:.1f}%

🔊 音频生成统计:
- 总脚本数: {stats['total_scenes']}
- 成功生成: {stats['audio_success']}个音频
- 生成失败: {stats['audio_failed']}个音频
- 成功率: {stats['audio_success_rate']:.1f}%

✅ 成功生成的图片:
{chr(10).join(f'  - {img}' for img in result.generated_images)}

✅ 成功生成的音频:
{chr(10).join(f'  - {audio}' for audio in result.generated_audio)}

✅ 成功生成的字幕:
{chr(10).join(f'  - {srt}' for srt in result.generated_srt)}
"""
    
    if result.failed_images:
        report += f"""
❌ 生成失败的图片:
{chr(10).join(f'  - {img}' for img in result.failed_images)}
"""
    
    if result.failed_audio:
        report += f"""
❌ 生成失败的音频:
{chr(10).join(f'  - {audio}' for audio in result.failed_audio)}
"""
    
    return report


def setup_chapter_directories(chapter_num: int) -> Dict[str, str]:
    """
    设置章节输出目录
    
    Args:
        chapter_num: 章节号
    
    Returns:
        包含所有目录路径的字典
    """
    output_dir = f"output/chapters/chapter_{chapter_num}"
    
    return {
        "output_dir": output_dir,
        "images_dir": os.path.join(output_dir, "images"),
        "audio_dir": os.path.join(output_dir, "audio"),
        "srt_dir": os.path.join(output_dir, "srt"),
        "temp_dir": output_dir,
        "json_path": os.path.join(output_dir, "scenes_scripts.json")
    }
