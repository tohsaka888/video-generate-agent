"""
小说阅读器工具模块
支持大文件分块读取，保持句子完整性，记录读取位置
"""
import os
import json
import re
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class ReadingState:
    """读取状态记录"""
    file_path: str
    current_position: int = 0  # 当前读取位置（字符位置）
    total_size: int = 0        # 文件总大小
    chunk_size: int = 500      # 每次读取的字符数
    last_read_time: str = ""   # 最后读取时间
    encoding: str = "utf-8"    # 文件编码
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReadingState":
        """从字典创建实例"""
        return cls(**data)


class NovelReader:
    """小说阅读器类"""
    
    def __init__(self, state_file: str = "novel_reading_state.json"):
        self.state_file = state_file
        self.reading_states: Dict[str, ReadingState] = {}
        self.load_states()
        
        # 初始化中文句子分割所需的模块
        try:
            import jieba  # type: ignore
            self.jieba = jieba
        except ImportError:
            self.jieba = None
            print("警告：jieba未安装，中文句子分割可能不够精确")
    
    def load_states(self) -> None:
        """加载读取状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for file_path, state_dict in data.items():
                        self.reading_states[file_path] = ReadingState.from_dict(state_dict)
            except Exception as e:
                print(f"加载读取状态失败: {e}")
                self.reading_states = {}
    
    def save_states(self) -> None:
        """保存读取状态"""
        try:
            data = {file_path: state.to_dict() for file_path, state in self.reading_states.items()}
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存读取状态失败: {e}")
    
    def get_file_encoding(self, file_path: str) -> str:
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
    
    def split_into_sentences(self, text: str) -> list:
        """将文本分割为句子，保持句子完整性"""
        if not text:
            return []
        
        # 中文句子分割模式
        chinese_sentence_pattern = r'[。！？；…]+|[\n\r]+'
        # 英文句子分割模式  
        english_sentence_pattern = r'[.!?;]+\s*|[\n\r]+'
        
        # 组合模式
        sentence_pattern = f'({chinese_sentence_pattern}|{english_sentence_pattern})'
        
        # 分割句子
        sentences = re.split(sentence_pattern, text)
        
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
    
    def find_sentence_boundary(self, text: str, target_position: int) -> int:
        """在目标位置附近找到完整的句子边界"""
        if target_position >= len(text):
            return len(text)
        
        # 分割为句子
        sentences = self.split_into_sentences(text)
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
    
    def init_novel_file(self, file_path: str, chunk_size: int = 500) -> ReadingState:
        """初始化小说文件读取状态"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 获取文件大小和编码
        file_size = os.path.getsize(file_path)
        encoding = self.get_file_encoding(file_path)
        
        # 创建或更新读取状态
        if file_path in self.reading_states:
            state = self.reading_states[file_path]
            state.chunk_size = chunk_size
            state.total_size = file_size
            state.encoding = encoding
        else:
            state = ReadingState(
                file_path=file_path,
                current_position=0,
                total_size=file_size,
                chunk_size=chunk_size,
                encoding=encoding
            )
            self.reading_states[file_path] = state
        
        self.save_states()
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
        if file_path not in self.reading_states:
            raise ValueError(f"文件未初始化: {file_path}")
        
        state = self.reading_states[file_path]
        
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
                    boundary_pos = self.find_sentence_boundary(raw_text, state.chunk_size)
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
                    previous_sentences = self.split_into_sentences(previous_text)
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
                self.save_states()
                
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
    
    def reset_reading_position(self, file_path: str) -> bool:
        """重置文件读取位置到开头"""
        if file_path in self.reading_states:
            self.reading_states[file_path].current_position = 0
            self.save_states()
            return True
        return False
    
    def set_reading_position(self, file_path: str, position: int) -> bool:
        """设置文件读取位置"""
        if file_path in self.reading_states:
            state = self.reading_states[file_path]
            state.current_position = max(0, min(position, state.total_size))
            self.save_states()
            return True
        return False
    
    def get_reading_progress(self, file_path: str) -> Optional[Dict[str, Any]]:
        """获取读取进度信息"""
        if file_path in self.reading_states:
            state = self.reading_states[file_path]
            progress = (state.current_position / state.total_size) * 100 if state.total_size > 0 else 0
            return {
                "file_path": state.file_path,
                "current_position": state.current_position,
                "total_size": state.total_size,
                "progress": progress,
                "chunk_size": state.chunk_size,
                "encoding": state.encoding
            }
        return None
    
    def list_reading_states(self) -> Dict[str, Dict[str, Any]]:
        """列出所有文件的读取状态"""
        result = {}
        for file_path in self.reading_states.keys():
            progress = self.get_reading_progress(file_path)
            if progress is not None:
                result[file_path] = progress
        return result
