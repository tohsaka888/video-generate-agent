# 📚 Video Generate Agent

一个基于AI的小说到视频生成系统，能够自动将小说章节转换为完整的视频内容，包括分镜脚本、图片生成、语音合成和字幕制作。

## ✨ 功能特性

- 🤖 **智能章节生成**: 基于大纲自动生成连贯的小说章节
- 🎬 **自动分镜脚本**: 将章节内容转换为5个精彩的分镜场景
- 🎨 **AI图片生成**: 根据分镜描述生成高质量的动漫风格或写实风格图片
- 🎵 **语音合成**: 使用Edge-TTS生成自然流畅的朗读音频
- 📽️ **字幕制作**: 自动生成时间精准的SRT字幕文件
- 🎞️ **视频合成**: 将图片、音频和字幕合成为完整的视频

## 🛠️ 技术栈

- **AI框架**: PydanticAI + Google GenAI
- **图片生成**: Stable Diffusion
- **语音合成**: Edge-TTS
- **视频处理**: MoviePy
- **音频处理**: Pydub
- **项目管理**: UV包管理器

## 📦 安装

### 前置要求

- Python 3.13+
- UV包管理器

### 快速安装

```bash
# 克隆项目
git clone <your-repo-url>
cd video-generate-agent

# 使用UV安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑.env文件，添加你的API密钥
```

### 环境变量配置

在`.env`文件中配置以下变量：

```env
# Google GenAI API密钥
GOOGLE_API_KEY=your_google_api_key

# 图片生成API配置（根据你使用的服务）
IMAGE_API_KEY=your_image_api_key
IMAGE_API_URL=your_image_api_url

# 代理配置（可选）
HTTP_PROXY=your_proxy_url
HTTPS_PROXY=your_proxy_url
```

## 🚀 使用方法

### 1. 创建小说章节

```python
from agents.novel_agent import novel_agent, NovelAgentDeps

# 定义小说大纲
outline = """
一个关于魔法与科技融合的冒险故事...
"""

# 生成章节内容
deps = NovelAgentDeps(outline=outline, current_chapter=1)
result = novel_agent.run("请生成第一章的内容", deps=deps)
```

### 2. 生成分镜脚本

```python
from agents.scene_agent import scene_agent, SceneAgentDeps

# 根据章节内容生成分镜
deps = SceneAgentDeps(outline=outline, current_chapter=1)
result = scene_agent.run("请为第一章生成分镜脚本", deps=deps)
```

### 3. 生成图片

```python
from agents.image_agent import image_agent, ImageAgentDeps

# 根据分镜生成图片
deps = ImageAgentDeps(current_chapter=1)
result = image_agent.run("请为第一章生成图片", deps=deps)
```

### 4. 生成音频和字幕

```python
from agents.audio_agent import audio_agent, AudioAgentDeps

# 生成音频和字幕
deps = AudioAgentDeps(current_chapter=1)
result = audio_agent.run("请为第一章生成音频", deps=deps)
```

### 5. 合成最终视频

项目会自动将生成的图片、音频和字幕合成为完整的视频文件。

## 📁 项目结构

```
video-generate-agent/
├── agents/                     # AI代理模块
│   ├── novel_agent.py         # 小说章节生成代理
│   ├── scene_agent.py         # 分镜脚本生成代理
│   ├── image_agent.py         # 图片生成代理
│   └── audio_agent.py         # 音频生成代理
├── utils/                      # 工具模块
│   ├── llm.py                 # 大语言模型配置
│   ├── generate_img.py        # 图片生成工具
│   ├── video.py               # 视频处理工具
│   └── mcp.py                 # MCP协议配置
├── output/                     # 输出目录
│   └── chapters/              # 按章节组织的输出文件
│       └── chapter_1/
│           ├── index.txt      # 章节内容
│           ├── scenes/        # 分镜文件
│           ├── scripts/       # 脚本文件
│           ├── images/        # 生成的图片
│           ├── audio/         # 音频文件
│           ├── srt/          # 字幕文件
│           └── generated_video.mp4  # 最终视频
├── example/                    # 示例输出
└── tests/                      # 测试文件
```

## 🎬 示例展示

我们为您准备了一个完整的示例，展示了从小说大纲到最终视频的完整生成流程：

### 📖 示例章节：命运的召唤

> 一个关于年轻女巫艾莉丝在魔法与科技交织的世界中寻找传说神器的冒险故事。

**故事梗概**: 艾莉丝·月影是暮光之森的年轻女巫，她渴望探索魔法与科技融合的可能性。当她从古籍中得知失落的"星辰之杖"后，决定踏上寻找这件神器的冒险之旅。

### 🎞️ 生成的视频

**完整视频展示**:

https://github.com/user-attachments/assets/your-video-asset-id

*👆 点击查看完整的AI生成视频*

### 🎨 分镜场景展示

我们为第一章生成了5个精美的分镜场景：

#### 场景1: 夕阳下的决心
![场景1](example/chapter_1/images/scene_1.png)
*艾莉丝站在小屋前眺望远方，夕阳将天空染成橙红色*

#### 场景2: 祖孙对话
![场景2](example/chapter_1/images/scene_2.png)
*祖母与艾莉丝的深度对话，传达智慧与关爱*

#### 场景3: 古籍的秘密
![场景3](example/chapter_1/images/scene_3.png)
*艾莉丝在图书馆中发现记载星辰之杖的古籍*

#### 场景4: 星辰之杖的传说
![场景4](example/chapter_1/images/scene_4.png)
*传说中的星辰之杖，散发着神秘的光芒*

#### 场景5: 踏上冒险之路
![场景5](example/chapter_1/images/scene_5.png)
*艾莉丝背起行囊，准备踏上寻找神器的冒险旅程*

### 🎵 音频特性

- **自然语音**: 使用Edge-TTS生成流畅自然的中文朗读
- **情感表达**: 根据情节内容调整语调和节奏
- **精准字幕**: 自动生成时间同步的SRT字幕文件

### 📊 生成统计

- **章节长度**: 约1000字
- **分镜数量**: 5个场景
- **音频时长**: 约3-5分钟
- **图片分辨率**: 1024x1024
- **视频格式**: MP4 (1080p)

## 🔧 高级配置

### 自定义分镜数量

在`scene_agent.py`中修改分镜数量：

```python
# 默认生成5个镜头，可以修改为其他数量
system_instruction = f"""
...
- 共生成5个镜头，每个镜头需详细描述...
...
"""
```

### 调整图片风格

在分镜生成时指定图片风格：

```python
# 在scene描述中指定风格
风格：动漫风  # 或 写实风
```

### 自定义语音配置

在`audio_agent.py`中修改语音参数：

```python
# 可选的语音类型
voices = [
    "zh-CN-XiaoxiaoNeural",  # 女声
    "zh-CN-YunxiNeural",     # 男声
    "zh-CN-YunyangNeural"    # 其他音色
]
```

## 🐛 故障排除

### 常见问题

1. **API密钥错误**
   ```bash
   # 检查环境变量是否正确设置
   echo $GOOGLE_API_KEY
   ```

2. **依赖安装失败**
   ```bash
   # 使用清华镜像加速
   uv sync --index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple
   ```

3. **图片生成失败**
   - 检查图片生成API配置
   - 确认网络连接正常
   - 验证API额度充足

4. **音频生成问题**
   ```bash
   # 检查edge-tts是否正常工作
   edge-tts --list-voices | grep zh-CN
   ```

### 性能优化

- **并行处理**: 可以并行生成多个分镜的图片
- **缓存机制**: 避免重复生成相同内容
- **批量处理**: 一次性处理多个章节

## 🤝 贡献指南

我们欢迎所有形式的贡献！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发环境设置

```bash
# 安装开发依赖
uv add --dev pytest black isort mypy

# 运行测试
uv run pytest

# 代码格式化
uv run black .
uv run isort .
```

## 📝 更新日志

### v0.1.0 (2025-06-16)

- ✨ 初始版本发布
- 🤖 实现基础的AI代理架构
- 🎬 支持小说到视频的完整流程
- 🎨 集成图片生成功能
- 🎵 集成语音合成和字幕生成
- 📽️ 实现视频合成功能

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [PydanticAI](https://github.com/pydantic/pydantic-ai) - 强大的AI代理框架
- [Edge-TTS](https://github.com/rany2/edge-tts) - 优秀的语音合成工具
- [MoviePy](https://github.com/Zulko/moviepy) - 强大的视频处理库
- [Google GenAI](https://ai.google.dev/) - 先进的大语言模型

⭐ 如果这个项目对您有帮助，请给我们一个星标！

🎬 **让AI为您的创意故事注入生命力！**
