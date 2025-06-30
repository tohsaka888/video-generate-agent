import os
import json
from dataclasses import dataclass
from typing import List, Dict, Literal
from pydantic_ai import Agent, RunContext
from utils.llm import chat_model


@dataclass
class TalkAgentDeps:
    script: str = ""  # 原始脚本内容
    scene_index: int = 1  # 场景索引
    chapter: int = 1  # 章节号，默认为1


@dataclass
class TalkAgentOutput:
    segment: str = ""
    voice_type: Literal["male", "female", "narrator"] = "narrator"

talk_agent = Agent(
    model=chat_model,
    deps_type=TalkAgentDeps,
    output_type=List[TalkAgentOutput],
)


@talk_agent.instructions
def process_script_content(ctx: RunContext[TalkAgentDeps]) -> str:
    """
    处理脚本内容，切分语句并分配音色类型。
    """
    script = ctx.deps.script
    scene_index = ctx.deps.scene_index
    
    system_instruction = f"""
你是一位专业的语音分析师，负责分析小说脚本内容并为每个语句分配合适的音色。

当前任务：
- 场景索引：{scene_index}
- 脚本内容：{script}

你需要完成以下工作：

1. **语句切分**：将脚本内容按照语义和语调自然切分成若干个语句段落
2. **音色分析**：为每个语句段落分析内容类型并分配合适的音色：
   - **男声(male)**：男性角色的对话、男性角色的内心独白
   - **女声(female)**：女性角色的对话、女性角色的内心独白  
   - **旁白(narrator)**：环境描述、心理描述、故事叙述、无明确性别的对话等

3. **输出格式**：
```py
[
{{
    "segment": "语句内容",
    "voice_type": Literal["male", "female", "narrator"] 默认为"narrator"
}}
]
```

**分析规则：**
- 直接对话（"xxx"）：根据说话者性别选择 male/female
- 内心独白：根据角色性别选择 male/female
- 环境描述、动作描述、心理描述：使用 narrator
- 无明确性别标识的内容：默认使用 narrator
- 保持语句的完整性，避免在一个完整句子中间切分

**注意事项：**
- 仔细分析上下文来判断角色性别
- 确保每个语句都有明确的音色分配

请调用 process_and_update_script 工具来处理并更新脚本。
"""
    return system_instruction


@talk_agent.tool
def process_and_update_script(ctx: RunContext[TalkAgentDeps], processed_segments: List[Dict[str, str]]) -> str:
    """
    处理脚本段落并更新到 scene_script.json 文件中
    
    Args:
        processed_segments: 处理后的语句段落列表，格式为 [{"text": "语句内容", "voice_type": "male/female/narrator"}, ...]
    """
    scene_index = ctx.deps.scene_index
    
    # 验证输入数据
    valid_voice_types = {"male", "female", "narrator"}
    validated_segments = []
    
    for segment in processed_segments:
        if not isinstance(segment, dict) or "text" not in segment or "voice_type" not in segment:
            continue
            
        text = segment["text"].strip()
        voice_type = segment["voice_type"]
        
        if not text:
            continue
            
        if voice_type not in valid_voice_types:
            print(f"警告：音色类型 '{voice_type}' 无效，已调整为 'narrator'")
            voice_type = "narrator"
            
        validated_segments.append({
            "text": text,
            "voice_type": voice_type
        })
    
    if not validated_segments:
        return f"❌ 场景 {scene_index} 没有有效的语句段落"
    
    # 确定 JSON 文件路径
    chapter = ctx.deps.chapter
    chapter_dir = f"output/chapters/chapter_{chapter}"
    json_path = os.path.join(chapter_dir, "scenes_scripts.json")
    
    # 读取现有的 JSON 文件
    scenes_data = []
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                scenes_data = json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            print(f"警告：读取 {json_path} 失败: {e}")
            scenes_data = []
    
    # 查找并更新对应场景的数据
    scene_found = False
    for scene in scenes_data:
        if scene.get("scene_index") == scene_index:
            scene["scene_script"] = validated_segments
            scene_found = True
            break
    
    if not scene_found:
        return f"❌ 未找到场景索引 {scene_index} 的数据"
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    
    # 写回 JSON 文件
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(scenes_data, f, ensure_ascii=False, indent=2)
        
        segment_count = len(validated_segments)
        voice_stats = {}
        for seg in validated_segments:
            voice_type = seg["voice_type"]
            voice_stats[voice_type] = voice_stats.get(voice_type, 0) + 1
        
        stats_str = ", ".join([f"{voice}: {count}段" for voice, count in voice_stats.items()])
        
        return f"✅ 场景 {scene_index} 脚本已更新: {segment_count}个语句段落 ({stats_str})"
        
    except Exception as e:
        return f"❌ 写入文件失败: {str(e)}"