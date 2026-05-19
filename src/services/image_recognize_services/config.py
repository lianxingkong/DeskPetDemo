# 获取配置参数
import os
from pathlib import Path

report_url = os.getenv("BAIDUAI__REPORT_REQUEST_URL")  # 提交任务的 URL
get_result_url = os.getenv("BAIDUAI__GET_RESULT_URL")  # 查询结果的 URL
api_key = os.getenv("BAIDUAI__API_KEY")
secret_key = os.getenv("BAIDUAI__SECRET_KEY")
token_url = os.getenv("BAIDUAI___TOKEN_URL")

# 1. 先定义目录
save_dir = Path("/")
# 2. 自动创建目录
save_dir.mkdir(parents=True, exist_ok=True)