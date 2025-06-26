import os
import glob
import json
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from utils.llm import chat_model
from utils.mcp import filesystem_mcp
from utils.comfyui import generate_image
from utils.tts import generate_audio_for_script
from utils.media_generator import (
    load_scenes_scripts,
    generate_media_concurrent,
    generate_media_report,
    setup_chapter_directories,
    validate_scenes_scripts
)


def validate_scene_count(scene_count: int) -> int:
    """
    验证并调整场景数量，确保在5-50范围内。
    
    Args:·
        scene_count: 用户输入的场景数量
        
    Returns:
        int: 调整后的场景数量
    """
    if scene_count < 5:
        print(f"警告：场景数量 {scene_count} 少于最小值5，已调整为5")
        return 5
    elif scene_count > 50:
        print(f"警告：场景数量 {scene_count} 超过最大值50，已调整为50")
        return 50
    return scene_count


@dataclass
class SceneAgentDeps:
    outline: str
    current_chapter: int = 1
    scene_count: int = 5  # 默认5个场景，可配置范围5-50
    
    def __post_init__(self):
        """后处理验证，确保 scene_count 在合理范围内"""
        self.scene_count = validate_scene_count(self.scene_count)


scene_agent = Agent(
    model=chat_model, deps_type=SceneAgentDeps, mcp_servers=[filesystem_mcp]
)


@scene_agent.instructions
def generate_complete_media_content(ctx: RunContext[SceneAgentDeps]) -> str:
    """
    生成完整的媒体内容，包括分镜脚本、图片和音频。
    """
    outline = ctx.deps.outline
    current_chapter = ctx.deps.current_chapter
    scene_count = ctx.deps.scene_count

    system_instruction = f"""
你是一位专业的多媒体内容生成助手，负责为小说章节生成完整的视频制作素材。

你的工作流程包括三个阶段：

**阶段1：分镜Stable Diffusion提示词和原文脚本生成（结构化输出）**
根据 output/chapters/chapter_{current_chapter}/index.txt 文件中的章节内容，结合用户提供的大纲，为本章节创作{scene_count}个分镜头。

**Stable Diffusion提示词编写要求：**
1. **必须使用英文**，遵循最佳SD动漫风格提示词格式
2. **人物描述顺序**：主体 → 外貌特征 → 服装 → 表情动作
3. **场景和构图**：环境描述 → 光照效果 → 镜头角度 → 艺术风格
4. **人物一致性**：相同角色必须保持一致的外貌特征（发色、眼色、体型、服装风格等）
5. **负向提示词考虑**：避免使用可能产生负面效果的词汇

**提示词结构示例：**
```
beautiful anime girl, solo, (silver hair:1.1), long hair, (blue eyes:1.1), school uniform, white shirt, blue skirt, (sitting on chair:1.1), classroom, soft lighting, anime style, detailed background, (sad expression:1.1)
```

**原文脚本要求：**
- 提取该镜头对应的小说原文内容

**音色配置要求：**
为每个脚本段落分析语义并选择合适的音色：
- **男声(male)**：男性角色对话、男性视角的独白
- **女声(female)**：女性角色对话、女性视角的独白
- **旁白(narrator)**：环境描述、心理描述、故事叙述等非对话内容

**输出格式要求：**
请将所有镜头的SD提示词、原文脚本和音色配置以如下结构化JSON格式输出：
```json
[
  {{
    "scene_index": 1,
    "scene_prompt": "<遵循最佳实践的英文SD提示词>",
    "scene_script": "<该镜头对应的小说原文（不要做翻译，保持原文）>",
    "voice_type": "<male/female/narrator之一>"
  }},
  {{
    "scene_index": 2,
    "scene_prompt": "<遵循最佳实践的英文SD提示词>",
    "scene_script": "<该镜头对应的小说原文（不要做翻译，保持原文）>",
    "voice_type": "<male/female/narrator之一>"
  }},
  ...
]
```

生成完成后，调用 save_scenes_scripts 工具保存到 scenes_scripts.json。

**阶段2&3：并发生成图片和音频**
调用 batch_generate_media_concurrent 工具，基于SD提示词和原文脚本并发生成高质量图片、音频和字幕文件，大幅减少总体生成时间。

**重要提示：**
- 保持角色外貌的一致性，避免同一人物在不同场景中外貌差异过大

故事大纲：
{outline}
"""
    return system_instruction


@scene_agent.tool
def save_scenes_scripts(ctx: RunContext[SceneAgentDeps], scenes_scripts: list) -> str:
    """
    工具：将所有分镜和脚本一次性写入json文件。
    scenes_scripts: List[dict]，每项包含scene_index, scene_prompt, scene_script, voice_type。
    """
    chapter_num = ctx.deps.current_chapter
    dirs = setup_chapter_directories(chapter_num)
    
    # 创建输出目录
    os.makedirs(dirs["output_dir"], exist_ok=True)
    
    # 验证和修正数据
    validated_scripts = validate_scenes_scripts(scenes_scripts)
    
    # 保存到JSON文件
    with open(dirs["json_path"], "w", encoding="utf-8") as f:
        json.dump(validated_scripts, f, ensure_ascii=False, indent=2)
    
    return f"✅ 已保存所有分镜、脚本和音色配置到 {dirs['json_path']}"


@scene_agent.tool
def batch_generate_media_concurrent(ctx: RunContext[SceneAgentDeps]) -> str:
    """
    并发批量生成图片和音频，读取scenes_scripts.json，同时执行图片和音频生成以减少总时间。
    """
    chapter_num = ctx.deps.current_chapter
    dirs = setup_chapter_directories(chapter_num)
    
    # 加载场景脚本配置
    scenes_scripts, error_msg = load_scenes_scripts(dirs["json_path"])
    if error_msg:
        return error_msg
    
    # 并发生成媒体文件
    result = generate_media_concurrent(scenes_scripts, dirs, max_workers=4)
    
    # 生成并返回报告
    report = generate_media_report(chapter_num, result, len(scenes_scripts))
    print(report)
    return report
