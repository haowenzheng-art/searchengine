"""配置模块 - 加载环境变量和API配置"""
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 火山引擎 API 配置
VOLCENGINE_API_KEY = os.getenv("VOLCENGINE_API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://apihub.agnes-ai.com/v1")
MODEL = os.getenv("MODEL_NAME", "ark-code-latest")

# 搜索配置
DEFAULT_SEARCH_KEYWORD = "企业业务流程步骤"
SEARCH_NUM_RESULTS = 15
MAX_CONTENT_LENGTH = 5000

# 文件路径
RESULTS_FILE = "results.json"
FINAL_OUTPUT_FILE = "final_output.json"
