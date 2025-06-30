import os
import json
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from utils.llm import chat_model
from utils.mcp import filesystem_mcp
from utils.media_generator import (
    load_scenes_scripts,
    generate_media_concurrent,
    setup_chapter_directories
)


def validate_scene_count(scene_count: int) -> int:
    """验证场景数量，确保在5-50范围内"""
    return max(5, min(scene_count, 50))


@dataclass
class SceneAgentDeps:
    current_chapter: int = 1
    scene_count: int = 5

    def __post_init__(self):
        self.scene_count = validate_scene_count(self.scene_count)


scene_agent = Agent(
    model=chat_model, deps_type=SceneAgentDeps, mcp_servers=[filesystem_mcp]
)


@scene_agent.instructions
def generate_complete_media_content(ctx: RunContext[SceneAgentDeps]) -> str:
    """生成完整的媒体内容，包括分镜脚本、图片和音频"""
    current_chapter = ctx.deps.current_chapter
    scene_count = ctx.deps.scene_count

    return f"""
你是一位专业的多媒体内容生成助手，负责为小说章节生成完整的视频制作素材。

请为本章节创作{scene_count}个分镜头，并生成相关媒体内容。

本章节的内容如下
"""


@scene_agent.tool
def save_scenes_scripts(ctx: RunContext[SceneAgentDeps], scenes_scripts: list) -> str:
    """保存分镜和脚本到JSON文件"""
    chapter_num = ctx.deps.current_chapter
    dirs = setup_chapter_directories(chapter_num)
    os.makedirs(dirs["output_dir"], exist_ok=True)

    json_path = os.path.join(dirs["output_dir"], "scenes_scripts.json")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(scenes_scripts, f, ensure_ascii=False, indent=2)

    return f"已保存到 {json_path}"


@scene_agent.tool
def batch_generate_media_concurrent(ctx: RunContext[SceneAgentDeps]) -> str:
    """并发生成图片和音频"""
    chapter_num = ctx.deps.current_chapter
    dirs = setup_chapter_directories(chapter_num)

    json_path = os.path.join(dirs["output_dir"], "scenes_scripts.json")
    scenes_scripts = load_scenes_scripts(json_path)
    result = generate_media_concurrent(scenes_scripts, dirs, chapter_num)

    return f"媒体生成完成: {result}"
