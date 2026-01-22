"""配置文件"""
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# 数据文件路径（运行时生成，不建议提交到 Git）
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DATA_FILE = os.path.join(DATA_DIR, "lottery_data.json")
TEST_DATA_FILE = os.path.join(DATA_DIR, "lottery_test_data.json")  # 测试数据单独存储

# 资源路径：统一使用 static/img，Web 与 Desktop 共用同一份图片资源
ASSETS_DIR = os.path.join(PROJECT_ROOT, "static", "img")

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
