# 导入日志监控库logfire
import os
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 导入主控制器
from agents.main_agent import AgentState, main_agent
from pydantic_ai.ag_ui import StateDeps
from utils.output_tree import build_output_tree

app = FastAPI()

# 创建cache
cache_dir = Path(".cache")
cache_dir.mkdir(exist_ok=True)

os.makedirs("output/images", exist_ok=True)
os.makedirs("output/audio", exist_ok=True)


# 允许跨域，便于前端轮询
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 可按需收紧到具体域名，例如: ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/output-tree")
def get_output_tree() -> Dict[str, Any]:
    """返回 output 目录当前快照（树结构）。前端可每秒轮询一次。"""
    base = Path("output").resolve()
    return build_output_tree(base)


# 兼容路径：与前端 Next 原接口名一致
@app.get("/api/file-tree")
def get_file_tree() -> Dict[str, Any]:
    return get_output_tree()


app.mount("/agent", main_agent.to_ag_ui(deps=StateDeps(AgentState())))

if __name__ == "__main__":
    uvicorn.run('main:app', host="0.0.0.0", port=8000, log_level="info", workers=8)
