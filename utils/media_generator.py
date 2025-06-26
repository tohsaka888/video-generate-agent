"""
媒体生成工具模块
包含图片和音频生成的通用函数，支持并发处理
"""
import os
import json
import threading
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
        self.generated_images.append(filename)
    
    def add_image_failure(self, filename: str, error: str = ""):
        error_msg = f"{filename}" + (f" (错误: {error})" if error else "")
        self.failed_images.append(error_msg)
    
    def add_audio_success(self, audio_file: str, srt_file: str):
        self.generated_audio.append(audio_file)
        self.generated_srt.append(srt_file)
    
    def add_audio_failure(self, audio_file: str, srt_file: str, error: str = ""):
        error_msg = f"{audio_file} / {srt_file}" + (f" (错误: {error})" if error else "")
        self.failed_audio.append(error_msg)


def validate_scenes_scripts(scenes_scripts: List[Dict]) -> List[Dict]:
    valid_voice_types = {"male", "female", "narrator"}
    for scene in scenes_scripts:
        voice_type = scene.get("voice_type", "narrator")
        if voice_type not in valid_voice_types:
            print(f"警告：场景 {scene.get('scene_index')} 的音色类型 '{voice_type}' 无效，已调整为 'narrator'")
            scene["voice_type"] = "narrator"
    return scenes_scripts


def load_scenes_scripts(json_path: str) -> Tuple[List[Dict], str]:
    if not os.path.exists(json_path):
        return [], f"❌ 未找到 {json_path}，请先生成分镜和脚本"
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            scenes_scripts = json.load(f)
        if not scenes_scripts:
            return [], f"❌ {json_path} 为空"
        scenes_scripts = validate_scenes_scripts(scenes_scripts)
        return scenes_scripts, ""
    except json.JSONDecodeError as e:
        return [], f"❌ JSON文件格式错误: {str(e)}"
    except Exception as e:
        return [], f"❌ 读取文件失败: {str(e)}"


def generate_single_image(item: Dict, images_dir: str) -> Dict[str, Any]:
    try:
        scene_index = item.get("scene_index")
        scene_content = item.get("scene_prompt", "").strip()
        image_path = os.path.join(images_dir, f"scene_{scene_index}.png")
        print(f"🎨 正在生成第{scene_index}张图片...")
        result = generate_image(prompt_text=scene_content, save_path=image_path)
        if result and os.path.exists(image_path):
            print(f"✅ 第{scene_index}张图片生成成功: scene_{scene_index}.png")
            return {"success": True, "file": f"scene_{scene_index}.png", "index": scene_index}
        else:
            print(f"❌ 第{scene_index}张图片生成失败")
            return {"success": False, "file": f"scene_{scene_index}.png", "index": scene_index, "error": "生成失败"}
    except Exception as e:
        print(f"❌ 第{scene_index}张图片生成异常: {str(e)}")
        return {"success": False, "file": f"scene_{scene_index}.png", "index": scene_index, "error": str(e)}


def generate_single_audio(item: Dict, audio_dir: str, srt_dir: str, temp_dir: str) -> Dict[str, Any]:
    try:
        scene_index = item.get("scene_index")
        script_content = item.get("scene_script", "").strip()
        voice_type = item.get("voice_type", "narrator")
        audio_path = os.path.join(audio_dir, f"audio_{scene_index}.mp3")
        srt_path = os.path.join(srt_dir, f"srt_{scene_index}.srt")
        print(f"🎵 正在生成第{scene_index}个音频文件（音色：{voice_type}）...")
        tmp_script_path = os.path.join(temp_dir, f"tmp_script_{scene_index}.txt")
        with open(tmp_script_path, "w", encoding="utf-8") as ftmp:
            ftmp.write(script_content)
        result = generate_audio_for_script(tmp_script_path, audio_path, srt_path, voice_type=voice_type)
        if os.path.exists(tmp_script_path):
            os.remove(tmp_script_path)
        if "已生成音频和字幕文件" in result or "音频和字幕生成完成" in result:
            print(f"✅ 第{scene_index}个音频和字幕生成成功")
            return {"success": True, "audio": f"audio_{scene_index}.mp3", "srt": f"srt_{scene_index}.srt", "index": scene_index}
        else:
            print(f"❌ 第{scene_index}个音频生成失败")
            return {"success": False, "audio": f"audio_{scene_index}.mp3", "srt": f"srt_{scene_index}.srt", "index": scene_index, "error": "生成失败"}
    except Exception as e:
        tmp_script_path = os.path.join(temp_dir, f"tmp_script_{scene_index}.txt")
        if os.path.exists(tmp_script_path):
            os.remove(tmp_script_path)
        print(f"❌ 第{scene_index}个音频生成异常: {str(e)}")
        return {"success": False, "audio": f"audio_{scene_index}.mp3", "srt": f"srt_{scene_index}.srt", "index": scene_index, "error": str(e)}


def generate_media_concurrent(scenes_scripts: List[Dict], output_dirs: Dict[str, str]) -> MediaGenerationResult:
    """
    并发生成图片和音频（分别为两个队列，队列内顺序执行）
    Args:
        scenes_scripts: 场景脚本列表
        output_dirs: 输出目录字典，包含 images_dir, audio_dir, srt_dir, temp_dir
    Returns:
        MediaGenerationResult: 生成结果
    """
    result = MediaGenerationResult()
    for dir_path in output_dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    print(f"🚀 开始生成{len(scenes_scripts)}个场景的图片和音频（图片/音频分别队列）...")

    def image_worker():
        for item in scenes_scripts:
            task_result = generate_single_image(item, output_dirs["images_dir"])
            if task_result["success"]:
                result.add_image_success(task_result["file"])
            else:
                error_info = task_result.get("error", "未知错误")
                result.add_image_failure(task_result["file"], error_info)

    def audio_worker():
        for item in scenes_scripts:
            task_result = generate_single_audio(item, output_dirs["audio_dir"], output_dirs["srt_dir"], output_dirs["temp_dir"])
            if task_result["success"]:
                result.add_audio_success(task_result["audio"], task_result["srt"])
            else:
                error_info = task_result.get("error", "未知错误")
                result.add_audio_failure(task_result["audio"], task_result["srt"], error_info)

    t_img = threading.Thread(target=image_worker)
    t_aud = threading.Thread(target=audio_worker)
    t_img.start()
    t_aud.start()
    t_img.join()
    t_aud.join()
    return result


def generate_media_report(chapter_num: int, result: MediaGenerationResult, total_scenes: int) -> str:
    """
    生成媒体文件生成结果报告
    Args:
        chapter_num: 章节号
        result: 生成结果
        total_scenes: 总场景数
    Returns:
        格式化的报告字符串
    """
    image_success = len(result.generated_images)
    image_failed = len(result.failed_images)
    audio_success = len(result.generated_audio)
    audio_failed = len(result.failed_audio)
    image_success_rate = (image_success / total_scenes * 100) if total_scenes > 0 else 0
    audio_success_rate = (audio_success / total_scenes * 100) if total_scenes > 0 else 0
    report = f"""
📊 第{chapter_num}章媒体文件生成完成报告:
==========================================
🖼️ 图片生成统计:
- 总场景数: {total_scenes}
- 成功生成: {image_success}张
- 生成失败: {image_failed}张
- 成功率: {image_success_rate:.1f}%

🔊 音频生成统计:
- 总脚本数: {total_scenes}
- 成功生成: {audio_success}个音频
- 生成失败: {audio_failed}个音频
- 成功率: {audio_success_rate:.1f}%

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
    output_dir = f"output/chapters/chapter_{chapter_num}"
    return {
        "output_dir": output_dir,
        "images_dir": os.path.join(output_dir, "images"),
        "audio_dir": os.path.join(output_dir, "audio"),
        "srt_dir": os.path.join(output_dir, "srt"),
        "temp_dir": output_dir,
        "json_path": os.path.join(output_dir, "scenes_scripts.json")
    }
