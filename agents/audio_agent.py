from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from utils.llm import chat_model
from utils.mcp import filesystem_mcp
import edge_tts
import os
import re

@dataclass
class AudioAgentDeps:
    current_chapter: int = 1

audio_agent = Agent(
    model=chat_model, deps_type=AudioAgentDeps, mcp_servers=[filesystem_mcp]
)

def clean_text_for_srt(text):
    """
    清理文本，只保留逗号、句号、感叹号，去除其他特殊符号
    """
    # 保留中文、英文、数字、空格、逗号、句号、感叹号
    cleaned_text = re.sub(r'[^\u4e00-\u9fff\u3400-\u4dbfA-Za-z0-9\s，。！,.]', '', text)
    # 去除多余的空格
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text

def create_sentence_based_srt(word_boundaries, text):
    """
    根据词汇边界信息创建基于语句的SRT字幕文件，精准同步音画
    """
    if not word_boundaries:
        return ""

    cleaned_text = clean_text_for_srt(text)
    # 智能句子分割
    sentences = []
    parts = re.split(r'([。！.!])', cleaned_text)
    current_sentence = ""
    for i, part in enumerate(parts):
        current_sentence += part
        if re.match(r'[。！.!]', part) or i == len(parts) - 1:
            if current_sentence.strip():
                clean_sentence = current_sentence.strip()
                if '？' in clean_sentence:
                    sub_parts = clean_sentence.split('？')
                    for j, sub_part in enumerate(sub_parts):
                        if sub_part.strip():
                            if j < len(sub_parts) - 1:
                                sentences.append(sub_part.strip() + '？')
                            else:
                                if sub_part.strip():
                                    sentences.append(sub_part.strip())
                else:
                    if clean_sentence and len(clean_sentence) > 1:
                        sentences.append(clean_sentence)
            current_sentence = ""
    # 进一步清理句子列表
    cleaned_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and len(sentence) > 1 and not re.match(r'^[，。！,.!]+$', sentence):
            cleaned_sentences.append(sentence)
    sentences = cleaned_sentences
    if not sentences:
        return ""

    # 拼接所有词边界文本，便于查找句子在词边界中的起止位置
    boundary_texts = [b.get('text', '').strip() for b in word_boundaries]
    joined_text = ''.join(boundary_texts)
    char_offsets = [b.get('offset', 0) for b in word_boundaries]
    char_durations = [b.get('duration', 1000000) for b in word_boundaries]

    srt_content = ""
    srt_index = 1
    last_end_idx = 0
    prev_end_time = 0.0  # 初始化，确保时间递增
    for sentence in sentences:
        # 去除标点和空格用于匹配
        sentence_clean = re.sub(r'[，。！,.!\s]+', '', sentence)
        # 在joined_text中查找该句的起止位置
        start_idx = joined_text.find(sentence_clean, last_end_idx)
        if start_idx == -1:
            # 匹配不到时，尝试从头查找
            start_idx = joined_text.find(sentence_clean)
        if start_idx == -1:
            # 仍找不到，回退为均分时间
            total_duration = (word_boundaries[-1].get('offset', 0) + word_boundaries[-1].get('duration', 1000000)) / 10000000
            time_per_sentence = total_duration / len(sentences)
            start_time = (srt_index - 1) * time_per_sentence
            end_time = srt_index * time_per_sentence
        else:
            # 找到起止词边界
            end_idx = start_idx + len(sentence_clean) - 1
            # 找到对应的词边界索引
            start_word_idx = None
            end_word_idx = None
            char_count = 0
            for i, t in enumerate(boundary_texts):
                if char_count == start_idx:
                    start_word_idx = i
                if char_count + len(t) - 1 >= end_idx and end_word_idx is None:
                    end_word_idx = i
                char_count += len(t)
            if start_word_idx is None:
                start_word_idx = 0
            if end_word_idx is None:
                end_word_idx = len(word_boundaries) - 1
            start_time = char_offsets[start_word_idx] / 10000000
            end_time = (char_offsets[end_word_idx] + char_durations[end_word_idx]) / 10000000
            last_end_idx = end_idx + 1
        # 确保时间递增
        if srt_index > 1 and start_time < prev_end_time:
            start_time = prev_end_time + 0.05
        if end_time <= start_time:
            end_time = start_time + max(len(sentence) * 0.08, 1.0)
        prev_end_time = end_time
        start_str = format_srt_time(start_time)
        end_str = format_srt_time(end_time)
        srt_content += f"{srt_index}\n{start_str} --> {end_str}\n{sentence}\n\n"
        srt_index += 1
    return srt_content

def format_srt_time(seconds):
    """
    将秒数转换为SRT时间格式 (HH:MM:SS,mmm)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

@audio_agent.instructions
def generate_audio(ctx: RunContext[AudioAgentDeps]) -> str:
    """
    生成当前章节的音频。
    """
    system_instruction = f"""
    你是一个音频生成助手，负责将章节内容转换为音频文件。
    
    请读取 output/chapters/chapter_{ctx.deps.current_chapter}/scripts 文件夹中的所有章节内容，
    并使用 edge-tts 工具将每个脚本转换为音频文件。
    使用 edge-tts 工具生成音频文件
    使用工具将audio保存到 output/chapters/chapter_{ctx.deps.current_chapter}/audio 目录下，文件名为 audio_index.mp3。 (index为script编号)
    使用工具将srt保存到 output/chapters/chapter_{ctx.deps.current_chapter}/srt 目录下，文件名为 srt_index.srt。 (index为script编号)
    """
    return system_instruction

@audio_agent.tool
def generate_audio_for_chapter(ctx: RunContext[AudioAgentDeps], script_path: str, audio_path: str, srt_path: str) -> str:
    """
    查询当前章节 scripts 目录下所有脚本文件，调用 edge-tts 朗读并保存为 mp3。
    生成的字幕按照语句进行分割，而不是逐字分割。
    """
    dir_name = os.path.dirname(audio_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    dir_name = os.path.dirname(srt_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    if not os.path.exists(script_path):
        raise FileNotFoundError(f"脚本文件未找到: {script_path}")
    
    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read()
    if not script_content.strip():
        raise ValueError(f"脚本文件内容为空: {script_path}")
    
    # 使用 edge-tts 生成音频
    communicate = edge_tts.Communicate(
        text=script_content,
        voice="zh-CN-XiaoxiaoNeural",
    )
    
    # 收集词汇边界信息用于生成基于语句的字幕
    word_boundaries = []
    
    with open(audio_path, "wb") as file:
        for chunk in communicate.stream_sync():
            if chunk["type"] == "audio" and "data" in chunk:
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append(chunk)

    # 使用自定义函数生成基于语句的字幕
    srt_content = create_sentence_based_srt(word_boundaries, script_content)
    
    with open(srt_path, "w", encoding="utf-8") as file:
        file.write(srt_content)
    
    return "已生成音频和基于语句分割的字幕文件。"