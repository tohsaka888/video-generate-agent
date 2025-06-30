"""
小说处理工具模块
提供文件读取和分句功能
"""

import hashlib
import json
from pathlib import Path
import chardet


def detect_encoding(file_path: str) -> str:
    """检测文件编码"""
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read(1000)
            result = chardet.detect(raw_data)
            encoding = result.get("encoding", "utf-8")
            
            # 简化编码处理
            if encoding and encoding.lower() in ["gb2312", "gbk"]:
                return "gbk"
            elif encoding and encoding.lower() == "big5":
                return "big5"
            else:
                return "utf-8"
    except Exception:
        return "utf-8"


def split_sentences(text: str) -> list:
    """简单分句处理"""
    if not text:
        return []
    
    # 按段落分割
    paragraphs = text.split("\n")
    sentences = []
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
            
        # 按句号分割
        parts = paragraph.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").split("\n")
        for part in parts:
            part = part.strip()
            if part and len(part) > 3:
                sentences.append(part)
    
    return sentences


def read_novel_content(novel_file_path: str, chunk_size: int = 500) -> dict:
    """
    读取小说内容
    返回: {"content": str, "finished": bool}
    """
    if not Path(novel_file_path).exists():
        raise FileNotFoundError(f"小说文件不存在: {novel_file_path}")
    
    # 生成缓存文件路径
    cache_dir = Path(".cache")
    cache_dir.mkdir(exist_ok=True)
    file_hash = hashlib.md5(novel_file_path.encode("utf-8")).hexdigest()
    cache_path = cache_dir / f"novel_{file_hash}.json"
    
    # 读取缓存
    offset = 0
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
                offset = cache.get("offset", 0)
        except Exception:
            offset = 0
    
    # 检测编码并读取文件
    encoding = detect_encoding(novel_file_path)
    
    try:
        with open(novel_file_path, "r", encoding=encoding) as f:
            f.seek(offset)
            raw_text = f.read(chunk_size * 2)
    except Exception:
        raise RuntimeError("无法读取文件")
    
    if not raw_text:
        return {"content": "", "finished": True}
    
    # 分句处理
    sentences = split_sentences(raw_text)
    
    # 选择合适长度的内容
    selected_text = ""
    for sentence in sentences:
        if len(selected_text + sentence) > chunk_size and selected_text:
            break
        selected_text += sentence
    
    if not selected_text:
        selected_text = raw_text[:chunk_size]
    
    # 更新缓存
    new_offset = offset + len(selected_text.encode(encoding))
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"offset": new_offset}, f)
    except Exception:
        pass
    
    return {
        "content": selected_text,
        "finished": False
    }
