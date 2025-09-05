# 导入OpenAI模型和提供者类
import httpx
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

# 导入环境变量相关库
import os
from dotenv import load_dotenv

# 从.env文件加载环境变量
load_dotenv()

# 获取必要的环境变量
CHAT_MODEL = os.getenv("CHAT_MODEL")  # 模型名称
CHAT_MODEL_KEY = os.getenv("CHAT_MODEL_KEY")  # API密钥
CHAT_BASE_URL = os.getenv("CHAT_BASE_URL")  # API基础URL

# 检查必需环境变量是否设置
if CHAT_MODEL is None:
    raise ValueError("CHAT_MODEL environment variable is not set")
if CHAT_MODEL_KEY is None:
    raise ValueError("CHAT_MODEL_KEY environment variable is not set")

# 初始化OpenAI提供者
provider = OpenAIProvider(
    base_url=CHAT_BASE_URL,  # API基础URL
    api_key=CHAT_MODEL_KEY,  # API密钥,
    http_client=httpx.AsyncClient(proxy='http://genova:genova@127.0.0.1:7897')
)

# 创建OpenAI模型实例
chat_model = OpenAIChatModel(
    model_name=CHAT_MODEL,  # 模型名称
    provider=provider,  # 提供者实例
)

