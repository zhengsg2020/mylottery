"""数据持久化模块"""
import json
import os
from .config import DATA_FILE, TEST_DATA_FILE


def load_all_data():
    """加载所有数据（正式购买）"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                purchased = data.get("purchased", [])
                winnings = data.get("winnings", {"ssq": [], "dlt": []})
                return purchased, winnings
        except Exception:
            pass
    return [], {"ssq": [], "dlt": []}


def save_all_data(purchased, winnings):
    """保存所有数据（正式购买）"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"purchased": purchased, "winnings": winnings},
            f,
            ensure_ascii=False,
            indent=4,
        )


def load_test_data():
    """加载测试数据"""
    if os.path.exists(TEST_DATA_FILE):
        try:
            with open(TEST_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("purchased", [])
        except Exception:
            pass
    return []


def save_test_data(purchased):
    """保存测试数据"""
    with open(TEST_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"purchased": purchased},
            f,
            ensure_ascii=False,
            indent=4,
        )
