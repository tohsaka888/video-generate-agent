from agents.image_agent import image_agent, ImageAgentDeps

async def main():
    async with image_agent.run_mcp_servers():
        for chapter in range(1, 4):
            print(f"Generating images for Chapter {chapter}...")
            deps = ImageAgentDeps(current_chapter=chapter)
            result = await image_agent.run(deps=deps, user_prompt="请为本章节所有分镜生成图片，风格为动漫风和二次元")
            print(f"Chapter {chapter} image generation result:\n{result}\n")

if __name__ == "__main__":
    import asyncio
    import logfire
    logfire.configure()
    logfire.instrument_pydantic_ai()
    asyncio.run(main())
