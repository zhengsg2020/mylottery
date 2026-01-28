"""网页版应用（Flask）"""
import os
import sys
import re
from datetime import datetime

from flask import Flask, flash, redirect, render_template_string, request, url_for

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.common import config, data, fetcher, lottery

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "..", "..", "static"))
app.secret_key = "dev-secret"  # 如需部署可替换为更安全的值


def _env_bool(name: str, default: bool = True) -> bool:
    """从环境变量读取布尔值"""
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() not in {"0", "false", "no", "off"}


WEB_FEATURES = {
    "enable_update": _env_bool("LOTTERY_WEB_ENABLE_UPDATE", True),
    "enable_buy": _env_bool("LOTTERY_WEB_ENABLE_BUY", True),
    "enable_check": _env_bool("LOTTERY_WEB_ENABLE_CHECK", True),
}


def get_prize_color_class(prize):
    """根据奖项返回CSS类名"""
    if not prize or prize == "未中奖":
        return "prize-none"
    if "一等奖" in prize:
        return "prize-jackpot"
    if "二等奖" in prize or "三等奖" in prize:
        return "prize-high"
    if "四等奖" in prize or "五等奖" in prize:
        return "prize-mid"
    return "prize-low"


@app.template_filter("fmt_num")
def fmt_num(n):
    """格式化数字为两位"""
    try:
        return f"{int(n):02d}"
    except Exception:
        return str(n)


@app.template_filter("prize_class")
def prize_class(prize):
    """返回奖项对应的CSS类"""
    return get_prize_color_class(prize)


@app.template_filter("fmt_money")
def fmt_money(amount):
    """格式化金额：带千分位的整数"""
    try:
        return f"{int(amount):,}"
    except Exception:
        return str(amount)


@app.template_filter("prize_amount")
def prize_amount(prize):
    """根据奖项名称返回对应的奖金金额（元）"""
    return lottery.get_prize_amount(prize)


@app.route("/", methods=["GET"])
def index():
    """首页"""
    purchased, winnings = data.load_all_data()
    test_tickets = data.load_test_data()
    # 正式购买的中奖票据
    formal_winning_tickets = [t for t in purchased if t.get("checked") and t.get("prize") and t.get("prize") != "未中奖"]
    
    # 按期号分组正式中奖票据
    formal_wins_by_issue = {}
    for t in formal_winning_tickets:
        key = f"{t['type']}_{t['issue']}"
        if key not in formal_wins_by_issue:
            win_info = next((w for w in winnings.get(t['type'], []) if w['issue'] == t['issue']), None)
            formal_wins_by_issue[key] = {
                "type": t['type'],
                "issue": t['issue'],
                "win_nums": win_info['nums'] if win_info else None,
                "tickets": []
            }
        formal_wins_by_issue[key]["tickets"].append(t)
    
    # 排序键（按期号倒序）
    sorted_issue_keys = sorted(formal_wins_by_issue.keys(), key=lambda k: formal_wins_by_issue[k]['issue'], reverse=True)

    # 测试购买的中奖票据（分开显示）
    test_winning_tickets = [t for t in test_tickets if t.get("checked") and t.get("prize") and t.get("prize") != "未中奖"]
    
    # 按期号分组测试中奖票据
    test_wins_by_issue = {}
    for t in test_winning_tickets:
        key = f"{t['type']}_{t['issue']}"
        if key not in test_wins_by_issue:
            win_info = next((w for w in winnings.get(t['type'], []) if w['issue'] == t['issue']), None)
            test_wins_by_issue[key] = {
                "type": t['type'],
                "issue": t['issue'],
                "win_nums": win_info['nums'] if win_info else None,
                "tickets": []
            }
        test_wins_by_issue[key]["tickets"].append(t)
    
    sorted_test_issue_keys = sorted(test_wins_by_issue.keys(), key=lambda k: test_wins_by_issue[k]['issue'], reverse=True)

    # 获取所有购买记录的期号
    ssq_issues = sorted(list(set(t['issue'] for t in purchased if t['type'] == 'ssq')), reverse=True)
    dlt_issues = sorted(list(set(t['issue'] for t in purchased if t['type'] == 'dlt')), reverse=True)

    # === 账户投注 / 中奖统计（仅统计正式购买） ===
    total_bet = len(purchased) * 2  # 每注 2 元
    total_win = sum(lottery.get_prize_amount(t.get("prize")) for t in purchased)
    net_profit = total_win - total_bet

    # === 我的彩票记录：按期号分页 ===
    # 默认展示「最近且已经有开奖数据的一期」，如果找不到就用最新一期
    def _default_page_for_type(issues, l_type):
        if not issues:
            return 1
        opened_issues = {w["issue"] for w in winnings.get(l_type, [])}
        for idx, iss in enumerate(issues, start=1):
            if iss in opened_issues:
                return idx
        return 1

    def _get_issue_page(issues, param_name, l_type):
        """根据 URL 参数按期号分页，每一页对应一个期号"""
        if not issues:
            return None, 1, 0
        raw = request.args.get(param_name)
        if raw is None:
            page = _default_page_for_type(issues, l_type)
        else:
            try:
                page = int(raw)
            except Exception:
                page = 1
        total = len(issues)
        if page < 1:
            page = 1
        if page > total:
            page = total
        return issues[page - 1], page, total

    # 双色球分页
    ssq_current_issue, ssq_page, ssq_total = _get_issue_page(ssq_issues, "ssq_page", "ssq")
    ssq_current_tickets = [
        t for t in purchased if t["type"] == "ssq" and t["issue"] == ssq_current_issue
    ] if ssq_current_issue else []
    ssq_current_win = next(
        (w for w in winnings.get("ssq", []) if w["issue"] == ssq_current_issue),
        None,
    ) if ssq_current_issue else None

    # 大乐透分页
    dlt_current_issue, dlt_page, dlt_total = _get_issue_page(dlt_issues, "dlt_page", "dlt")
    dlt_current_tickets = [
        t for t in purchased if t["type"] == "dlt" and t["issue"] == dlt_current_issue
    ] if dlt_current_issue else []
    dlt_current_win = next(
        (w for w in winnings.get("dlt", []) if w["issue"] == dlt_current_issue),
        None,
    ) if dlt_current_issue else None

    # 准备开奖号码映射 { 'ssq_issue': [nums], ... }
    issue_win_map = {}
    for w in winnings.get('ssq', []):
        issue_win_map[f"ssq_{w['issue']}"] = w['nums']
    for w in winnings.get('dlt', []):
        issue_win_map[f"dlt_{w['issue']}"] = w['nums']

    # 智能推荐：根据 query 参数决定是否生成推荐号码
    analyze_type = request.args.get("analyze_type")
    recommendations = None
    if analyze_type in {"ssq", "dlt"} and winnings.get(analyze_type):
        try:
            target_issue = lottery.get_next_issue(winnings, analyze_type)
            rec_items = []
            for i in range(10):
                nums = lottery.generate_recommended_nums(winnings, analyze_type, history_count=100)
                rec_items.append({"index": i, "nums": nums})
            recommendations = {
                "type": analyze_type,
                "issue": target_issue,
                "items": rec_items,
            }
        except Exception:
            recommendations = None

    # 准备可购买的期号列表
    # real: 下一期 + 未来9期 (共10期)
    # test: 下一期 + 最近9期
    buy_options = {"ssq": {"real": [], "test": []}, "dlt": {"real": [], "test": []}}
    for l_type in ["ssq", "dlt"]:
        next_iss = lottery.get_next_issue(winnings, l_type)
        
        # Real: Future 10 issues
        try:
            current_int = int(next_iss)
            for i in range(10):
                future_iss = str(current_int + i)
                label_text = f"下一期 ({future_iss})" if i == 0 else f"未来第 {i+1} 期 ({future_iss})"
                buy_options[l_type]["real"].append({"value": future_iss, "label": label_text})
        except:
             # Fallback if issue is not int
             buy_options[l_type]["real"].append({"value": next_iss, "label": f"下一期 ({next_iss})"})
        
        # Test: Next + History
        buy_options[l_type]["test"].append({"value": next_iss, "label": f"下一期 ({next_iss})"})
        history = winnings.get(l_type, [])
        for i in range(min(len(history), 9)):
            iss = history[i]["issue"]
            buy_options[l_type]["test"].append({"value": iss, "label": f"第 {iss} 期"})

    return render_template_string(
        TEMPLATE,
        purchased=purchased,
        test_tickets=test_tickets,
        formal_winning_tickets=formal_winning_tickets,
        formal_wins_by_issue=formal_wins_by_issue,
        sorted_issue_keys=sorted_issue_keys,
        test_winning_tickets=test_winning_tickets,
        test_wins_by_issue=test_wins_by_issue,
        sorted_test_issue_keys=sorted_test_issue_keys,
        winnings=winnings,
        ssq_issues=ssq_issues,
        dlt_issues=dlt_issues,
        ssq_current_issue=ssq_current_issue,
        dlt_current_issue=dlt_current_issue,
        ssq_current_tickets=ssq_current_tickets,
        dlt_current_tickets=dlt_current_tickets,
        ssq_current_win=ssq_current_win,
        dlt_current_win=dlt_current_win,
        ssq_pagination={"current": ssq_page, "total": ssq_total},
        dlt_pagination={"current": dlt_page, "total": dlt_total},
        recommendations=recommendations,
        issue_win_map=issue_win_map,
        buy_options=buy_options,
        features=WEB_FEATURES,
        total_bet=total_bet,
        total_win=total_win,
        net_profit=net_profit,
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


@app.post("/update")
def update():
    """更新开奖数据"""
    if not WEB_FEATURES["enable_update"]:
        flash("该功能在网页版已被管理员关闭。", "warning")
        return redirect(url_for("index"))
    purchased, winnings = data.load_all_data()
    try:
        for l_type in ["ssq", "dlt"]:
            existing = winnings.get(l_type) or []
            if not existing:
                # 本地无数据：一次性拉取最近 1000 期
                winnings[l_type] = fetcher.fetch_500_data(l_type, limit=1000)
                continue

            latest_local = existing[0]["issue"]
            remote = fetcher.fetch_500_data(l_type, limit=200)
            if not remote:
                continue

            # 已经最新则不更新
            if remote[0]["issue"] == latest_local:
                continue

            # 找到本地最新期号在远端中的位置
            idx = next((i for i, r in enumerate(remote) if r["issue"] == latest_local), None)
            if idx is None:
                # 太久没更新，合并去重，最多保留 1000 期
                merged = []
                seen = set()
                for item in remote + existing:
                    if item["issue"] in seen:
                        continue
                    seen.add(item["issue"])
                    merged.append(item)
                    if len(merged) >= 1000:
                        break
                winnings[l_type] = merged
            else:
                new_items = remote[:idx]
                if new_items:
                    winnings[l_type] = new_items + existing

        data.save_all_data(purchased, winnings)
        flash(
            f"更新成功！最新期：SSQ-{winnings['ssq'][0]['issue']} | DLT-{winnings['dlt'][0]['issue']}",
            "success",
        )
    except Exception as e:
        flash(f"更新失败: {e}", "error")
    return redirect(url_for("index"))


@app.post("/buy")
def buy():
    """购买彩票"""
    if not WEB_FEATURES["enable_buy"]:
        flash("该功能在网页版已被管理员关闭。", "warning")
        return redirect(url_for("index"))
    l_type = request.form.get("type")
    count = request.form.get("count", "1")
    is_test = request.form.get("mode") == "test"

    purchased, winnings = data.load_all_data()
    try:
        n = max(1, int(count))  # 移除上限限制
    except Exception:
        flash("请输入有效的注数（至少1注）", "error")
        return redirect(url_for("index"))

    if not winnings.get(l_type):
        flash("请先联网更新获取期号信息", "warning")
        return redirect(url_for("index"))

    # 获取用户选择的期号，如果未提供则使用默认逻辑
    selected_issue = request.form.get("issue")
    if selected_issue:
        issue = selected_issue
    else:
        issue = (
            winnings[l_type][0]["issue"]
            if is_test
            else lottery.get_next_issue(winnings, l_type)
        )
    
    new_tickets = []
    for _ in range(n):
        ticket = lottery.generate_ticket(l_type, issue, is_test)
        new_tickets.append(ticket)

    if is_test:
        # 测试购买写入测试文件
        test_tickets = data.load_test_data()
        test_tickets.extend(new_tickets)
        data.save_test_data(test_tickets)
        mode_str = "测试(不保存)"
    else:
        # 正式购买写入正式文件
        purchased.extend(new_tickets)
        data.save_all_data(purchased, winnings)
        
        # 判断是下一期还是未来期
        try:
            next_iss = lottery.get_next_issue(winnings, l_type)
            if issue == next_iss:
                mode_str = "下一期"
            elif int(issue) > int(next_iss):
                diff = int(issue) - int(next_iss)
                mode_str = f"未来第{diff+1}期"
            else:
                mode_str = "往期补购"
        except:
            mode_str = "正式购买"

    flash(
        f"成功购买 {n} 注 {'双色球' if l_type=='ssq' else '大乐透'} [{issue}] ({mode_str})",
        "success",
    )
    return redirect(url_for("index"))


@app.post("/buy_recommend")
def buy_recommend():
    """购买智能推荐的号码（正式购买，带推荐标记）"""
    if not WEB_FEATURES["enable_buy"]:
        flash("该功能在网页版已被管理员关闭。", "warning")
        return redirect(url_for("index"))

    l_type = request.form.get("type")
    issue = request.form.get("issue")
    chosen = request.form.getlist("choose")

    if not l_type or l_type not in {"ssq", "dlt"}:
        flash("无效的彩种类型。", "error")
        return redirect(url_for("index"))

    if not chosen:
        flash("请至少选择一组推荐号码。", "warning")
        return redirect(url_for("index", analyze_type=l_type) + "#recommend")

    purchased, winnings = data.load_all_data()
    if not winnings.get(l_type):
        flash("请先联网更新获取开奖数据。", "warning")
        return redirect(url_for("index"))

    # 如果未提供期号，则默认使用下一期
    if not issue:
        issue = lottery.get_next_issue(winnings, l_type)

    new_tickets = []
    for idx in chosen:
        line = request.form.get(f"nums_{idx}")
        if not line:
            continue
        try:
            parts = [p.strip() for p in line.split("|")]
            reds = [int(x) for x in parts[0].split()]
            blues = [int(x) for x in parts[1].split()] if len(parts) > 1 else []
            nums = [reds, blues]
            ticket = lottery.create_ticket_with_nums(
                l_type, issue, nums, recommended=True
            )
            new_tickets.append(ticket)
        except Exception:
            continue

    if not new_tickets:
        flash("解析推荐号码失败，未生成任何有效注数。", "error")
        return redirect(url_for("index", analyze_type=l_type) + "#recommend")

    purchased.extend(new_tickets)
    data.save_all_data(purchased, winnings)

    flash(
        f"已根据智能推荐成功购买 {len(new_tickets)} 注 {'双色球' if l_type=='ssq' else '大乐透'} [第 {issue} 期]（已标记为推荐）",
        "success",
    )
    return redirect(url_for("index") + "#records")


@app.post("/check")
def check():
    """批量兑奖"""
    if not WEB_FEATURES["enable_check"]:
        flash("该功能在网页版已被管理员关闭。", "warning")
        return redirect(url_for("index"))
    purchased, winnings = data.load_all_data()
    test_tickets = data.load_test_data()
    
    un_checked = [t for t in purchased if not t.get("checked")]
    un_checked_test = [t for t in test_tickets if not t.get("checked")]
    
    if not un_checked and not un_checked_test:
        flash("没有待兑奖的票据。", "info")
        return redirect(url_for("index"))

    # 自动更新检查：如果待兑奖票据的期号在本地没有开奖结果，尝试更新一次
    need_update = False
    all_unchecked_tickets = un_checked + un_checked_test
    for t in all_unchecked_tickets:
        l_type = t["type"]
        issue = t["issue"]
        # 检查该期号是否存在于winnings中
        has_result = any(w["issue"] == issue for w in winnings.get(l_type, []))
        if not has_result:
            need_update = True
            break
    
    if need_update and WEB_FEATURES["enable_update"]:
        try:
            # 尝试更新数据
            for l_type in ["ssq", "dlt"]:
                existing = winnings.get(l_type) or []
                if not existing:
                    winnings[l_type] = fetcher.fetch_500_data(l_type, limit=1000)
                    continue

                latest_local = existing[0]["issue"]
                remote = fetcher.fetch_500_data(l_type, limit=200)
                if not remote:
                    continue
                if remote[0]["issue"] == latest_local:
                    continue

                idx = next((i for i, r in enumerate(remote) if r["issue"] == latest_local), None)
                if idx is None:
                    merged = []
                    seen = set()
                    for item in remote + existing:
                        if item["issue"] in seen:
                            continue
                        seen.add(item["issue"])
                        merged.append(item)
                        if len(merged) >= 1000:
                            break
                    winnings[l_type] = merged
                else:
                    new_items = remote[:idx]
                    if new_items:
                        winnings[l_type] = new_items + existing
            # 保存更新后的开奖数据(此时还不保存purchased状态，下面统一保存)
            # 注意：data.save_all_data需要purchased参数，这里暂时不保存，等兑奖完了一起保存
            # 但为了防止check_ticket用到旧数据，我们已经更新了winnings变量
        except Exception:
            pass # 更新失败则忽略，继续用本地数据兑奖

    checked_any = False
    # 检查正式购买的票据
    for ticket in un_checked:
        result = lottery.check_ticket(ticket, winnings)
        if result:
            ticket["checked"] = True
            ticket["prize"] = result["prize"]
            checked_any = True

    # 检查测试购买的票据
    for ticket in un_checked_test:
        result = lottery.check_ticket(ticket, winnings)
        if result:
            ticket["checked"] = True
            ticket["prize"] = result["prize"]
            checked_any = True

    data.save_all_data(purchased, winnings)
    data.save_test_data(test_tickets)
    
    if checked_any:
        flash("兑奖完成，已更新中奖结果。", "success")
    else:
        flash("未找到匹配的开奖结果，可能尚未开奖。", "warning")
    return redirect(url_for("index"))


@app.post("/verify")
def verify():
    """自定义选号验奖"""
    if not WEB_FEATURES["enable_check"]:
        flash("该功能在网页版已被管理员关闭。", "warning")
        return redirect(url_for("index"))
    
    l_type = request.form.get("verify_type")
    issue = request.form.get("verify_issue", "").strip()
    numbers_text = request.form.get("verify_numbers", "").strip()
    
    purchased, winnings = data.load_all_data()
    
    if not winnings.get(l_type):
        flash("请先联网更新获取开奖数据", "warning")
        return redirect(url_for("index"))
    
    if not issue:
        flash("请输入期号", "error")
        return redirect(url_for("index"))
    
    if not numbers_text:
        flash("请输入号码", "error")
        return redirect(url_for("index"))
    
    # 查找对应期号的开奖结果
    win_info = next((w for w in winnings[l_type] if w["issue"] == issue), None)
    if not win_info:
        flash(f"未找到期号 {issue} 的开奖结果", "warning")
        return redirect(url_for("index"))
    
    # 解析输入的号码
    lines = [line.strip() for line in numbers_text.split("\\n") if line.strip()]
    results = []
    
    for line in lines:
        try:
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if l_type == "ssq":
                    if len(parts) != 2:
                        continue
                    reds = [int(x.strip()) for x in parts[0].split() if x.strip()]
                    blue = [int(parts[1].strip())]
                    if len(reds) != 6 or len(blue) != 1:
                        continue
                    nums = [sorted(reds), blue]
                else:  # dlt
                    if len(parts) != 2:
                        continue
                    front = [int(x.strip()) for x in parts[0].split() if x.strip()]
                    back = [int(x.strip()) for x in parts[1].split() if x.strip()]
                    if len(front) != 5 or len(back) != 2:
                        continue
                    nums = [sorted(front), sorted(back)]
            else:
                # 尝试自动识别格式
                all_nums = [int(x.strip()) for x in line.split() if x.strip()]
                if l_type == "ssq":
                    if len(all_nums) != 7:
                        continue
                    nums = [sorted(all_nums[:6]), [all_nums[6]]]
                else:
                    if len(all_nums) != 7:
                        continue
                    nums = [sorted(all_nums[:5]), sorted(all_nums[5:])]
            
            # 检查号码
            ticket = {"type": l_type, "issue": issue, "nums": nums}
            result = lottery.check_ticket(ticket, winnings)
            if result:
                results.append({
                    "nums": nums,
                    "prize": result["prize"],
                    "hits_red": result["hits_red"],
                    "hits_blue": result["hits_blue"],
                })
            else:
                results.append({
                    "nums": nums,
                    "prize": "未中奖",
                    "hits_red": 0,
                    "hits_blue": 0,
                })
        except Exception:
            continue
    
    if not results:
        flash("未能解析任何有效号码，请检查格式", "error")
        return redirect(url_for("index"))
    
    # 将结果存储到session或flash中（简化处理，直接显示在flash中）
    winning_count = sum(1 for r in results if r["prize"] != "未中奖")
    flash(
        f"验奖完成！共检查 {len(results)} 组号码，其中 {winning_count} 组中奖。详情请查看购票记录。",
        "success" if winning_count > 0 else "info",
    )
    
    # 将验奖结果添加到购票记录（标记为临时，不保存）
    # 这里简化处理，直接显示在页面上
    return redirect(url_for("index"))


@app.post("/analyze")
def analyze():
    """分析下期开奖，给出推荐号码"""
    l_type = request.form.get("analyze_type", "dlt")
    if l_type not in {"ssq", "dlt"}:
        l_type = "dlt"

    purchased, winnings = data.load_all_data()
    test_tickets = data.load_test_data()

    if not winnings.get(l_type):
        flash("暂无开奖数据，请先点击“立即更新数据”。", "warning")
        return redirect(url_for("index"))

    # 生成 10 组推荐号码
    recommended_groups = []
    for _ in range(10):
        nums = lottery.generate_recommended_nums(winnings, l_type, history_count=100)
        reds, blues = nums
        recommended_groups.append(
            {
                "nums": nums,
                "red_str": " ".join(f"{n:02d}" for n in reds),
                "blue_str": " ".join(f"{n:02d}" for n in blues),
            }
        )

    # 重新渲染首页，但携带推荐结果（其余逻辑与 index 基本一致）
    # --- 以下逻辑与 index() 中相同，只是多传了 recommended_groups / analyze_type ---

    # 正式购买的中奖票据
    formal_winning_tickets = [t for t in purchased if t.get("checked") and t.get("prize") and t.get("prize") != "未中奖"]
    
    # 按期号分组正式中奖票据
    formal_wins_by_issue = {}
    for t in formal_winning_tickets:
        key = f"{t['type']}_{t['issue']}"
        if key not in formal_wins_by_issue:
            win_info = next((w for w in winnings.get(t['type'], []) if w['issue'] == t['issue']), None)
            formal_wins_by_issue[key] = {
                "type": t['type'],
                "issue": t['issue'],
                "win_nums": win_info['nums'] if win_info else None,
                "tickets": []
            }
        formal_wins_by_issue[key]["tickets"].append(t)
    
    sorted_issue_keys = sorted(formal_wins_by_issue.keys(), key=lambda k: formal_wins_by_issue[k]['issue'], reverse=True)

    # 测试购买的中奖票据（分开显示）
    test_winning_tickets = [t for t in test_tickets if t.get("checked") and t.get("prize") and t.get("prize") != "未中奖"]
    
    test_wins_by_issue = {}
    for t in test_winning_tickets:
        key = f"{t['type']}_{t['issue']}"
        if key not in test_wins_by_issue:
            win_info = next((w for w in winnings.get(t['type'], []) if w['issue'] == t['issue']), None)
            test_wins_by_issue[key] = {
                "type": t['type'],
                "issue": t['issue'],
                "win_nums": win_info['nums'] if win_info else None,
                "tickets": []
            }
        test_wins_by_issue[key]["tickets"].append(t)
    
    sorted_test_issue_keys = sorted(test_wins_by_issue.keys(), key=lambda k: test_wins_by_issue[k]['issue'], reverse=True)

    ssq_issues = sorted(list(set(t['issue'] for t in purchased if t['type'] == 'ssq')), reverse=True)
    dlt_issues = sorted(list(set(t['issue'] for t in purchased if t['type'] == 'dlt')), reverse=True)

    total_bet = len(purchased) * 2
    total_win = sum(lottery.get_prize_amount(t.get("prize")) for t in purchased)
    net_profit = total_win - total_bet

    def _get_issue_page(issues, param_name):
        if not issues:
            return None, 1, 0
        try:
            page = int(request.args.get(param_name, "1"))
        except Exception:
            page = 1
        total = len(issues)
        if page < 1:
            page = 1
        if page > total:
            page = total
        return issues[page - 1], page, total

    ssq_current_issue, ssq_page, ssq_total = _get_issue_page(ssq_issues, "ssq_page")
    ssq_current_tickets = [
        t for t in purchased if t["type"] == "ssq" and t["issue"] == ssq_current_issue
    ] if ssq_current_issue else []
    ssq_current_win = next(
        (w for w in winnings.get("ssq", []) if w["issue"] == ssq_current_issue),
        None,
    ) if ssq_current_issue else None

    dlt_current_issue, dlt_page, dlt_total = _get_issue_page(dlt_issues, "dlt_page")
    dlt_current_tickets = [
        t for t in purchased if t["type"] == "dlt" and t["issue"] == dlt_current_issue
    ] if dlt_current_issue else []
    dlt_current_win = next(
        (w for w in winnings.get("dlt", []) if w["issue"] == dlt_current_issue),
        None,
    ) if dlt_current_issue else None

    issue_win_map = {}
    for w in winnings.get('ssq', []):
        issue_win_map[f"ssq_{w['issue']}"] = w['nums']
    for w in winnings.get('dlt', []):
        issue_win_map[f"dlt_{w['issue']}"] = w['nums']

    buy_options = {"ssq": {"real": [], "test": []}, "dlt": {"real": [], "test": []}}
    for lt in ["ssq", "dlt"]:
        next_iss = lottery.get_next_issue(winnings, lt)
        try:
            current_int = int(next_iss)
            for i in range(10):
                future_iss = str(current_int + i)
                label_text = f"下一期 ({future_iss})" if i == 0 else f"未来第 {i+1} 期 ({future_iss})"
                buy_options[lt]["real"].append({"value": future_iss, "label": label_text})
        except:
            buy_options[lt]["real"].append({"value": next_iss, "label": f"下一期 ({next_iss})"})

        buy_options[lt]["test"].append({"value": next_iss, "label": f"下一期 ({next_iss})"})
        history = winnings.get(lt, [])
        for i in range(min(len(history), 9)):
            iss = history[i]["issue"]
            buy_options[lt]["test"].append({"value": iss, "label": f"第 {iss} 期"})

    return render_template_string(
        TEMPLATE,
        purchased=purchased,
        test_tickets=test_tickets,
        formal_winning_tickets=formal_winning_tickets,
        formal_wins_by_issue=formal_wins_by_issue,
        sorted_issue_keys=sorted_issue_keys,
        test_winning_tickets=test_winning_tickets,
        test_wins_by_issue=test_wins_by_issue,
        sorted_test_issue_keys=sorted_test_issue_keys,
        winnings=winnings,
        ssq_issues=ssq_issues,
        dlt_issues=dlt_issues,
        ssq_current_issue=ssq_current_issue,
        dlt_current_issue=dlt_current_issue,
        ssq_current_tickets=ssq_current_tickets,
        dlt_current_tickets=dlt_current_tickets,
        ssq_current_win=ssq_current_win,
        dlt_current_win=dlt_current_win,
        ssq_pagination={"current": ssq_page, "total": ssq_total},
        dlt_pagination={"current": dlt_page, "total": dlt_total},
        issue_win_map=issue_win_map,
        buy_options=buy_options,
        features=WEB_FEATURES,
        total_bet=total_bet,
        total_win=total_win,
        net_profit=net_profit,
        recommended_groups=recommended_groups,
        analyze_type=l_type,
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


@app.post("/clear_test")
def clear_test():
    """清空测试购买记录（不影响正式购买）"""
    data.save_test_data([])
    flash("测试购买记录已清空。", "success")
    return redirect(url_for("index"))


@app.route("/history")
def history():
    """所有开奖结果页面"""
    purchased, winnings = data.load_all_data()
    return render_template_string(
        HISTORY_TEMPLATE,
        winnings=winnings,
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


# HTML模板
TEMPLATE = """
<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <title>自嗨彩票 - 模拟器</title>
  <style>
    :root {
      --primary: #2f54eb;
      --primary-hover: #597ef7;
      --bg: #f0f2f5;
      --card-bg: #ffffff;
      --text: #1f1f1f;
      --text-secondary: #8c8c8c;
      --border: #f0f0f0;
      --success: #52c41a;
      --error: #ff4d4f;
      --warning: #faad14;
    }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: var(--bg); margin: 0; padding: 0; color: var(--text); }
    
    /* Navbar */
    .navbar { background: var(--primary); color: #fff; height: 56px; display: flex; align-items: center; padding: 0 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
    .logo { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 600; }
    .logo img { width: 28px; height: 28px; }
    .nav-links { margin-left: auto; display: flex; gap: 20px; }
    .nav-links a { color: rgba(255,255,255,0.85); text-decoration: none; font-size: 14px; transition: color 0.3s; }
    .nav-links a:hover { color: #fff; }

    /* Layout */
    .container { max-width: 1200px; margin: 24px auto; padding: 0 16px; display: grid; gap: 24px; grid-template-columns: 300px 1fr; }
    @media (max-width: 800px) { .container { grid-template-columns: 1fr; } }
    
    /* Cards */
    .card { background: var(--card-bg); border-radius: 8px; box-shadow: 0 6px 18px rgba(0,0,0,0.06); padding: 20px; border: 1px solid #f0f0f0; }
    .card-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }
    
    /* Status Section (Left) */
    .status-panel { display: flex; flex-direction: column; gap: 16px; }
    .info-block { background: linear-gradient(135deg,#fafafa,#fefefe); padding: 12px; border-radius: 6px; border: 1px dashed #d9d9d9; }
    .info-label { font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }
    .info-value { font-size: 14px; font-weight: 500; }

    .stat-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; margin-top:12px; }
    .stat-item { background:#fff7e6; border-radius:6px; padding:8px 10px; border:1px solid #ffe7ba; }
    .stat-label { font-size:12px; color:#ad6800; margin-bottom:4px; }
    .stat-value { font-size:16px; font-weight:700; color:#d48806; }
    .stat-value.negative { color:#cf1322; }
    .stat-value.positive { color:#389e0d; }

    /* Forms & Inputs */
    .form-group { margin-bottom: 16px; }
    .form-label { display: block; margin-bottom: 8px; font-size: 14px; color: #555; }
    select, input[type="number"], input[type="text"], textarea { 
        width: 100%; padding: 8px 12px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 14px; transition: all 0.3s; box-sizing: border-box; 
    }
    select:focus, input:focus, textarea:focus { border-color: var(--primary); outline: none; box-shadow: 0 0 0 2px rgba(47, 84, 235, 0.2); }
    
    /* Mode Selector */
    .mode-selector { display: flex; gap: 12px; background: #f5f5f5; padding: 8px; border-radius: 6px; margin-bottom: 20px; }
    .radio-label { flex: 1; text-align: center; cursor: pointer; padding: 8px; border-radius: 4px; font-size: 14px; color: #666; transition: all 0.2s; border: 1px solid transparent; }
    .radio-label:hover { background: rgba(0,0,0,0.05); }
    input[type="radio"] { display: none; }
    input[type="radio"]:checked + .radio-label { background: #fff; color: var(--primary); font-weight: 600; border-color: #e8e8e8; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }

    /* Buttons */
    .btn { display: inline-flex; align-items: center; justify-content: center; padding: 8px 16px; border-radius: 4px; border: none; cursor: pointer; font-size: 14px; transition: all 0.3s; gap: 6px; }
    .btn-block { width: 100%; }
    .btn-primary { background: var(--primary); color: #fff; }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-success { background: var(--success); color: #fff; }
    .btn-success:hover { opacity: 0.9; }
    .btn-danger { background: var(--error); color: #fff; }
    .btn-ghost { background: transparent; color: #666; border: 1px solid #d9d9d9; }
    .btn-ghost:hover { color: var(--primary); border-color: var(--primary); }
    .btn-disabled { background: #f5f5f5; color: #ccc; cursor: not-allowed; border: none; }
    .btn-sm { padding: 4px 10px; font-size: 12px; height: auto; }

    /* Table */
    .table-card { grid-column: 1 / -1; }
    .table-wrapper { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }
    th { text-align: left; background: #fafafa; padding: 12px 16px; border-bottom: 1px solid #e8e8e8; font-weight: 600; color: #666; }
    td { padding: 12px 16px; border-bottom: 1px solid #f0f0f0; color: #333; }
    tr:hover td { background: #fafafa; }
    
    /* Balls */
    .ball { display: inline-block; width: 28px; height: 28px; line-height: 28px; text-align: center; border-radius: 50%; color: #fff; font-size: 13px; font-weight: bold; margin-right: 4px; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.25); text-shadow: 1px 1px 1px rgba(0,0,0,0.35); transition: box-shadow 0.25s, transform 0.25s; }
    .ball-red { background: #f5222d; }
    .ball-blue { background: #1677ff; }
    .ball-hit { box-shadow: 0 0 0 2px rgba(255,255,255,1), 0 0 0 4px rgba(250,173,20,0.9), 0 0 18px rgba(250,140,22,1); transform: translateY(-1px); }

    /* Tags */
    .status-tag { padding: 2px 8px; border-radius: 4px; font-size: 12px; }
    .status-won { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
    .status-lost { background: #fff2f0; color: #ff4d4f; border: 1px solid #ffccc7; }
    .status-wait { background: #f5f5f5; color: #8c8c8c; border: 1px solid #d9d9d9; }

    .tag-rec { display:inline-block; padding:0 6px; margin-right:4px; border-radius:10px; font-size:11px; background:#fff1f0; color:#cf1322; border:1px solid #ffa39e; }

    /* Tabs */
    .tabs { display: flex; border-bottom: 1px solid #e8e8e8; margin-bottom: 16px; }
    .tab { padding: 10px 20px; cursor: pointer; color: #666; border-bottom: 2px solid transparent; font-weight: 500; }
    .tab:hover { color: var(--primary); }
    .tab.active { color: var(--primary); border-bottom-color: var(--primary); }

    .flash-container { grid-column: 1 / -1; }
    .flash { padding: 12px; border-radius: 4px; margin-bottom: 12px; font-size: 14px; display: flex; align-items: center; justify-content: space-between; }
    .flash-success { background: #f6ffed; border: 1px solid #b7eb8f; color: #389e0d; }
    .flash-error { background: #fff2f0; border: 1px solid #ffccc7; color: #cf1322; }
    .flash-warning { background: #fffbe6; border: 1px solid #ffe58f; color: #d48806; }
    .flash-info { background: #e6f7ff; border: 1px solid #91d5ff; color: #096dd9; }
    
    /* Animations */
    @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
    .card, .flash { animation: fadeIn 0.3s ease-out; }

    /* Pagination / Issue selector */
    .pagination { display: flex; align-items: center; justify-content: flex-end; gap: 8px; font-size: 13px; margin-bottom: 8px; color: #666; }
    .pagination select { min-width: 140px; }
  </style>
  <script>
    var buyOptions = {{ buy_options|tojson }};
    
    function updateBuyIssues() {
        var type = document.getElementById('buy_type').value;
        var mode = document.querySelector('input[name="mode_select"]:checked').value;
        var issueSelect = document.getElementById('buy_issue');
        var btnReal = document.getElementById('btn-buy-real');
        var btnTest = document.getElementById('btn-buy-test');

        if (issueSelect) {
            issueSelect.innerHTML = '';
            var issues = buyOptions[type][mode] || [];
            issues.forEach(function(item) {
                var opt = document.createElement('option');
                opt.value = item.value;
                opt.textContent = item.label;
                issueSelect.appendChild(opt);
            });
        }
        
        if (btnReal && btnTest) {
            if (mode === 'real') {
                btnReal.style.display = 'inline-flex';
                btnTest.style.display = 'none';
            } else {
                btnReal.style.display = 'none';
                btnTest.style.display = 'inline-flex';
            }
        }
    }
    
    function toggleCustomVerify() {
        var content = document.getElementById('custom-verify-content');
        var icon = document.getElementById('verify-toggle-icon');
        if (content.style.display === 'none') {
            content.style.display = 'block';
            icon.textContent = '▲ 收起';
        } else {
            content.style.display = 'none';
            icon.textContent = '▼ 展开';
        }
    }

    function switchHistoryTab(type) {
        document.querySelectorAll('.tab-btn').forEach(function (b) {
            var t = b.getAttribute('data-tab');
            if (t === type) {
                b.classList.add('active');
            } else {
                b.classList.remove('active');
            }
        });
        document.querySelectorAll('.history-tab-content').forEach(function (c) {
            c.style.display = (c.id === 'history-' + type) ? 'block' : 'none';
        });
    }

    function selectIssue(type) {
        var ssqSelect = document.getElementById('ssq_issue_select');
        var dltSelect = document.getElementById('dlt_issue_select');
        var ssqPage = {{ ssq_pagination.current }};
        var dltPage = {{ dlt_pagination.current }};

        if (ssqSelect && ssqSelect.value) {
            ssqPage = ssqSelect.value;
        }
        if (dltSelect && dltSelect.value) {
            dltPage = dltSelect.value;
        }

        // 保持两种彩票当前选择的页码，只更新被操作的那个
        if (type === 'ssq' && ssqSelect) {
            ssqPage = ssqSelect.value;
        } else if (type === 'dlt' && dltSelect) {
            dltPage = dltSelect.value;
        }

        var params = new URLSearchParams(window.location.search);
        params.set('ssq_page', ssqPage);
        params.set('dlt_page', dltPage);
        params.set('tab', type); // 保持当前选中的标签页
        // 跳转到“我的彩票记录”锚点，避免每次都滚回页面最上方
        window.location.href = '?' + params.toString() + '#records';
    }

    function initHistoryTab() {
        var params = new URLSearchParams(window.location.search);
        var active = params.get('tab') || 'ssq';
        switchHistoryTab(active);
    }

    window.addEventListener('DOMContentLoaded', function () {
        updateBuyIssues();
        initHistoryTab();
    });
  </script>
</head>
<body>
  <div class="navbar">
    <div class="logo">
      <img src="{{ url_for('static', filename='img/slot.png') }}" alt="logo">
      <span>自嗨彩票</span>
    </div>
    <div class="nav-links">
      <a href="{{ url_for('history') }}">📜 历史开奖结果</a>
    </div>
  </div>

  <div class="container">
    <div class="flash-container">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, msg in messages %}
              <div class="flash flash-{{category}}">
                  <span>{{ msg }}</span>
                  <span style="cursor:pointer;" onclick="this.parentElement.style.display='none'">×</span>
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}
    </div>

    <!-- Left Column: Status & Update -->
    <div class="status-panel">
        <div class="card">
            <div class="card-title">系统状态</div>
            <div class="info-block">
                <div class="info-label">当前时间</div>
                <div class="info-value">{{ now }}</div>
            </div>
            <div class="info-block" style="margin-top: 10px;">
                <div class="info-label">数据源</div>
                <div class="info-value">500.com (实时)</div>
            </div>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-label">累计购票金额</div>
                    <div class="stat-value">{{ total_bet|fmt_money }} 元</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">累计中奖金额</div>
                    <div class="stat-value">{{ total_win|fmt_money }} 元</div>
                </div>
                <div class="stat-item" style="grid-column:1 / -1;">
                    <div class="stat-label">盈亏统计</div>
                    <div class="stat-value {% if net_profit >= 0 %}positive{% else %}negative{% endif %}">
                        {% if net_profit >= 0 %}+{{ net_profit|fmt_money }} 元{% else %}{{ net_profit|fmt_money }} 元{% endif %}
                    </div>
                </div>
            </div>
            
            <form method="post" action="{{ url_for('update') }}" style="margin-top: 20px;">
                {% if features.enable_update %}
                  <button class="btn btn-primary btn-block" type="submit">
                    <img src="{{ url_for('static', filename='img/globe.png') }}" style="width:16px;height:16px;">
                    立即更新数据
                  </button>
                {% else %}
                  <button class="btn btn-ghost btn-block" type="button" disabled>更新已关闭</button>
                {% endif %}
            </form>
            
            <div style="margin-top: 12px; display:flex; gap:8px;">
                <form method="get" action="{{ url_for('index') }}" style="flex:1; margin:0;">
                    <input type="hidden" name="analyze_type" value="ssq">
                    <button class="btn btn-ghost btn-block" type="submit">🎯 分析下一期双色球</button>
                </form>
                <form method="get" action="{{ url_for('index') }}" style="flex:1; margin:0;">
                    <input type="hidden" name="analyze_type" value="dlt">
                    <button class="btn btn-ghost btn-block" type="submit">🎯 分析下一期大乐透</button>
                </form>
            </div>
        </div>

        <div class="card">
            <div class="card-title" onclick="toggleCustomVerify()" style="cursor: pointer;">
                <span>🎯 选号验奖</span>
                <span id="verify-toggle-icon" style="font-size: 12px; color: #999;">▼</span>
            </div>
            <div id="custom-verify-content" style="display: none;">
                <form method="post" action="{{ url_for('verify') }}">
                    <div class="form-group">
                        <label class="form-label">彩种</label>
                        <select name="verify_type">
                            <option value="ssq">双色球</option>
                            <option value="dlt">大乐透</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">期号</label>
                        <input type="text" name="verify_issue" placeholder="如: 2024001">
                    </div>
                    <div class="form-group">
                        <label class="form-label">号码 (每行一组)</label>
                        <textarea name="verify_numbers" placeholder="01 02 03 04 05 06 | 10" style="height: 80px; font-family: monospace;"></textarea>
                    </div>
                    <button class="btn btn-primary btn-block" type="submit">开始验证</button>
                </form>
            </div>
        </div>
    </div>

    <!-- Right Column: Buy -->
    <div class="card">
        <div class="card-title">购买彩票</div>
        <form method="post" action="{{ url_for('buy') }}">
            <div class="mode-selector">
                <label>
                    <input type="radio" name="mode_select" value="real" checked onchange="updateBuyIssues()">
                    <div class="radio-label">✅ 正式购买 (记录存档)</div>
                </label>
                <label>
                    <input type="radio" name="mode_select" value="test" onchange="updateBuyIssues()">
                    <div class="radio-label">🧪 模拟测试 (不保存)</div>
                </label>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div class="form-group">
                    <label class="form-label">彩种选择</label>
                    <select name="type" id="buy_type" onchange="updateBuyIssues()">
                      <option value="ssq">双色球</option>
                      <option value="dlt">大乐透</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">购买数量</label>
                    <input type="number" name="count" value="1" min="1">
                </div>
            </div>

            <div class="form-group">
                <label class="form-label">选择期号</label>
                <select name="issue" id="buy_issue">
                    <!-- Populated by JS -->
                </select>
            </div>

            <div style="margin-top: 24px;">
                {% if features.enable_buy %}
                  <button id="btn-buy-real" class="btn btn-primary btn-block" type="submit" name="mode" value="normal" style="height: 40px; font-size: 16px;">
                    <img src="{{ url_for('static', filename='img/ticket.png') }}" style="width:18px;"> 确认出票
                  </button>
                  <button id="btn-buy-test" class="btn btn-success btn-block" type="submit" name="mode" value="test" style="display:none; height: 40px; font-size: 16px;">
                    <img src="{{ url_for('static', filename='img/ticket.png') }}" style="width:18px;"> 开始模拟
                  </button>
                {% else %}
                  <button class="btn btn-ghost btn-block" type="button" disabled>购买功能已关闭</button>
                {% endif %}
            </div>
            
            <div style="margin-top: 16px; font-size: 12px; color: #999; text-align: center;">
                * 模拟器仅供娱乐，请理性购买彩票
            </div>
        </form>
    </div>

    {% if recommendations %}
    <!-- 推荐号码区域 -->
    <div id="recommend" class="card table-card">
        <div class="card-title">
            <span>智能推荐 · {{ '双色球' if recommendations.type=='ssq' else '大乐透' }} 第 {{ recommendations.issue }} 期</span>
        </div>
        <form method="post" action="{{ url_for('buy_recommend') }}">
            <input type="hidden" name="type" value="{{ recommendations.type }}">
            <input type="hidden" name="issue" value="{{ recommendations.issue }}">
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th width="60">选择</th>
                            <th>号码</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in recommendations['items'] %}
                        {% set reds = item.nums[0] %}
                        {% set blues = item.nums[1] %}
                        <tr>
                            <td>
                                <input type="checkbox" name="choose" value="{{ item.index }}">
                                <input type="hidden" name="nums_{{ item.index }}" value="{{ reds|join(' ') }} | {{ blues|join(' ') }}">
                            </td>
                            <td>
                                {% for n in reds %}<span class="ball ball-red">{{ n|fmt_num }}</span>{% endfor %}
                                {% for n in blues %}<span class="ball ball-blue">{{ n|fmt_num }}</span>{% endfor %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            <div style="margin-top: 12px; text-align: right; font-size: 12px; color:#999;">
                系统根据最近开奖数据生成，仅供娱乐参考，不能保证中奖。
            </div>
            <div style="margin-top: 8px; text-align: right;">
                <button class="btn btn-primary" type="submit">
                    🎯 购买选中推荐号码
                </button>
            </div>
        </form>
    </div>
    {% endif %}

    <!-- Full Width: Records -->
    <div id="records" class="card table-card">
        <div class="card-title">
            <span>我的彩票记录 {% if purchased %}<span style="font-weight: normal; color: #999; font-size: 14px;">(共 {{ purchased|length }} 条)</span>{% endif %}</span>
            <form method="post" action="{{ url_for('check') }}" style="margin:0;">
                {% if features.enable_check %}
                  <button class="btn btn-danger" type="submit">
                    <img src="{{ url_for('static', filename='img/money.png') }}" style="width:16px;"> 批量兑奖
                  </button>
                {% endif %}
            </form>
        </div>

        {% if purchased %}
            <div class="tabs">
                <div class="tab active tab-btn" data-tab="ssq" onclick="switchHistoryTab('ssq')">双色球</div>
                <div class="tab tab-btn" data-tab="dlt" onclick="switchHistoryTab('dlt')">大乐透</div>
            </div>

            <div id="history-ssq" class="history-tab-content">
                {% if ssq_current_issue %}
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; font-size:13px; color:#595959;">
                    <div>
                        当前期号：<strong>{{ ssq_current_issue }}</strong>
                        {% if ssq_current_win %}
                          <span style="margin-left:8px; color:#8c8c8c;">当期开奖号码：</span>
                          {% for n in ssq_current_win.nums[0] %}
                            <span class="ball ball-red">{{ n|fmt_num }}</span>
                          {% endfor %}
                          {% for n in ssq_current_win.nums[1] %}
                            <span class="ball ball-blue">{{ n|fmt_num }}</span>
                          {% endfor %}
                        {% else %}
                          <span style="margin-left:8px; color:#faad14;">该期暂无开奖号码，请先联网更新。</span>
                        {% endif %}
                    </div>
                    <div class="pagination">
                        <span>选择期号：</span>
                        <select id="ssq_issue_select" onchange="selectIssue('ssq')">
                          {% for iss in ssq_issues %}
                            <option value="{{ loop.index }}" {% if iss == ssq_current_issue %}selected{% endif %}>
                              第 {{ iss }} 期
                            </option>
                          {% endfor %}
                        </select>
                    </div>
                </div>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th width="100">期号</th>
                                <th>号码</th>
                                <th width="150">购买时间</th>
                                <th width="100">状态</th>
                                <th width="120">奖项</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for t in ssq_current_tickets|reverse %}
                            <tr>
                                <td>
                                    {% if t.recommended %}
                                      <span class="tag-rec">荐</span>
                                    {% endif %}
                                    {{ t.issue }}
                                </td>
                                <td>
                                    {% for n in t.nums[0] %}
                                      <span class="ball ball-red {% if ssq_current_win and n in ssq_current_win.nums[0] %}ball-hit{% endif %}">{{ n|fmt_num }}</span>
                                    {% endfor %}
                                    {% for n in t.nums[1] %}
                                      <span class="ball ball-blue {% if ssq_current_win and n in ssq_current_win.nums[1] %}ball-hit{% endif %}">{{ n|fmt_num }}</span>
                                    {% endfor %}
                                </td>
                                <td>{{ t.time }}</td>
                                <td>
                                    {% if t.checked %}
                                        {% if t.prize and t.prize != '未中奖' %}
                                            <span class="status-tag status-won">已中奖</span>
                                        {% else %}
                                            <span class="status-tag status-lost">未中奖</span>
                                        {% endif %}
                                    {% else %}
                                        <span class="status-tag status-wait">待开奖</span>
                                    {% endif %}
                                </td>
                                <td style="font-weight: bold; color: {% if '一等奖' in t.prize %}#ffd700{% elif '二' in t.prize %}#ff7a00{% else %}#52c41a{% endif %}">
                                    {% if t.prize and t.prize != '未中奖' %}
                                      {{ t.prize }}（{{ t.prize|prize_amount|fmt_money }} 元）
                                    {% else %}
                                      -
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                  <div style="padding: 20px; text-align: center; color: #999;">
                    暂无双色球购买记录。
                  </div>
                {% endif %}
            </div>

            <div id="history-dlt" class="history-tab-content" style="display:none;">
                {% if dlt_current_issue %}
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; font-size:13px; color:#595959;">
                    <div>
                        当前期号：<strong>{{ dlt_current_issue }}</strong>
                        {% if dlt_current_win %}
                          <span style="margin-left:8px; color:#8c8c8c;">当期开奖号码：</span>
                          {% for n in dlt_current_win.nums[0] %}
                            <span class="ball ball-red">{{ n|fmt_num }}</span>
                          {% endfor %}
                          {% for n in dlt_current_win.nums[1] %}
                            <span class="ball ball-blue">{{ n|fmt_num }}</span>
                          {% endfor %}
                        {% else %}
                          <span style="margin-left:8px; color:#faad14;">该期暂无开奖号码，请先联网更新。</span>
                        {% endif %}
                    </div>
                    <div class="pagination">
                        <span>选择期号：</span>
                        <select id="dlt_issue_select" onchange="selectIssue('dlt')">
                          {% for iss in dlt_issues %}
                            <option value="{{ loop.index }}" {% if iss == dlt_current_issue %}selected{% endif %}>
                              第 {{ iss }} 期
                            </option>
                          {% endfor %}
                        </select>
                    </div>
                </div>
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th width="100">期号</th>
                                <th>号码</th>
                                <th width="150">购买时间</th>
                                <th width="100">状态</th>
                                <th width="120">奖项</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for t in dlt_current_tickets|reverse %}
                            <tr>
                                <td>
                                    {% if t.recommended %}
                                      <span class="tag-rec">荐</span>
                                    {% endif %}
                                    {{ t.issue }}
                                </td>
                                <td>
                                    {% for n in t.nums[0] %}
                                      <span class="ball ball-red {% if dlt_current_win and n in dlt_current_win.nums[0] %}ball-hit{% endif %}">{{ n|fmt_num }}</span>
                                    {% endfor %}
                                    {% for n in t.nums[1] %}
                                      <span class="ball ball-blue {% if dlt_current_win and n in dlt_current_win.nums[1] %}ball-hit{% endif %}">{{ n|fmt_num }}</span>
                                    {% endfor %}
                                </td>
                                <td>{{ t.time }}</td>
                                <td>
                                    {% if t.checked %}
                                        {% if t.prize and t.prize != '未中奖' %}
                                            <span class="status-tag status-won">已中奖</span>
                                        {% else %}
                                            <span class="status-tag status-lost">未中奖</span>
                                        {% endif %}
                                    {% else %}
                                        <span class="status-tag status-wait">待开奖</span>
                                    {% endif %}
                                </td>
                                <td style="font-weight: bold; color: {% if '一等奖' in t.prize %}#ffd700{% elif '二' in t.prize %}#ff7a00{% else %}#52c41a{% endif %}">
                                    {% if t.prize and t.prize != '未中奖' %}
                                      {{ t.prize }}（{{ t.prize|prize_amount|fmt_money }} 元）
                                    {% else %}
                                      -
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                  <div style="padding: 20px; text-align: center; color: #999;">
                    暂无大乐透购买记录。
                  </div>
                {% endif %}
            </div>
        {% else %}
            <div style="text-align: center; padding: 40px; color: #999;">
                暂无购买记录，快去买一注吧！
            </div>
        {% endif %}
    </div>

    <!-- Test Records (Hidden by default or smaller) -->
    {% if test_tickets %}
    <div class="card table-card" style="margin-top: 20px; border-style: dashed;">
        <div class="card-title">
            <span>🧪 测试记录 (不保存)</span>
            <form method="post" action="{{ url_for('clear_test') }}" style="margin:0;">
                <button class="btn btn-ghost btn-sm" type="submit">清空测试</button>
            </form>
        </div>
        <div style="font-size: 12px; color: #999; margin-bottom: 10px;">测试记录仅用于验证功能，不会保存到数据库。</div>
        
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>类型</th>
                        <th>期号</th>
                        <th>号码</th>
                        <th>状态</th>
                        <th>奖项</th>
                    </tr>
                </thead>
                <tbody>
                    {% for t in test_tickets|reverse %}
                    <tr>
                        <td>{{ "双色球" if t.type=='ssq' else "大乐透" }}</td>
                        <td>{{ t.issue }}</td>
                        <td>
                            <span style="color: #f5222d;">{{ t.nums[0]|map("fmt_num")|join(" ") }}</span> + 
                            <span style="color: #1677ff;">{{ t.nums[1]|map("fmt_num")|join(" ") }}</span>
                        </td>
                         <td>
                            {% if t.checked %}
                                {% if t.prize and t.prize != '未中奖' %}
                                    <span class="status-tag status-won">已中奖</span>
                                {% else %}
                                    <span class="status-tag status-lost">未中奖</span>
                                {% endif %}
                            {% else %}
                                <span class="status-tag status-wait">待开奖</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if t.prize and t.prize != '未中奖' %}
                              {{ t.prize }}（{{ t.prize|prize_amount|fmt_money }} 元）
                            {% else %}
                              {{ t.prize or '-' }}
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    {% endif %}

  </div>
</body>
</html>
"""

HISTORY_TEMPLATE = """
<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <title>所有开奖结果 - 自嗨彩票</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#f7f8fa; margin:0; padding:0; }
    .nav { background:#2f54eb; color:#fff; padding:14px 20px; font-size:18px; display:flex; align-items:center; gap:10px; }
    .nav img { width:28px; height:28px; image-rendering:auto; }
    .nav a { color: #fff; text-decoration: none; font-size: 16px; margin-left: 20px; opacity: 0.8; }
    .nav a:hover { opacity: 1; text-decoration: underline; }
    .wrap { max-width: 1080px; margin: 20px auto; padding: 0 16px; }
    .card { background:#fff; border-radius:10px; box-shadow:0 4px 14px rgba(0,0,0,0.06); padding:16px; margin-bottom:14px; }
    .title { font-weight:bold; margin-bottom:8px; font-size: 16px; }
    table { width:100%; border-collapse:collapse; margin-top:10px; }
    th, td { padding:10px 8px; border-bottom:1px solid #f0f0f0; text-align:left; }
    th { background:#fafafa; font-weight: 600; color: #333; }
    .ball { display: inline-block; width: 28px; height: 28px; line-height: 28px; text-align: center; border-radius: 50%; color: #fff; font-size: 13px; font-weight: bold; margin-right: 4px; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.2); text-shadow: 1px 1px 1px rgba(0,0,0,0.2); }
    .ball-red { background: #f5222d; }
    .ball-blue { background: #1677ff; }
    .tab-bar { display: flex; border-bottom: 1px solid #e8e8e8; margin-bottom: 15px; }
    .tab-btn { padding: 10px 20px; cursor: pointer; border-bottom: 2px solid transparent; color: #666; font-weight: 500; }
    .tab-btn.active { color: #2f54eb; border-bottom-color: #2f54eb; }
    .tab-btn:hover { color: #2f54eb; }
  </style>
  <script>
    function switchTab(type) {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        event.target.classList.add('active');
        document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
        document.getElementById('content-' + type).style.display = 'block';
    }
  </script>
</head>
<body>
  <div class="nav">
    <img alt="logo" src="{{ url_for('static', filename='img/slot.png') }}">
    <div>自嗨彩票 · Web</div>
    <a href="{{ url_for('index') }}">🏠 返回首页</a>
  </div>
  <div class="wrap">
    <div class="card">
      <div class="title">📜 历史开奖结果</div>
      <div style="color:#888; margin-bottom: 15px; font-size: 14px;">数据来源: 500.com (最近30期) | 更新时间: {{ now }}</div>
      
      <div class="tab-bar">
        <div class="tab-btn active" onclick="switchTab('ssq')">双色球 ({{ winnings.ssq|length }})</div>
        <div class="tab-btn" onclick="switchTab('dlt')">大乐透 ({{ winnings.dlt|length }})</div>
      </div>

      <div id="content-ssq" class="tab-content">
        {% if winnings.ssq %}
        <table>
            <thead>
                <tr>
                    <th>期号</th>
                    <th>开奖号码 (红球 | 蓝球)</th>
                </tr>
            </thead>
            <tbody>
                {% for item in winnings.ssq %}
                <tr>
                    <td>{{ item.issue }}</td>
                    <td>
                        {% for n in item.nums[0] %}<span class="ball ball-red">{{ n|fmt_num }}</span>{% endfor %}
                        {% for n in item.nums[1] %}<span class="ball ball-blue">{{ n|fmt_num }}</span>{% endfor %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div style="padding: 20px; text-align: center; color: #999;">暂无数据，请在首页点击“联网更新”。</div>
        {% endif %}
      </div>

      <div id="content-dlt" class="tab-content" style="display:none;">
        {% if winnings.dlt %}
        <table>
            <thead>
                <tr>
                    <th>期号</th>
                    <th>开奖号码 (前区 | 后区)</th>
                </tr>
            </thead>
            <tbody>
                {% for item in winnings.dlt %}
                <tr>
                    <td>{{ item.issue }}</td>
                    <td>
                        {% for n in item.nums[0] %}<span class="ball ball-red">{{ n|fmt_num }}</span>{% endfor %}
                        {% for n in item.nums[1] %}<span class="ball ball-blue">{{ n|fmt_num }}</span>{% endfor %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div style="padding: 20px; text-align: center; color: #999;">暂无数据，请在首页点击“联网更新”。</div>
        {% endif %}
      </div>

    </div>
  </div>
</body>
</html>
"""


if __name__ == "__main__":
    # host=0.0.0.0 方便局域网设备访问；可按需改端口
    app.run(host="0.0.0.0", port=5000, debug=False)
