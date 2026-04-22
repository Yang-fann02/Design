# 学生消费统计及可视化平台

基于 **Flask + SQLite + ECharts 5** 的轻量单页数据看板，用于展示、筛选与管理学生消费记录，包含汇总指标、类别占比饼图、每日消费趋势柱图和明细表。

---

## 目录

1. [项目目标与适用场景](#1-项目目标与适用场景)
2. [技术栈与依赖](#2-技术栈与依赖)
3. [目录结构](#3-目录结构)
4. [快速启动](#4-快速启动)
5. [后端架构与数据流](#5-后端架构与数据流)
6. [REST API 说明](#6-rest-api-说明)
7. [前端页面与交互](#7-前端页面与交互)
8. [CSS 分层体系](#8-css-分层体系)
9. [日期筛选规则](#9-日期筛选规则)
10. [常见开发任务](#10-常见开发任务)
11. [本地验证清单](#11-本地验证清单)
12. [已知约束](#12-已知约束)
13. [可扩展方向](#13-可扩展方向)

---

## 1. 项目目标与适用场景

本项目适合以下场景：

- 课程作业或毕业设计中的"消费行为统计与可视化"主题
- 快速验证"小体量数据看板"完整链路（存储 → 聚合 → 可视化）
- 作为 Flask 单页应用、CSS 分层治理、ECharts 集成的参考模板

核心价值在于将"可运行的业务看板"压缩到少量文件内，保持可读、可改、可继续扩展。

---

## 2. 技术栈与依赖

### 后端

| 组件 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.9+ | 运行环境 |
| Flask | ≥ 2.0 | Web 路由与模板渲染 |
| pandas | ≥ 1.3 | 分组统计、日期转换 |
| sqlite3 | 标准库 | 数据持久化 |

### 前端

| 组件 | 引入方式 | 用途 |
|------|----------|------|
| 原生 HTML / CSS / JS | — | 页面结构与交互 |
| ECharts 5.4.3 | CDN | 饼图、柱状图可视化 |

### 依赖文件

```
requirements.txt
```

安装命令：

```bash
pip install -r requirements.txt
```

---

## 3. 目录结构

```text
Design-develop/
├── backend.py                          # Flask 入口、数据库访问、统计逻辑
├── requirements.txt                    # Python 依赖
├── student_expense_record.db           # SQLite 数据库（运行后自动创建）
├── README.md                           # 本文件（项目总说明）
├── DATABASE.md                         # 数据库设计详细说明
├── templates/
│   └── frontend.html                   # 单页模板 + 内联前端脚本
├── static/
│   ├── icons/
│   │   └── money-bag.png               # 应用图标
│   └── css/
│       ├── frontend.PC-Mphone.css      # CSS 总入口（仅做 @import）
│       ├── frontend.PC.tokens.css      # 设计令牌 / 全局变量 / reset
│       ├── frontend.PC.layout.css      # 页面骨架 / 侧栏 / 顶栏 / 视图动画
│       ├── frontend.PC.theme.css       # 主题切换组件与暗色覆盖
│       ├── frontend.PC.components.css  # 通用组件（按钮、卡片等）
│       ├── frontend.PC.dashboard.css   # 图表、指标卡、表格业务样式
│       ├── frontend.PC.modal.css       # 日期筛选弹窗
│       ├── frontend.Mphone.responsive.css  # 移动端响应式覆盖（≤768px / ≤480px）
│       └── README.md                   # CSS 分层维护手册
└── backups/                            # 文档备份（不进入运行时）
```

---

## 4. 快速启动

### 4.1 安装依赖

```bash
# 可选：创建虚拟环境
python -m venv .venv

# Windows PowerShell
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 4.2 启动服务

```bash
python backend.py
```

默认监听：

- Host：`0.0.0.0`
- Port：`8000`

浏览器访问：[http://127.0.0.1:8000](http://127.0.0.1:8000)

### 4.3 数据库路径配置

默认数据库文件：`student_expense_record.db`（与 `backend.py` 同目录）

通过环境变量覆盖：

```bash
# Windows PowerShell
$env:DATABASE_PATH = "D:\data\my_expenses.db"
python backend.py

# macOS / Linux
DATABASE_PATH=/data/my_expenses.db python backend.py
```

若 `DATABASE_PATH` 为相对路径，以 `backend.py` 所在目录为基准解析。

---

## 5. 后端架构与数据流

`backend.py` 按职责分为四层：

| 层次 | 函数 | 说明 |
|------|------|------|
| 存储层 | `get_db()` `init_db()` `expense_row_count()` | 连接管理、表初始化、行数查询 |
| 读取层 | `get_all_expenses()` `get_all_categories()` | 原始数据读取为 DataFrame |
| 统计层 | `get_statistics()` `get_date_index()` | 筛选、聚合、日期索引构建 |
| 接口层 | Flask 路由 `/` 及各 `/api/*` | 参数解析、JSON 序列化 |

请求数据流（简化）：

```
前端 fetch('/api/statistics?...')
  → 后端读 expenses 表 → pd.DataFrame
  → 按参数筛选（日期 / 类别）
  → groupby 聚合：总额、日均、类别占比、每日明细
  → jsonify 返回
  → 前端刷新指标卡 / 饼图 / 柱图 / 明细表
```

---

## 6. REST API 说明

### `GET /`

返回单页应用模板 `templates/frontend.html`。

---

### `GET /api/statistics`

按条件统计消费数据，供图表与表格渲染使用。

#### 查询参数

支持两种筛选模式（互斥，`only_month` 有效时优先）：

| 参数 | 类型 | 说明 |
|------|------|------|
| `start_date` | `YYYY-MM-DD` | 区间起始（可单独使用） |
| `end_date` | `YYYY-MM-DD` | 区间结束（可单独使用） |
| `only_month` | `1–12` | 跨年同月筛选（忽略年份） |
| `only_dom` | `1–31` | 与 `only_month` 配合，进一步限定日 |
| `only_category` | 字符串 | 类别精确匹配（可叠加在任意模式上） |

#### 返回字段

```jsonc
{
  "total_expense": 1280.50,        // 总消费金额
  "daily_average": 42.68,          // 日均消费
  "category_expense": {            // 按类别汇总
    "早饭": 320.00,
    "午饭": 480.00
  },
  "daily_trend": {                 // 按日期汇总（YYYY-MM-DD → 金额）
    "2026-04-01": 85.00
  },
  "daily_detail": {                // 每日明细（YYYY-MM-DD → [{类别, 金额}]）
    "2026-04-01": [
      {"类别": "早饭", "金额": 15.00}
    ]
  },
  "date_range": {"min": "2026-04-01", "max": "2026-04-30"},
  "raw_table": [                   // 明细行数组，供表格渲染
    {"日期": "2026-04-01", "类别": "早饭", "金额": 15.00}
  ],
  "has_data": true                 // 筛选结果是否非空
}
```

#### 示例

```http
# 按日期区间
GET /api/statistics?start_date=2026-04-01&end_date=2026-04-30

# 跨年同月（所有年份 4 月）
GET /api/statistics?only_month=4

# 跨年同月同日（所有年份 4 月 20 日）
GET /api/statistics?only_month=4&only_dom=20

# 区间 + 类别
GET /api/statistics?start_date=2026-04-01&end_date=2026-04-30&only_category=午饭
```

---

### `GET /api/date_index`

构建前端日期弹窗所需的可选年 / 月 / 日索引。

```jsonc
{
  "has_data": true,
  "date_index": {
    "years": [2025, 2026],
    "months_by_year": {"2025": [11, 12], "2026": [1, 2, 3, 4]},
    "days_by_year_month": {"2026-04": [1, 5, 10, 20]},
    "date_range": {"min": "2025-11-01", "max": "2026-04-22"}
  }
}
```

---

### `GET /api/categories`

返回所有出现过的消费类别（含内置默认 16 类）。

```jsonc
{"categories": ["交通", "医疗", "午饭", "娱乐", ...]}
```

---

### `POST /api/add_expense`

新增一条消费记录。

请求体：

```jsonc
{"date": "2026-04-22", "category": "午饭", "amount": 18.5}
```

返回：

```jsonc
{"success": true, "id": 128}
```

---

### `GET /api/expenses_by_date`

查询某日所有记录（含 `id`，供变更页使用）。

```http
GET /api/expenses_by_date?date=2026-04-22
```

返回：

```jsonc
{"records": [{"id": 128, "date": "2026-04-22", "category": "午饭", "amount": 18.5}]}
```

---

### `POST /api/update_expense`

更新单条记录。

请求体：

```jsonc
{"id": 128, "date": "2026-04-22", "category": "晚饭", "amount": 32.0}
```

返回：`{"success": true}`

---

### `POST /api/delete_expense`

删除单条记录。

请求体：`{"id": 128}`

返回：`{"success": true}`

---

## 7. 前端页面与交互

前端逻辑集中在 `templates/frontend.html`（HTML 结构 + 内联 `<script>`）。

### 三个主视图

| 视图 ID | 菜单项 | 内容 |
|---------|--------|------|
| `overview` | 概览 | 指标卡 + 饼图 + 柱图 |
| `statistics` | 统计 | 与概览图表相同，独立实例 |
| `details` | 明细 | 消费明细表 + 增删改操作 |

### 日期筛选弹窗

- 支持：仅年、仅月、年+月、年+月+日、跨年同月、跨年同月同日
- 顶栏显示当前筛选条件，一键清除

### ECharts 图表

| 实例 ID | 视图 | 类型 |
|---------|------|------|
| `pc-category-chart` | 概览 | 圆环饼图（类别占比） |
| `pc-trend-chart` | 概览 | 柱状图（每日消费） |
| `pc-category-chart2` | 统计 | 同概览饼图 |
| `pc-trend-chart2` | 统计 | 同概览柱图 |

四个实例由同一套 `pcRenderUI()` 数据驱动，主题切换时重绘 option 而不重新请求接口（有缓存时）。

### 其他交互

- **主题切换**：亮色 / 暗色，状态持久化到 `localStorage`（键：`fd-theme`）
- **桌面侧栏**：可拖拽调整宽度
- **移动端侧栏**：抽屉式，汉堡按钮触发，遮罩点击收起

---

## 8. CSS 分层体系

CSS 采用"单入口 + 分层模块"方案，详见 `static/css/README.md`。

加载顺序（`frontend.PC-Mphone.css` 按此顺序 `@import`）：

```
tokens → layout → theme → components → dashboard → modal → responsive
```

各层职责：

| 文件 | 职责 |
|------|------|
| `tokens` | 设计令牌（颜色、圆角、阴影、动效变量）与全局 reset |
| `layout` | 页面骨架、侧栏、顶栏、视图切换动画 |
| `theme` | 主题切换组件 + `html[data-theme="dark"]` 暗色覆盖 |
| `components` | 跨页面通用组件（按钮、卡片、标题等） |
| `dashboard` | 指标卡、图表容器、明细表业务样式 |
| `modal` | 日期筛选弹窗全套 UI |
| `responsive` | `≤768px` / `≤480px` 移动端覆盖 |

---

## 9. 日期筛选规则

前端 `pcBuildRangeFromFilter()` 生成查询参数，后端 `get_statistics()` 解析：

| 用户选择 | 传参形式 | 语义 |
|---------|----------|------|
| 只选年 | `start_date=YYYY-01-01&end_date=YYYY-12-31` | 该年全年 |
| 年 + 月 | `start_date=YYYY-MM-01&end_date=YYYY-MM-28/30/31` | 该年该月 |
| 年 + 月 + 日 | `start_date=end_date=YYYY-MM-DD` | 单日 |
| 只选月 | `only_month=M` | 所有年份的该月 |
| 只选月 + 日 | `only_month=M&only_dom=D` | 所有年份该月该日 |

---

## 10. 常见开发任务

### 新增 API 返回字段

1. 修改 `backend.py` 中 `get_statistics()` 的返回 dict
2. 在 `frontend.html` 的 `pcRenderUI()` 中消费新字段
3. 如有展示需要，在对应 CSS 层补充样式

### 修改图表配色

1. 调整 `frontend.html` 内 `pcChart` / `PC_CAT_COLORS` 色板对象
2. 同步检查 dark / light 两套颜色
3. 验证 tooltip、legend、axis 文字可读性

### 调整移动端布局

1. 优先改 `frontend.Mphone.responsive.css`
2. 避免反向改桌面文件导致覆盖冲突
3. 重点回归：侧栏抽屉、顶栏工具条、图表高度、表格滚动

### 新增消费类别

1. 在 `backend.py` `get_all_categories()` 的 `default_cats` 列表追加
2. 在 `frontend.html` `PC_CAT_COLORS` 对象追加对应颜色

---

## 11. 本地验证清单

每次改动后建议验证：

- [ ] 服务启动无报错，首页正常打开
- [ ] `GET /api/statistics` 与 `GET /api/date_index` 返回正确
- [ ] 三个视图切换正常，图表数据正确
- [ ] 日期筛选各种组合均能得到正确结果
- [ ] 亮色 / 暗色主题切换后图表与页面配色同步
- [ ] 新增、修改、删除记录后数据刷新
- [ ] 窄屏（≤768px / ≤480px）下导航、图表、表格可用

---

## 12. 已知约束

- `date` 字段以文本存储，写入时须严格遵循 `YYYY-MM-DD` 格式，排序依赖字符串顺序
- `amount` 为浮点型，展示时前端格式化为 `¥XX.XX`
- 无用户系统、无鉴权、无限流，仅适合本地或受信任内网使用
- 前端脚本内联在模板中，适合中小体量，后续可拆为独立静态 JS 模块
- 静态文件缓存在开发模式下被禁用（`SEND_FILE_MAX_AGE_DEFAULT = 0`），生产部署时应配合反向代理缓存

---

## 13. 可扩展方向

按优先级建议：

1. **数据导入**：支持 CSV / Excel 批量导入消费记录
2. **高级筛选**：按金额区间、多类别组合筛选
3. **数据导出**：将筛选结果导出为 CSV / Excel
4. **单元测试**：补充 `pytest` 对统计函数的单元测试
5. **前端模块化**：将内联 JS 拆分为独立 ES Module 文件
6. **生产部署**：Gunicorn / uWSGI + Nginx 反向代理，添加 HTTPS
7. **安全加固**：输入校验加强、CSRF 防护、速率限制

---

## 参考文档

| 文档 | 说明 |
|------|------|
| `DATABASE.md` | 数据库表结构、字段说明、迁移记录 |
| `static/css/README.md` | CSS 分层架构与维护规范（详版） |
| `requirements.txt` | Python 依赖声明 |
