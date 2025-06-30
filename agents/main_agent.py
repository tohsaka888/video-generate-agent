from dataclasses import dataclass
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
    novel_file_path: str = ""  # 小说源文件路径
    chunk_size: int = 500      # 每次读取字符数，可配置
    overlap_sentences: int = 1  # 重叠句子数，保持上下文连贯


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
    return """
    你是AI视频生成系统的主控制器，负责协调整个视频生成流程。

    你需要按照以下步骤生成完整的AI视频：

    1. **文本生成阶段**: 调用 generate_content
    2. **媒体生成阶段**: 调用 generate_media 
    3. **视频合成阶段**: 调用 compose_video

    请开始执行视频生成流程。
    """


@main_agent.tool
async def generate_content(ctx: RunContext[MainAgentDeps]) -> str:
    """
    生成文本内容，支持从小说文件中读取内容
    """
    os.makedirs("output", exist_ok=True)
    
    if not ctx.deps.novel_file_path:
        return "未提供小说源文件，无法生成内容。"
    
    if not os.path.exists(ctx.deps.novel_file_path):
        return f"小说源文件不存在: {ctx.deps.novel_file_path}"
        
    deps = NovelAgentDeps(
        novel_file_path=ctx.deps.novel_file_path,
        chunk_size=ctx.deps.chunk_size,
    )
    
    result = await novel_agent.run("请读取小说源文件并生成内容", deps=deps)
    return f"文本内容已生成: {result.output}"


@main_agent.tool
async def generate_media(ctx: RunContext[MainAgentDeps]) -> str:
    """
    生成分镜头脚本、图片和音频
    """
    deps = SceneAgentDeps()
    result = await scene_agent.run("请生成完整的媒体内容，包括分镜脚本、图片和音频", deps=deps)
    return f"媒体内容已生成: {result.output}"


@main_agent.tool
def compose_video(ctx: RunContext[MainAgentDeps]) -> str:
    """
    合成最终视频
    """
    result = generate_video()
    return result


# 便捷的启动函数
async def start_video_generation(
    novel_file_path: str = "",
    requirement: str = '',
    chunk_size: int = 500,
    overlap_sentences: int = 1
) -> str:
    """
    启动AI视频生成流程的便捷函数
    
    Args:
        novel_file_path: 小说源文件路径
        requirement: 用户需求描述
        chunk_size: 每次读取字符数，可配置
        overlap_sentences: 重叠句子数，保持上下文连贯
    
    Returns:
        生成结果描述
    """
    
    deps = MainAgentDeps(
        novel_file_path=novel_file_path,
        chunk_size=chunk_size,
        overlap_sentences=overlap_sentences
    )
    
    async with main_agent.run_mcp_servers():
        result = await main_agent.run(
            f"请生成完整的AI视频, {requirement}",
            deps=deps,
        )
        return result.output


if __name__ == "__main__":
    # 示例用法
    import asyncio
    
    # 运行示例
    asyncio.run(start_video_generation(
        novel_file_path="/path/to/your/novel.txt",
        requirement="基于源文件生成视频内容",
        chunk_size=800,
        overlap_sentences=2
    ))