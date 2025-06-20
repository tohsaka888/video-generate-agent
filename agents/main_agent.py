from dataclasses import dataclass
from typing import Optional
from pydantic_ai import Agent, RunContext
from utils.llm import chat_model
from utils.mcp import filesystem_mcp
from utils.video import generate_video
from .novel_agent import novel_agent, NovelAgentDeps
from .scene_agent import scene_agent, SceneAgentDeps
import asyncio
import os


@dataclass
class MainAgentDeps:
    outline: str
    start_chapter: int = 1
    end_chapter: int = 1
    total_chapters: Optional[int] = None
    scene_count: int = 5  # 每章节的场景数量，默认5个，范围5-50


main_agent = Agent(
    model=chat_model,
    deps_type=MainAgentDeps,
    mcp_servers=[filesystem_mcp]
)


@main_agent.instructions
def orchestrate_video_generation(ctx: RunContext[MainAgentDeps]) -> str:
    """
    主控制器，协调整个AI视频生成流程。
    """
    outline = ctx.deps.outline
    start_chapter = ctx.deps.start_chapter
    end_chapter = ctx.deps.end_chapter
    
    system_instruction = f"""
    你是AI视频生成系统的主控制器，负责协调整个视频生成流程。

    你需要按照以下步骤为每个章节生成完整的AI视频：

    1. **文本生成阶段**: 调用 generate_chapter_content 工具生成章节文本内容
    2. **完整媒体生成阶段**: 调用 generate_scene_scripts 工具生成分镜脚本、图片和音频（一站式完成）
    3. **视频合成阶段**: 调用 compose_final_video 工具将所有素材合成最终视频

    **工作流程**:
    - 从第{start_chapter}章开始，到第{end_chapter}章结束
    - 每个章节必须严格按照上述3个步骤顺序执行
    - 确保前一步完成后再执行下一步
    - 在每个步骤完成后，报告当前进度

    **用户提供的大纲**: {outline}

    **注意事项**:
    - 每个步骤都需要等待前一步完全完成
    - 如果某个步骤失败，需要重试或报告错误
    - 最终生成的视频文件保存在 output/chapters/chapter_X/generated_video.mp4
    - 步骤2（generate_scene_scripts）现在会一次性完成分镜脚本、图片和音频的生成

    请开始执行视频生成流程。
    """
    return system_instruction


@main_agent.tool
async def generate_chapter_content(ctx: RunContext[MainAgentDeps], chapter_num: int) -> str:
    """
    生成指定章节的文本内容
    """
    try:
        print(f"🚀 开始生成第{chapter_num}章文本内容...")
        
        # 创建章节目录
        chapter_dir = f"output/chapters/chapter_{chapter_num}"
        os.makedirs(chapter_dir, exist_ok=True)
        
        # 调用novel_agent生成章节内容
        deps = NovelAgentDeps(outline=ctx.deps.outline, current_chapter=chapter_num)
        result = await novel_agent.run("请生成当前章节的内容", deps=deps)
        
        print(f"✅ 第{chapter_num}章文本内容生成完成")
        return f"第{chapter_num}章文本内容已生成: {result.data}"
        
    except Exception as e:
        error_msg = f"❌ 第{chapter_num}章文本生成失败: {str(e)}"
        print(error_msg)
        return error_msg


@main_agent.tool
async def generate_scene_scripts(ctx: RunContext[MainAgentDeps], chapter_num: int) -> str:
    """
    生成指定章节的分镜头脚本、图片和音频（完整流程）
    """
    try:
        print(f"🎬 开始生成第{chapter_num}章的完整媒体内容...")
        
        # 调用scene_agent生成完整的媒体内容（分镜脚本+图片+音频）
        deps = SceneAgentDeps(
            outline=ctx.deps.outline, 
            current_chapter=chapter_num,
            scene_count=ctx.deps.scene_count
        )
        result = await scene_agent.run("请生成完整的媒体内容，包括分镜脚本、图片和音频", deps=deps)
        
        print(f"✅ 第{chapter_num}章完整媒体内容生成完成")
        return f"第{chapter_num}章完整媒体内容已生成: {result.data}"
        
    except Exception as e:
        error_msg = f"❌ 第{chapter_num}章媒体内容生成失败: {str(e)}"
        print(error_msg)
        return error_msg


@main_agent.tool
def compose_final_video(ctx: RunContext[MainAgentDeps], chapter_num: int) -> str:
    """
    合成指定章节的最终视频
    """
    try:
        print(f"🎥 开始合成第{chapter_num}章最终视频...")
        
        # 调用video.py中的generate_video函数
        generate_video(chapter_num)
        
        video_path = f"output/chapters/chapter_{chapter_num}/generated_video.mp4"
        print(f"✅ 第{chapter_num}章视频合成完成: {video_path}")
        return f"第{chapter_num}章视频已成功生成: {video_path}"
        
    except Exception as e:
        error_msg = f"❌ 第{chapter_num}章视频合成失败: {str(e)}"
        print(error_msg)
        return error_msg


@main_agent.tool
def get_generation_progress(ctx: RunContext[MainAgentDeps]) -> str:
    """
    获取当前生成进度
    """
    start_chapter = ctx.deps.start_chapter
    end_chapter = ctx.deps.end_chapter
    total_chapters = end_chapter - start_chapter + 1
    
    completed_chapters = []
    for chapter_num in range(start_chapter, end_chapter + 1):
        video_path = f"output/chapters/chapter_{chapter_num}/generated_video.mp4"
        if os.path.exists(video_path):
            completed_chapters.append(chapter_num)
    
    progress = len(completed_chapters) / total_chapters * 100
    
    return f"""
📊 当前生成进度:
- 总章节数: {total_chapters}
- 已完成章节: {len(completed_chapters)} ({completed_chapters})
- 完成进度: {progress:.1f}%
- 剩余章节: {total_chapters - len(completed_chapters)}
"""


# 便捷的启动函数
async def start_video_generation(outline: str, start_chapter: int = 1, end_chapter: int = 1, requirement: str = '', scene_count: int = 5) -> str:
    """
    启动AI视频生成流程的便捷函数
    
    Args:
        outline: 小说大纲
        start_chapter: 开始章节号
        end_chapter: 结束章节号
        requirement: 用户需求描述
        scene_count: 每章节的场景数量，范围5-50，默认5
    
    Returns:
        生成结果描述
    """
    print("🎯 开始AI视频生成任务")
    print(f"📖 章节范围: 第{start_chapter}章 - 第{end_chapter}章")
    print(f"🎬 每章场景数量: {scene_count}个")
    print(f"📝 大纲: {outline[:100]}...")
    
    deps = MainAgentDeps(
        outline=outline,
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        scene_count=scene_count
    )
    
    try:
        async with main_agent.run_mcp_servers():
            result = await main_agent.run(
                f"请为第{start_chapter}章到第{end_chapter}章生成完整的AI视频, {requirement}",
                deps=deps,
            )

            print("🎉 AI视频生成任务完成!")
            return result.output
        
    except Exception as e:
        error_msg = f"❌ AI视频生成任务失败: {str(e)}"
        print(error_msg)
        return error_msg


if __name__ == "__main__":
    # 示例用法
    import asyncio
    
    sample_outline = """
    这是一个关于年轻法师艾莉丝的冒险故事。
    第一章：艾莉丝在魔法学院接受训练，遇到了好友凯尔。
    第二章：他们接到任务，前往黑暗森林调查异常现象。
    第三章：在森林中发现了古老的魔法遗迹和邪恶力量。
    """
    
    # 运行示例
    asyncio.run(start_video_generation(
        outline=sample_outline,
        start_chapter=1,
        end_chapter=1
    ))