from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from utils.llm import chat_model
import hashlib
import json
from pathlib import Path
import re
import charset_normalizer


@dataclass
class NovelAgentDeps:
    current_chapter: int = 1
    novel_file_path: str = ""  # 小说源文件路径
    chunk_size: int = 500      # 每次读取字符数，可配置
    overlap_sentences: int = 1  # 重叠句子数，保持上下文连贯


novel_agent = Agent(
    model=chat_model,
    deps_type=NovelAgentDeps,
)

CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)

def _get_cache_path(novel_file_path: str) -> Path:
    """根据小说文件路径生成唯一的缓存文件路径"""
    h = hashlib.md5(novel_file_path.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"novel_read_{h}.json"

@novel_agent.tool
def read_novel_chunk(ctx: RunContext[NovelAgentDeps]) -> dict:
    """
    读取 chunk_size 附近的完整句子，并记录进度，支持句子重叠。
    返回内容和当前偏移量。
    """
    current_chapter = ctx.deps.current_chapter
    novel_file_path = ctx.deps.novel_file_path
    chunk_size = ctx.deps.chunk_size
    overlap_sentences = ctx.deps.overlap_sentences
    cache_path = _get_cache_path(novel_file_path)
    if not Path(novel_file_path).exists():
        raise FileNotFoundError(f"小说文件不存在: {novel_file_path}")
    # 自动初始化进度文件
    if not cache_path.exists():
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"offset": 0}, f)
    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)
    offset = cache.get("offset", 0)
    # 检测文件编码
    with open(novel_file_path, "rb") as f:
        raw_bytes = f.read(4096)
        result = charset_normalizer.from_bytes(raw_bytes)
        encoding = result.best().encoding if result and result.best() else "utf-8"
    with open(novel_file_path, "r", encoding=encoding) as f:
        f.seek(offset)
        # 读取多一点，保证句子完整
        raw = f.read(chunk_size * 2)
    # 按中文句号、问号、感叹号分句
    sentences = re.split(r'(。|！|？|\!|\?)', raw)
    # 合并分隔符为完整句子
    full_sentences = []
    for i in range(0, len(sentences)-1, 2):
        full_sentences.append(sentences[i] + sentences[i+1])
    # 选取能凑到 chunk_size 的句子
    chunk = ''
    count = 0
    for s in full_sentences:
        if len(chunk) + len(s) > chunk_size and count > 0:
            break
        chunk += s
        count += 1
    # 处理 overlap
    if overlap_sentences > 0 and count > overlap_sentences:
        overlap = full_sentences[max(0, count-overlap_sentences):count]
    else:
        overlap = []
    # 计算新 offset
    new_offset = offset + len(chunk.encode('utf-8'))
    # 更新进度
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({"offset": new_offset}, f)
     # 确保目录存在
    output_dir = Path(f'output/chapters/chapter_{current_chapter}')
    output_dir.mkdir(parents=True, exist_ok=True)
    # 追加写入内容
    with open(output_dir / 'index.txt', 'a', encoding='utf-8') as f:
        f.write(chunk)
    return {"content": chunk, "offset": new_offset, "overlap": ''.join(overlap)}

@novel_agent.instructions
def generate_chapter_content(ctx: RunContext[NovelAgentDeps]) -> str:
    """
    根据小说源文件智能生成章节内容。
    支持大文件分块读取，保持句子完整性。
    """

    system_instruction = """
你是一个短视频小说助手，你现在需要从用户给定的小说中读取章节内容。

注意，为了后续工作能够正常执行，你读取的内容的总字数在100字左右，不要超出太多。
"""
    return system_instruction