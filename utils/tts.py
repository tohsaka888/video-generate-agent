import os
from typing import Optional
from indextts.infer import IndexTTS
from faster_whisper import WhisperModel


def format_srt_time(seconds):
    """
    将秒数转换为SRT时间格式 (HH:MM:SS,mmm)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"


def generate_srt_from_segments(segments, srt_path: str):
    """
    从Whisper分段结果生成SRT字幕文件
    """
    srt_content = ""
    for i, segment in enumerate(segments, 1):
        start_time = format_srt_time(segment.start)
        end_time = format_srt_time(segment.end)
        text = segment.text.strip()
        
        srt_content += f"{i}\n"
        srt_content += f"{start_time} --> {end_time}\n"
        srt_content += f"{text}\n\n"
    
    # 确保输出目录存在
    if os.path.dirname(srt_path):
        os.makedirs(os.path.dirname(srt_path), exist_ok=True)
    
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)


def generate_audio(text: str, audio_path: str, srt_path: Optional[str] = None):
    """
    使用IndexTTS生成音频，然后使用Whisper生成SRT字幕
    
    Args:
        text: 要转换为语音的文本
        audio_path: 输出音频文件路径
        srt_path: 输出SRT字幕文件路径（可选）
    """
    # 确保输出目录存在
    if os.path.dirname(audio_path):
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    
    # 使用IndexTTS生成音频
    tts = IndexTTS(model_dir="index-tts/checkpoints", cfg_path="index-tts/checkpoints/config.yaml")
    voice = "assets/voice/zh.wav"
    tts.infer(voice, text, audio_path)
    
    print(f"✅ 音频已生成: {audio_path}")
    
    # 如果提供了SRT路径，则生成字幕文件
    if srt_path:
        model_size = "large-v3"
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        segments, info = model.transcribe(audio_path)
        
        print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
        
        # 生成SRT字幕文件
        generate_srt_from_segments(segments, srt_path)
        print(f"✅ SRT字幕已生成: {srt_path}")
        
        # 可选：打印分段信息用于调试
        for segment in segments:
            print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
    
    return "音频和字幕生成完成"


def generate_audio_for_script(script_path: str, audio_path: str, srt_path: str) -> str:
    """
    为脚本文件生成音频和字幕
    
    Args:
        script_path: 脚本文件路径
        audio_path: 输出音频文件路径
        srt_path: 输出SRT字幕文件路径
    
    Returns:
        str: 生成结果描述
    """
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"脚本文件未找到: {script_path}")
    
    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read().strip()
    
    if not script_content:
        raise ValueError(f"脚本文件内容为空: {script_path}")
    
    # 生成音频和字幕
    generate_audio(script_content, audio_path, srt_path)
    
    return "已生成音频和字幕文件"


if __name__ == "__main__":
    generate_audio("你好，世界", "output.wav", "output.srt")