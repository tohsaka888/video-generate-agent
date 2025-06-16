from agents.novel_agent import novel_agent, NovelAgentDeps

async def main():
    async with novel_agent.run_mcp_servers():
        outline = (
            "在一个魔法与科技并存的世界中，年轻的女巫艾莉丝踏上了寻找失落神器的旅程。"
        )
        for chapter in range(1, 4):
            print(f"Generating content for Chapter {chapter}...")
            deps = NovelAgentDeps(outline=outline, current_chapter=chapter)
            result = await novel_agent.run(deps=deps, user_prompt="请帮我生成1000字左右章节内容。情节跌宕起伏，角色生动有趣。")
            print(f"Chapter {chapter} content:\n{result}\n")

if __name__ == "__main__":
    import asyncio

    # 导入日志监控库logfire
    import logfire

    # 配置logfire日志监控
    logfire.configure()
    # 对pydantic_ai进行监控
    logfire.instrument_pydantic_ai()
    asyncio.run(main())