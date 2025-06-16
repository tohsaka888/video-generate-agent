from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from utils.llm import chat_model
from utils.mcp import filesystem_mcp


@dataclass
class SceneAgentDeps:
    outline: str
    current_chapter: int = 1


scene_agent = Agent(
    model=chat_model, deps_type=SceneAgentDeps, mcp_servers=[filesystem_mcp]
)


@scene_agent.instructions
def generate_chapter_content(ctx: RunContext[SceneAgentDeps]) -> str:
    """
    生成章节内容。
    """
    outline = ctx.deps.outline
    current_chapter = ctx.deps.current_chapter

    # 这里可以实现章节内容生成的逻辑
    system_instruction = f"""
    你是一位专业的图片生成助手，擅长根据小说章节内容提炼高质量的图片生成提示词。
    请根据 output/chapters/chapter_{current_chapter}/index.txt 文件中的章节内容，结合用户提供的大纲，为本章节创作分镜头脚本。

    要求如下：
    - 共生成5个镜头，每个镜头需详细描述，突出画面感，便于生成动漫风格或写实风格的图片。
    - 每个镜头描述需包含：
      1. 人物：主要角色的外貌、服饰、神态、动作。
      2. 场景：环境、氛围、光影等细节。
      3. 镜头：角色的动作、互动，描述图片中的构图和人物关系（不包含对话）。
      4. 风格：明确为“动漫风”或“写实风”二选一。
    - 每个镜头描述约100字，内容连贯有趣，符合大纲设定。
    - 生成内容后，调用工具将每个镜头的提示词分别保存至 output/chapters/chapter_{current_chapter}/scenes/scene_i.txt（i为镜头编号）。
    - 还需要生成每个镜头对应的脚本文件，脚本文件是指这个镜头对应的原文内容，调用工具保存至 output/chapters/chapter_{current_chapter}/scripts/script_i.txt（i为镜头编号）。

    示例：
    ```md
    人物：
    1. 艾莉丝：年轻女巫，金色长发，穿蓝色长袍，手持魔法杖。
    2. 凯尔：年轻骑士，短发，银色盔甲，手持剑，面带微笑。
    场景：神秘森林，光影斑驳。
    镜头：艾莉丝站在森林中央，魔杖挥舞，周围萦绕着光点；凯尔在一旁注视。
    风格：动漫风
    ```

    故事大纲：
    {outline}
    """
    return system_instruction
