import os
import json
from dataclasses import dataclass
from typing import List, Literal
from pydantic_ai import Agent, RunContext
from utils.llm import chat_model
from utils.tts import (
    generate_sentence_audio_and_srt, 
    merge_audio_files, 
    merge_srt_files
)


@dataclass
class TalkAgentDeps:
    scene_id: int = 1  # 场景ID


@dataclass
class TalkAgentOutput:
    text: str = ""
    voice_type: Literal["male", "female", "narrator"] = "narrator"


talk_agent = Agent(
    model=chat_model,
    deps_type=TalkAgentDeps,
    output_type=List[TalkAgentOutput],
)


@talk_agent.instructions
def analyze_script_and_generate_audio(ctx: RunContext[TalkAgentDeps]) -> str:
    """分析脚本内容，生成语音和字幕文件"""
    scene_id = ctx.deps.scene_id
    
    return f"""
你是一位专业的语音分析师，负责为场景 {scene_id} 的脚本生成语音和字幕。

工作流程：
1. 调用 read_scene_script 工具读取场景脚本
2. 分析脚本内容，将文本按语义拆分成句子
3. 为每个句子分配合适的音色类型：
   - **male**: 男性角色对话、男性内心独白
   - **female**: 女性角色对话、女性内心独白  
   - **narrator**: 环境描述、叙述文字、无明确性别的内容
4. 调用 generate_audio_and_srt 工具生成音频和字幕文件

分析规则：
- 直接对话用引号包围，根据上下文判断说话者性别
- 内心独白通常以"心想"、"暗自"等词汇开头
- 环境描述、动作描述使用narrator音色
- 保持句子完整性，在标点符号处自然断句
- 每个句子20-50字为宜，过长需要拆分

请先读取脚本，然后分析并生成音频文件。
"""


@talk_agent.tool
def read_scene_script(ctx: RunContext[TalkAgentDeps]) -> str:
    """读取指定场景的脚本内容"""
    scene_id = ctx.deps.scene_id
    scenes_file = "output/scenes.json"
    
    if not os.path.exists(scenes_file):
        return f"❌ 场景文件不存在: {scenes_file}"
    
    try:
        with open(scenes_file, "r", encoding="utf-8") as f:
            scenes_data = json.load(f)
        
        # 查找指定场景
        for scene in scenes_data:
            if scene.get("scene_id") == scene_id:
                script = scene.get("script", "")
                if not script:
                    return f"❌ 场景 {scene_id} 的脚本内容为空"
                
                return f"""场景 {scene_id} 脚本内容：

{script}

字符数: {len(script)}

请分析此脚本，按语义拆分句子并分配音色，然后调用 generate_audio_and_srt 工具生成音频和字幕。"""
        
        return f"❌ 未找到场景 {scene_id} 的数据"
        
    except Exception as e:
        return f"❌ 读取场景文件失败: {str(e)}"


@talk_agent.tool
def generate_audio_and_srt(ctx: RunContext[TalkAgentDeps], segments: List[TalkAgentOutput]) -> str:
    """为分析后的句子生成音频和字幕文件"""
    scene_id = ctx.deps.scene_id
    
    if not segments:
        return f"❌ 场景 {scene_id} 没有有效的语句段落"
    
    # 验证数据
    valid_segments = []
    for seg in segments:
        if seg.text.strip():
            valid_segments.append((seg.text.strip(), seg.voice_type))
    
    if not valid_segments:
        return f"❌ 场景 {scene_id} 没有有效的文本内容"
    
    try:
        # 确保输出目录存在
        audio_dir = "output/audio"
        srt_dir = "output/srt"
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(srt_dir, exist_ok=True)
        
        # 生成每个句子的音频和字幕
        audio_files, srt_files = generate_sentence_audio_and_srt(
            valid_segments, 
            "output", 
            scene_id
        )
        
        if not audio_files:
            return f"❌ 场景 {scene_id} 音频生成失败"
        
        # 合并音频文件
        merged_audio_path = os.path.join(audio_dir, f"scene_{scene_id}.wav")
        audio_result = merge_audio_files(audio_files, merged_audio_path)
        
        # 合并SRT文件
        merged_srt_path = os.path.join(srt_dir, f"scene_{scene_id}.srt")
        srt_result = merge_srt_files(srt_files, merged_srt_path)
        
        # 清理临时文件
        for temp_file in audio_files + srt_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
        
        # 统计音色使用情况
        voice_stats = {}
        for _, voice_type in valid_segments:
            voice_stats[voice_type] = voice_stats.get(voice_type, 0) + 1
        
        stats_str = ", ".join([f"{voice}: {count}句" for voice, count in voice_stats.items()])
        
        return f"""✅ 场景 {scene_id} 音频和字幕生成完成:

📊 统计信息:
- 句子总数: {len(valid_segments)}
- 音色分布: {stats_str}

📁 输出文件:
- 音频: {merged_audio_path}
- 字幕: {merged_srt_path}

🔧 处理结果:
- {audio_result}
- {srt_result}"""
        
    except Exception as e:
        return f"❌ 生成音频和字幕失败: {str(e)}"