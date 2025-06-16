from agents.scene_agent import scene_agent, SceneAgentDeps


async def main():
    async with scene_agent.run_mcp_servers():
        outline = "在一个魔法与科技并存的世界中，年轻的女巫艾莉丝踏上了寻找失落神器的旅程。"
        for chapter in range(1, 4):
            print(f"Generating scene script for Chapter {chapter}...")
            deps = SceneAgentDeps(outline=outline, current_chapter=chapter)
            result = await scene_agent.run(deps=deps, user_prompt="生成的风格为动漫风和二次元")
            print(f"Chapter {chapter} scene script:\n{result}\n")

if __name__ == "__main__":
    import asyncio
    import logfire
    logfire.configure()
    logfire.instrument_pydantic_ai()
    asyncio.run(main())
