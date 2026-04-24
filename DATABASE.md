# 数据库设计说明

本文档描述学生消费统计平台的数据库结构、字段规范、访问模式及维护记录。

数据库引擎：**SQLite 3**
数据库文件：`student_expense_record.db`（与 `backend.py` 同目录，可通过环境变量 `DATABASE_PATH` 覆盖）

---

## 目录

1. [总体设计原则](#1-总体设计原则)
2. [表结构](#2-表结构)
3. [字段详细说明](#3-字段详细说明)
4. [索引设计](#4-索引设计)
5. [约束说明](#5-约束说明)
6. [初始化与迁移逻辑](#6-初始化与迁移逻辑)
7. [数据访问模式](#7-数据访问模式)
8. [内置消费类别](#8-内置消费类别)
9. [数据样例](#9-数据样例)
10. [常见查询示例](#10-常见查询示例)
11. [备份与恢复](#11-备份与恢复)
12. [变更记录](#12-变更记录)

---

## 1. 总体设计原则

- **最小化结构**：当前业务场景单表即可覆盖全部需求，不引入不必要的关联表
- **文本存日期**：`date` 以 `TEXT` 类型存储 `YYYY-MM-DD` 字符串，利用字符串排序等价于日期排序，无需额外转换
- **浮点存金额**：`amount` 以 `REAL` 存储，写入前统一 `round(float, 2)` 保留两位小数，避免精度漂移
- **自增主键**：`id` 使用 `INTEGER PRIMARY KEY AUTOINCREMENT`，全局唯一且单调递增，便于分页与关联扩展
- **NOT NULL 全覆盖**：所有业务字段均为 `NOT NULL`，防止空值污染统计结果
- **与 AI 功能的关系**：内置 AI 分析仅通过应用代码**只读**查询 `expenses`（经 `get_all_expenses()` 等路径聚合），**不新增数据库表**、不向库中写入对话内容或密钥；AI 服务凭证由仓库外的 `ai_api_secrets.json` 或环境变量提供，与 SQLite 文件相互独立

---

## 2. 表结构

### `expenses`（消费记录表）

```sql
CREATE TABLE IF NOT EXISTS expenses (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    date     TEXT    NOT NULL,
    category TEXT    NOT NULL,
    amount   REAL    NOT NULL
);
```

#### ER 图（简化）

```
┌────────────────────────────────┐
│            expenses            │
├──────────┬──────────┬──────────┤
│  id (PK) │   date   │ category │
│  INTEGER │  TEXT    │  TEXT    │
│ NOT NULL │ NOT NULL │ NOT NULL │
├──────────┴──────────┴──────────┤
│              amount            │
│              REAL              │
│            NOT NULL            │
└────────────────────────────────┘
```

---

## 3. 字段详细说明

### `id`

| 属性 | 说明 |
|------|------|
| 类型 | `INTEGER` |
| 约束 | `PRIMARY KEY AUTOINCREMENT` |
| 含义 | 自增主键，系统自动分配，全局唯一 |
| 写入规则 | 插入时不传，由 SQLite 自动生成 |
| 用途 | 用于更新（`UPDATE ... WHERE id=?`）和删除（`DELETE ... WHERE id=?`） |

---

### `date`

| 属性 | 说明 |
|------|------|
| 类型 | `TEXT` |
| 约束 | `NOT NULL` |
| 格式 | `YYYY-MM-DD`（严格遵循，如 `2026-04-22`） |
| 含义 | 消费发生日期 |
| 写入规则 | 由前端日期选择器生成，后端不做额外格式校验，需确保前端传入符合规范 |
| 排序特性 | `YYYY-MM-DD` 格式字符串排序结果与日期自然顺序一致，可直接 `ORDER BY date` |

> **注意**：写入非标准格式（如 `2026/4/22`、`22-04-2026`）不会报错，但会导致日期过滤和排序结果异常。

---

### `category`

| 属性 | 说明 |
|------|------|
| 类型 | `TEXT` |
| 约束 | `NOT NULL` |
| 含义 | 消费类别名称，如 `早饭`、`交通`、`购物` 等 |
| 写入规则 | 来自前端下拉选择或自由输入，后端仅做空值校验，不限制枚举值 |
| 大小写 | 存储原始输入值，统计时区分大小写（`早饭` 与 `早 饭` 视为不同类别） |
| 内置类别 | 见第 8 节，系统在 `get_all_categories()` 中合并内置列表与数据库实际值 |

---

### `amount`

| 属性 | 说明 |
|------|------|
| 类型 | `REAL` |
| 约束 | `NOT NULL` |
| 含义 | 消费金额（人民币元，保留两位小数） |
| 取值范围 | 大于 0 的浮点数（后端校验 `amount > 0`） |
| 写入规则 | 写入前执行 `round(float(amount), 2)`，确保最多两位小数 |
| 显示规则 | 前端展示时添加 `¥` 前缀，格式化为 `¥XX.XX` |

---

## 4. 索引设计

当前版本**无显式附加索引**，仅有主键索引（SQLite 对 `INTEGER PRIMARY KEY` 自动建立 B-Tree 索引）。

### 当前查询性能分析

| 查询类型 | 代价 | 说明 |
|----------|------|------|
| `WHERE id = ?` | O(log n) | 主键索引，已足够 |
| `WHERE date = ?` | O(n) | 全表扫描，数据量小时可接受 |
| `WHERE date BETWEEN ? AND ?` | O(n) | 全表扫描 |
| `SELECT DISTINCT category` | O(n) | 全表扫描 |

### 扩展建议

若记录数超过 10 万条，建议补充以下索引：

```sql
-- 按日期查询 / 排序加速
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses (date);

-- 按类别统计加速
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses (category);

-- 复合索引：日期 + 类别联合查询
CREATE INDEX IF NOT EXISTS idx_expenses_date_category ON expenses (date, category);
```

---

## 5. 约束说明

### 主键约束

`id INTEGER PRIMARY KEY AUTOINCREMENT`：每次插入自动分配递增整数，不可重复，不可为 NULL。

### NOT NULL 约束

三个业务字段（`date`、`category`、`amount`）均设置 `NOT NULL`，在数据库层面防止关键信息缺失。

### 业务层校验（`backend.py`）

数据库约束之外，后端接口还做以下校验：

| 字段 | 校验规则 |
|------|---------|
| `date` | 非空字符串（不校验格式，依赖前端） |
| `category` | 非空字符串（strip 后非空） |
| `amount` | 可转为 `float` 且 `> 0` |

### 无外键约束

当前版本无用户表、分类枚举表等关联表，`category` 为自由文本，不做外键限制。

---

## 6. 初始化与迁移逻辑

### `init_db()`（后端启动时调用）

执行流程：

```
1. CREATE TABLE IF NOT EXISTS expenses (...)
   → 若表不存在，建表并设置完整约束

2. PRAGMA table_info(expenses)
   → 检查 category 列的 notnull 标志

3. 若 category.notnull == 0（旧库，category 无 NOT NULL 约束）
   → 执行"重建表迁移"：
     a. UPDATE expenses SET category='其他' WHERE category IS NULL OR category=''
     b. CREATE TABLE expenses_new (完整约束)
     c. INSERT INTO expenses_new SELECT * FROM expenses
     d. DROP TABLE expenses
     e. ALTER TABLE expenses_new RENAME TO expenses
```

> **说明**：SQLite 不支持 `ALTER COLUMN` 直接修改约束，因此通过"新建 + 迁移 + 替换"的方式完成 schema 升级。整个操作包裹在事务中（`BEGIN; ... COMMIT;`），保证原子性，不会出现数据丢失。

### 手动建表（可选）

如需手动创建或重置数据库，可在 SQLite 客户端执行：

```sql
-- 删除旧表（谨慎！不可恢复）
DROP TABLE IF EXISTS expenses;

-- 创建新表
CREATE TABLE expenses (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    date     TEXT    NOT NULL,
    category TEXT    NOT NULL,
    amount   REAL    NOT NULL
);
```

---

## 7. 数据访问模式

### 查询操作（只读）

| 操作 | 后端函数 | SQL 摘要 |
|------|---------|---------|
| 全量读取 | `get_all_expenses()` | `SELECT date, category, amount FROM expenses ORDER BY date` |
| 行数统计 | `expense_row_count()` | `SELECT COUNT(*) AS c FROM expenses` |
| 按日期查询 | `api_expenses_by_date()` | `SELECT id, date, category, amount FROM expenses WHERE date=? ORDER BY id` |
| 类别列表 | `get_all_categories()` | `SELECT DISTINCT category FROM expenses ORDER BY category` |

### 写操作

| 操作 | 后端函数 / 接口 | SQL 摘要 |
|------|----------------|---------|
| 新增 | `add_expense()` / `POST /api/add_expense` | `INSERT INTO expenses (date, category, amount) VALUES (?, ?, ?)` |
| 更新 | `POST /api/update_expense` | `UPDATE expenses SET date=?, category=?, amount=? WHERE id=?` |
| 删除 | `POST /api/delete_expense` | `DELETE FROM expenses WHERE id=?` |

### 统计聚合（pandas 层完成）

统计逻辑不在 SQL 层执行，而是由 `get_statistics()` 将全量数据读入 pandas DataFrame 后进行：

```python
# 类别汇总
df.groupby("类别")["金额"].sum().round(2)

# 日期汇总
df.groupby("日期")["金额"].sum().round(2)

# 每日明细
df.sort_values(["日期", "类别"]).groupby("日期")
```

> **设计取舍**：这种方式在记录数 < 10 万时性能充足，且易于在 Python 层实现复杂的跨年月筛选逻辑。若数据量增大，可考虑将聚合下推到 SQL 层。

---

## 8. 内置消费类别

系统内置 16 个默认类别（`backend.py` 的 `get_all_categories()`），在下拉框中始终显示：

| 分组 | 类别 |
|------|------|
| 餐饮 | 早饭、午饭、晚饭、夜宵 |
| 出行 | 交通 |
| 购物 / 日用 | 购物、生活用品 |
| 健康 | 运动健身、医疗 |
| 社交 / 娱乐 | 娱乐、游戏、话费充值、社交聚餐 |
| 学习 / 旅行 | 学习、旅行 |
| 其他 | 其他 |

用户自定义类别（从数据库读取的 `DISTINCT category`）会与内置列表**合并去重后升序排列**，一并展示在下拉框中。

前端颜色映射（`frontend.html` 中的 `PC_CAT_COLORS`）为以上类别及常用别名（如"吃饭"→早饭色）分配固定色值；未收录的自定义类别通过名称哈希从调色板取色，保证视觉区分度。

---

## 9. 数据样例

```sql
-- 插入示例记录
INSERT INTO expenses (date, category, amount) VALUES
    ('2026-04-01', '早饭',   12.00),
    ('2026-04-01', '午饭',   25.50),
    ('2026-04-01', '交通',    4.00),
    ('2026-04-02', '晚饭',   38.00),
    ('2026-04-02', '购物',  120.00),
    ('2026-04-05', '学习',   89.90),
    ('2026-04-10', '运动健身', 50.00),
    ('2026-04-15', '社交聚餐', 68.00),
    ('2026-04-20', '医疗',   200.00),
    ('2026-04-22', '午饭',   22.00);
```

查询全部（按日期升序）：

```sql
SELECT * FROM expenses ORDER BY date;
```

| id | date | category | amount |
|----|------|----------|--------|
| 1 | 2026-04-01 | 早饭 | 12.00 |
| 2 | 2026-04-01 | 午饭 | 25.50 |
| 3 | 2026-04-01 | 交通 | 4.00 |
| 4 | 2026-04-02 | 晚饭 | 38.00 |
| 5 | 2026-04-02 | 购物 | 120.00 |
| ... | ... | ... | ... |

---

## 10. 常见查询示例

### 按日期区间筛选

```sql
SELECT date, category, amount
FROM expenses
WHERE date >= '2026-04-01' AND date <= '2026-04-30'
ORDER BY date;
```

### 某日所有记录（含 id，供编辑使用）

```sql
SELECT id, date, category, amount
FROM expenses
WHERE date = '2026-04-22'
ORDER BY id;
```

### 按类别汇总金额

```sql
SELECT category, ROUND(SUM(amount), 2) AS total
FROM expenses
GROUP BY category
ORDER BY total DESC;
```

### 按日期汇总（每日总消费）

```sql
SELECT date, ROUND(SUM(amount), 2) AS daily_total
FROM expenses
GROUP BY date
ORDER BY date;
```

### 跨年同月筛选（所有年份的 4 月）

```sql
SELECT date, category, amount
FROM expenses
WHERE CAST(SUBSTR(date, 6, 2) AS INTEGER) = 4
ORDER BY date;
```

### 跨年同月同日（所有年份的 4 月 20 日）

```sql
SELECT date, category, amount
FROM expenses
WHERE CAST(SUBSTR(date, 6, 2) AS INTEGER) = 4
  AND CAST(SUBSTR(date, 9, 2) AS INTEGER) = 20
ORDER BY date;
```

### 统计记录总行数

```sql
SELECT COUNT(*) AS total_rows FROM expenses;
```

### 查询所有出现过的类别

```sql
SELECT DISTINCT category FROM expenses ORDER BY category;
```

---

## 11. 备份与恢复

### 备份

SQLite 数据库为单文件，直接复制文件即可备份：

```powershell
# Windows PowerShell
Copy-Item student_expense_record.db backups\student_expense_record_$(Get-Date -Format 'yyyyMMdd').db
```

```bash
# macOS / Linux
cp student_expense_record.db backups/student_expense_record_$(date +%Y%m%d).db
```

### 使用 SQLite 命令行导出 SQL

```bash
sqlite3 student_expense_record.db .dump > backup.sql
```

### 从 SQL 恢复

```bash
sqlite3 student_expense_record_new.db < backup.sql
```

### 导出为 CSV

```bash
sqlite3 -header -csv student_expense_record.db \
  "SELECT id, date, category, amount FROM expenses ORDER BY date;" \
  > expenses_export.csv
```

### 从 CSV 导入

```bash
# 先创建表（若不存在）
sqlite3 student_expense_record.db \
  "CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL);"

# 导入（跳过首行表头）
sqlite3 student_expense_record.db \
  ".mode csv" ".import expenses_export.csv expenses"
```

---

## 12. 变更记录

| 版本 / 日期 | 变更内容 | 说明 |
|-------------|---------|------|
| v1.0 初始版本 | 创建 `expenses` 表，字段：`id, date, category, amount` | 初始建表，`category` 无 NOT NULL 约束 |
| v1.1 迁移补丁 | 为 `category` 补加 `NOT NULL` 约束 | 通过"重建表 + 数据迁移"方式完成，空值自动填充为"其他"；`init_db()` 自动检测并执行，无需手动操作 |
| — | （应用层）AI 消费助手 | 不修改 `expenses` 表结构；仅只读消费数据用于上下文摘要 |

---

## 附：数据库连接配置参考

### Python（sqlite3 标准库）

```python
import sqlite3, os

db_path = os.environ.get("DATABASE_PATH", "student_expense_record.db")
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row   # 支持按列名访问

cursor = conn.execute("SELECT * FROM expenses ORDER BY date")
rows = cursor.fetchall()
conn.close()
```

### SQLite 命令行客户端

```bash
sqlite3 student_expense_record.db

# 查看表结构
.schema expenses

# 查看所有表
.tables

# 开启表头显示
.headers on
.mode column

# 查询示例
SELECT * FROM expenses LIMIT 10;
```

### DB Browser for SQLite（GUI 工具）

支持可视化浏览表结构、数据、执行 SQL，推荐用于开发调试。官网：[https://sqlitebrowser.org](https://sqlitebrowser.org)
