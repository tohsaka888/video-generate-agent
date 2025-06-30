from moviepy import (
    TextClip,
    CompositeVideoClip,
    CompositeAudioClip,
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
    vfx,
)
from moviepy.video.VideoClip import VideoClip
import os
import json
import random
from moviepy.video.tools.subtitles import SubtitlesClip
from typing import cast
import dotenv

dotenv.load_dotenv()

FONT_PATH = os.getenv("FONT_PATH") or 'assets/font/MapleMono-NF-CN-Regular.ttf'


def generate_video() -> str:
    """
    根据扁平化的output目录结构生成最终视频
    
    Returns:
        str: 生成结果描述
    """
    try:
        # 检查必要的目录和文件
        scenes_file = "output/scenes.json"
        audio_dir = "output/audio"
        image_dir = "output/images"
        srt_dir = "output/srt"
        
        if not os.path.exists(scenes_file):
            return f"❌ 场景文件不存在: {scenes_file}"
        
        # 读取场景数据
        with open(scenes_file, "r", encoding="utf-8") as f:
            scenes_data = json.load(f)
        
        if not scenes_data:
            return "❌ 没有找到场景数据"
        
        # 按scene_id排序
        scenes_data.sort(key=lambda x: x.get("scene_id", 0))
        
        # 收集所有场景的媒体文件
        clips = []
        missing_files = []
        
        for scene in scenes_data:
            scene_id = scene.get("scene_id")
            if not scene_id:
                continue
                
            # 构建文件路径
            audio_file = os.path.join(audio_dir, f"scene_{scene_id}.wav")
            image_file = os.path.join(image_dir, f"scene_{scene_id}.png")
            srt_file = os.path.join(srt_dir, f"scene_{scene_id}.srt")
            
            # 检查文件是否存在
            if not os.path.exists(audio_file):
                missing_files.append(f"音频: {audio_file}")
                continue
            if not os.path.exists(image_file):
                missing_files.append(f"图片: {image_file}")
                continue
            if not os.path.exists(srt_file):
                missing_files.append(f"字幕: {srt_file}")
                continue
            
            # 创建视频片段
            try:
                clip = create_video_clip(audio_file, image_file, srt_file)
                clips.append(clip)
            except Exception as e:
                missing_files.append(f"场景 {scene_id} 处理失败: {str(e)}")
        
        if missing_files:
            return "❌ 以下文件缺失或处理失败:\n" + "\n".join(missing_files)
        
        if not clips:
            return "❌ 没有可用的视频片段"
        
        # 合成最终视频
        final_video_path = compose_final_video(clips)
        
        return f"✅ 视频生成成功: {final_video_path}\n共包含 {len(clips)} 个场景"
        
    except Exception as e:
        return f"❌ 视频生成失败: {str(e)}"


def create_video_clip(audio_file: str, image_file: str, srt_file: str) -> VideoClip:
    """
    创建单个视频片段
    
    Args:
        audio_file: 音频文件路径
        image_file: 图片文件路径
        srt_file: 字幕文件路径
        
    Returns:
        VideoClip: 视频片段
    """
    # 加载音频
    audio_clip = AudioFileClip(audio_file)
    
    # 加载图片并设置持续时间
    image_clip = ImageClip(image_file, duration=audio_clip.duration)
    
    # 创建字幕
    srt_clip = SubtitlesClip(
        subtitles=srt_file,
        encoding="utf-8",
        make_textclip=lambda text: TextClip(
            font=FONT_PATH if os.path.exists(FONT_PATH) else "Arial",
            text=text,
            font_size=48,
            color="white",
            stroke_color="black",
            stroke_width=2,
            vertical_align="center",
            margin=(10, 10, 10, 48 * 3),
            method="caption",
            text_align="center",
            size=(image_clip.w, None),
        ),
    )
    
    # 应用特效到图片
    image_with_effects = cast(
        VideoClip,
        image_clip.with_effects([
            vfx.FadeIn(0.5),
            vfx.FadeOut(0.5),
        ])
    )
    
    # 合成视频片段
    video_clip = CompositeVideoClip([
        image_with_effects.with_audio(audio_clip),
        srt_clip.with_position(("center", "bottom")),
    ])
    
    return video_clip


def compose_final_video(clips: list) -> str:
    """
    合成最终视频
    
    Args:
        clips: 视频片段列表
        
    Returns:
        str: 输出视频文件路径
    """
    if not clips:
        raise ValueError("没有视频片段可合成")
    
    # 确保输出目录存在
    os.makedirs("output", exist_ok=True)
    
    # 合并所有视频片段
    final_clip = concatenate_videoclips(clips=clips, method="compose")
    
    # 添加背景音乐
    final_clip = add_background_music(final_clip)
    
    # 输出文件路径
    output_path = "output/final_video.mp4"
    
    # 渲染视频
    final_clip.write_videofile(
        output_path,
        fps=24
    )
    
    return output_path


def add_background_music(video_clip: VideoClip) -> VideoClip:
    """
    为视频添加背景音乐
    
    Args:
        video_clip: 原视频片段
        
    Returns:
        VideoClip: 添加背景音乐后的视频
    """
    bgm_path = "assets/bgm"
    
    if not os.path.exists(bgm_path) or not os.path.isdir(bgm_path):
        return video_clip
    
    # 查找背景音乐文件
    bgm_files = [
        f for f in os.listdir(bgm_path) 
        if f.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a'))
    ]
    
    if not bgm_files:
        return video_clip
    
    try:
        # 随机选择一个背景音乐
        selected_bgm = random.choice(bgm_files)
        bgm_clip = AudioFileClip(os.path.join(bgm_path, selected_bgm))
        
        # 调整BGM音量为原声的10%
        bgm_clip = bgm_clip.with_volume_scaled(0.1)
        
        # 循环BGM以匹配视频长度
        if bgm_clip.duration < video_clip.duration:
            bgm_clip = bgm_clip.with_effects([vfx.Loop()]).with_duration(video_clip.duration)
        else:
            bgm_clip = bgm_clip.subclipped(0, video_clip.duration)
        
        # 混合音频
        original_audio = video_clip.audio
        if original_audio:
            mixed_audio = CompositeAudioClip([original_audio, bgm_clip])
            return video_clip.with_audio(mixed_audio)
        else:
            return video_clip.with_audio(bgm_clip)
            
    except Exception as e:
        print(f"警告：添加背景音乐失败: {e}")
        return video_clip
    
    return video_clip


# 保持向后兼容的旧函数（废弃）
def generate_video_legacy(current_chapter: int) -> None:
    """
    废弃的旧版本generate_video函数，仅保持向后兼容
    请使用新的generate_video()函数
    """
    print("警告：此函数已废弃，请使用新的generate_video()函数")
    result = generate_video()
    print(result)


if __name__ == "__main__":
    result = generate_video()
    print(result)