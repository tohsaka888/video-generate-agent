from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from utils.llm import chat_model
from utils.mcp import filesystem_mcp
from utils.generate_img import generate_image

@dataclass
class ImageAgentDeps:
    current_chapter: int = 1

image_agent = Agent(
    model=chat_model, deps_type=ImageAgentDeps, mcp_servers=[filesystem_mcp]
)

@image_agent.instructions
def generate_images_for_chapter(ctx: RunContext[ImageAgentDeps]) -> str:
    """
    查询当前章节 scenes 目录下所有分镜文件，调用 generate_image 生成图片。
    """
    system_instruction = f"""
    你是一个图片生成助手。

    你需要使用工具读取 output/chapters/chapter_{ctx.deps.current_chapter}/scenes 目录下的分镜文件，并根据文件内容生成图片。
    读取完scenes目录下的所有分镜文件后，你需要调用 generate_image 工具生成图片。
    文件保存在 output/chapters/chapter_{ctx.deps.current_chapter}/images 目录下，文件名为 scene_i.png（i为镜头编号）。

    注意：不要批量生成图片，你需要读取一个场景生成一张图片，防止多次调用时出现重复图片。
    """
    return system_instruction

@image_agent.tool
def generate_image_tool(ctx: RunContext[ImageAgentDeps], scene: str, save_path: str) -> str:
    """
    调用生成图片的工具。
    """
    return generate_image(prompt=scene, save_path=save_path)