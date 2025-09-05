"""
异步任务管理器，用于管理图片生成和视频合成任务
"""
import asyncio
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from utils.comfyui import generate_image
from utils.video import generate_video as sync_generate_video


class TaskStatus(Enum):
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败


class TaskType(Enum):
    IMAGE_GENERATION = "image_generation"     # 图片生成
    VIDEO_COMPOSITION = "video_composition"   # 视频合成


@dataclass
class Task:
    task_id: str
    task_type: TaskType
    status: TaskStatus
    progress: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    params: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['task_type'] = self.task_type.value
        data['status'] = self.status.value
        return data


class TaskManager:
    """异步任务管理器"""
    
    def __init__(self, max_workers: int = 4):
        self.tasks: Dict[str, Task] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()
        
    def create_task(self, task_id: str, task_type: TaskType, params: Dict[str, Any]) -> Task:
        """创建一个新任务"""
        with self._lock:
            task = Task(
                task_id=task_id,
                task_type=task_type,
                status=TaskStatus.PENDING,
                params=params
            )
            self.tasks[task_id] = task
            return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          progress: Optional[float] = None, error_message: Optional[str] = None,
                          result: Optional[Dict[str, Any]] = None):
        """更新任务状态"""
        with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task.status = status
                if progress is not None:
                    task.progress = progress
                if error_message is not None:
                    task.error_message = error_message
                if result is not None:
                    task.result = result
                
                if status == TaskStatus.RUNNING and task.start_time is None:
                    task.start_time = time.time()
                elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    task.end_time = time.time()
    
    async def submit_image_generation_task(self, scenes_data: List[Dict[str, Any]]) -> str:
        """提交图片生成任务"""
        task_id = f"images_{int(time.time())}"
        params = {"scenes": scenes_data, "total_scenes": len(scenes_data)}
        
        self.create_task(task_id, TaskType.IMAGE_GENERATION, params)
        
        # 在线程池中异步执行
        loop = asyncio.get_event_loop()
        loop.run_in_executor(self.executor, self._generate_images_worker, task_id, scenes_data)
        
        return task_id
    
    def _generate_images_worker(self, task_id: str, scenes_data: List[Dict[str, Any]]):
        """图片生成工作线程"""
        try:
            self.update_task_status(task_id, TaskStatus.RUNNING, progress=0.0)
            
            total_scenes = len(scenes_data)
            completed = 0
            
            # 确保输出目录存在
            os.makedirs("output/images", exist_ok=True)
            
            for idx, scene in enumerate(scenes_data):
                try:
                    # 生成单个场景图片
                    generate_image(
                        prompt_text=scene["sd_prompt"],
                        save_path=f"output/images/scene_{idx}.png",
                    )
                    completed += 1
                    progress = (completed / total_scenes) * 100
                    self.update_task_status(task_id, TaskStatus.RUNNING, progress=progress)
                    
                except Exception as e:
                    error_msg = f"生成场景 {idx} 图片失败: {str(e)}"
                    self.update_task_status(task_id, TaskStatus.FAILED, error_message=error_msg)
                    return
            
            # 所有图片生成完成
            result = {
                "total_images": total_scenes,
                "completed_images": completed,
                "output_directory": "output/images"
            }
            self.update_task_status(task_id, TaskStatus.COMPLETED, progress=100.0, result=result)
            
        except Exception as e:
            self.update_task_status(task_id, TaskStatus.FAILED, error_message=str(e))
    
    async def submit_video_composition_task(self) -> str:
        """提交视频合成任务"""
        task_id = f"video_{int(time.time())}"
        params = {"output_path": "output/final_video.mp4"}
        
        self.create_task(task_id, TaskType.VIDEO_COMPOSITION, params)
        
        # 在线程池中异步执行
        loop = asyncio.get_event_loop()
        loop.run_in_executor(self.executor, self._generate_video_worker, task_id)
        
        return task_id
    
    def _generate_video_worker(self, task_id: str):
        """视频合成工作线程"""
        try:
            self.update_task_status(task_id, TaskStatus.RUNNING, progress=0.0)
            
            # 调用视频生成函数
            result_message = sync_generate_video()
            
            if "✅" in result_message:
                # 成功
                result = {
                    "output_path": "output/final_video.mp4",
                    "message": result_message
                }
                self.update_task_status(task_id, TaskStatus.COMPLETED, progress=100.0, result=result)
            else:
                # 失败
                self.update_task_status(task_id, TaskStatus.FAILED, error_message=result_message)
                
        except Exception as e:
            self.update_task_status(task_id, TaskStatus.FAILED, error_message=str(e))
    
    def get_all_tasks_status(self) -> List[Dict[str, Any]]:
        """获取所有任务状态"""
        return [task.to_dict() for task in self.tasks.values()]
    
    def cleanup_completed_tasks(self, older_than_hours: int = 24):
        """清理已完成的旧任务"""
        current_time = time.time()
        cutoff_time = current_time - (older_than_hours * 3600)
        
        with self._lock:
            to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and 
                    task.end_time and task.end_time < cutoff_time):
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.tasks[task_id]


# 全局任务管理器实例
task_manager = TaskManager()
