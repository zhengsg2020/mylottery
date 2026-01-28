"""彩票业务逻辑模块"""
import random
import time


# 假设每期奖池为 1 亿，下面的金额只是演示用的固定奖级金额，
# 并不等同于真实彩票的官方奖金规则。
SSQ_PRIZE_AMOUNT = {
    "★一等奖(一千万)★": 10_000_000,
    "二等奖": 5_000_000,
    "三等奖": 3_000_000,
    "四等奖": 30_000,
    "五等奖": 3_000,
    "六等奖(5元)": 5,
}

DLT_PRIZE_AMOUNT = {
    "★一等奖(一千万)★": 10_000_000,
    "二等奖": 5_000_000,
    "三等奖": 3_000_000,
    "四等奖": 100_000,
    "五等奖": 50_000,
    "六等奖": 10_000,
    "七等奖": 5_000,
    "八等奖": 1_000,
    "九等奖(5元)": 5,
}


def calculate_prize(l_type, r, b):
    """计算奖项"""
    if l_type == "ssq":
        if r == 6 and b == 1:
            return "★一等奖(一千万)★"
        if r == 6:
            return "二等奖"
        if r == 5 and b == 1:
            return "三等奖"
        if r == 5 or (r == 4 and b == 1):
            return "四等奖"
        if r == 4 or (r == 3 and b == 1):
            return "五等奖"
        if b == 1:
            return "六等奖(5元)"
    else:  # dlt
        if r == 5 and b == 2:
            return "★一等奖(一千万)★"
        if r == 5 and b == 1:
            return "二等奖"
        if r == 5:
            return "三等奖"
        if r == 4 and b == 2:
            return "四等奖"
        if r == 4 and b == 1:
            return "五等奖"
        if r == 3 and b == 2:
            return "六等奖"
        if r == 4:
            return "七等奖"
        if (r == 3 and b == 1) or (r == 2 and b == 2):
            return "八等奖"
        if r == 3 or (r == 1 and b == 2) or (r == 2 and b == 1) or b == 2:
            return "九等奖(5元)"
    return "未中奖"


def get_prize_amount(prize: str) -> int:
    """根据奖项名称返回假设的奖金金额（单位：元）"""
    if not prize or prize == "未中奖":
        return 0
    if prize in SSQ_PRIZE_AMOUNT:
        return SSQ_PRIZE_AMOUNT[prize]
    if prize in DLT_PRIZE_AMOUNT:
        return DLT_PRIZE_AMOUNT[prize]
    # 兜底：如果未来新增文案但没配置金额，则视为 0 元
    return 0


def get_next_issue(winnings, l_type):
    """计算下一期期号"""
    if not winnings[l_type]:
        return "2024001"
    latest = int(winnings[l_type][0]["issue"])
    return str(latest + 1)


def generate_ticket(l_type, issue, is_test=False):
    """生成一张彩票"""
    if l_type == "ssq":
        nums = [
            sorted(random.sample(range(1, 34), 6)),
            [random.randint(1, 16)],
        ]
    else:  # dlt
        nums = [
            sorted(random.sample(range(1, 36), 5)),
            sorted(random.sample(range(1, 13), 2)),
        ]

    return {
        "type": l_type,
        "issue": issue,
        "nums": nums,
        "checked": False,
        "time": time.strftime("%Y-%m-%d %H:%M"),
        "prize": "",
    }


def check_ticket(ticket, winnings):
    """检查单张彩票是否中奖"""
    win = next(
        (
            w
            for w in winnings.get(ticket["type"], [])
            if w["issue"] == ticket["issue"]
        ),
        None,
    )
    if not win:
        return None

    my_red, my_blue = ticket["nums"]
    win_red, win_blue = win["nums"]
    hits_r = len(set(my_red) & set(win_red))
    hits_b = len(set(my_blue) & set(win_blue))
    prize = calculate_prize(ticket["type"], hits_r, hits_b)

    return {
        "hits_red": hits_r,
        "hits_blue": hits_b,
        "prize": prize,
        "winning_nums": win["nums"],
    }
