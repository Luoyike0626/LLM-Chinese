"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# API configuration (SiliconFlow - OpenAI compatible)
API_KEY = os.getenv("SILICONFLOW_API_KEY")
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

# Council members - SiliconFlow model identifiers
# Browse all available models: https://siliconflow.cn/models
COUNCIL_MODELS = [
    "deepseek-ai/DeepSeek-V3",       # DeepSeek 综合旗舰
    "deepseek-ai/DeepSeek-R1",       # DeepSeek 推理特化
    "Qwen/Qwen3.5-397B-A17B",        # 通义千问3.5 超大规模 MoE
    "Pro/zai-org/GLM-5.1",           # 智谱 GLM-5.1 最新旗舰
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "deepseek-ai/DeepSeek-R1"

# Title generation model (cheap/fast, free on SiliconFlow)
TITLE_MODEL = "Qwen/Qwen2.5-7B-Instruct"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
