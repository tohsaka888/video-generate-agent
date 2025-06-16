from agents.audio_agent import audio_agent, AudioAgentDeps


async def main():
    async with audio_agent.run_mcp_servers():
        for chapter in range(1, 4):
            print(f"Generating audio for Chapter {chapter}...")
            deps = AudioAgentDeps(current_chapter=chapter)
            result = await audio_agent.run(
                deps=deps,
                user_prompt="请为本章节生成音频，风格为动漫风和二次元",
            )
            print(f"Chapter {chapter} audio generation result:\n{result}\n")


if __name__ == "__main__":
    import asyncio
    import logfire

    logfire.configure()
    logfire.instrument_pydantic_ai()
    asyncio.run(main())
