# 学生消费统计及可视化平台

基于 **Flask + SQLite + pandas + requests + ECharts 5** 的单页应用：消费记录的增删改查、按条件统计与图表展示；内置 **AI 消费分析助手**（服务端从数据库汇总上下文，经兼容 OpenAI 的聊天 API **流式**返回）。

---

## 目录

1. [项目目标与适用场景](#1-项目目标与适用场景)
2. [技术栈与依赖](#2-技术栈与依赖)
3. [目录结构](#3-目录结构)
4. [快速启动](#4-快速启动)
5. [AI 密钥配置文件](#5-ai-密钥配置文件)
6. [后端架构与数据流](#6-后端架构与数据流)
7. [REST API 说明](#7-rest-api-说明)
8. [AI 对话接口（SSE）](#8-ai-对话接口sse)
9. [前端页面与交互](#9-前端页面与交互)
10. [CSS 分层体系](#10-css-分层体系)
11. [日期筛选规则](#11-日期筛选规则)
12. [常见开发任务](#12-常见开发任务)
13. [本地验证清单](#13-本地验证清单)
14. [已知约束与安全提示](#14-已知约束与安全提示)
15. [可扩展方向](#15-可扩展方向)
16. [参考文档](#16-参考文档)

---

## 1. 项目目标与适用场景

- 课程作业或毕业设计中的「消费行为统计与可视化」主题  
- 验证小体量数据看板：SQLite → pandas 聚合 → JSON API → ECharts 与表格  
- 参考实现：Flask 单页、CSS 分模块、`text/event-stream` 流式前端、本地密钥文件与 Git 隔离  

---

## 2. 技术栈与依赖

### 后端

| 组件 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.9+ | 运行环境 |
| Flask | ≥ 2.3 | 路由、模板、静态资源 |
| pandas | ≥ 2.0 | 筛选、分组、日期处理 |
| requests | ≥ 2.28（见 `requirements.txt`） | AI 接口 HTTP、重试、流式响应体 |
| sqlite3 | 标准库 | SQLite |

### 前端

| 组件 | 引入方式 | 用途 |
|------|----------|------|
| 原生 HTML / CSS / JS | `templates/frontend.html` | 视图、请求、SSE 解析 |
| ECharts 5.4.3 | CDN | 类别饼图、每日柱状图 |

```bash
pip install -r requirements.txt
```

---

## 3. 目录结构

```text
Design/                    # 仓库根目录名称以本机为准
├── backend.py             # Flask、数据库、统计、AI 代理
├── requirements.txt
├── student_expense_record.db   # 默认 SQLite（运行 init_db 后可用）
├── ai_api_secrets.example.json  # AI 配置模板（可提交，无真实密钥）
├── ai_api_secrets.json     # 真实密钥（勿提交；见 .gitignore）
├── README.md
├── DATABASE.md
├── .gitignore
├── templates/
│   └── frontend.html      # 单页 + 内联脚本
├── static/
│   ├── icons/
│   │   └── money-bag.png
│   └── css/
│       ├── frontend.PC-Mphone.css   # 样式总入口
│       ├── frontend.PC.tokens.css
│       ├── frontend.PC.layout.css
│       ├── frontend.PC.theme.css
│       ├── frontend.PC.components.css
│       ├── frontend.PC.dashboard.css
│       ├── frontend.PC.modal.css
│       ├── frontend.Mphone.responsive.css
│       ├── frontend.PC.ai-chat.css
│       └── README.md      # CSS 分层说明
└── backups/               # 本地备份（不参与运行）
```

---

## 4. 快速启动

### 4.1 虚拟环境与依赖

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4.2 启动

```bash
python backend.py
```

启动时调用 `init_db()`：创建 `expenses` 表（若不存在），并按需完成旧库 `category` NOT NULL 迁移。

默认监听 **`0.0.0.0:8000`**：[http://127.0.0.1:8000](http://127.0.0.1:8000)

### 4.3 数据库路径

默认与 `backend.py` 同目录的 `student_expense_record.db`。覆盖方式：

```powershell
$env:DATABASE_PATH = "D:\data\my_expenses.db"
python backend.py
```

```bash
DATABASE_PATH=/data/my_expenses.db python backend.py
```

相对路径相对于 `backend.py` 所在目录。

---

## 5. AI 密钥配置文件

密钥**不写进** `backend.py`，由 **`ai_api_secrets.json`**（与 `backend.py` 同目录）或环境变量提供。

| 方式 | 说明 |
|------|------|
| **推荐** | 复制 `ai_api_secrets.example.json` 为 `ai_api_secrets.json`，填写 `api_key`；可选 `api_url`、`model`。 |
| **自定义路径** | 设置环境变量 `AI_API_SECRETS_PATH`（绝对路径，或相对于 `backend.py` 所在目录的相对路径）。 |
| **回退** | 若 JSON 中无有效 `api_key`，再读取 `MOARK_API_KEY` 或 `OPENAI_API_KEY`（便于 CI/服务器）。 |

`ai_api_secrets.json` 已列入 **`.gitignore`**，请勿将含真实密钥的文件提交到远程仓库。

**示例字段**（与 `ai_api_secrets.example.json` 一致）：

```json
{
  "api_key": "你的密钥",
  "api_url": "https://api.moark.com/v1/chat/completions",
  "model": "MiniMax-M2.7"
}
```

`api_url`、`model` 可省略时使用代码内与示例相同的默认值（仅 `api_key` 为敏感信息）。

---

## 6. 后端架构与数据流

| 层次 | 主要符号 | 说明 |
|------|-----------|------|
| 存储 | `get_db()`、`init_db()`、`expense_row_count()` | 连接、建表/迁移、行数 |
| 读取 | `get_all_expenses()`、`get_all_categories()` | DataFrame / 类别列表 |
| 统计 | `get_statistics()`、`get_date_index()` | 日期与类别筛选、聚合 |
| HTTP | 各 `/api/*`、`index()` | JSON 或 SSE |
| AI | `_ai_secrets_file_path()`、`_load_moark_ai_config()`、`_parse_time_range_with_history()`、`_build_expense_context()`、`api_ai_chat()` | 读配置、解析用户时间/类别、拼摘要、转发流式补全 |

统计主路径：`GET /api/statistics` → 读 `expenses` → pandas → `jsonify` → 前端更新指标与图表。

---

## 7. REST API 说明

### `GET /`

渲染 `templates/frontend.html`。

### `GET /api/statistics`

**查询参数**：`start_date`、`end_date`（`YYYY-MM-DD`）；或 `only_month`（1–12）、可选 `only_dom`（1–31）；均可加 `only_category`。

**返回**（节选）：`total_expense`、`daily_average`、`category_expense`、`daily_trend`、`daily_detail`、`date_range`、`raw_table`、`has_data`。

```http
GET /api/statistics?start_date=2026-04-01&end_date=2026-04-30
GET /api/statistics?only_month=4&only_dom=20
```

### `GET /api/date_index`

返回 `has_data` 与 `date_index`（`years`、`months_by_year`、`days_by_year_month`、`date_range`），供日期弹窗使用。

### `GET /api/categories`

`{"categories":[...]}`：内置类别与库中类别合并去重。

### `POST /api/add_expense`

JSON：`date`、`category`、`amount` → `{"success":true,"id":...}` 或 400。

### `GET /api/expenses_by_date?date=YYYY-MM-DD`

该日所有记录（含 `id`）。

### `POST /api/update_expense` / `POST /api/delete_expense`

更新或删除单条；请求体含 `id` 等字段。

---

## 8. AI 对话接口（SSE）

### `POST /api/ai_chat`

- **Body**：`{"messages":[{"role":"user","content":"..."}, ...]}`  
- **响应**：`text/event-stream`；增量为 `data: {"t":"..."}`；结束为 `data: [DONE]`；错误为 `data: {"error":"..."}` 后 `[DONE]`  

流程简述：从对话中推断时间范围与类别 → `_build_expense_context()` 生成文本摘要 → 与系统提示词合并 → 向 `api_url` 发起流式 `POST`（Bearer `api_key`）。

未配置有效密钥时，流内返回说明性错误（提示创建 `ai_api_secrets.json` 等），不暴露密钥内容。

---

## 9. 前端页面与交互

逻辑在 `templates/frontend.html`。

| 视图 | 内容 |
|------|------|
| 概览 | 指标卡、饼图、柱图 |
| 统计 | 独立图表实例 |
| 明细 | 表格与增删改 |
| AI 助手 | SSE 聊天；样式见 `frontend.PC.ai-chat.css` |

主题亮/暗、侧栏（桌面可调宽 / 移动抽屉）、日期筛选弹窗与后端查询参数一致。

---

## 10. CSS 分层体系

唯一串联入口：`static/css/frontend.PC-Mphone.css`。

```
tokens → layout → theme → components → dashboard → modal → responsive → ai-chat
```

细则见 `static/css/README.md`。

---

## 11. 日期筛选规则

| 用户意图 | 典型参数 |
|----------|-----------|
| 整年 | `start_date=YYYY-01-01&end_date=YYYY-12-31` |
| 年+月 | 该月首日至末日 |
| 单日 | `start_date` = `end_date` = `YYYY-MM-DD` |
| 跨年同月 | `only_month=M` |
| 跨年同月同日 | `only_month=M&only_dom=D` |

可与 `only_category` 组合。

---

## 12. 常见开发任务

| 任务 | 位置 |
|------|------|
| 统计字段 | `get_statistics()` + `frontend.html` |
| 图表配色 | 模板内 ECharts option / 色板 |
| 移动端 | `frontend.Mphone.responsive.css` |
| 默认类别 | `get_all_categories()` + 前端颜色映射 |
| AI 提示与摘要 | `_AI_SYSTEM_PROMPT`、`_build_expense_context()` |
| AI 接入点 | `_load_moark_ai_config()`、`api_ai_chat()` |

---

## 13. 本地验证清单

- [ ] `python backend.py` 正常，首页可开  
- [ ] `/api/statistics`、`/api/date_index`、`/api/categories` 正常  
- [ ] 三主视图与日期筛选、增删改  
- [ ] 亮/暗主题下图表可读  
- [ ] 窄屏布局可用  
- [ ] 配置 `ai_api_secrets.json` 后 AI 流式回复正常；未配置时错误提示合理  

---

## 14. 已知约束与安全提示

- `date` 须为 `YYYY-MM-DD` 文本排序语义（详见 `DATABASE.md`）。  
- `amount` 须大于 0，写入两位小数。  
- **无用户鉴权**：仅适合本机或可信内网。  
- `SEND_FILE_MAX_AGE_DEFAULT = 0`：开发时静态资源不缓存。  
- **AI**：依赖外网；密钥仅存于被忽略的本地文件或环境变量，**不要**把 `ai_api_secrets.json` 推送到公开仓库。  

---

## 15. 可扩展方向

1. CSV / Excel 批量导入  
2. 金额区间、多类别筛选  
3. 筛选结果导出  
4. `pytest` 覆盖统计与日期解析  
5. 前端脚本模块化  
6. 生产 WSGI + 反向代理 + HTTPS  
7. CSRF、校验、限流  

---

## 16. 参考文档

| 文件 | 说明 |
|------|------|
| `DATABASE.md` | 表结构、字段、迁移、SQL 示例 |
| `static/css/README.md` | CSS 分层与导入顺序 |
| `ai_api_secrets.example.json` | AI 配置字段模板 |
| `requirements.txt` | Python 依赖 |
