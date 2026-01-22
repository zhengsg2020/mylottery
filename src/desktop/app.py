"""桌面版应用（Tkinter）"""
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.common import config, data, fetcher, lottery


class LotteryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("自嗨彩票 - Desktop")
        # 设置窗口大小和最小尺寸，适配不同显示器
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        # 默认窗口大小为屏幕的70%，最小尺寸为800x600
        default_width = max(800, int(screen_width * 0.7))
        default_height = max(600, int(screen_height * 0.7))
        self.root.geometry(f"{default_width}x{default_height}")
        self.root.minsize(800, 600)  # 设置最小窗口大小
        self.root.configure(bg="#f0f2f5")
        # 允许窗口调整大小
        self.root.resizable(True, True)

        # 数据存储
        self.purchased_tickets = []  # 正式购买
        self.test_tickets = []  # 测试购买（不写入正式文件）
        self.winning_data = {"ssq": [], "dlt": []}
        self.win_tickets = []
        self.load_all_data()

        self.setup_styles()
        self.setup_ui()

    def _asset_path(self, name: str) -> str:
        return os.path.join(config.ASSETS_DIR, name)

    def _load_photo(self, name: str):
        """加载PNG资源（若不存在则返回None）"""
        p = self._asset_path(name)
        if not os.path.exists(p):
            return None
        try:
            return tk.PhotoImage(file=p)
        except Exception:
            return None

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f0f2f5")
        style.configure("TLabel", background="#f0f2f5", font=("Microsoft YaHei", 10))
        style.configure("Header.TLabel", font=("Microsoft YaHei", 12, "bold"))
        style.configure("Red.TButton", foreground="white", background="#ff4d4f", padding=5)
        style.configure("Blue.TButton", foreground="white", background="#1890ff", padding=5)

    def setup_ui(self):
        # 顶部标题
        header_bar = tk.Frame(self.root, bg="#2f54eb")
        header_bar.pack(fill="x")

        self._logo_img = self._load_photo("slot.png")
        if self._logo_img:
            tk.Label(header_bar, image=self._logo_img, bg="#2f54eb").pack(
                side="left", padx=(16, 8), pady=10
            )
            try:
                self.root.iconphoto(True, self._logo_img)
            except Exception:
                pass
        else:
            tk.Label(
                header_bar,
                text="🎰",
                font=("Microsoft YaHei", 20, "bold"),
                bg="#2f54eb",
                fg="white",
            ).pack(side="left", padx=(16, 8), pady=10)

        tk.Label(
            header_bar,
            text="自嗨彩票 · Desktop",
            font=("Microsoft YaHei", 20, "bold"),
            bg="#2f54eb",
            fg="white",
            pady=15,
        ).pack(side="left")

        main_container = ttk.Frame(self.root, padding=10)
        main_container.pack(fill="both", expand=True)

        # 第一部分：购买面板
        buy_panel = ttk.LabelFrame(main_container, text=" 购票中心 ", padding=10)
        buy_panel.pack(fill="x", pady=5)

        # 购买注数
        ttk.Label(buy_panel, text="购买注数:").grid(row=0, column=0, padx=5, sticky="w")
        self.num_entry = ttk.Entry(buy_panel, width=10, font=("Arial", 11))
        self.num_entry.insert(0, "1")
        self.num_entry.grid(row=0, column=1, padx=5, sticky="w")

        # 彩票类型选择（使用中文名称显示，方便扩展更多类型）
        ttk.Label(buy_panel, text="类型:").grid(row=0, column=2, padx=5, sticky="w")
        self.type_var = tk.StringVar(value="ssq")
        # 类型映射：显示名称 -> 内部值
        self.type_map = {"双色球": "ssq", "大乐透": "dlt"}
        self.type_map_reverse = {v: k for k, v in self.type_map.items()}
        self.type_combo = ttk.Combobox(
            buy_panel,
            textvariable=self.type_var,
            values=list(self.type_map.keys()),  # 显示中文名称
            state="readonly",
            width=10,
        )
        self.type_combo.grid(row=0, column=3, padx=5, sticky="w")
        # 设置默认值为"双色球"
        self.type_combo.set("双色球")
        # 绑定选择事件，将中文名称转换为内部值
        self.type_combo.bind("<<ComboboxSelected>>", self._on_type_selected)

        # 按钮组：使用所选类型进行购买或测试
        btn_frame = ttk.Frame(buy_panel)
        btn_frame.grid(row=0, column=4, padx=20, sticky="w")

        ttk.Button(
            btn_frame,
            text="购买下一期",
            command=lambda: self.buy(self._get_type_value(), False),
        ).pack(side="left", padx=4)

        ttk.Button(
            btn_frame,
            text="测试本期(不保存)",
            command=lambda: self.buy(self._get_type_value(), True),
            cursor="hand2",
        ).pack(side="left", padx=4)

        # 配置列权重，使按钮区域可以自适应
        buy_panel.columnconfigure(4, weight=1)

        # 第二部分：控制面板
        ctrl_panel = ttk.Frame(main_container)
        ctrl_panel.pack(fill="x", pady=5)

        self.update_btn = ttk.Button(
            ctrl_panel, text="🌐 联网更新开奖号码", command=self.update_winning_numbers
        )
        self.update_btn.pack(side="left", padx=5)

        self.check_btn = ttk.Button(
            ctrl_panel, text="🧧 批量兑奖", command=self.check_winnings
        )
        self.check_btn.pack(side="left", padx=5)

        ttk.Button(
            ctrl_panel, text="🎯 自定义选号验奖", command=self.open_manual_check_dialog
        ).pack(side="left", padx=5)

        ttk.Button(
            ctrl_panel, text="🧪 清空测试记录", command=self.clear_test_history
        ).pack(side="left", padx=5)

        ttk.Button(
            ctrl_panel, text="🗑️ 清空记录", command=self.clear_history
        ).pack(side="right", padx=5)

        # 第三部分：显示面板（使用 Notebook 分页）
        display_panel = ttk.LabelFrame(main_container, text=" 显示与统计 ", padding=5)
        display_panel.pack(fill="both", expand=True, pady=5)

        notebook = ttk.Notebook(display_panel)
        notebook.pack(fill="both", expand=True)

        # 日志页
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="日志与过程")

        self.result_area = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            bg="#ffffff",
            font=("Consolas", 11),
            padx=10,
            pady=10,
        )
        self.result_area.pack(fill="both", expand=True)

        # 配置文本颜色标签
        self.result_area.tag_config("red", foreground="#ff4d4f", font=("Consolas", 11, "bold"))
        self.result_area.tag_config("blue", foreground="#1890ff", font=("Consolas", 11, "bold"))
        self.result_area.tag_config("system", foreground="#8c8c8c")
        self.result_area.tag_config("lose", foreground="#595959", font=("Microsoft YaHei", 11, "bold"))
        self.result_area.tag_config("win_jackpot", foreground="#faad14", font=("Microsoft YaHei", 12, "bold"))
        self.result_area.tag_config("win_high", foreground="#d46b08", font=("Microsoft YaHei", 12, "bold"))
        self.result_area.tag_config("win_mid", foreground="#722ed1", font=("Microsoft YaHei", 11, "bold"))
        self.result_area.tag_config("win_low", foreground="#389e0d", font=("Microsoft YaHei", 11, "bold"))

        # 中奖汇总页
        summary_frame = ttk.Frame(notebook)
        notebook.add(summary_frame, text="中奖汇总")

        self.summary_area = scrolledtext.ScrolledText(
            summary_frame,
            wrap=tk.WORD,
            bg="#ffffff",
            font=("Consolas", 11),
            padx=10,
            pady=10,
        )
        self.summary_area.pack(fill="both", expand=True)
        self.summary_area.tag_config("title", foreground="#722ed1", font=("Microsoft YaHei", 12, "bold"))
        self.summary_area.tag_config("prize_top", foreground="#d48806", font=("Microsoft YaHei", 11, "bold"))
        self.summary_area.tag_config("prize_other", foreground="#389e0d", font=("Microsoft YaHei", 10, "bold"))

        self.refresh_win_summary()

        self.log("系统就绪。请先点击'联网更新'同步最新奖池。")

    def _on_type_selected(self, event=None):
        """类型选择事件处理：将中文名称转换为内部值"""
        selected_text = self.type_combo.get()
        if selected_text in self.type_map:
            self.type_var.set(self.type_map[selected_text])

    def _get_type_value(self):
        """获取当前选择的类型值（内部值）"""
        selected_text = self.type_combo.get()
        return self.type_map.get(selected_text, "ssq")

    def log(self, text, tag="system"):
        self.result_area.insert(tk.END, text + "\n", tag)
        self.result_area.see(tk.END)

    def load_all_data(self):
        self.purchased_tickets, self.winning_data = data.load_all_data()
        self.test_tickets = data.load_test_data()
        self.win_tickets = [
            t
            for t in self.purchased_tickets
            if t.get("prize") and t.get("prize") != "未中奖"
        ]

    def save_all_data(self):
        data.save_all_data(self.purchased_tickets, self.winning_data)
        data.save_test_data(self.test_tickets)

    def buy(self, l_type, is_test=False):
        try:
            n = int(self.num_entry.get())
            if n < 1:
                messagebox.showerror("错误", "购买数量至少为1注")
                return
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return

        if not self.winning_data[l_type]:
            messagebox.showwarning("提示", "请先点击联网更新以获取当前期数信息")
            return

        issue = (
            self.winning_data[l_type][0]["issue"]
            if is_test
            else lottery.get_next_issue(self.winning_data, l_type)
        )

        new_tickets = []
        for _ in range(n):
            ticket = lottery.generate_ticket(l_type, issue, is_test)
            new_tickets.append(ticket)

        if is_test:
            # 测试购买写入测试文件
            self.test_tickets.extend(new_tickets)
            data.save_test_data(self.test_tickets)
            mode = "【测试-最新期-不保存】"
        else:
            # 正式购买写入正式文件
            self.purchased_tickets.extend(new_tickets)
            data.save_all_data(self.purchased_tickets, self.winning_data)
            mode = "【普通-下一期】"

        self.log(
            f"✅ 成功购买 {n} 注 {('双色球' if l_type=='ssq' else '大乐透')} 期号：{issue} {mode}"
        )

    def test_buy(self):
        """同时购买两种彩票的最新一期用于测试"""
        self.buy("ssq", True)
        self.buy("dlt", True)

    def update_winning_numbers(self):
        def worker():
            self.log("📡 正在连接中国体彩/福彩数据中心...")
            try:
                self.winning_data["ssq"] = fetcher.fetch_500_data("ssq")
                self.winning_data["dlt"] = fetcher.fetch_500_data("dlt")
                self.save_all_data()
                self.root.after(
                    0,
                    lambda: self.log(
                        f"✨ 数据同步完成！最新期：SSQ-{self.winning_data['ssq'][0]['issue']} | DLT-{self.winning_data['dlt'][0]['issue']}"
                    ),
                )
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"更新失败: {e}"))

        threading.Thread(target=worker).start()

    def check_winnings(self):
        # 检查正式购买和测试购买的票据
        un_checked = [t for t in self.purchased_tickets if not t.get("checked")]
        un_checked_test = [t for t in self.test_tickets if not t.get("checked")]
        
        if not un_checked and not un_checked_test:
            self.log("💡 没有待兑奖的票据。")
            return

        self.log("\n🔍 开始扫描奖池进行兑奖...")

        # 先检查正式购买的票据
        for ticket in un_checked:
            result = lottery.check_ticket(ticket, self.winning_data)
            if result:
                self.animate_check(ticket, result)
                ticket["checked"] = True
                ticket["prize"] = result["prize"]
                if ticket["prize"] != "未中奖":
                    self.win_tickets.append(ticket)
            else:
                self.log(f"⏳ 期号 {ticket['issue']} 尚未开奖，请耐心等待。")

        # 再检查测试购买的票据（不保存到正式文件）
        for ticket in un_checked_test:
            result = lottery.check_ticket(ticket, self.winning_data)
            if result:
                self.animate_check(ticket, result)
                ticket["checked"] = True
                ticket["prize"] = result["prize"]
                if ticket["prize"] != "未中奖":
                    self.win_tickets.append(ticket)
            else:
                self.log(f"⏳ 期号 {ticket['issue']} 尚未开奖，请耐心等待。")

        # 只保存正式购买的数据
        self.save_all_data()
        # 测试票据的兑奖结果也保存（用于显示）
        data.save_test_data(self.test_tickets)
        self.refresh_win_summary()

    def animate_check(self, ticket, result):
        """模拟开奖对比动画"""
        l_type = ticket["type"]
        name = "双色球" if l_type == "ssq" else "大乐透"
        my_red, my_blue = ticket["nums"]
        win_red, win_blue = result["winning_nums"]
        hits_r = set(my_red) & set(win_red)
        hits_b = set(my_blue) & set(win_blue)
        prize = result["prize"]

        # 打印详细比对（按奖项级别上色）
        header_tag = self._prize_tag(prize)
        self.log(f"--- 兑奖单: {name} 第 {ticket['issue']} 期 ---", tag=header_tag)

        # 逐行显示号码
        self.result_area.insert(tk.END, "  我的: ")
        for n in my_red:
            self.result_area.insert(tk.END, f"{n:02d} ", "red" if n in hits_r else "")
        self.result_area.insert(tk.END, "| ")
        for n in my_blue:
            self.result_area.insert(tk.END, f"{n:02d} ", "blue" if n in hits_b else "")
        self.result_area.insert(tk.END, "\n")

        self.result_area.insert(tk.END, "  开奖: ")
        for n in win_red:
            self.result_area.insert(tk.END, f"{n:02d} ")
        self.result_area.insert(tk.END, "| ")
        for n in win_blue:
            self.result_area.insert(tk.END, f"{n:02d} ")
        self.result_area.insert(tk.END, "\n")

        # 特效逻辑（按奖项级别上色）
        if "一等奖" in prize:
            effect = "👑 🎆 👑 🎆 👑 🎆 👑\n恭喜！天选之子！\n👑 🎆 👑 🎆 👑 🎆 👑"
            tag = self._prize_tag(prize)
        elif "奖" in prize:
            effect = f"🎊 💰 恭喜中得: {prize}! 💰 🎊"
            tag = self._prize_tag(prize)
        else:
            effect = "❄️ 未中奖，离大奖又近了一步。"
            tag = self._prize_tag(prize)

        self.log(effect, tag)
        self.log("-" * 40)

    def _prize_tag(self, prize: str) -> str:
        """将奖项映射到日志颜色标签。"""
        if not prize or prize == "未中奖":
            return "lose"
        # 一等奖（最高亮）
        if "一等奖" in prize:
            return "win_jackpot"
        # 二等/三等（高亮橙）
        if ("二等奖" in prize) or ("三等奖" in prize):
            return "win_high"
        # 四等/五等（紫色）
        if ("四等奖" in prize) or ("五等奖" in prize):
            return "win_mid"
        # 六等奖及以下（绿色）
        return "win_low"

    def refresh_win_summary(self):
        """刷新"中奖汇总"页签（正式和测试分开显示）"""
        if not hasattr(self, "summary_area"):
            return
        self.summary_area.configure(state="normal")
        self.summary_area.delete("1.0", tk.END)
        self.summary_area.insert(tk.END, "🎉 历史中奖记录汇总\n", "title")
        self.summary_area.insert(tk.END, "-" * 40 + "\n\n")

        # 正式购买的中奖票据
        formal_win_tickets = [
            t for t in self.purchased_tickets
            if t.get("prize") and t.get("prize") != "未中奖"
        ]

        # 测试购买的中奖票据
        test_win_tickets = [
            t for t in self.test_tickets
            if t.get("prize") and t.get("prize") != "未中奖"
        ]

        # 显示正式中奖记录
        if formal_win_tickets:
            self.summary_area.insert(tk.END, "【正式购买】中奖记录：\n", "title")
            for t in sorted(formal_win_tickets, key=lambda x: x.get("time", "")):
                name = "双色球" if t["type"] == "ssq" else "大乐透"
                red, blue = t["nums"]
                prize = t.get("prize", "未注明")
                line = (
                    f"  {t.get('time','未知时间')} | {name} 第 {t['issue']} 期 | "
                    f"{' '.join(f'{n:02d}' for n in red)} | "
                    f"{' '.join(f'{n:02d}' for n in blue)} -> {prize}\n"
                )
                tag = "prize_top" if "一等奖" in prize else "prize_other"
                self.summary_area.insert(tk.END, line, tag)
            self.summary_area.insert(tk.END, "\n")

        # 显示测试中奖记录
        if test_win_tickets:
            self.summary_area.insert(tk.END, "【测试购买】中奖记录：\n", "title")
            for t in sorted(test_win_tickets, key=lambda x: x.get("time", "")):
                name = "双色球" if t["type"] == "ssq" else "大乐透"
                red, blue = t["nums"]
                prize = t.get("prize", "未注明")
                line = (
                    f"  {t.get('time','未知时间')} | {name} 第 {t['issue']} 期 | "
                    f"{' '.join(f'{n:02d}' for n in red)} | "
                    f"{' '.join(f'{n:02d}' for n in blue)} -> {prize}\n"
                )
                tag = "prize_top" if "一等奖" in prize else "prize_other"
                self.summary_area.insert(tk.END, line, tag)
            self.summary_area.insert(tk.END, "\n")

        if not formal_win_tickets and not test_win_tickets:
            self.summary_area.insert(tk.END, "目前还没有任何中奖记录。\n")

        self.summary_area.configure(state="disabled")

    def open_manual_check_dialog(self):
        """打开自定义选号验奖窗口"""
        if not (self.winning_data["ssq"] or self.winning_data["dlt"]):
            messagebox.showwarning("提示", "请先联网更新最新开奖号码。")
            return

        win = tk.Toplevel(self.root)
        win.title("自定义选号验奖")
        win.geometry("480x420")
        win.grab_set()

        ttk.Label(win, text="彩票类型:").pack(anchor="w", padx=10, pady=(10, 2))
        type_var = tk.StringVar(value="ssq")
        type_frame = ttk.Frame(win)
        type_frame.pack(anchor="w", padx=10)
        ttk.Radiobutton(type_frame, text="双色球", variable=type_var, value="ssq").pack(
            side="left", padx=4
        )
        ttk.Radiobutton(type_frame, text="大乐透", variable=type_var, value="dlt").pack(
            side="left", padx=4
        )

        ttk.Label(win, text="期号（可从下拉选择或手动输入）:").pack(
            anchor="w", padx=10, pady=(10, 2)
        )
        issue_values = [w["issue"] for w in self.winning_data["ssq"] or self.winning_data["dlt"]]
        issue_var = tk.StringVar(value=issue_values[0] if issue_values else "")
        issue_box = ttk.Combobox(win, textvariable=issue_var, values=issue_values)
        issue_box.pack(fill="x", padx=10)

        ttk.Label(
            win,
            text=(
                "号码输入规则：每行一注\n"
                "双色球：6个红球空格分隔，后接竖线，再写1个蓝球，例如：\n"
                "  01 02 03 04 05 06 | 10\n"
                "大乐透：5个前区 + 竖线 + 2个后区，例如：\n"
                "  01 02 03 04 05 | 06 07\n"
            ),
            justify="left",
        ).pack(anchor="w", padx=10, pady=(10, 2))

        text = scrolledtext.ScrolledText(
            win, wrap=tk.WORD, height=10, font=("Consolas", 10)
        )
        text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        def do_check():
            l_type = type_var.get()
            issue = issue_var.get().strip()
            if not issue:
                messagebox.showerror("错误", "请输入期号。")
                return

            # 检查是否存在该期开奖号码
            win_info = next(
                (
                    w
                    for w in self.winning_data.get(l_type, [])
                    if w["issue"] == issue
                ),
                None,
            )
            if not win_info:
                messagebox.showerror("错误", f"未找到 {issue} 期的开奖号码，请确认已联网更新。")
                return

            lines = [ln.strip() for ln in text.get("1.0", tk.END).splitlines() if ln.strip()]
            if not lines:
                messagebox.showwarning("提示", "请先输入至少一行号码。")
                return

            self.log(f"\n🎯 自定义验奖 - {('双色球' if l_type=='ssq' else '大乐透')} 第 {issue} 期")

            for idx, line in enumerate(lines, start=1):
                try:
                    parts = [p.strip() for p in line.split("|")]
                    reds = [int(x) for x in parts[0].split()]
                    blues = [int(x) for x in parts[1].split()] if len(parts) > 1 else []
                except Exception:
                    self.log(f"第 {idx} 行格式错误，已跳过。")
                    continue

                if l_type == "ssq":
                    if len(reds) != 6 or len(blues) != 1:
                        self.log(f"第 {idx} 行数量不符（需要 6 红 1 蓝），已跳过。")
                        continue
                else:
                    if len(reds) != 5 or len(blues) != 2:
                        self.log(f"第 {idx} 行数量不符（需要 5 前区 2 后区），已跳过。")
                        continue

                ticket = {
                    "type": l_type,
                    "issue": issue,
                    "nums": [reds, blues],
                    "checked": True,
                    "time": "",
                    "prize": "",
                }
                result = lottery.check_ticket(ticket, self.winning_data)
                if not result:
                    self.log(f"第 {idx} 行：未找到该期开奖号码。")
                    continue

                prize = result["prize"]
                hits_r = result["hits_red"]
                hits_b = result["hits_blue"]

                msg = (
                    f"第 {idx} 行 -> 红命中 {hits_r} 个，蓝命中 {hits_b} 个，结果：{prize}"
                )
                self.log(msg, tag="win" if prize != "未中奖" else "system")

                if prize != "未中奖":
                    # 记录到中奖汇总中（但不写入持久化购票记录，仅展示用途）
                    t_copy = ticket.copy()
                    t_copy["prize"] = prize
                    self.win_tickets.append(t_copy)

            self.refresh_win_summary()

        ttk.Button(btn_frame, text="开始检查", command=do_check).pack(
            side="left", padx=5
        )
        ttk.Button(btn_frame, text="关闭", command=win.destroy).pack(
            side="right", padx=5
        )

    def clear_history(self):
        if messagebox.askyesno("确认", "确定清空购票历史吗？"):
            self.purchased_tickets = []
            self.save_all_data()
            self.result_area.delete("1.0", tk.END)
            self.log("所有历史记录已销毁。")

    def clear_test_history(self):
        """清空测试购买记录（包括测试中奖记录，不影响正式购买）"""
        if messagebox.askyesno("确认", "确定清空所有测试购买记录吗？\n（包括测试中奖记录，不影响正式购买记录）"):
            self.test_tickets = []
            data.save_test_data(self.test_tickets)
            self.refresh_win_summary()  # 刷新中奖汇总，移除测试中奖记录
            self.log("测试购买记录（包括中奖记录）已清空。", tag="system")


if __name__ == "__main__":
    root = tk.Tk()
    app = LotteryApp(root)
    root.mainloop()
