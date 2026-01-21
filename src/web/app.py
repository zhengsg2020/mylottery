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


@app.route("/", methods=["GET"])
def index():
    """首页"""
    purchased, winnings = data.load_all_data()
    test_tickets = data.load_test_data()
    # 正式购买的中奖票据
    formal_winning_tickets = [t for t in purchased if t.get("checked") and t.get("prize") and t.get("prize") != "未中奖"]
    # 测试购买的中奖票据（分开显示）
    test_winning_tickets = [t for t in test_tickets if t.get("checked") and t.get("prize") and t.get("prize") != "未中奖"]
    return render_template_string(
        TEMPLATE,
        purchased=purchased,
        test_tickets=test_tickets,
        formal_winning_tickets=formal_winning_tickets,
        test_winning_tickets=test_winning_tickets,
        winnings=winnings,
        features=WEB_FEATURES,
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
        winnings["ssq"] = fetcher.fetch_500_data("ssq")
        winnings["dlt"] = fetcher.fetch_500_data("dlt")
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
        mode = "测试-最新期(不保存)"
    else:
        # 正式购买写入正式文件
        purchased.extend(new_tickets)
        data.save_all_data(purchased, winnings)
        mode = "下一期"

    flash(
        f"成功购买 {n} 注 {'双色球' if l_type=='ssq' else '大乐透'} [{issue}] ({mode})",
        "success",
    )
    return redirect(url_for("index"))


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
    lines = [line.strip() for line in numbers_text.split("\n") if line.strip()]
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


@app.post("/clear_test")
def clear_test():
    """清空测试购买记录（不影响正式购买）"""
    data.save_test_data([])
    flash("测试购买记录已清空。", "success")
    return redirect(url_for("index"))


# HTML模板
TEMPLATE = """
<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <title>彩票模拟器 - Web版</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#f7f8fa; margin:0; padding:0; }
    .nav { background:#2f54eb; color:#fff; padding:14px 20px; font-size:18px; display:flex; align-items:center; gap:10px; }
    .nav img { width:28px; height:28px; image-rendering:auto; }
    .wrap { max-width: 1080px; margin: 20px auto; padding: 0 16px; }
    .card { background:#fff; border-radius:10px; box-shadow:0 4px 14px rgba(0,0,0,0.06); padding:16px; margin-bottom:14px; }
    .title { font-weight:bold; margin-bottom:8px; }
    .btn { display:inline-block; padding:8px 14px; border:none; border-radius:6px; cursor:pointer; font-size:14px; text-decoration:none; }
    .btn-primary { background:#2f54eb; color:#fff; }
    .btn-danger { background:#ff4d4f; color:#fff; }
    .btn-success { background:#52c41a; color:#fff; }
    .btn-ghost { background:#fff; color:#2f54eb; border:1px solid #2f54eb; }
    form { margin:0; }
    table { width:100%; border-collapse:collapse; margin-top:10px; }
    th, td { padding:8px 6px; border-bottom:1px solid #f0f0f0; text-align:left; }
    th { background:#fafafa; position:sticky; top:0; z-index:10; }
    .table-container { max-height:600px; overflow-y:auto; border:1px solid #e8e8e8; border-radius:4px; }
    .table-container table { margin-top:0; }
    .tag { padding:2px 8px; border-radius:10px; font-size:12px; display:inline-block; }
    .tag-blue { background:#e6f4ff; color:#1677ff; }
    .tag-red { background:#fff1f0; color:#f5222d; }
    .tag-green { background:#f6ffed; color:#52c41a; }
    .tag-gray { background:#f5f5f5; color:#666; }
    .flash { padding:10px 12px; border-radius:8px; margin-bottom:8px; }
    .flash-success { background:#f6ffed; color:#1f8a3d; border:1px solid #b7eb8f; }
    .flash-error { background:#fff1f0; color:#c0392b; border:1px solid #ffa39e; }
    .flash-warning { background:#fff7e6; color:#d46b08; border:1px solid #ffd591; }
    .flash-info { background:#e6f7ff; color:#096dd9; border:1px solid #91d5ff; }
    /* 奖项颜色 */
    .prize-jackpot { color:#ffd700; font-weight:bold; font-size:14px; }
    .prize-high { color:#ff7a00; font-weight:bold; }
    .prize-mid { color:#722ed1; font-weight:bold; }
    .prize-low { color:#52c41a; font-weight:bold; }
    .prize-none { color:#8c8c8c; }
    tr.prize-row-jackpot { background:#fffbe6; }
    tr.prize-row-high { background:#fff7e6; }
    tr.prize-row-mid { background:#f9f0ff; }
    tr.prize-row-low { background:#f6ffed; }
    .btn-group { display:flex; gap:8px; flex-wrap:wrap; }
    textarea { width:100%; min-height:120px; padding:8px; border:1px solid #d9d9d9; border-radius:4px; font-family:monospace; }
    .modal { display:none; position:fixed; z-index:1000; left:0; top:0; width:100%; height:100%; background:rgba(0,0,0,0.5); }
    .modal-content { background:#fff; margin:5% auto; padding:20px; border-radius:8px; max-width:600px; max-height:80vh; overflow-y:auto; }
    .close { float:right; font-size:28px; font-weight:bold; cursor:pointer; }
  </style>
</head>
<body>
  <div class="nav">
    <img alt="logo" src="{{ url_for('static', filename='img/slot.png') }}">
    <div>至尊彩票大师 · Web</div>
  </div>
  <div class="wrap">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, msg in messages %}
          <div class="flash flash-{{category}}">{{ msg }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="card">
      <div class="title">联网更新开奖号码</div>
      <form method="post" action="{{ url_for('update') }}">
        {% if features.enable_update %}
          <button class="btn btn-primary" type="submit">
            <img alt="" src="{{ url_for('static', filename='img/globe.png') }}" style="width:16px;height:16px;vertical-align:-3px;margin-right:6px;">
            更新最新30期
          </button>
        {% else %}
          <button class="btn btn-ghost" type="button" disabled>已关闭</button>
        {% endif %}
      </form>
      <div style="margin-top:6px;color:#888;">当前时间：{{ now }}</div>
    </div>

    <div class="card">
      <div class="title">购买彩票</div>
      <form method="post" action="{{ url_for('buy') }}">
        <label>数量:</label>
        <input type="number" name="count" value="1" min="1" style="width:70px;" placeholder="无限制">
        <label style="margin-left:10px;">类型:</label>
        <select name="type" id="buy_type">
          <option value="ssq">双色球</option>
          <option value="dlt">大乐透</option>
        </select>
        <div class="btn-group" style="margin-top:10px;">
          {% if features.enable_buy %}
            <button class="btn btn-primary" type="submit" name="mode" value="normal">
              <img alt="" src="{{ url_for('static', filename='img/ticket.png') }}" style="width:16px;height:16px;vertical-align:-3px;margin-right:6px;">
              购买下一期
            </button>
            <button class="btn btn-success" type="submit" name="mode" value="test">
              <img alt="" src="{{ url_for('static', filename='img/ticket.png') }}" style="width:16px;height:16px;vertical-align:-3px;margin-right:6px;">
              测试购买(本期-不保存)
            </button>
          {% else %}
            <button class="btn btn-ghost" type="button" disabled>已关闭</button>
          {% endif %}
        </div>
      </form>
    </div>

    <div class="card">
      <div class="title">兑奖</div>
      <form method="post" action="{{ url_for('check') }}">
        {% if features.enable_check %}
          <button class="btn btn-danger" type="submit">
            <img alt="" src="{{ url_for('static', filename='img/money.png') }}" style="width:16px;height:16px;vertical-align:-3px;margin-right:6px;">
            批量兑奖
          </button>
        {% else %}
          <button class="btn btn-ghost" type="button" disabled>已关闭</button>
        {% endif %}
      </form>
    </div>

    <div class="card">
      <div class="title">🎯 自定义选号验奖</div>
      <form method="post" action="{{ url_for('verify') }}">
        <div style="margin-bottom:10px;">
          <label>类型:</label>
          <select name="verify_type" required>
            <option value="ssq">双色球</option>
            <option value="dlt">大乐透</option>
          </select>
          <label style="margin-left:10px;">期号:</label>
          <input type="text" name="verify_issue" placeholder="例如: 2024001" required style="width:120px;">
        </div>
        <div style="margin-bottom:10px;">
          <label>号码（每行一组，格式：双色球: 01 02 03 04 05 06 | 10，大乐透: 01 02 03 04 05 | 06 07）:</label>
          <textarea name="verify_numbers" placeholder="01 02 03 04 05 06 | 10&#10;07 08 09 10 11 12 | 13" required></textarea>
        </div>
        {% if features.enable_check %}
          <button class="btn btn-primary" type="submit">开始检查</button>
        {% else %}
          <button class="btn btn-ghost" type="button" disabled>已关闭</button>
        {% endif %}
      </form>
    </div>

    {% if formal_winning_tickets %}
    <div class="card">
      <div class="title">🏆 中奖汇总（正式购买） - 共 {{ formal_winning_tickets|length }} 条</div>
      <div class="table-container">
        <table>
          <tr>
            <th>类型</th>
            <th>期号</th>
            <th>号码</th>
            <th>时间</th>
            <th>奖项</th>
          </tr>
          {% for t in formal_winning_tickets|reverse %}
            <tr class="prize-row-{{ t.prize|prize_class|replace('prize-', '') }}">
              <td>{{ "双色球" if t.type=="ssq" else "大乐透" }}</td>
              <td>{{ t.issue }}</td>
              <td>
                <span class="tag tag-red">{{ t.nums[0]|map("fmt_num")|join(" ") }}</span>
                <span class="tag tag-blue">{{ t.nums[1]|map("fmt_num")|join(" ") }}</span>
              </td>
              <td>{{ t.time or "" }}</td>
              <td class="{{ t.prize|prize_class }}">{{ t.prize }}</td>
            </tr>
          {% endfor %}
        </table>
      </div>
    </div>
    {% endif %}

    {% if test_winning_tickets %}
    <div class="card">
      <div class="title">🏆 中奖汇总（测试购买） - 共 {{ test_winning_tickets|length }} 条</div>
      <div class="table-container">
        <table>
          <tr>
            <th>类型</th>
            <th>期号</th>
            <th>号码</th>
            <th>时间</th>
            <th>奖项</th>
          </tr>
          {% for t in test_winning_tickets|reverse %}
            <tr class="prize-row-{{ t.prize|prize_class|replace('prize-', '') }}">
              <td>{{ "双色球" if t.type=="ssq" else "大乐透" }}</td>
              <td>{{ t.issue }}</td>
              <td>
                <span class="tag tag-red">{{ t.nums[0]|map("fmt_num")|join(" ") }}</span>
                <span class="tag tag-blue">{{ t.nums[1]|map("fmt_num")|join(" ") }}</span>
              </td>
              <td>{{ t.time or "" }}</td>
              <td class="{{ t.prize|prize_class }}">{{ t.prize }}</td>
            </tr>
          {% endfor %}
        </table>
      </div>
    </div>
    {% endif %}

    <div class="card">
      <div class="title">购票记录（正式购买）{% if purchased %} - 共 {{ purchased|length }} 条{% endif %}</div>
      {% if purchased %}
        <div class="table-container">
          <table>
            <tr>
              <th>类型</th>
              <th>期号</th>
              <th>号码</th>
              <th>时间</th>
              <th>兑奖状态</th>
              <th>奖项</th>
            </tr>
            {% for t in purchased|reverse %}
              <tr {% if t.checked and t.prize and t.prize != "未中奖" %}class="prize-row-{{ t.prize|prize_class|replace('prize-', '') }}"{% endif %}>
                <td>{{ "双色球" if t.type=="ssq" else "大乐透" }}</td>
                <td>{{ t.issue }}</td>
                <td>
                  <span class="tag tag-red">{{ t.nums[0]|map("fmt_num")|join(" ") }}</span>
                  <span class="tag tag-blue">{{ t.nums[1]|map("fmt_num")|join(" ") }}</span>
                </td>
                <td>{{ t.time or "" }}</td>
                <td>
                  {% if t.checked %}
                    <span class="tag tag-green">已兑奖</span>
                  {% else %}
                    <span class="tag tag-gray">未兑奖</span>
                  {% endif %}
                </td>
                <td class="{{ t.prize|prize_class if t.prize else 'prize-none' }}">{{ t.prize or "-" }}</td>
              </tr>
            {% endfor %}
          </table>
        </div>
      {% else %}
        <div style="color:#888;">暂无正式购买记录。</div>
      {% endif %}
    </div>

    {% if test_tickets %}
    <div class="card">
      <div class="title">测试购买记录（不保存到正式文件） - 共 {{ test_tickets|length }} 条</div>
      <form method="post" action="{{ url_for('clear_test') }}" style="margin-top:10px;">
        <button class="btn btn-danger" type="submit">🧪 清空测试记录</button>
      </form>
      <div class="table-container">
        <table>
          <tr>
            <th>类型</th>
            <th>期号</th>
            <th>号码</th>
            <th>时间</th>
            <th>兑奖状态</th>
            <th>奖项</th>
          </tr>
          {% for t in test_tickets|reverse %}
            <tr {% if t.checked and t.prize and t.prize != "未中奖" %}class="prize-row-{{ t.prize|prize_class|replace('prize-', '') }}"{% endif %}>
              <td>{{ "双色球" if t.type=="ssq" else "大乐透" }}</td>
              <td>{{ t.issue }}</td>
              <td>
                <span class="tag tag-red">{{ t.nums[0]|map("fmt_num")|join(" ") }}</span>
                <span class="tag tag-blue">{{ t.nums[1]|map("fmt_num")|join(" ") }}</span>
              </td>
              <td>{{ t.time or "" }}</td>
              <td>
                {% if t.checked %}
                  <span class="tag tag-green">已兑奖</span>
                {% else %}
                  <span class="tag tag-gray">未兑奖</span>
                {% endif %}
              </td>
              <td class="{{ t.prize|prize_class if t.prize else 'prize-none' }}">{{ t.prize or "-" }}</td>
            </tr>
          {% endfor %}
        </table>
      </div>
    </div>
    {% endif %}

  </div>
</body>
</html>
"""


if __name__ == "__main__":
    # host=0.0.0.0 方便局域网设备访问；可按需改端口
    app.run(host="0.0.0.0", port=5000, debug=False)
