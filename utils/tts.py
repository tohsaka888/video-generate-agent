import os
from typing import Optional
from indextts.infer import IndexTTS


def generate_audio(text: str, audio_path: str, srt_path: Optional[str] = None, voice_type: str = "narrator"):
    """
    使用IndexTTS生成音频
    
    Args:
        text: 要转换为语音的文本
        audio_path: 输出音频文件路径
        srt_path: 输出SRT字幕文件路径（可选）
        voice_type: 音色类型 ("male", "female", "narrator")
    """
    # 确保输出目录存在
    if os.path.dirname(audio_path):
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    
    # 根据音色类型选择对应的音色文件
    voice_map = {
        "male": "assets/voice/male.wav",
        "female": "assets/voice/female.wav", 
        "narrator": "assets/voice/narrator.wav"
    }
    
    # 如果指定的音色类型不存在，使用默认音色
    voice = voice_map.get(voice_type, "assets/voice/zh.wav")
    
    # 如果音色文件不存在，使用默认音色
    if not os.path.exists(voice):
        print(f"警告：音色文件 {voice} 不存在，使用默认音色")
        voice = "assets/voice/zh.wav"
    
    # 使用IndexTTS生成音频
    tts = IndexTTS(model_dir="index-tts/checkpoints", cfg_path="index-tts/checkpoints/config.yaml")
    tts.infer(voice, text, audio_path)
    
    print(f"✅ 音频已生成 ({voice_type} 音色): {audio_path}")


def generate_audio_for_script(script_path: str, audio_path: str, srt_path: str, voice_type: str = "narrator") -> str:
    """
    为脚本文件生成音频和字幕
    
    Args:
        script_path: 脚本文件路径
        audio_path: 输出音频文件路径
        srt_path: 输出SRT字幕文件路径
        voice_type: 音色类型 ("male", "female", "narrator")
    
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
    generate_audio(script_content, audio_path, srt_path, voice_type)
    
    return "已生成音频和字幕文件"


if __name__ == "__main__":
    generate_audio("你好，世界", "output.wav", "output.srt")