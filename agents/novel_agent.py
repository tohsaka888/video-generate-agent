from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from utils.llm import chat_model
from utils.mcp import filesystem_mcp

@dataclass
class NovelAgentDeps:
    outline: str
    current_chapter: int = 1


novel_agent = Agent(
   model=chat_model,
   deps_type=NovelAgentDeps,
   mcp_servers=[filesystem_mcp]
)

@novel_agent.instructions
def generate_chapter_content(ctx: RunContext[NovelAgentDeps]) -> str:
    """
    生成章节内容。
    """
    outline = ctx.deps.outline
    current_chapter = ctx.deps.current_chapter

    # 这里可以实现章节内容生成的逻辑
    system_instruction = f"""
    你是一个小说创作助手，能够帮助用户构思情节、发展角色和创建世界观。
    根据用户提供的大纲编写章节内容。每个章节的内容在1000字左右。
    如果当前章节不是第一章，你需要先读取之前的章节内容，以便更好地衔接故事。
    请确保章节内容连贯、有趣，并符合用户提供的大纲。
    chapter的存储目录在output/chapters/chapter_{current_chapter}文件夹中，你可以在这个目录中读取之前的章节内容。
    请使用工具将当前章节内容保存到chapter目录中，文件名为index.txt，不要使用markdown，纯文本即可，
    需要包含章节名称，格式为：第x章，xxxxx。
    用户提供的大纲为：{outline}
    当前章节为第{current_chapter}章。
    """
    return system_instruction