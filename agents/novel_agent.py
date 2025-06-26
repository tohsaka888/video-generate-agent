import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pydantic_ai import Agent, RunContext
from utils.llm import chat_model
from utils.mcp import filesystem_mcp
from utils.novel_reader import NovelReader


@dataclass
class NovelAgentDeps:
    current_chapter: int = 1
    novel_file_path: str = ""  # 小说源文件路径
    chunk_size: int = 500      # 每次读取字符数，可配置
    overlap_sentences: int = 1  # 重叠句子数，保持上下文连贯


novel_agent = Agent(
    model=chat_model,
    deps_type=NovelAgentDeps,
    mcp_servers=[filesystem_mcp]
)

@novel_agent.instructions
def generate_chapter_content(ctx: RunContext[NovelAgentDeps]) -> str:
    """
    根据小说源文件智能生成章节内容。
    支持大文件分块读取，保持句子完整性。
    """
    current_chapter = ctx.deps.current_chapter
    novel_file_path = ctx.deps.novel_file_path
    chunk_size = ctx.deps.chunk_size

    system_instruction = f"""
# 智能小说章节生成助手

## 角色定位
你是一位专业的小说创作助手，具备以下能力：
1. **智能阅读**：能够分块读取大型小说文件（10MB+），保持句子完整性
2. **上下文理解**：通过句子重叠技术保持前后文连贯性

## 当前任务
- 目标章节：第{current_chapter}章
- 章节长度：1000-1500字
- 阅读块大小：{chunk_size}字符
- 源文件：{novel_file_path if novel_file_path else "未指定，将使用传统创作模式"}

## 工作流程

### 阶段1：源文件读取（如果提供）
1. 首先调用 `init_novel_reading` 初始化小说文件读取
2. 使用 `read_novel_chunk` 智能读取相关内容
3. 根据读取进度决定是否继续读取更多内容

### 阶段2：章节内容生成
1. 结合源文件内容（如有）和用户大纲
2. 保持与前几章的连贯性
3. 创作引人入胜的章节内容

### 阶段3：内容保存
1. 将生成的章节保存到指定路径
2. 更新读取进度状态

## 文件操作
- 保存路径：output/chapters/chapter_{current_chapter}/index.txt
- 格式：纯文本，包含章节标题
- 标题格式：第{current_chapter}章 [章节名称]

## 参考信息
- 当前章节：{current_chapter}
- 源文件路径：{novel_file_path if novel_file_path else "无"}
"""
    return system_instruction


@novel_agent.tool
def init_novel_reading(ctx: RunContext[NovelAgentDeps], file_path: str) -> str:
    """
    初始化小说文件读取，设置读取参数。
    
    Args:
        file_path: 小说文件路径
        
    Returns:
        str: 初始化结果信息
    """
    try:
        # 创建小说阅读器实例
        reader = NovelReader()
        
        # 初始化文件读取状态
        state = reader.init_novel_file(file_path, ctx.deps.chunk_size)
        
        progress_info = reader.get_reading_progress(file_path)
        if progress_info is None:
            return f"❌ 获取进度信息失败"
        
        return f"""✅ 小说文件初始化成功！

📁 文件信息：
- 路径：{file_path}
- 大小：{state.total_size:,} 字节 ({state.total_size / 1024 / 1024:.2f} MB)
- 编码：{state.encoding}
- 块大小：{state.chunk_size} 字符

📊 读取状态：
- 当前位置：{progress_info['current_position']} / {progress_info['total_size']}
- 进度：{progress_info['progress']:.1f}%

🎯 准备开始智能读取章节内容..."""
        
    except Exception as e:
        return f"❌ 初始化失败：{str(e)}"


@novel_agent.tool
def read_novel_chunk(ctx: RunContext[NovelAgentDeps], file_path: str) -> str:
    """
    读取小说文件的下一个文本块，保持句子完整性。
    
    Args:
        file_path: 小说文件路径
        
    Returns:
        str: 读取的文本内容和状态信息
    """
    try:
        reader = NovelReader()
        
        # 读取下一个文本块
        chunk_text, is_end, read_info = reader.read_next_chunk(
            file_path, 
            overlap_sentences=ctx.deps.overlap_sentences
        )
        
        if not chunk_text:
            return "📄 已到达文件末尾，没有更多内容可读取。"
        
        status_info = f"""
📖 读取状态：
- 本次读取：{read_info['chunk_size']} 字符
- 重叠内容：{'是' if read_info['has_overlap'] else '否'} ({read_info.get('overlap_size', 0)} 字符)
- 进度：{read_info['progress']:.1f}% ({read_info['current_position']:,} / {read_info['total_size']:,})
- 是否结束：{'是' if is_end else '否'}

📝 读取内容：
{chunk_text}
"""
        
        return status_info
        
    except Exception as e:
        return f"❌ 读取失败：{str(e)}"


@novel_agent.tool
def get_reading_progress(ctx: RunContext[NovelAgentDeps], file_path: str) -> str:
    """
    获取小说文件的读取进度信息。
    
    Args:
        file_path: 小说文件路径
        
    Returns:
        str: 进度信息
    """
    try:
        reader = NovelReader()
        progress = reader.get_reading_progress(file_path)
        
        if progress is None:
            return f"❌ 文件 {file_path} 未初始化，请先调用 init_novel_reading"
        
        return f"""📊 读取进度报告：

📁 文件：{progress['file_path']}
📏 大小：{progress['total_size']:,} 字节 ({progress['total_size'] / 1024 / 1024:.2f} MB)
📍 位置：{progress['current_position']:,} / {progress['total_size']:,}
📈 进度：{progress['progress']:.1f}%
⚙️ 块大小：{progress['chunk_size']} 字符
🔤 编码：{progress['encoding']}
"""
        
    except Exception as e:
        return f"❌ 获取进度失败：{str(e)}"


@novel_agent.tool
def reset_reading_position(ctx: RunContext[NovelAgentDeps], file_path: str) -> str:
    """
    重置小说文件读取位置到开头。
    
    Args:
        file_path: 小说文件路径
        
    Returns:
        str: 重置结果
    """
    try:
        reader = NovelReader()
        success = reader.reset_reading_position(file_path)
        
        if success:
            return f"✅ 已重置文件 {file_path} 的读取位置到开头"
        else:
            return f"❌ 文件 {file_path} 未初始化，无法重置位置"
            
    except Exception as e:
        return f"❌ 重置失败：{str(e)}"


@novel_agent.tool
def set_reading_position(ctx: RunContext[NovelAgentDeps], file_path: str, position: int) -> str:
    """
    设置小说文件读取位置到指定位置。
    
    Args:
        file_path: 小说文件路径
        position: 目标位置（字符位置）
        
    Returns:
        str: 设置结果
    """
    try:
        reader = NovelReader()
        success = reader.set_reading_position(file_path, position)
        
        if success:
            return f"✅ 已设置文件 {file_path} 的读取位置到 {position}"
        else:
            return f"❌ 文件 {file_path} 未初始化，无法设置位置"
            
    except Exception as e:
        return f"❌ 设置失败：{str(e)}"


@novel_agent.tool
def list_all_reading_states(ctx: RunContext[NovelAgentDeps]) -> str:
    """
    列出所有小说文件的读取状态。
    
    Returns:
        str: 所有文件的读取状态信息
    """
    try:
        reader = NovelReader()
        states = reader.list_reading_states()
        
        if not states:
            return "📝 当前没有任何小说文件的读取记录"
        
        result = "📚 所有小说文件读取状态：\n\n"
        
        for file_path, progress in states.items():
            filename = os.path.basename(file_path)
            result += f"""📖 {filename}
   📁 路径：{file_path}
   📏 大小：{progress['total_size'] / 1024 / 1024:.2f} MB
   📈 进度：{progress['progress']:.1f}%
   📍 位置：{progress['current_position']:,} / {progress['total_size']:,}
   ⚙️ 块大小：{progress['chunk_size']} 字符

"""
        
        return result
        
    except Exception as e:
        return f"❌ 获取状态列表失败：{str(e)}"


@novel_agent.tool
def save_chapter_content(ctx: RunContext[NovelAgentDeps], content: str, chapter_title: str = "") -> str:
    """
    保存生成的章节内容到指定路径。
    
    Args:
        content: 章节内容
        chapter_title: 章节标题（可选）
        
    Returns:
        str: 保存结果
    """
    try:
        chapter_num = ctx.deps.current_chapter
        chapter_dir = f"output/chapters/chapter_{chapter_num}"
        os.makedirs(chapter_dir, exist_ok=True)
        
        # 组合最终内容
        if chapter_title:
            final_content = f"第{chapter_num}章 {chapter_title}\n\n{content}"
        else:
            final_content = f"第{chapter_num}章\n\n{content}"
        
        # 保存到文件
        output_path = f"{chapter_dir}/index.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        return f"✅ 章节内容已保存到: {output_path}\n字数: {len(content)} 字符"
        
    except Exception as e:
        return f"❌ 保存失败: {str(e)}"