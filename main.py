# 导入日志监控库logfire
import logfire
import asyncio
import dotenv
import os

# 导入主控制器
from agents.main_agent import start_video_generation

dotenv.load_dotenv('.env')

MODE = os.getenv("MODE")

if MODE == "dev":
    # 配置logfire日志监控
    logfire.configure()
    # 对pydantic_ai进行监控
    logfire.instrument_pydantic_ai()


async def main():
    """
    主函数 - AI视频生成系统入口
    """
    print("🎬 欢迎使用AI视频生成系统!")
    print("=" * 50)

    # 配置生成参数
    chapter = 1
    scene_count = 15  # 每章节场景数量（范围：5-50）
    
    # 智能读取配置（可选）
    novel_file_path = "assets/novel/index.txt"  # 设置为你的小说文件路径，例如: "/path/to/your/novel.txt"
    chunk_size = 500      # 每次读取字符数
    overlap_sentences = 1 # 重叠句子数

    print("🎯 生成设置:")
    print(f"   开始章节: 第{chapter}章")
    print(f"   每章场景数: {scene_count}个")
    if novel_file_path:
        print(f"   小说源文件: {novel_file_path}")
        print(f"   读取块大小: {chunk_size}字符")
        print(f"   重叠句子数: {overlap_sentences}")
    else:
        print("   模式: 传统创作模式（无源文件）")
    print("=" * 50)

    # 启动AI视频生成
    result = await start_video_generation(
        chapter=chapter,
        scene_count=scene_count,
        requirement="请帮我生成一个完整的AI视频",
        novel_file_path=novel_file_path,
        chunk_size=chunk_size,
        overlap_sentences=overlap_sentences
    )

    print("\n" + "=" * 50)
    print("📋 生成结果:")
    print(result)
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
