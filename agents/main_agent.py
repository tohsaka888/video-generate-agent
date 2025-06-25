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

    1. **文本生成阶段**: 调用 generate_chapter_content 工具生成或加载章节文本内容
       - 如果检测到用户在 input/chapters/chapter_{chapter}/index.txt 已提供章节内容，则直接使用
       - 如果用户未提供，则调用AI生成章节内容
    2. **完整媒体生成阶段**: 调用 generate_scene_scripts 工具生成分镜脚本、图片和音频（一站式完成）
    3. **视频合成阶段**: 调用 compose_final_video 工具将所有素材合成最终视频

    **工作流程**:
    - 只生成第{chapter}章
    - 每个步骤必须严格按照上述3个步骤顺序执行
    - 确保前一步完成后再执行下一步
    - 在每个步骤完成后，报告当前进度

    **用户章节内容检测**:
    - 系统会自动检查 input/chapters/chapter_{chapter}/index.txt 是否存在
    - 如果存在，将跳过AI生成，直接使用用户提供的章节内容
    - 如果不存在，将根据用户的需求生成章节内容

    **注意事项**:
    - 每个步骤都需要等待前一步完全完成
    - 如果某个步骤失败，需要重试或报告错误
    - 最终生成的视频文件保存在 output/chapters/chapter_{chapter}/generated_video.mp4
    - 步骤2（generate_scene_scripts）现在会一次性完成分镜脚本、图片和音频的生成

    请开始执行视频生成流程。
    """
    return system_instruction


@main_agent.tool
async def generate_chapter_content(ctx: RunContext[MainAgentDeps], outline: str) -> str:
    """
    生成指定章节的文本内容，如果用户已经提供了章节内容则跳过生成
    """
    chapter_num = ctx.deps.chapter
    try:
        # 创建章节目录
        chapter_dir = f"output/chapters/chapter_{chapter_num}"
        os.makedirs(chapter_dir, exist_ok=True)
        
        # 检查用户是否已经提供了章节内容
        output_chapter_path = f"{chapter_dir}/index.txt"
        
        if os.path.exists(output_chapter_path):
            print(f"检测到用户已提供第{chapter_num}章内容，跳过AI生成...")

            return f"第{chapter_num}章文本内容已存在: {output_chapter_path}"
        else:
            print(f"🚀 用户未提供第{chapter_num}章内容，开始AI生成...")
            
            # 调用novel_agent生成章节内容
            deps = NovelAgentDeps(current_chapter=chapter_num, outline=outline)
            result = await novel_agent.run("请生成当前章节的内容", deps=deps)
            
            print(f"✅ 第{chapter_num}章文本内容AI生成完成")
            return f"第{chapter_num}章文本内容已AI生成: {result.data}"
        
    except Exception as e:
        error_msg = f"❌ 第{chapter_num}章文本处理失败: {str(e)}"
        print(error_msg)
        return error_msg


@main_agent.tool
async def generate_scene_scripts(ctx: RunContext[MainAgentDeps], outline: str) -> str:
    """
    生成指定章节的分镜头脚本、图片和音频（完整流程）
    """
    chapter_num = ctx.deps.chapter
    try:
        print(f"🎬 开始生成第{chapter_num}章的完整媒体内容...")
        
        # 调用scene_agent生成完整的媒体内容（分镜脚本+图片+音频）
        deps = SceneAgentDeps(
            outline=outline, 
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
async def start_video_generation(chapter: int = 1, requirement: str = '', scene_count: int = 5) -> str:
    """
    启动AI视频生成流程的便捷函数（单章节）
    
    Args:
        outline: 小说大纲
        chapter: 章节号
        requirement: 用户需求描述
        scene_count: 每章节的场景数量，范围5-50，默认5
    
    Returns:
        生成结果描述
    """
    print("🎯 开始AI视频生成任务")
    print(f"📖 章节号: 第{chapter}章")
    print(f"🎬 每章场景数量: {scene_count}个")
    
    deps = MainAgentDeps(
        chapter=chapter,
        scene_count=scene_count
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
    
    sample_outline = """
    这是一个关于年轻法师艾莉丝的冒险故事。
    第一章：艾莉丝在魔法学院接受训练，遇到了好友凯尔。
    第二章：他们接到任务，前往黑暗森林调查异常现象。
    第三章：在森林中发现了古老的魔法遗迹和邪恶力量。
    """
    
    # 运行示例
    asyncio.run(start_video_generation(
        outline=sample_outline,
        chapter=1
    ))