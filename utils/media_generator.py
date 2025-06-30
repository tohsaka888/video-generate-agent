"""
媒体生成工具模块 - 简化版
并发生成图片和音频，支持音频合并
"""

import os
import json
import threading
from typing import List, Dict, Any, Tuple
from utils.comfyui import generate_image
from utils.tts import generate_audio
from pydub import AudioSegment
import pysrt

def load_scenes_scripts(json_path: str) -> List[Dict]:
    """加载场景脚本文件"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_single_image(scene_data: Dict, images_dir: str) -> bool:
    """生成单个图片"""
    scene_index = scene_data.get("scene_index")
    scene_content = scene_data.get("scene_prompt", "").strip()
    image_path = os.path.join(images_dir, f"scene_{scene_index}.png")
    result = generate_image(prompt_text=scene_content, save_path=image_path)
    return result and os.path.exists(image_path)

def generate_single_audio_segment(text: str, voice_type: str, temp_dir: str, segment_name: str) -> Tuple[str, float]:
    """生成单个音频段落，返回文件路径和时长"""
    audio_path = os.path.join(temp_dir, f"temp_audio_{segment_name}.wav")
    generate_audio(text, audio_path, voice_type=voice_type)
    if os.path.exists(audio_path):
        audio_segment = AudioSegment.from_wav(audio_path)
        return audio_path, len(audio_segment) / 1000.0
    return "", 0.0

def generate_scene_audio(scene_data: Dict, audio_dir: str, srt_dir: str, temp_dir: str) -> bool:
    """生成场景音频和字幕"""
    from agents.talk_agent import talk_agent, TalkAgentDeps, TalkAgentOutput

    scene_index = scene_data.get("scene_index")
    if scene_index is None:
        raise ValueError("scene_index 不能为空")

    scene_script = scene_data.get("scene_script", "").strip()
    talk_deps = TalkAgentDeps(script=scene_script, scene_index=int(scene_index), chapter=1)

    import asyncio
    talk_result = asyncio.run(talk_agent.run("处理脚本", deps=talk_deps))
    segments = talk_result.output

    temp_audio_files = []
    srt_entries = []
    current_time = 0.0

    for i, segment in enumerate(segments):
        if isinstance(segment, TalkAgentOutput):
            text = segment.segment.strip()
            voice_type = segment.voice_type
        elif isinstance(segment, dict):
            text = segment.get('text', '').strip()
            voice_type = segment.get('voice_type')
        else:
            raise TypeError("段落格式错误")

        audio_path, duration = generate_single_audio_segment(text, voice_type, temp_dir, f"{scene_index}_{i}")
        if audio_path:
            temp_audio_files.append(audio_path)
            start_time = current_time
            end_time = current_time + duration
            srt_item = pysrt.SubRipItem(index=len(srt_entries) + 1, start=pysrt.SubRipTime(milliseconds=int(start_time * 1000)), end=pysrt.SubRipTime(milliseconds=int(end_time * 1000)), text=text)
            srt_entries.append(srt_item)
            current_time = end_time

    combined_audio = AudioSegment.empty()
    for audio_file in temp_audio_files:
        combined_audio += AudioSegment.from_wav(audio_file)
        os.remove(audio_file)

    final_audio_path = os.path.join(audio_dir, f"audio_{scene_index}.mp3")
    combined_audio.export(final_audio_path, format="mp3")

    srt_path = os.path.join(srt_dir, f"srt_{scene_index}.srt")
    srt_file = pysrt.SubRipFile(srt_entries)
    srt_file.save(srt_path, encoding='utf-8')

    return True

def merge_all_audio_files(audio_dir: str, srt_dir: str, output_dir: str, chapter_num: int):
    """合并所有音频和字幕文件"""
    audio_files = sorted((int(f.replace("audio_", "").replace(".mp3", "")), os.path.join(audio_dir, f)) for f in os.listdir(audio_dir) if f.startswith("audio_") and f.endswith(".mp3"))
    srt_files = sorted((int(f.replace("srt_", "").replace(".srt", "")), os.path.join(srt_dir, f)) for f in os.listdir(srt_dir) if f.startswith("srt_") and f.endswith(".srt"))

    combined_audio = AudioSegment.empty()
    for _, audio_path in audio_files:
        combined_audio += AudioSegment.from_file(audio_path)
    final_audio_path = os.path.join(output_dir, f"chapter_{chapter_num}_complete.mp3")
    combined_audio.export(final_audio_path, format="mp3")

    combined_srt = pysrt.SubRipFile()
    current_time_offset = 0.0
    for _, srt_path in srt_files:
        srt_file = pysrt.open(srt_path, encoding='utf-8')
        for item in srt_file:
            start_ms = item.start.ordinal + int(current_time_offset * 1000)
            end_ms = item.end.ordinal + int(current_time_offset * 1000)
            combined_srt.append(pysrt.SubRipItem(index=len(combined_srt) + 1, start=pysrt.SubRipTime(milliseconds=start_ms), end=pysrt.SubRipTime(milliseconds=end_ms), text=item.text))
            current_time_offset = max(current_time_offset, end_ms / 1000.0)
    final_srt_path = os.path.join(output_dir, f"chapter_{chapter_num}_complete.srt")
    combined_srt.save(final_srt_path, encoding='utf-8')

def generate_media_concurrent(scenes_scripts: List[Dict], output_dirs: Dict[str, str], chapter: int = 1) -> Dict[str, Any]:
    """并发生成图片和音频"""
    for dir_path in output_dirs.values():
        os.makedirs(dir_path, exist_ok=True)

    image_results = []
    audio_results = []

    def image_worker():
        for scene_data in scenes_scripts:
            image_results.append(generate_single_image(scene_data, output_dirs["images_dir"]))

    def audio_worker():
        for scene_data in scenes_scripts:
            audio_results.append(generate_scene_audio(scene_data, output_dirs["audio_dir"], output_dirs["srt_dir"], output_dirs["temp_dir"]))

    threading.Thread(target=image_worker).start()
    threading.Thread(target=audio_worker).start()

    merge_all_audio_files(output_dirs["audio_dir"], output_dirs["srt_dir"], output_dirs["output_dir"], chapter)

    total_scenes = len(scenes_scripts)
    return {
        "total_scenes": total_scenes,
        "image_success": sum(image_results),
        "audio_success": sum(audio_results),
    }

def setup_chapter_directories(chapter_num: int) -> Dict[str, str]:
    """设置章节目录"""
    output_dir = f"output/chapters/chapter_{chapter_num}"
    return {
        "output_dir": output_dir,
        "images_dir": os.path.join(output_dir, "images"),
        "audio_dir": os.path.join(output_dir, "audio"),
        "srt_dir": os.path.join(output_dir, "srt"),
        "temp_dir": os.path.join(output_dir, "temp")
    }
