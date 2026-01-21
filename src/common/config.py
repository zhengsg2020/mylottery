"""配置文件"""
import os

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DATA_FILE = os.path.join(DATA_DIR, "lottery_data.json")
TEST_DATA_FILE = os.path.join(DATA_DIR, "lottery_test_data.json")  # 测试数据单独存储

# 资源路径（当前版本统一使用 assets/img 与 static/img）
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "img")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static", "img")

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
