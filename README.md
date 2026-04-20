# 学生消费统计及可视化平台

Flask 单页应用：SQLite 存消费记录，首页展示汇总、ECharts 图表与明细表，支持日期筛选与明暗主题。

## 入口与 API

- **`backend.py`**：Web 服务、数据库访问、统计与日期索引逻辑；各函数说明见文件内文档字符串。
- **`/`**：返回 `templates/frontend.html`。
- **`GET /api/statistics`**：查询参数 `start_date`、`end_date` 和/或 `only_month`、`only_dom`（跨年月日筛选），返回 JSON。
- **`GET /api/date_index`**：返回前端日期控件所需年/月/日索引。

## 前端

- **`templates/frontend.html`**：页面结构 + 内联脚本；脚本内各函数前有注释。
- **`static/css/frontend.PC-Mphone.css`**：样式总入口（`@import` 各分表），各分表文件首行注释说明职责。

## 依赖

见 **`requirements.txt`**（Flask、pandas、gunicorn）。

## 运行

```bash
python backend.py
```

默认监听 `0.0.0.0:8000`；数据库默认同目录 `student_expense_record.db`，可通过环境变量 `DATABASE_PATH` 指定路径。
