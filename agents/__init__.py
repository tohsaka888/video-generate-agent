# Agents Package
# AI视频生成系统的核心代理模块

from .main_agent import main_agent, start_video_generation, MainAgentDeps
from .novel_agent import novel_agent, NovelAgentDeps
from .scene_agent import scene_agent, SceneAgentDeps
from .image_agent import image_agent, ImageAgentDeps
from .audio_agent import audio_agent, AudioAgentDeps

__all__ = [
    # Main Agent
    'main_agent',
    'start_video_generation', 
    'MainAgentDeps',
    
    # Specialized Agents
    'novel_agent',
    'NovelAgentDeps',
    'scene_agent', 
    'SceneAgentDeps',
    'image_agent',
    'ImageAgentDeps',
    'audio_agent',
    'AudioAgentDeps',
]
