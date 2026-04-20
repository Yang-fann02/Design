# 学生消费统计及可视化平台

基于 Flask + SQLite + ECharts 的单页数据看板应用，用于展示学生消费数据的汇总指标、类别占比、每日趋势和明细表。

项目当前已支持：

- 多视图单页切换（概览 / 统计 / 明细）
- 明暗主题切换（含本地持久化）
- 年 / 月 / 日多模式日期筛选（含跨年份同月同日筛选）
- PC 与移动端响应式布局（移动端侧栏抽屉）
- 后端统一统计聚合接口 + 日期索引接口

---

## 1. 项目目标与使用场景

这个项目适合以下场景：

- 课程作业或毕业设计中的“消费行为统计与可视化”主题
- 快速验证“小体量数据看板”完整链路（存储 -> 聚合 -> 可视化）
- 作为 Flask 单页应用、CSS 分层治理、ECharts 集成的参考模板

核心价值是把“可运行的业务看板”压缩到少量文件，保持可读、可改、可继续扩展。

---

## 2. 技术栈与依赖

### 后端

- Python 3.9+（建议）
- Flask（Web 路由与模板渲染）
- pandas（分组统计、日期转换与聚合）
- sqlite3（Python 标准库，数据存储）

### 前端

- 原生 HTML/CSS/JavaScript（无前端构建工具）
- ECharts 5（CDN 引入，用于饼图和折线图）

### Python 依赖文件

见 `requirements.txt`：

- `flask>=2.0.0`
- `pandas>=1.3.0`

---

## 3. 目录结构说明

```text
Design-develop/
├─ backend.py                         # Flask 入口、数据库访问、统计与日期索引逻辑
├─ requirements.txt                   # Python 依赖
├─ student_expense_record.db          # SQLite 数据库（运行后生成 / 使用）
├─ templates/
│  └─ frontend.html                   # 单页模板 + 前端主逻辑（内联 JS）
└─ static/
   ├─ icons/
   │  └─ money-bag.png
   └─ css/
      ├─ frontend.PC-Mphone.css       # CSS 总入口（只做 import）
      ├─ frontend.PC.tokens.css       # 设计令牌 / 变量 / 全局基线
      ├─ frontend.PC.layout.css       # 页面骨架 / 侧栏 / 顶栏 / 视图布局
      ├─ frontend.PC.theme.css        # 主题切换组件与 dark 覆盖
      ├─ frontend.PC.components.css   # 按钮/卡片等通用组件层
      ├─ frontend.PC.dashboard.css    # 图表、指标卡、表格业务层
      ├─ frontend.PC.modal.css        # 日期筛选弹窗层
      ├─ frontend.Mphone.responsive.css # 768/480 响应式覆盖层
      └─ README.md                    # 样式体系详细维护文档
```

> 说明：`static/css/README.md` 已经是细粒度样式维护手册。根目录本文档主要覆盖项目级信息与运行维护流程。

---

## 4. 快速启动

### 4.1 安装依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

建议使用虚拟环境（可选）：

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
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

浏览器访问：

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

### 4.3 数据库路径配置

默认数据库文件名：`student_expense_record.db`

可以通过环境变量覆盖：

```bash
# Windows PowerShell
$env:DATABASE_PATH="D:\data\student_expense_record.db"
python backend.py
```

如果 `DATABASE_PATH` 是相对路径，后端会按 `backend.py` 所在目录解析。

---

## 5. 后端架构与数据流

后端单文件在 `backend.py`，职责可以概括为四层：

1. **存储层**：`get_db()`、`init_db()`、`expense_row_count()`
2. **数据读取层**：`get_all_expenses()`
3. **统计层**：`get_statistics()`、`get_date_index()`
4. **接口层**：`/`、`/api/statistics`、`/api/date_index`

请求数据流（简化）：

1. 前端 `fetch('/api/statistics?...')`
2. 后端读取 `expenses` 表
3. pandas 执行筛选与聚合
4. 返回 JSON
5. 前端刷新指标卡 / 图表 / 表格

---

## 6. 数据库设计

后端会在启动时执行 `init_db()`，自动创建 `expenses` 表（如果不存在）：

```sql
CREATE TABLE IF NOT EXISTS expenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  date TEXT NOT NULL,
  category TEXT NOT NULL,
  amount REAL NOT NULL
);
```

字段说明：

- `date`：消费日期，建议格式 `YYYY-MM-DD`
- `category`：消费类别（如日常消费、医疗支出等）
- `amount`：金额（浮点）

---

## 7. API 说明（详细）

## `GET /`

返回页面模板 `templates/frontend.html`。

---

## `GET /api/statistics`

### 查询参数

支持两类筛选逻辑（互斥）：

1. **月/日跨年筛选模式**
   - `only_month`：1~12
   - `only_dom`：1~31（可选）
2. **日期区间模式**
   - `start_date`：`YYYY-MM-DD`（可选）
   - `end_date`：`YYYY-MM-DD`（可选）

> 当 `only_month` 合法时，后端优先走跨年模式，不使用 `start_date/end_date`。

### 返回字段

- `total_expense`：总消费金额
- `daily_average`：日均消费（总额 / 有数据的不重复日期数）
- `category_expense`：按类别汇总对象
- `daily_trend`：按日期汇总对象
- `date_range`：当前筛选结果的最小/最大日期
- `raw_table`：明细行数组
- `has_data`：是否有数据

### 示例 1：按日期区间

```http
GET /api/statistics?start_date=2026-04-01&end_date=2026-04-30
```

### 示例 2：跨年同月

```http
GET /api/statistics?only_month=4
```

### 示例 3：跨年同月同日

```http
GET /api/statistics?only_month=4&only_dom=20
```

---

## `GET /api/date_index`

用于前端日期弹窗的“可选年份 / 可选月份 / 可选日”索引构建。

返回结构：

- `has_data`：表里是否存在任意记录
- `date_index.years`：年份数组
- `date_index.months_by_year`：每年有哪些月份
- `date_index.days_by_year_month`：每个 `YYYY-MM` 有哪些日
- `date_index.date_range`：全表最小/最大日期

---

## 8. 前端页面与交互说明

前端集中在 `templates/frontend.html`，由结构层 + 内联脚本组成。

主要交互能力：

- 三个主视图切换：`overview` / `statistics` / `details`
- 日期筛选弹窗（支持仅年、仅月、年+月、年+月+日、跨年同月、跨年同月同日）
- 顶栏筛选状态展示与一键清除
- 主题切换（`localStorage` 键：`fd-theme`）
- 桌面端侧栏拖拽宽度调整
- 窄屏侧栏抽屉 + 遮罩

图表实例：

- 首页：`pc-category-chart`、`pc-trend-chart`
- 统计页：`pc-category-chart2`、`pc-trend-chart2`

四个图表由同一套数据驱动，主题切换时会重绘而不是强制重新请求接口（有缓存时）。

---

## 9. CSS 分层与维护原则

CSS 采用“单入口 + 分层模块”：

- 入口文件：`static/css/frontend.PC-Mphone.css`
- 由入口按顺序 `@import` 到各分层文件

推荐理解方式（从底到顶）：

1. `tokens`：变量、reset、全局设计令牌
2. `layout`：页面骨架和导航结构
3. `theme`：主题开关与暗色覆盖
4. `components`：通用组件
5. `dashboard`：图表与统计业务样式
6. `modal`：日期弹窗
7. `responsive`：移动端覆盖

更细维护规范见 `static/css/README.md`。

---

## 10. 日期筛选规则（重点）

当前筛选策略的业务语义：

- **只选年**：该年全年（`start=YYYY-01-01`, `end=YYYY-12-31`）
- **年 + 月**：该年月
- **年 + 月 + 日**：单日
- **只选月（不选年）**：各年份中该月（`only_month`）
- **只选月 + 日（不选年）**：各年份中该月该日（`only_month + only_dom`）

这套规则由前端 `pcBuildRangeFromFilter()` 生成查询参数，后端 `get_statistics()` 解析执行。

---

## 11. 常见开发任务

## 新增一个 API 字段

1. 修改 `backend.py` 中统计返回对象
2. 在 `frontend.html` 的 `pcRenderUI()` 消费字段
3. 如有展示需要，补充对应 CSS

## 修改图表配色

1. 调整 `frontend.html` 内 `pcChart` 色板对象
2. 同步检查 dark/light 两套颜色
3. 验证 tooltip、legend、axis 可读性

## 调整移动端布局

1. 优先改 `frontend.Mphone.responsive.css`
2. 避免反向改桌面文件导致覆盖冲突
3. 重点回归侧栏抽屉、顶栏工具条、图表高度、表格滚动

---

## 12. 本地验证清单

每次改动后建议至少验证：

- 启动服务无报错，首页可打开
- `GET /api/statistics` 与 `GET /api/date_index` 返回正常
- 三个页面切换正常，图表显示正常
- 日期筛选各种组合能正确出结果
- 明暗主题切换后图表与页面配色同步
- 窄屏（<=768 / <=480）下导航、图表、表格可用

---

## 13. 已知约束与注意事项

- `date` 字段以文本存储，建议严格写入 `YYYY-MM-DD` 格式
- 金额为浮点，展示时前端会做格式化（如 `¥` 前缀）
- 当前项目无用户系统、无权限控制、无写入接口（以读取分析为主）
- 前端脚本内联在模板中，适合中小体量项目，后续可拆分成独立静态 JS 文件

---

## 14. 可扩展方向

如果后续要继续完善，建议优先级如下：

1. 增加消费录入 / 编辑 / 删除接口与页面
2. 增加导入能力（CSV/Excel）
3. 增加按类别、金额区间等高级筛选
4. 增加单元测试与接口测试
5. 将前端脚本拆分模块，减少模板体积
6. 生产部署加入 WSGI 服务与反向代理

---

## 15. 关键文件索引

- 后端入口与接口：`backend.py`
- 页面模板与前端逻辑：`templates/frontend.html`
- 样式入口：`static/css/frontend.PC-Mphone.css`
- 样式维护手册：`static/css/README.md`
- 依赖定义：`requirements.txt`

---

## 16. 许可证与说明

本项目可按课程/个人项目用途继续扩展。若用于正式生产环境，请补充：

- 安全策略（输入校验、限流、鉴权）
- 错误日志与监控
- 部署与备份方案
