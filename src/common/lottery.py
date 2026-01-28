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


def _init_weight_dict(max_number: int):
    """初始化 1..max_number 的权重字典"""
    return {i: 1 for i in range(1, max_number + 1)}


def _count_history_nums(winnings, l_type, history_count: int = 100):
    """统计最近 N 期开奖中每个号码出现次数"""
    history = winnings.get(l_type, [])[:history_count]
    if l_type == "ssq":
        red_weights = _init_weight_dict(33)
        blue_weights = _init_weight_dict(16)
    else:
        red_weights = _init_weight_dict(35)
        blue_weights = _init_weight_dict(12)

    for item in history:
        reds, blues = item["nums"]
        for n in reds:
            if n in red_weights:
                red_weights[n] += 1
        for n in blues:
            if n in blue_weights:
                blue_weights[n] += 1
    return red_weights, blue_weights


def _pick_by_weight(candidates, weights, count):
    """根据权重不放回抽取 count 个不同的号码"""
    pool = list(candidates)
    result = []
    for _ in range(count):
        total = sum(weights[n] for n in pool)
        r = random.uniform(0, total)
        acc = 0.0
        chosen = pool[0]
        for n in pool:
            acc += weights[n]
            if r <= acc:
                chosen = n
                break
        result.append(chosen)
        pool.remove(chosen)
    return sorted(result)


def generate_recommended_nums(winnings, l_type, history_count: int = 100):
    """基于最近 N 期历史的简单“热号/冷号”权重生成一注推荐号码"""
    red_w, blue_w = _count_history_nums(winnings, l_type, history_count=history_count)
    if l_type == "ssq":
        reds = _pick_by_weight(range(1, 34), red_w, 6)
        blues = _pick_by_weight(range(1, 17), blue_w, 1)
    else:
        reds = _pick_by_weight(range(1, 36), red_w, 5)
        blues = _pick_by_weight(range(1, 13), blue_w, 2)
    return [reds, blues]


def _build_ticket(l_type, issue, nums, recommended: bool = False):
    """内部工具：构造一张彩票记录"""
    return {
        "type": l_type,
        "issue": issue,
        "nums": nums,
        "checked": False,
        "time": time.strftime("%Y-%m-%d %H:%M"),
        "prize": "",
        "recommended": recommended,
    }


def generate_ticket(l_type, issue, is_test=False):
    """生成一张随机彩票"""
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

    return _build_ticket(l_type, issue, nums, recommended=False)


def create_ticket_with_nums(l_type, issue, nums, recommended: bool = False):
    """根据指定号码创建一张彩票（供推荐购买使用）"""
    # 简单校验长度，避免脏数据
    if l_type == "ssq":
        if len(nums) != 2 or len(nums[0]) != 6 or len(nums[1]) != 1:
            raise ValueError("非法的双色球号码结构")
    else:
        if len(nums) != 2 or len(nums[0]) != 5 or len(nums[1]) != 2:
            raise ValueError("非法的大乐透号码结构")
    # 规范化排序
    return _build_ticket(
        l_type,
        issue,
        [sorted(nums[0]), sorted(nums[1])],
        recommended=recommended,
    )


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
