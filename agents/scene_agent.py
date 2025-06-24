import os
import glob
import re
import json
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from utils.llm import chat_model
from utils.mcp import filesystem_mcp
from utils.comfyui import generate_image
import edge_tts


def validate_scene_count(scene_count: int) -> int:
    """
    验证并调整场景数量，确保在5-50范围内。
    
    Args:·
        scene_count: 用户输入的场景数量
        
    Returns:
        int: 调整后的场景数量
    """
    if scene_count < 5:
        print(f"警告：场景数量 {scene_count} 少于最小值5，已调整为5")
        return 5
    elif scene_count > 50:
        print(f"警告：场景数量 {scene_count} 超过最大值50，已调整为50")
        return 50
    return scene_count


@dataclass
class SceneAgentDeps:
    outline: str
    current_chapter: int = 1
    scene_count: int = 5  # 默认5个场景，可配置范围5-50
    
    def __post_init__(self):
        """后处理验证，确保 scene_count 在合理范围内"""
        self.scene_count = validate_scene_count(self.scene_count)


scene_agent = Agent(
    model=chat_model, deps_type=SceneAgentDeps, mcp_servers=[filesystem_mcp]
)


def clean_text_for_srt(text):
    """
    清理文本，只保留逗号、句号、感叹号，去除其他特殊符号
    """
    # 保留中文、英文、数字、空格、逗号、句号、感叹号
    cleaned_text = re.sub(r'[^\u4e00-\u9fff\u3400-\u4dbfA-Za-z0-9\s，。！,.]', '', text)
    # 去除多余的空格
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text

def create_sentence_based_srt(word_boundaries, text):
    """
    根据词汇边界信息创建基于语句的SRT字幕文件，精准同步音画
    """
    if not word_boundaries:
        return ""

    cleaned_text = clean_text_for_srt(text)
    # 智能句子分割
    sentences = []
    parts = re.split(r'([。！.!])', cleaned_text)
    current_sentence = ""
    for i, part in enumerate(parts):
        current_sentence += part
        if re.match(r'[。！.!]', part) or i == len(parts) - 1:
            if current_sentence.strip():
                clean_sentence = current_sentence.strip()
                if '？' in clean_sentence:
                    sub_parts = clean_sentence.split('？')
                    for j, sub_part in enumerate(sub_parts):
                        if sub_part.strip():
                            if j < len(sub_parts) - 1:
                                sentences.append(sub_part.strip() + '？')
                            else:
                                if sub_part.strip():
                                    sentences.append(sub_part.strip())
                else:
                    if clean_sentence and len(clean_sentence) > 1:
                        sentences.append(clean_sentence)
            current_sentence = ""
    # 进一步清理句子列表
    cleaned_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and len(sentence) > 1 and not re.match(r'^[，。！,.!]+$', sentence):
            cleaned_sentences.append(sentence)
    sentences = cleaned_sentences
    if not sentences:
        return ""

    # 拼接所有词边界文本，便于查找句子在词边界中的起止位置
    boundary_texts = [b.get('text', '').strip() for b in word_boundaries]
    joined_text = ''.join(boundary_texts)
    char_offsets = [b.get('offset', 0) for b in word_boundaries]
    char_durations = [b.get('duration', 1000000) for b in word_boundaries]

    srt_content = ""
    srt_index = 1
    last_end_idx = 0
    prev_end_time = 0.0  # 初始化，确保时间递增
    for sentence in sentences:
        # 去除标点和空格用于匹配
        sentence_clean = re.sub(r'[，。！,.!\s]+', '', sentence)
        # 在joined_text中查找该句的起止位置
        start_idx = joined_text.find(sentence_clean, last_end_idx)
        if start_idx == -1:
            # 匹配不到时，尝试从头查找
            start_idx = joined_text.find(sentence_clean)
        if start_idx == -1:
            # 仍找不到，回退为均分时间
            total_duration = (word_boundaries[-1].get('offset', 0) + word_boundaries[-1].get('duration', 1000000)) / 10000000
            time_per_sentence = total_duration / len(sentences)
            start_time = (srt_index - 1) * time_per_sentence
            end_time = srt_index * time_per_sentence
        else:
            # 找到起止词边界
            end_idx = start_idx + len(sentence_clean) - 1
            # 找到对应的词边界索引
            start_word_idx = None
            end_word_idx = None
            char_count = 0
            for i, t in enumerate(boundary_texts):
                if char_count == start_idx:
                    start_word_idx = i
                if char_count + len(t) - 1 >= end_idx and end_word_idx is None:
                    end_word_idx = i
                char_count += len(t)
            if start_word_idx is None:
                start_word_idx = 0
            if end_word_idx is None:
                end_word_idx = len(word_boundaries) - 1
            start_time = char_offsets[start_word_idx] / 10000000
            end_time = (char_offsets[end_word_idx] + char_durations[end_word_idx]) / 10000000
            last_end_idx = end_idx + 1
        # 确保时间递增
        if srt_index > 1 and start_time < prev_end_time:
            start_time = prev_end_time + 0.05
        if end_time <= start_time:
            end_time = start_time + max(len(sentence) * 0.08, 1.0)
        prev_end_time = end_time
        start_str = format_srt_time(start_time)
        end_str = format_srt_time(end_time)
        srt_content += f"{srt_index}\n{start_str} --> {end_str}\n{sentence}\n\n"
        srt_index += 1
    return srt_content

def format_srt_time(seconds):
    """
    将秒数转换为SRT时间格式 (HH:MM:SS,mmm)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

def generate_audio_for_script(script_path: str, audio_path: str, srt_path: str) -> str:
    """
    为单个脚本文件生成音频和字幕的核心函数。
    """
    dir_name = os.path.dirname(audio_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    dir_name = os.path.dirname(srt_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    if not os.path.exists(script_path):
        raise FileNotFoundError(f"脚本文件未找到: {script_path}")
    
    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read()
    if not script_content.strip():
        raise ValueError(f"脚本文件内容为空: {script_path}")
    
    # 使用 edge-tts 生成音频
    communicate = edge_tts.Communicate(
        text=script_content,
        voice="zh-CN-XiaoxiaoNeural",
    )
    
    # 收集词汇边界信息用于生成基于语句的字幕
    word_boundaries = []
    
    with open(audio_path, "wb") as file:
        for chunk in communicate.stream_sync():
            if chunk["type"] == "audio" and "data" in chunk:
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append(chunk)

    # 使用自定义函数生成基于语句的字幕
    srt_content = create_sentence_based_srt(word_boundaries, script_content)
    
    with open(srt_path, "w", encoding="utf-8") as file:
        file.write(srt_content)
    
    return "已生成音频和基于语句分割的字幕文件。"


@scene_agent.instructions
def generate_complete_media_content(ctx: RunContext[SceneAgentDeps]) -> str:
    """
    生成完整的媒体内容，包括分镜脚本、图片和音频。
    """
    outline = ctx.deps.outline
    current_chapter = ctx.deps.current_chapter
    scene_count = ctx.deps.scene_count

    system_instruction = f"""
你是一位专业的多媒体内容生成助手，负责为小说章节生成完整的视频制作素材。

你的工作流程包括三个阶段：

**阶段1：分镜Stable Diffusion提示词和原文脚本生成（结构化输出）**
根据 output/chapters/chapter_{current_chapter}/index.txt 文件中的章节内容，结合用户提供的大纲，为本章节创作{scene_count}个分镜头。

**Stable Diffusion提示词编写要求：**
1. **必须使用英文**，遵循最佳SD提示词格式
2. **权重和质量词汇**：
   - 必须包含：embedding:lazypos
   - 高质量词汇：masterpiece, best quality, ultra detailed, 8k, photorealistic
   - 根据需要使用权重语法：(word:1.2) 或 ((word))
3. **人物描述顺序**：主体 → 外貌特征 → 服装 → 表情动作
4. **场景和构图**：环境描述 → 光照效果 → 镜头角度 → 艺术风格
5. **人物一致性**：相同角色必须保持一致的外貌特征（发色、眼色、体型、服装风格等）
6. **负向提示词考虑**：避免使用可能产生负面效果的词汇

**提示词结构示例：**
```
embedding:lazypos, masterpiece, best quality, ultra detailed, (beautiful anime girl:1.2), solo, (silver hair:1.1), long hair, (blue eyes:1.1), school uniform, white shirt, blue skirt, (sitting on chair:1.1), classroom, soft lighting, anime style, detailed background, (sad expression:1.1)
```

**原文脚本要求：**
- 提取该镜头对应的小说原文内容
- 确保文本适合语音合成（去除特殊符号，保持自然语调）
- 每段脚本长度适中，便于生成音频和字幕

**输出格式要求：**
请将所有镜头的SD提示词和原文脚本以如下结构化JSON格式输出：
```json
[
  {{
    "scene_index": 1,
    "scene_prompt": "<遵循最佳实践的英文SD提示词>",
    "scene_script": "<该镜头对应的小说原文>"
  }},
  {{
    "scene_index": 2,
    "scene_prompt": "<遵循最佳实践的英文SD提示词>",
    "scene_script": "<该镜头对应的小说原文>"
  }},
  ...
]
```

生成完成后，调用 save_scenes_scripts 工具保存到 scenes_scripts.json。

**阶段2：图片生成**
调用 batch_generate_images 工具，基于SD提示词批量生成高质量图片。

**阶段3：音频生成**
调用 batch_generate_audio 工具，基于原文脚本批量生成音频和字幕文件。

**重要提示：**
- 确保所有SD提示词符合最佳实践，使用高质量描述词汇
- 保持角色外貌的一致性，避免同一人物在不同场景中外貌差异过大
- 原文脚本应忠实于小说内容，确保语音合成效果自然
- 严格按照三个阶段顺序执行

故事大纲：
{outline}
"""
    return system_instruction


@scene_agent.tool
def save_scenes_scripts(ctx: RunContext[SceneAgentDeps], scenes_scripts: list) -> str:
    """
    工具：将所有分镜和脚本一次性写入json文件。
    scenes_scripts: List[dict]，每项包含scene_index, scene_prompt, scene_script。
    """
    chapter_num = ctx.deps.current_chapter
    output_dir = f"output/chapters/chapter_{chapter_num}"
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "scenes_scripts.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(scenes_scripts, f, ensure_ascii=False, indent=2)
    return f"✅ 已保存所有分镜和脚本到 {json_path}"


@scene_agent.tool
def batch_generate_images(ctx: RunContext[SceneAgentDeps]) -> str:
    """
    批量生成图片，读取scenes_scripts.json。
    """
    chapter_num = ctx.deps.current_chapter
    output_dir = f"output/chapters/chapter_{chapter_num}"
    images_dir = os.path.join(output_dir, "images")
    json_path = os.path.join(output_dir, "scenes_scripts.json")
    os.makedirs(images_dir, exist_ok=True)
    if not os.path.exists(json_path):
        return f"❌ 未找到 {json_path}，请先生成分镜和脚本"
    with open(json_path, "r", encoding="utf-8") as f:
        scenes_scripts = json.load(f)
    if not scenes_scripts:
        return f"❌ {json_path} 为空"
    generated_images = []
    failed_images = []
    print(f"🖼️ 开始批量生成第{chapter_num}章的{len(scenes_scripts)}张图片...")
    for item in scenes_scripts:
        i = item.get("scene_index")
        scene_content = item.get("scene_prompt", "").strip()
        image_path = os.path.join(images_dir, f"scene_{i}.png")
        try:
            if os.path.exists(image_path):
                print(f"⏭️ 第{i}张图片已存在，跳过生成: {image_path}")
                generated_images.append(f"scene_{i}.png (已存在)")
                continue
            print(f"🎨 正在生成第{i}/{len(scenes_scripts)}张图片...")
            result = generate_image(prompt_text=scene_content, save_path=image_path)
            if result and os.path.exists(image_path):
                generated_images.append(f"scene_{i}.png")
                print(f"✅ 第{i}张图片生成成功: scene_{i}.png")
            else:
                failed_images.append(f"scene_{i}.png")
                print(f"❌ 第{i}张图片生成失败")
        except Exception as e:
            failed_images.append(f"scene_{i}.png (错误: {str(e)})")
            print(f"❌ 第{i}张图片生成异常: {str(e)}")
    total_scenes = len(scenes_scripts)
    success_count = len(generated_images)
    failed_count = len(failed_images)
    result_report = f"""
📊 第{chapter_num}章图片生成完成报告:
- 总场景数: {total_scenes}
- 成功生成: {success_count}张
- 生成失败: {failed_count}张
- 成功率: {(success_count/total_scenes*100):.1f}%\n\n✅ 成功生成的图片:\n{chr(10).join(f'  - {img}' for img in generated_images)}
"""
    if failed_images:
        result_report += f"""
❌ 生成失败的图片:\n{chr(10).join(f'  - {img}' for img in failed_images)}
"""
    print(result_report)
    return result_report

@scene_agent.tool
def batch_generate_audio(ctx: RunContext[SceneAgentDeps]) -> str:
    """
    批量生成音频和字幕，读取scenes_scripts.json。
    """
    chapter_num = ctx.deps.current_chapter
    output_dir = f"output/chapters/chapter_{chapter_num}"
    audio_dir = os.path.join(output_dir, "audio")
    srt_dir = os.path.join(output_dir, "srt")
    json_path = os.path.join(output_dir, "scenes_scripts.json")
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(srt_dir, exist_ok=True)
    if not os.path.exists(json_path):
        return f"❌ 未找到 {json_path}，请先生成分镜和脚本"
    with open(json_path, "r", encoding="utf-8") as f:
        scenes_scripts = json.load(f)
    if not scenes_scripts:
        return f"❌ {json_path} 为空"
    generated_audio = []
    generated_srt = []
    failed_items = []
    print(f"🔊 开始批量生成第{chapter_num}章的{len(scenes_scripts)}个音频文件...")
    for item in scenes_scripts:
        i = item.get("scene_index")
        script_content = item.get("scene_script", "").strip()
        audio_path = os.path.join(audio_dir, f"audio_{i}.mp3")
        srt_path = os.path.join(srt_dir, f"srt_{i}.srt")
        try:
            if os.path.exists(audio_path) and os.path.exists(srt_path):
                print(f"⏭️ 第{i}个音频和字幕已存在，跳过生成")
                generated_audio.append(f"audio_{i}.mp3 (已存在)")
                generated_srt.append(f"srt_{i}.srt (已存在)")
                continue
            print(f"🎵 正在生成第{i}/{len(scenes_scripts)}个音频文件...")
            # 直接用内容生成音频和字幕
            tmp_script_path = os.path.join(output_dir, f"tmp_script_{i}.txt")
            with open(tmp_script_path, "w", encoding="utf-8") as ftmp:
                ftmp.write(script_content)
            result = generate_audio_for_script(tmp_script_path, audio_path, srt_path)
            os.remove(tmp_script_path)
            if "已生成音频和基于语句分割的字幕文件" in result:
                generated_audio.append(f"audio_{i}.mp3")
                generated_srt.append(f"srt_{i}.srt")
                print(f"✅ 第{i}个音频和字幕生成成功")
            else:
                failed_items.append(f"audio_{i}.mp3 / srt_{i}.srt")
                print(f"❌ 第{i}个音频生成失败")
        except Exception as e:
            failed_items.append(f"audio_{i}.mp3 / srt_{i}.srt (错误: {str(e)})")
            print(f"❌ 第{i}个音频生成异常: {str(e)}")
    total_scripts = len(scenes_scripts)
    success_count = len(generated_audio)
    failed_count = len(failed_items)
    result_report = f"""
📊 第{chapter_num}章音频生成完成报告:
- 总脚本数: {total_scripts}
- 成功生成: {success_count}个音频
- 生成失败: {failed_count}个音频
- 成功率: {(success_count/total_scripts*100):.1f}%\n\n✅ 成功生成的音频:\n{chr(10).join(f'  - {audio}' for audio in generated_audio)}\n\n✅ 成功生成的字幕:\n{chr(10).join(f'  - {srt}' for srt in generated_srt)}
"""
    if failed_items:
        result_report += f"""
❌ 生成失败的项目:\n{chr(10).join(f'  - {item}' for item in failed_items)}
"""
    print(result_report)
    return result_report


# 用于直接调用的便捷函数，可以在其他地方直接使用
def generate_chapter_images_directly(chapter_num: int) -> str:
    """
    直接生成指定章节的所有图片，不通过agent调用。
    这是一个便捷函数，可以在需要时直接调用。
    """
    scenes_dir = f"output/chapters/chapter_{chapter_num}/scenes"
    images_dir = f"output/chapters/chapter_{chapter_num}/images"
    
    # 创建图片输出目录
    os.makedirs(images_dir, exist_ok=True)
    
    # 获取所有场景文件
    scene_files = glob.glob(os.path.join(scenes_dir, "scene_*.txt"))
    scene_files.sort(key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))
    
    if not scene_files:
        return f"❌ 未找到第{chapter_num}章的场景文件，请先生成分镜脚本"
    
    generated_images = []
    failed_images = []
    
    print(f"🖼️ 开始批量生成第{chapter_num}章的{len(scene_files)}张图片...")
    
    for i, scene_file in enumerate(scene_files, 1):
        try:
            # 读取场景描述
            with open(scene_file, 'r', encoding='utf-8') as f:
                scene_content = f.read().strip()
            
            # 生成图片保存路径
            image_path = os.path.join(images_dir, f"scene_{i}.png")
            
            # 检查图片是否已存在
            if os.path.exists(image_path):
                print(f"⏭️ 第{i}张图片已存在，跳过生成: {image_path}")
                generated_images.append(f"scene_{i}.png (已存在)")
                continue
            
            print(f"🎨 正在生成第{i}/{len(scene_files)}张图片...")
            
            # 调用图片生成
            result = generate_image(prompt_text=scene_content, save_path=image_path)
            
            if result and os.path.exists(image_path):
                generated_images.append(f"scene_{i}.png")
                print(f"✅ 第{i}张图片生成成功: scene_{i}.png")
            else:
                failed_images.append(f"scene_{i}.png")
                print(f"❌ 第{i}张图片生成失败")
                
        except Exception as e:
            failed_images.append(f"scene_{i}.png (错误: {str(e)})")
            print(f"❌ 第{i}张图片生成异常: {str(e)}")
    
    # 生成结果报告
    total_scenes = len(scene_files)
    success_count = len(generated_images)
    failed_count = len(failed_images)
    
    result_report = f"""
📊 第{chapter_num}章图片生成完成报告:
- 总场景数: {total_scenes}
- 成功生成: {success_count}张
- 生成失败: {failed_count}张
- 成功率: {(success_count/total_scenes*100):.1f}%

✅ 成功生成的图片:
{chr(10).join(f"  - {img}" for img in generated_images)}
"""
    
    if failed_images:
        result_report += f"""
❌ 生成失败的图片:
{chr(10).join(f"  - {img}" for img in failed_images)}
"""
    
    return result_report


def generate_chapter_audio_directly(chapter_num: int) -> str:
    """
    直接生成指定章节的所有音频和字幕，不通过agent调用。
    这是一个便捷函数，可以在需要时直接调用。
    """
    scripts_dir = f"output/chapters/chapter_{chapter_num}/scripts"
    audio_dir = f"output/chapters/chapter_{chapter_num}/audio"
    srt_dir = f"output/chapters/chapter_{chapter_num}/srt"
    
    # 创建输出目录
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(srt_dir, exist_ok=True)
    
    # 获取所有脚本文件
    script_files = glob.glob(os.path.join(scripts_dir, "script_*.txt"))
    script_files.sort(key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))
    
    if not script_files:
        return f"❌ 未找到第{chapter_num}章的脚本文件，请先生成分镜脚本"
    
    generated_audio = []
    generated_srt = []
    failed_items = []
    
    print(f"🔊 开始批量生成第{chapter_num}章的{len(script_files)}个音频文件...")
    
    for i, script_file in enumerate(script_files, 1):
        try:
            # 生成输出路径
            audio_path = os.path.join(audio_dir, f"audio_{i}.mp3")
            srt_path = os.path.join(srt_dir, f"srt_{i}.srt")
            
            # 检查文件是否已存在
            if os.path.exists(audio_path) and os.path.exists(srt_path):
                print(f"⏭️ 第{i}个音频和字幕已存在，跳过生成")
                generated_audio.append(f"audio_{i}.mp3 (已存在)")
                generated_srt.append(f"srt_{i}.srt (已存在)")
                continue
            
            print(f"🎵 正在生成第{i}/{len(script_files)}个音频文件...")
            
            # 调用音频生成
            result = generate_audio_for_script(script_file, audio_path, srt_path)
            
            if "已生成音频和基于语句分割的字幕文件" in result:
                generated_audio.append(f"audio_{i}.mp3")
                generated_srt.append(f"srt_{i}.srt")
                print(f"✅ 第{i}个音频和字幕生成成功")
            else:
                failed_items.append(f"audio_{i}.mp3 / srt_{i}.srt")
                print(f"❌ 第{i}个音频生成失败")
                
        except Exception as e:
            failed_items.append(f"audio_{i}.mp3 / srt_{i}.srt (错误: {str(e)})")
            print(f"❌ 第{i}个音频生成异常: {str(e)}")
    
    # 生成结果报告
    total_scripts = len(script_files)
    success_count = len(generated_audio)
    failed_count = len(failed_items)
    
    result_report = f"""
📊 第{chapter_num}章音频生成完成报告:
- 总脚本数: {total_scripts}
- 成功生成: {success_count}个音频
- 生成失败: {failed_count}个音频
- 成功率: {(success_count/total_scripts*100):.1f}%\n\n✅ 成功生成的音频:\n{chr(10).join(f'  - {audio}' for audio in generated_audio)}\n\n✅ 成功生成的字幕:\n{chr(10).join(f'  - {srt}' for srt in generated_srt)}
"""
    
    if failed_items:
        result_report += f"""
❌ 生成失败的项目:\n{chr(10).join(f'  - {item}' for item in failed_items)}
"""
    
    return result_report
