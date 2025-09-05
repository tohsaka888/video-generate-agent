import json
import os
from time import sleep
from pydantic_ai import Agent, RunContext
from utils.edge_tts import generate_audio_for_script
from utils.llm import chat_model
from utils.task_manager import task_manager
from .character_agent import character_agent
from .novel_agent import novel_agent, NovelAgentDeps
from .scene_agent import scene_agent
from ag_ui.core import EventType, StateSnapshotEvent
from pydantic import BaseModel
from pydantic_ai.ag_ui import StateDeps
from utils.config import system_prompt


class AgentState(BaseModel):
    """State for the agent."""

    message: str = ""
    detail: str = ""


main_agent = Agent(model=chat_model, deps_type=StateDeps[AgentState])


@main_agent.instructions
def main_instructions(ctx: RunContext[StateDeps[AgentState]]) -> str:
    return f"""
你是一个短视频制作agent，你的主要任务是根据用户提供的小说基线进行小说的编写和短视频的生成。

你的工作流程如下：
1. 调用工具创建小说
2. 调用工具创建人物设定
3. 调用工具生成分镜场景
4. 调用工具批量生成所有场景图片（异步执行）
5. 调用工具查询图片生成状态，直到完成
6. 调用工具生成音频和字幕
7. 调用工具开始视频合成，执行成功后提醒用户关注后台生成进度。

当视频合成完成后，系统将自动通知用户。你可以结束并给用户汇总执行结果。

{system_prompt}
"""


@main_agent.tool_plain
async def novel_creation(baseline: str, word_limit: int = 1000) -> StateSnapshotEvent:
    result = await novel_agent.run(
        user_prompt="请根据要求编写小说。",
        deps=NovelAgentDeps(baseline=baseline, word_limit=word_limit),
    )
    # save novel
    novel_content = result.output
    with open("output/novel_content.txt", "w", encoding="utf-8") as f:
        f.write(novel_content)
    return StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={"message": "小说内容已创建。", "detail": novel_content},
    )


@main_agent.tool_plain
async def send_current_plan(message: str, detail: str) -> StateSnapshotEvent:
    return StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT, snapshot={"message": message, "detail": detail}
    )


@main_agent.tool_plain
async def generate_character_settings() -> StateSnapshotEvent:
    result = await character_agent.run(
        user_prompt="请根据要求生成角色设定。",
    )
    # save character settings
    character_settings = []
    # format to dict
    for item in result.output:
        character_settings.append(
            {
                "name": item.name,
                "character_setting": item.character_setting,
            }
        )
    with open("output/character_settings.json", "w", encoding="utf-8") as f:
        json.dump(character_settings, f, ensure_ascii=False, indent=4)
    return StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={
            "message": "角色设定已创建。",
            "detail": json.dumps(character_settings, ensure_ascii=False, indent=4),
        },
    )


@main_agent.tool_plain
async def generate_scenes() -> StateSnapshotEvent:
    scenes = await scene_agent.run(
        user_prompt="请根据要求生成场景。",
    )

    return StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={
            "message": f"场景已创建。总共 {len(scenes.output)} 个场景。",
            "detail": json.dumps(scenes.output, ensure_ascii=False, indent=4),
        },
    )


@main_agent.tool_plain
async def generate_all_scene_images() -> StateSnapshotEvent:
    """批量生成所有场景图片（异步执行）"""
    with open("output/scenes.json", "r", encoding="utf-8") as f:
        scenes = json.load(f)

    # 提交异步图片生成任务
    task_id = await task_manager.submit_image_generation_task(scenes)

    return StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={
            "message": f"已开始批量生成 {len(scenes)} 个场景图片。",
            "detail": f"任务ID: {task_id}\n请使用查询任务状态工具监控进度。",
        },
    )


@main_agent.tool_plain
async def generate_audios() -> StateSnapshotEvent:
    with open("output/scenes.json", "r", encoding="utf-8") as f:
        scene = json.load(f)

    for idx, item in enumerate(scene):
        # 2) 保存脚本文本
        script_path = f"output/scripts/scene_{idx}.txt"
        os.makedirs("output/scripts", exist_ok=True)
        with open(script_path, "w", encoding="utf-8") as sf:
            sf.write(item["script"])
        # 3) 生成音频与字幕
        audio_path = f"output/audio/scene_{idx}.mp3"
        srt_path = f"output/subtitles/scene_{idx}.srt"
        generate_audio_for_script(
            script_path=script_path, audio_path=audio_path, srt_path=srt_path
        )

    return StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={
            "message": "分镜配音已生成。",
            "detail": "音频文件已保存至 output/audio/ 目录\n字幕文件已保存至 output/subtitles/ 目录",
        },
    )


@main_agent.tool_plain
async def check_task_status(task_id: str) -> StateSnapshotEvent:
    """查询任务状态"""
    task = task_manager.get_task(task_id)

    if not task:
        return StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot={
                "message": "任务不存在。",
                "detail": f"未找到任务ID: {task_id}",
            },
        )

    status_info = {
        "task_id": task.task_id,
        "task_type": task.task_type.value,
        "status": task.status.value,
        "progress": f"{task.progress:.1f}%",
        "error_message": task.error_message,
        "result": task.result,
    }

    if task.status.value == "completed":
        if task.task_type.value == "image_generation":
            completed_images = (
                task.result.get("completed_images", 0) if task.result else 0
            )
            message = f"✅ 图片生成任务已完成！共生成 {completed_images} 张图片。"
        elif task.task_type.value == "video_composition":
            output_path = task.result.get("output_path", "") if task.result else ""
            message = f"✅ 视频合成任务已完成！输出文件: {output_path}"
        else:
            message = "✅ 任务已完成！"
    elif task.status.value == "failed":
        message = f"❌ 任务执行失败: {task.error_message}"
    elif task.status.value == "running":
        message = f"🔄 任务正在执行中，进度: {task.progress:.1f}%"
    else:
        message = "⏳ 任务等待中..."

    sleep(25)

    return StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={
            "message": message,
            "detail": json.dumps(status_info, ensure_ascii=False, indent=2),
        },
    )


@main_agent.tool_plain
async def start_video_composition() -> StateSnapshotEvent:
    """开始视频合成（异步执行）"""
    await task_manager.submit_video_composition_task()

    return StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={
            "message": "已开始视频合成任务。",
            "detail": "视频生成已开始，请您关注后台生成进度。",
        },
    )


@main_agent.tool_plain
async def get_all_tasks_status() -> StateSnapshotEvent:
    """获取所有任务状态"""
    all_tasks = task_manager.get_all_tasks_status()

    if not all_tasks:
        return StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot={
                "message": "当前没有任何任务。",
                "detail": "",
            },
        )

    # 按状态分组统计
    status_summary = {}
    for task in all_tasks:
        status = task["status"]
        if status not in status_summary:
            status_summary[status] = 0
        status_summary[status] += 1

    summary_text = "任务状态概览:\n"
    for status, count in status_summary.items():
        summary_text += f"- {status}: {count} 个任务\n"

    return StateSnapshotEvent(
        type=EventType.STATE_SNAPSHOT,
        snapshot={
            "message": f"当前共有 {len(all_tasks)} 个任务。",
            "detail": summary_text
            + "\n详细信息:\n"
            + json.dumps(all_tasks, ensure_ascii=False, indent=2),
        },
    )


# 测试agent
if __name__ == "__main__":
    import asyncio

    async def main():
        async with main_agent:
            res = await main_agent.run(
                user_prompt="请写一个关于人工智能的短篇小说，字数在1000字以内。",
                deps=StateDeps[AgentState](state=AgentState()),
            )
        print(res.output)

    asyncio.run(main())
