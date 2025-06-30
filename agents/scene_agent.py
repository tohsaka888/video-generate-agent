from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from utils.llm import chat_model
from utils.scene import (
    read_content_file,
    save_scenes_scripts,
    batch_generate_images,
    clean_scenes_data
)
from agents.talk_agent import talk_agent, TalkAgentDeps


@dataclass
class SceneAgentDeps:
    content_file: str = "output/content.txt"  # 小说内容文件路径


scene_agent = Agent(
    model=chat_model, 
    deps_type=SceneAgentDeps, 
)


@scene_agent.instructions
def generate_scenes_and_images(ctx: RunContext[SceneAgentDeps]) -> str:
    """生成分镜脚本和对应的图片"""
    return """
你是一位专业的分镜师，负责将小说内容转换为视频分镜脚本。

## 工作流程：
1. 调用 read_content 工具读取小说内容
2. 调用 generate_scenes 工具保存分镜脚本（必须严格按照JSON格式）
3. 调用 generate_images_and_audio 工具同时生成图片和音频

## 重要：generate_scenes工具的数据格式要求

调用generate_scenes时，scenes_data参数必须是包含以下字段的JSON数组：

```json
[
  {
    "scene_id": 1,
    "script": "当前image_prompt对应的原文片段",
    "image_prompt": "stable diffusion提示词，用于生成分镜的图片",
  }
]
```

注意：
1. script中的原文片段拼接起来应为整个小说内容，你不能有任何的删减导致script直接文本不连贯。
2. image_prompt必须是详细的英文提示词，描述顺序为: 人物(男/女，年龄，眼睛，发色，服装, ...) -> 生态(开心，伤心，愤怒...) -> 动作 -> 场景。例如：a girl, young, blue eyes, blonde hair, wearing a school dress, looking happy, school, classroom, sit on the floor.
3. 不同分镜的相同任务必须保证任务提示词统一，尤其是脸部特征、服装（除非不同场景有不同的服装）等细节，确保生成的图片风格一致。
"""


@scene_agent.tool
def read_content(ctx: RunContext[SceneAgentDeps]) -> str:
    """读取小说内容文件"""
    content_file = ctx.deps.content_file
    
    try:
        return read_content_file(content_file)
        
    except Exception as e:
        return f"读取内容失败: {str(e)}"


@scene_agent.tool
def generate_scenes(ctx: RunContext[SceneAgentDeps], scenes_data: list) -> str:
    """保存AI生成的分镜脚本"""
    try:
        # 清理和验证数据
        cleaned_scenes = clean_scenes_data(scenes_data)
        
        if not cleaned_scenes:
            return "错误: 没有有效的场景数据"
        
        # 保存分镜脚本
        result = save_scenes_scripts(cleaned_scenes)
        
        return f"成功保存 {len(cleaned_scenes)} 个场景的分镜脚本。{result}"
        
    except Exception as e:
        return f"保存分镜脚本失败: {str(e)}"


@scene_agent.tool
async def generate_images_and_audio(ctx: RunContext[SceneAgentDeps]) -> str:
    """同时生成场景图片和音频文件"""
    try:
        # 从保存的脚本文件中读取场景数据
        from utils.scene import load_scenes_scripts
        scenes_scripts = load_scenes_scripts()
        
        if not scenes_scripts:
            return "❌ 没有找到场景脚本数据"
        
        total_scenes = len(scenes_scripts)
        image_results = []
        audio_results = []
        
        # 1. 批量生成图片
        try:
            image_result = batch_generate_images(scenes_scripts)
            image_results.append(f"图片生成: {image_result['success_count']}/{image_result['total_scenes']} 成功")
        except Exception as e:
            image_results.append(f"图片生成失败: {str(e)}")
        
        # 2. 并行生成每个场景的音频
        import concurrent.futures
        
        async def generate_scene_audio(scene_id):
            """为单个场景生成音频"""
            try:
                deps = TalkAgentDeps(scene_id=scene_id)
                await talk_agent.run("请生成场景音频和字幕", deps=deps)
                return f"场景 {scene_id}: ✅ 音频生成成功"
            except Exception as e:
                return f"场景 {scene_id}: ❌ 音频生成失败 - {str(e)}"
        
        # 使用线程池并行处理音频生成
        scene_ids = [scene['scene_id'] for scene in scenes_scripts]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            audio_futures = {executor.submit(generate_scene_audio, scene_id): scene_id for scene_id in scene_ids}
            
            for future in concurrent.futures.as_completed(audio_futures):
                scene_id = audio_futures[future]
                try:
                    result = future.result()
                    audio_results.append(result)
                except Exception as e:
                    audio_results.append(f"场景 {scene_id}: ❌ 音频处理异常 - {str(e)}")
        
        # 统计结果
        audio_success_count = len([r for r in audio_results if "✅" in r])
        audio_failed_count = len([r for r in audio_results if "❌" in r])
        
        return f"""🎬 场景处理完成:

📊 总体统计:
- 总场景数: {total_scenes}

🖼️ 图片生成结果:
{chr(10).join(image_results)}

🔊 音频生成结果:
- 成功: {audio_success_count} 个场景
- 失败: {audio_failed_count} 个场景

📝 详细结果:
{chr(10).join(audio_results)}

✅ 所有场景的图片和音频文件已生成到 output/ 目录"""
        
    except Exception as e:
        return f"生成图片和音频失败: {str(e)}"
