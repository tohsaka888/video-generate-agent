"""
小说阅读器工具模块
支持大文件分块读取，保持句子完整性，基于文件缓存记录读取位置
"""
import os
import json
import re
import hashlib
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ReadingState:
    """读取状态记录"""
    file_path: str
    current_position: int = 0  # 当前读取位置（字符位置）
    total_size: int = 0        # 文件总大小
    chunk_size: int = 500      # 每次读取的字符数
    last_read_time: str = ""   # 最后读取时间
    encoding: str = "utf-8"    # 文件编码
    file_hash: str = ""        # 文件哈希值，用于检测文件变化
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReadingState":
        """从字典创建实例"""
        return cls(**data)


class NovelReader:
    """小说阅读器类"""
    
    def __init__(self, cache_dir: str = ".cache"):
        """初始化阅读器
        
        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_dir = cache_dir
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self) -> None:
        """确保缓存目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_file_path(self, file_path: str) -> str:
        """获取缓存文件路径"""
        # 使用文件路径的哈希值作为缓存文件名
        file_hash = hashlib.md5(file_path.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"novel_state_{file_hash}.json")
    
    def _get_file_hash(self, file_path: str) -> str:
        """获取文件哈希值"""
        try:
            stat = os.stat(file_path)
            # 使用文件大小和修改时间计算哈希
            content = f"{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return ""
    
    def _load_state(self, file_path: str) -> Optional[ReadingState]:
        """加载读取状态"""
        cache_file = self._get_cache_file_path(file_path)
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                state = ReadingState.from_dict(data)
                
                # 检查文件是否发生变化
                current_hash = self._get_file_hash(file_path)
                if current_hash and state.file_hash != current_hash:
                    # 文件已变化，重置读取位置
                    state.current_position = 0
                    state.file_hash = current_hash
                
                return state
        except Exception as e:
            print(f"加载缓存状态失败: {e}")
            return None
    
    def _save_state(self, state: ReadingState) -> None:
        """保存读取状态"""
        cache_file = self._get_cache_file_path(state.file_path)
        try:
            state.last_read_time = datetime.now().isoformat()
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存缓存状态失败: {e}")

    
    def _get_file_encoding(self, file_path: str) -> str:
        """检测文件编码"""
        try:
            # 尝试常见编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read(100)  # 读取前100个字符测试
                    return encoding
                except UnicodeDecodeError:
                    continue
        except Exception:
            pass
        return 'utf-8'  # 默认返回utf-8
    
    def _split_into_sentences(self, text: str) -> list:
        """将文本分割为句子，保持句子完整性"""
        if not text:
            return []
        
        # 中文和英文句子分割模式
        sentence_pattern = r'[。！？；…]+|[.!?;]+\s*|[\n\r]+'
        
        # 分割句子
        sentences = re.split(f'({sentence_pattern})', text)
        
        # 重新组合句子和标点
        result = []
        i = 0
        while i < len(sentences):
            if i + 1 < len(sentences) and re.match(sentence_pattern, sentences[i + 1]):
                # 句子 + 标点
                result.append(sentences[i] + sentences[i + 1])
                i += 2
            else:
                # 单独的句子
                if sentences[i].strip():
                    result.append(sentences[i])
                i += 1
        
        return [s.strip() for s in result if s.strip()]
    
    def _find_sentence_boundary(self, text: str, target_position: int) -> int:
        """在目标位置附近找到完整的句子边界"""
        if target_position >= len(text):
            return len(text)
        
        # 分割为句子
        sentences = self._split_into_sentences(text)
        if not sentences:
            return min(target_position, len(text))
        
        # 计算每个句子的累计长度
        current_pos = 0
        for sentence in sentences:
            sentence_end = current_pos + len(sentence)
            if sentence_end >= target_position:
                return sentence_end
            current_pos = sentence_end
        
        return len(text)
    
    def init_file(self, file_path: str, chunk_size: int = 500) -> ReadingState:
        """初始化小说文件读取状态"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 获取文件大小、编码和哈希
        file_size = os.path.getsize(file_path)
        encoding = self._get_file_encoding(file_path)
        file_hash = self._get_file_hash(file_path)
        
        # 尝试加载现有状态
        state = self._load_state(file_path)
        
        if state is None:
            # 创建新状态
            state = ReadingState(
                file_path=file_path,
                current_position=0,
                total_size=file_size,
                chunk_size=chunk_size,
                encoding=encoding,
                file_hash=file_hash
            )
        else:
            # 更新状态
            state.chunk_size = chunk_size
            state.total_size = file_size
            state.encoding = encoding
            state.file_hash = file_hash
        
        self._save_state(state)
        return state
    
    def read_next_chunk(self, file_path: str, overlap_sentences: int = 1) -> Tuple[str, bool, Dict[str, Any]]:
        """
        读取下一个文本块
        
        Args:
            file_path: 文件路径
            overlap_sentences: 重叠的句子数量，确保上下文连贯
            
        Returns:
            Tuple[str, bool, Dict[str, Any]]: (读取的文本, 是否已到文件末尾, 读取信息)
        """
        state = self._load_state(file_path)
        if state is None:
            raise ValueError(f"文件未初始化: {file_path}")
        
        try:
            with open(file_path, 'r', encoding=state.encoding) as f:
                # 移动到当前位置
                f.seek(state.current_position)
                
                # 读取指定大小的文本块，加上一些额外的字符以确保完整句子
                buffer_size = state.chunk_size + 200  # 额外缓冲区
                raw_text = f.read(buffer_size)
                
                if not raw_text:
                    # 已到文件末尾
                    return "", True, {
                        "current_position": state.current_position,
                        "total_size": state.total_size,
                        "progress": 100.0,
                        "chunk_size": 0
                    }
                
                # 找到合适的句子边界
                if len(raw_text) == buffer_size:
                    # 还没到文件末尾，需要找句子边界
                    boundary_pos = self._find_sentence_boundary(raw_text, state.chunk_size)
                    chunk_text = raw_text[:boundary_pos]
                else:
                    # 已到文件末尾
                    chunk_text = raw_text
                    boundary_pos = len(raw_text)
                
                # 处理重叠部分（获取前面的句子作为上下文）
                overlap_text = ""
                if state.current_position > 0 and overlap_sentences > 0:
                    # 回读一些内容获取重叠句子
                    f.seek(max(0, state.current_position - 300))
                    previous_text = f.read(300)
                    previous_sentences = self._split_into_sentences(previous_text)
                    if len(previous_sentences) > overlap_sentences:
                        overlap_text = "".join(previous_sentences[-overlap_sentences:])
                
                # 组合最终文本
                final_text = (overlap_text + chunk_text).strip()
                
                # 更新读取位置
                state.current_position += boundary_pos
                is_end = state.current_position >= state.total_size
                
                # 计算进度
                progress = (state.current_position / state.total_size) * 100 if state.total_size > 0 else 100
                
                # 保存状态
                self._save_state(state)
                
                read_info = {
                    "current_position": state.current_position,
                    "total_size": state.total_size,
                    "progress": progress,
                    "chunk_size": len(final_text),
                    "has_overlap": len(overlap_text) > 0,
                    "overlap_size": len(overlap_text)
                }
                
                return final_text, is_end, read_info
                
        except Exception as e:
            raise RuntimeError(f"读取文件失败: {e}")
    
    def reset_position(self, file_path: str) -> bool:
        """重置文件读取位置到开头"""
        state = self._load_state(file_path)
        if state is not None:
            state.current_position = 0
            self._save_state(state)
            return True
        return False
    
    def set_position(self, file_path: str, position: int) -> bool:
        """设置文件读取位置"""
        state = self._load_state(file_path)
        if state is not None:
            state.current_position = max(0, min(position, state.total_size))
            self._save_state(state)
            return True
        return False
    
    def get_progress(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取读取进度信息"""
        state = self._load_state(file_path)
        if state is not None:
            progress = (state.current_position / state.total_size) * 100 if state.total_size > 0 else 0
            return {
                "file_path": state.file_path,
                "current_position": state.current_position,
                "total_size": state.total_size,
                "progress": progress,
                "chunk_size": state.chunk_size,
                "encoding": state.encoding,
                "last_read_time": state.last_read_time
            }
        return None
    
    def list_cached_files(self) -> Dict[str, Dict[str, Any]]:
        """列出所有缓存的文件读取状态"""
        result = {}
        
        # 遍历缓存目录
        for filename in os.listdir(self.cache_dir):
            if filename.startswith("novel_state_") and filename.endswith(".json"):
                cache_file = os.path.join(self.cache_dir, filename)
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        state = ReadingState.from_dict(data)
                        
                        # 检查文件是否仍存在
                        if os.path.exists(state.file_path):
                            progress = (state.current_position / state.total_size) * 100 if state.total_size > 0 else 0
                            result[state.file_path] = {
                                "current_position": state.current_position,
                                "total_size": state.total_size,
                                "progress": progress,
                                "chunk_size": state.chunk_size,
                                "encoding": state.encoding,
                                "last_read_time": state.last_read_time
                            }
                except Exception as e:
                    print(f"读取缓存文件 {filename} 失败: {e}")
        
        return result


# 创建默认实例
default_reader = NovelReader()

# 兼容性函数，保持原有API
def init_novel_file(file_path: str, chunk_size: int = 500) -> ReadingState:
    """初始化小说文件读取状态（兼容性函数）"""
    return default_reader.init_file(file_path, chunk_size)

def read_next_chunk(file_path: str, overlap_sentences: int = 1) -> Tuple[str, bool, Dict[str, Any]]:
    """读取下一个文本块（兼容性函数）"""
    return default_reader.read_next_chunk(file_path, overlap_sentences)

def reset_reading_position(file_path: str) -> bool:
    """重置文件读取位置到开头（兼容性函数）"""
    return default_reader.reset_position(file_path)

def set_reading_position(file_path: str, position: int) -> bool:
    """设置文件读取位置（兼容性函数）"""
    return default_reader.set_position(file_path, position)

def get_reading_progress(file_path: str) -> Optional[Dict[str, Any]]:
    """获取读取进度信息（兼容性函数）"""
    return default_reader.get_progress(file_path)

def list_reading_states() -> Dict[str, Dict[str, Any]]:
    """列出所有文件的读取状态（兼容性函数）"""
    return default_reader.list_cached_files()
