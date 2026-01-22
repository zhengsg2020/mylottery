## 项目简介

这是一个**自嗨彩票模拟器**，支持：
- **网页版**：Flask
- **桌面版**：Tkinter

开奖数据支持从 500.com 拉取近 30 期数据；购票/兑奖记录会落盘到本地 `data/`（该目录已被 `.gitignore` 排除，适合直接上传 Git）。

## 目录结构（精简版）

```
mylottery/
├─ start.bat          # Windows 一键启动入口（推荐）
├─ scripts/           # Windows 一键脚本
├─ src/
│  ├─ common/        # 配置、数据持久化、抓取、业务逻辑
│  ├─ web/           # Flask Web
│  └─ desktop/       # Tkinter GUI
├─ static/
│  └─ img/           # Web/桌面共用图标
├─ requirements.txt
└─ .gitignore
```

## 环境要求

- Python 3.x

## 一键启动（Windows 推荐）

下载后**直接双击**：
- `start.bat`：菜单式启动（最推荐）

脚本会自动创建虚拟环境 `.venv` 并安装依赖（首次运行需要联网下载依赖）。

你也可以直接双击：
- `scripts/quick_start.bat`：菜单式启动
- `scripts/run_web.bat`：直接启动网页版
- `scripts/run_desktop.bat`：直接启动桌面版
- `scripts/setup.bat`：只安装/更新依赖

## 命令行运行（可选）

### 运行网页版（Flask）

```bash
python src/web/app.py
```

默认端口 `5000`，浏览器打开 `http://127.0.0.1:5000`。

#### 网页版功能开关（环境变量）

- `LOTTERY_WEB_ENABLE_UPDATE=0`：关闭联网更新
- `LOTTERY_WEB_ENABLE_BUY=0`：关闭购买
- `LOTTERY_WEB_ENABLE_CHECK=0`：关闭兑奖/验奖

### 运行桌面版（Tkinter）

```bash
python src/desktop/app.py
```

## 数据文件说明

运行后会自动创建：
- `data/lottery_data.json`：正式购买与开奖数据
- `data/lottery_test_data.json`：测试购买数据

`data/` 为运行时生成目录，已在 `.gitignore` 中排除，避免污染仓库。

## 免责声明

本项目仅供学习与娱乐使用。
