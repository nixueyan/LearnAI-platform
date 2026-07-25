import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "")

# ⚠️ 真实密钥只应放在项目根目录的 .env 文件里（已被 .gitignore 忽略，不会进仓库）。
# 以下默认值为空字符串：若 .env 未配置，代码会进入“未配置”的模拟模式，
# 而不是偷偷使用别人/仓库里的硬编码密钥。
XUNFEI_APP_ID = os.getenv("XUNFEI_APP_ID", "")
XUNFEI_API_KEY = os.getenv("XUNFEI_API_KEY", "")
XUNFEI_API_SECRET = os.getenv("XUNFEI_API_SECRET", "")
XUNFEI_API_URL = os.getenv("XUNFEI_API_URL", "https://spark-api-open.xf-yun.com/v1/chat/completions")

DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER", "xunfei")
