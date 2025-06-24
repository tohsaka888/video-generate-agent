# 🎬 Video Generate Agent

AI驱动的“小说到视频”自动生成系统，支持从大纲到分镜、图片、音频、字幕、视频一站式生成。适合AI内容创作、短视频自动化、小说可视化等场景。

---

## 🚀 主要特性
- **一键生成**：输入大纲，自动生成多章节、多场景的完整视频
- **分镜可控**：每章场景数可自定义（5-50）
- **多模态输出**：自动生成分镜脚本、图片、配音、字幕、视频
- **命令行/代码双入口**：支持CLI批量生成，也可作为Python包调用
- **可扩展**：各环节均为独立Agent，便于二次开发

---

## 🛠️ 安装与环境
- Python 3.13+
- 推荐使用 [uv](https://github.com/astral-sh/uv) 包管理器

```bash
# 克隆仓库
git clone <your-repo-url>
cd video-generate-agent

# 安装依赖
uv sync
```

如需自定义API密钥、字体、图片生成服务等，请配置 `.env` 文件。

---

## ⚡ 快速开始

### 1. 命令行批量生成

```bash
python main_cli.py --scene-count 10 --start-chapter 1 --end-chapter 3 --outline-file my_outline.txt
```

- 支持参数：`--scene-count`、`--start-chapter`、`--end-chapter`、`--outline-file`、`--config`
- 也可用 `--config` 加载Python格式的批量配置

### 2. 代码调用

```python
from agents.main_agent import start_video_generation

result = await start_video_generation(
    outline="你的故事大纲...",
    start_chapter=1,
    end_chapter=2,
    scene_count=10,
    requirement="剧情要有爽感和逆袭元素"
)
print(result)
```

---

## 📁 目录结构

```
video-generate-agent/
├── main.py              # 交互式入口示例
├── main_cli.py          # 命令行入口，支持批量参数
├── agents/              # 各环节AI Agent
│   ├── main_agent.py    # 总控Agent，编排全流程
│   ├── novel_agent.py   # 小说章节生成
│   ├── scene_agent.py   # 分镜+图片+音频一体化生成
│   └── ...
├── utils/               # 工具模块
│   ├── video.py         # 视频合成
│   ├── comfyui.py       # 图片生成（支持ComfyUI）
│   └── ...
├── assets/              # 字体、workflow等资源
├── output/              # 生成结果（按章节组织）
├── example/             # 示例大纲与生成样例
└── pyproject.toml       # 依赖声明
```

---

## ⚙️ 高级用法与自定义
- **分镜数量**：`--scene-count` 或 `SceneAgentDeps.scene_count` 参数控制
- **图片生成**：支持自定义ComfyUI服务，详见 `utils/comfyui.py`
- **字体/样式**：可通过 `.env` 配置 `FONT_PATH`
- **批量生成**：支持多章节、批量大纲、配置文件
- **自定义大纲/风格**：直接修改大纲文本或传入 requirement

---

## ❓ 常见问题
- 依赖安装失败：建议用 `uv sync`，如需加速可用清华镜像
- 图片/音频生成失败：检查API密钥、服务可用性、网络
- 视频合成报错：确认图片、音频、字幕数量一致

---

## 🤝 贡献
欢迎PR、Issue和建议！如需自定义Agent或扩展新功能，建议参考 `agents/` 和 `utils/` 目录实现。

---

## 📄 License
MIT

---

> 本项目致力于让AI为你的故事创作赋能，自动生成高质量多模态内容！
