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
    chapter: int = 1  # 只支持单章节生成
    scene_count: int = 5  # 每章节的场景数量，默认5个，范围5-50
    novel_file_path: str = ""  # 小说源文件路径，用于智能读取
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
    主控制器，协调整个AI视频生成流程（单章节）。
    """
    chapter = ctx.deps.chapter
    
    system_instruction = f"""
    你是AI视频生成系统的主控制器，负责协调整个视频生成流程。

    你需要按照以下步骤为第{chapter}章生成完整的AI视频：

    1. **文本生成阶段**: 调用 generate_chapter_content
    2. **完整媒体生成阶段**: 调用 generate_scene_scripts 
    3. **视频合成阶段**: 调用 compose_final_video 工具将所有素材合成最终视频


    **注意事项**:
    - 每个步骤都需要等待前一步完全完成
    - 如果某个步骤失败，需要重试或报告错误
    - 最终生成的视频文件保存在 output/chapters/chapter_{chapter}/generated_video.mp4
    - 步骤2（generate_scene_scripts）现在会一次性完成分镜脚本、图片和音频的生成

    请开始执行视频生成流程。
    """
    return system_instruction


@main_agent.tool
async def generate_chapter_content(ctx: RunContext[MainAgentDeps]) -> str:
    """
    生成指定章节的文本内容，如果用户已经提供了章节内容则跳过生成
    支持从大型小说文件中智能读取内容
    """
    chapter_num = ctx.deps.chapter
    try:
        # 创建章节目录
        chapter_dir = f"output/chapters/chapter_{chapter_num}"
        os.makedirs(chapter_dir, exist_ok=True)
        
        if not ctx.deps.novel_file_path:
            print("⚠️ 未提供小说源文件，即将退出")
            return "未提供小说源文件，无法生成章节内容。请提供源文件或手动编写章节内容。"
        
        # 检查小说源文件是否存在
        if not os.path.exists(ctx.deps.novel_file_path):
            print(f"❌ 小说源文件不存在: {ctx.deps.novel_file_path}")
            return f"小说源文件不存在: {ctx.deps.novel_file_path}"
            
        # 调用novel_agent生成章节内容
        deps = NovelAgentDeps(
            current_chapter=chapter_num,
            novel_file_path=ctx.deps.novel_file_path,
            chunk_size=ctx.deps.chunk_size,
            overlap_sentences=ctx.deps.overlap_sentences
        )
        
        # 构建包含大纲的提示
        result = await novel_agent.run(f"请读取小说源文件并生成第{chapter_num}章的内容", deps=deps)

        print(f"✅ 第{chapter_num}章文本内容AI生成完成")
        return f"第{chapter_num}章文本内容已AI生成: {result.data}"
        
    except Exception as e:
        error_msg = f"❌ 第{chapter_num}章文本处理失败: {str(e)}"
        print(error_msg)
        return error_msg


@main_agent.tool
async def generate_scene_scripts(ctx: RunContext[MainAgentDeps]) -> str:
    """
    生成指定章节的分镜头脚本、图片和音频（完整流程）
    """
    chapter_num = ctx.deps.chapter
    try:
        print(f"🎬 开始生成第{chapter_num}章的完整媒体内容...")
        
        # 调用scene_agent生成完整的媒体内容（分镜脚本+图片+音频）
        deps = SceneAgentDeps(
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
def compose_final_video(ctx: RunContext[MainAgentDeps]) -> str:
    """
    合成指定章节的最终视频
    """
    chapter_num = ctx.deps.chapter
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
    获取当前生成进度（单章节）
    """
    chapter_num = ctx.deps.chapter
    video_path = f"output/chapters/chapter_{chapter_num}/generated_video.mp4"
    completed = os.path.exists(video_path)
    progress = 100.0 if completed else 0.0
    return f"""
📊 当前生成进度:
- 章节号: {chapter_num}
- 是否已完成: {'是' if completed else '否'}
- 完成进度: {progress:.1f}%
"""


@main_agent.tool
def check_user_provided_chapters(ctx: RunContext[MainAgentDeps]) -> str:
    """
    检查用户是否提供了章节内容，并显示相关信息
    """
    chapter_num = ctx.deps.chapter
    user_chapter_path = f"input/chapters/chapter_{chapter_num}/index.txt"
    
    # 检查input目录结构
    input_dir = "input/chapters"
    if not os.path.exists(input_dir):
        os.makedirs(input_dir, exist_ok=True)
    
    # 检查章节文件
    chapter_exists = os.path.exists(user_chapter_path)
    
    result = f"""
📁 用户章节内容检查结果:

目标章节: 第{chapter_num}章
预期路径: {user_chapter_path}
文件存在: {'是' if chapter_exists else '否'}

📝 使用说明:
如果您希望使用自己编写的章节内容而不是AI生成，请：
1. 在项目根目录创建 input/chapters/chapter_{chapter_num}/ 文件夹
2. 在该文件夹下创建 index.txt 文件
3. 将您的章节内容写入 index.txt 文件
4. 重新运行视频生成程序

📂 推荐的文件结构:
input/
└── chapters/
    ├── chapter_1/
    │   └── index.txt    # 第1章内容
    ├── chapter_2/
    │   └── index.txt    # 第2章内容
    └── ...
"""
    
    if chapter_exists:
        # 读取文件信息
        try:
            with open(user_chapter_path, "r", encoding="utf-8") as f:
                content = f.read()
            word_count = len(content)
            result += f"""
✅ 检测到用户提供的第{chapter_num}章内容:
- 文件大小: {word_count} 字符
- 内容预览: {content[:100]}{'...' if len(content) > 100 else ''}
"""
        except Exception as e:
            result += f"""
⚠️  文件存在但读取失败: {str(e)}
"""
    
    return result


# 便捷的启动函数
async def start_video_generation(
    chapter: int = 1, 
    requirement: str = '', 
    scene_count: int = 5,
    novel_file_path: str = "",
    chunk_size: int = 500,
    overlap_sentences: int = 1
) -> str:
    """
    启动AI视频生成流程的便捷函数（单章节）
    
    Args:
        chapter: 章节号
        requirement: 用户需求描述
        scene_count: 每章节的场景数量，范围5-50，默认5
        novel_file_path: 小说源文件路径，用于智能读取
        chunk_size: 每次读取字符数，可配置
        overlap_sentences: 重叠句子数，保持上下文连贯
    
    Returns:
        生成结果描述
    """
    print("🎯 开始AI视频生成任务")
    print(f"📖 章节号: 第{chapter}章")
    print(f"🎬 每章场景数量: {scene_count}个")
    if novel_file_path:
        print(f"📚 小说源文件: {novel_file_path}")
        print(f"⚙️ 读取块大小: {chunk_size}字符")
    
    deps = MainAgentDeps(
        chapter=chapter,
        scene_count=scene_count,
        novel_file_path=novel_file_path,
        chunk_size=chunk_size,
        overlap_sentences=overlap_sentences
    )
    
    try:
        async with main_agent.run_mcp_servers():
            result = await main_agent.run(
                f"请为第{chapter}章生成完整的AI视频, {requirement}",
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
    
    # 运行示例 - 基本模式（不使用源文件）
    asyncio.run(start_video_generation(
        chapter=1,
        requirement="请根据用户提供的大纲生成章节内容"
    ))
    
    # 运行示例 - 智能读取模式（使用大型小说源文件）
    # asyncio.run(start_video_generation(
    #     chapter=1,
    #     requirement="基于源文件智能生成章节内容",
    #     novel_file_path="/path/to/your/novel.txt",
    #     chunk_size=800,
    #     overlap_sentences=2
    # ))