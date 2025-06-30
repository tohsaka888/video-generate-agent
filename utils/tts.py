import os
import pysrt
from typing import Optional, List, Tuple
from datetime import timedelta
from pydub import AudioSegment
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


def split_text_into_sentences(text: str) -> List[str]:
    """
    将文本拆分为句子列表，智能处理中英文标点
    
    Args:
        text: 要拆分的文本
        
    Returns:
        List[str]: 句子列表
    """
    import re
    # 使用正则表达式按句号、问号、感叹号拆分，支持中英文标点
    sentences = re.split(r'[。！？.!?]+', text)
    # 过滤空字符串并去除首尾空格
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # 进一步处理过长的句子（超过100字符的句子尝试按逗号拆分）
    refined_sentences = []
    for sentence in sentences:
        if len(sentence) > 100:
            # 尝试按逗号拆分长句
            sub_sentences = re.split(r'[，,]', sentence)
            for sub in sub_sentences:
                if sub.strip():
                    refined_sentences.append(sub.strip())
        else:
            refined_sentences.append(sentence)
    
    return refined_sentences


def generate_audio_with_srt(text: str, audio_path: str, srt_path: str, voice_type: str = "narrator") -> Tuple[float, str]:
    """
    生成音频文件和对应的SRT字幕文件
    
    Args:
        text: 要转换的文本
        audio_path: 音频文件输出路径
        srt_path: SRT字幕文件输出路径
        voice_type: 音色类型
        
    Returns:
        Tuple[float, str]: (音频时长, 结果描述)
    """
    # 确保输出目录存在
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)
    os.makedirs(os.path.dirname(srt_path), exist_ok=True)
    
    # 生成音频
    generate_audio(text, audio_path, voice_type=voice_type)
    
    # 获取音频时长
    try:
        audio = AudioSegment.from_file(audio_path)
        duration = len(audio) / 1000.0  # 转换为秒
    except Exception as e:
        print(f"警告：无法获取音频时长: {e}")
        duration = len(text) * 0.1  # 估算时长（每个字符0.1秒）
    
    # 生成SRT字幕文件
    srt_content = pysrt.SubRipFile()
    srt_item = pysrt.SubRipItem()
    srt_item.index = 1
    srt_item.start = pysrt.SubRipTime(0, 0, 0, 0)
    srt_item.end = pysrt.SubRipTime(seconds=int(duration), milliseconds=int((duration % 1) * 1000))
    srt_item.text = text
    srt_content.append(srt_item)
    
    # 保存SRT文件
    srt_content.save(srt_path, encoding='utf-8')
    
    return duration, f"已生成音频 ({duration:.2f}s) 和SRT字幕"


def merge_audio_files(audio_files: List[str], output_path: str) -> str:
    """
    合并多个音频文件
    
    Args:
        audio_files: 音频文件路径列表
        output_path: 输出文件路径
        
    Returns:
        str: 结果描述
    """
    if not audio_files:
        return "没有音频文件需要合并"
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 加载第一个音频文件
    combined_audio = AudioSegment.from_file(audio_files[0])
    
    # 依次合并其他音频文件
    for audio_file in audio_files[1:]:
        if os.path.exists(audio_file):
            audio = AudioSegment.from_file(audio_file)
            combined_audio += audio
        else:
            print(f"警告：音频文件不存在: {audio_file}")
    
    # 保存合并后的音频
    combined_audio.export(output_path, format="wav")
    
    total_duration = len(combined_audio) / 1000.0
    return f"已合并 {len(audio_files)} 个音频文件，总时长: {total_duration:.2f}s"


def merge_srt_files(srt_files: List[str], output_path: str) -> str:
    """
    合并多个SRT字幕文件
    
    Args:
        srt_files: SRT文件路径列表
        output_path: 输出文件路径
        
    Returns:
        str: 结果描述
    """
    if not srt_files:
        return "没有SRT文件需要合并"
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    combined_srt = pysrt.SubRipFile()
    current_time_offset = timedelta(0)
    index = 1
    
    for srt_file in srt_files:
        if not os.path.exists(srt_file):
            print(f"警告：SRT文件不存在: {srt_file}")
            continue
            
        try:
            srt_content = pysrt.open(srt_file, encoding='utf-8')
            
            # 如果文件为空，跳过
            if not srt_content:
                print(f"警告：SRT文件为空: {srt_file}")
                continue
            
            # 记录这个文件的最大结束时间
            max_end_time = timedelta(0)
            
            for item in srt_content:
                new_item = pysrt.SubRipItem()
                new_item.index = index
                
                # 计算新的开始和结束时间（加上偏移量）
                new_start = current_time_offset + item.start.to_timedelta()
                new_end = current_time_offset + item.end.to_timedelta()
                
                # 将timedelta转换回SubRipTime
                total_seconds_start = int(new_start.total_seconds())
                milliseconds_start = int((new_start.total_seconds() % 1) * 1000)
                hours_start = total_seconds_start // 3600
                minutes_start = (total_seconds_start % 3600) // 60
                seconds_start = total_seconds_start % 60
                
                total_seconds_end = int(new_end.total_seconds())
                milliseconds_end = int((new_end.total_seconds() % 1) * 1000)
                hours_end = total_seconds_end // 3600
                minutes_end = (total_seconds_end % 3600) // 60
                seconds_end = total_seconds_end % 60
                
                new_item.start = pysrt.SubRipTime(hours_start, minutes_start, seconds_start, milliseconds_start)
                new_item.end = pysrt.SubRipTime(hours_end, minutes_end, seconds_end, milliseconds_end)
                new_item.text = item.text
                
                combined_srt.append(new_item)
                index += 1
                
                # 更新最大结束时间
                if new_end > max_end_time:
                    max_end_time = new_end
            
            # 更新时间偏移为当前文件的最大结束时间
            current_time_offset = max_end_time
                
        except Exception as e:
            print(f"警告：读取SRT文件失败 {srt_file}: {e}")
            continue
    
    if not combined_srt:
        return "没有有效的SRT内容可以合并"
    
    # 保存合并后的SRT文件
    try:
        combined_srt.save(output_path, encoding='utf-8')
    except Exception as e:
        return f"保存SRT文件失败: {e}"
    
    return f"已合并 {len(srt_files)} 个SRT文件，共 {len(combined_srt)} 个字幕条目"


def generate_sentence_audio_and_srt(sentences: List[Tuple[str, str]], output_dir: str, scene_id: int) -> Tuple[List[str], List[str]]:
    """
    为句子列表生成音频和SRT文件
    
    Args:
        sentences: 句子列表，每个元素为 (text, voice_type)
        output_dir: 输出目录
        scene_id: 场景ID
        
    Returns:
        Tuple[List[str], List[str]]: (音频文件列表, SRT文件列表)
    """
    audio_files = []
    srt_files = []
    
    for i, (text, voice_type) in enumerate(sentences):
        sentence_id = i + 1
        audio_file = os.path.join(output_dir, f"scene_{scene_id}_sentence_{sentence_id}.wav")
        srt_file = os.path.join(output_dir, f"scene_{scene_id}_sentence_{sentence_id}.srt")
        
        try:
            duration, result = generate_audio_with_srt(text, audio_file, srt_file, voice_type)
            audio_files.append(audio_file)
            srt_files.append(srt_file)
            print(f"✅ 句子 {sentence_id}: {result}")
        except Exception as e:
            print(f"❌ 句子 {sentence_id} 生成失败: {e}")
    
    return audio_files, srt_files


if __name__ == "__main__":
    generate_audio("你好，世界", "output.wav", "output.srt")