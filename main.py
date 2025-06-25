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
    chapter = 4
    scene_count = 15  # 每章节场景数量（范围：5-50）

    print("🎯 生成设置:")
    print(f"   开始章节: 第{chapter}章")
    print(f"   每章场景数: {scene_count}个")
    print("=" * 50)

    # 启动AI视频生成
    result = await start_video_generation(
        chapter=chapter,
        scene_count=scene_count,
        requirement="情节跌宕起伏，要体现出复仇的爽感。",
    )

    print("\n" + "=" * 50)
    print("📋 生成结果:")
    print(result)
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
