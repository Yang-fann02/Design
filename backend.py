"""
学生消费统计 Web 应用（Flask）。

提供首页单页模板、按条件统计的 JSON API，以及供前端日期筛选使用的日期索引 API。
数据库默认为同目录下的 SQLite 文件 student_expense_record.db，可通过环境变量 DATABASE_PATH 覆盖。
"""
import os
import sqlite3

import pandas as pd
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
# 开发时关闭静态文件缓存，修改 CSS/JS 后刷新即可看到最新资源（生产可用反向代理缓存替代）
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


def get_db():
    """
    创建并返回指向业务库的 SQLite 连接。

    路径规则：优先使用环境变量 DATABASE_PATH；若为相对路径，则相对于本文件所在目录解析。
    使用 sqlite3.Row，便于通过列名访问字段（如 row['date']）。
    """
    db_path = os.environ.get("DATABASE_PATH", "student_expense_record.db")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def expense_row_count():
    """查询 expenses 表总行数，用于判断是否存在任意消费记录（与日期是否有效无关）。"""
    conn = get_db()
    row = conn.execute("SELECT COUNT(*) AS c FROM expenses").fetchone()
    conn.close()
    return int(row["c"]) if row else 0


def init_db():
    """若不存在则创建 expenses 表（id, date, category, amount），不删除已有数据。"""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def get_all_expenses():
    """
    读取全部消费记录，按日期升序。

    Returns:
        pandas.DataFrame: 列名为中文「日期、类别、金额」，若无数据则为空表。
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT date, category, amount FROM expenses ORDER BY date"
    ).fetchall()
    conn.close()
    if not rows:
        return pd.DataFrame()
    data = [{"日期": r["date"], "类别": r["category"], "金额": r["amount"]} for r in rows]
    return pd.DataFrame(data)


def get_statistics(start_date=None, end_date=None, only_month=None, only_dom=None):
    """
    按筛选条件汇总消费数据，供前端图表与表格使用。

    筛选逻辑（互斥二选一）：
    - 当 only_month 为合法 1–12：不按公历年过滤，保留所有年份中该月的记录；若再传 only_dom（1–31），
      则进一步限定为「各年中该月的号数」，用于「无年份 + 月 + 日」筛选。
    - 否则：按 start_date / end_date 字符串（YYYY-MM-DD）与「日期」列做闭区间过滤；未传则不过滤该端。

    Args:
        start_date: 起始日期字符串，可与 end_date 单独或组合使用。
        end_date: 结束日期字符串。
        only_month: 公历月份 1–12，与 only_dom 搭配表示跨年的「月/日」筛选。
        only_dom: 公历日 1–31，仅在与 only_month 同时有效时生效。

    Returns:
        dict: total_expense, daily_average（总支出/有数据的不重复日期数）,
              category_expense, daily_trend, date_range{min,max}, raw_table（明细行列表）。
    """
    df = get_all_expenses()
    if df.empty:
        return {
            "total_expense": 0,
            "daily_average": 0,
            "category_expense": {},
            "daily_trend": {},
            "date_range": {"min": None, "max": None},
            "raw_table": [],
        }
    if "金额" in df.columns:
        df["金额"] = pd.to_numeric(df["金额"], errors="coerce")
    if "日期" in df.columns:
        df["日期"] = pd.to_datetime(df["日期"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.dropna(subset=["日期", "金额"])

    used_month_only = False
    if only_month is not None and str(only_month).strip() != "":
        try:
            mi = int(only_month)
        except (TypeError, ValueError):
            mi = None
        if mi is not None and 1 <= mi <= 12:
            dt = pd.to_datetime(df["日期"], errors="coerce")
            mask = dt.dt.month == mi
            if only_dom is not None and str(only_dom).strip() != "":
                try:
                    di = int(only_dom)
                except (TypeError, ValueError):
                    di = None
                if di is not None and 1 <= di <= 31:
                    mask = mask & (dt.dt.day == di)
            df = df.loc[mask].copy()
            used_month_only = True

    if not used_month_only:
        if start_date:
            df = df[df["日期"] >= start_date]
        if end_date:
            df = df[df["日期"] <= end_date]

    if df.empty:
        return {
            "total_expense": 0,
            "daily_average": 0,
            "category_expense": {},
            "daily_trend": {},
            "date_range": {"min": None, "max": None},
            "raw_table": [],
        }

    total = round(df["金额"].sum(), 2)
    day_count = int(df["日期"].nunique())
    avg = round(total / day_count, 2) if day_count else 0

    category_data = df.groupby("类别")["金额"].sum().round(2).to_dict()
    category_data = {str(k): round(float(v), 2) for k, v in category_data.items()}

    daily_data = df.groupby("日期")["金额"].sum().round(2).to_dict()
    daily_data = {str(k): round(float(v), 2) for k, v in daily_data.items()}

    dates = sorted(df["日期"].unique())
    date_min = dates[0] if dates else None
    date_max = dates[-1] if dates else None

    table_data = df.fillna("").to_dict(orient="records")
    for row in table_data:
        for key, val in row.items():
            if key == "金额" and val and val != "nan":
                try:
                    row[key] = round(float(val), 2)
                except (TypeError, ValueError):
                    pass

    return {
        "total_expense": total,
        "daily_average": avg,
        "category_expense": category_data,
        "daily_trend": daily_data,
        "date_range": {"min": date_min, "max": date_max},
        "raw_table": table_data,
    }


def get_date_index():
    """
    根据全表日期构造前端下拉与日历所需的索引结构。

    Returns:
        dict:
            years: 升序年份列表。
            months_by_year: 键为年份字符串，值为该年出现过的月份（升序）。
            days_by_year_month: 键为 \"YYYY-MM\"，值为该月出现过的「日」数字列表（升序）。
            date_range: 全表最小、最大日期字符串。
    """
    df = get_all_expenses()
    empty = {
        "years": [],
        "months_by_year": {},
        "days_by_year_month": {},
        "date_range": {"min": None, "max": None},
    }
    if df.empty or "日期" not in df.columns:
        return empty

    dates = pd.to_datetime(df["日期"], errors="coerce").dropna().dt.strftime("%Y-%m-%d")
    uniq = sorted(set(dates.tolist()))
    if not uniq:
        return empty

    years = sorted({int(d[0:4]) for d in uniq if len(d) >= 10})
    months_by_year = {str(y): [] for y in years}
    days_by_year_month = {}

    for ds in uniq:
        if len(ds) < 10:
            continue
        y, m, d = ds[0:4], ds[5:7], ds[8:10]
        if not (y.isdigit() and m.isdigit() and d.isdigit()):
            continue
        mi, di = int(m), int(d)
        if mi not in months_by_year[y]:
            months_by_year[y].append(mi)
        ym = f"{y}-{m}"
        if ym not in days_by_year_month:
            days_by_year_month[ym] = []
        if di not in days_by_year_month[ym]:
            days_by_year_month[ym].append(di)

    for yk in months_by_year:
        months_by_year[yk] = sorted(months_by_year[yk])
    for ym in days_by_year_month:
        days_by_year_month[ym] = sorted(days_by_year_month[ym])

    return {
        "years": years,
        "months_by_year": months_by_year,
        "days_by_year_month": days_by_year_month,
        "date_range": {"min": uniq[0], "max": uniq[-1]},
    }


@app.route("/")
def index():
    """首页：渲染单页应用模板 frontend.html。"""
    return render_template("frontend.html")


@app.route("/api/statistics")
def get_stats():
    """
    统计 JSON：查询参数 start_date、end_date、only_month、only_dom 传给 get_statistics；
    额外返回 has_data 表示筛选后 raw_table 是否非空。
    """
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    only_month = request.args.get("only_month")
    only_dom = request.args.get("only_dom")
    stats = get_statistics(
        start_date=start_date,
        end_date=end_date,
        only_month=only_month,
        only_dom=only_dom,
    )
    has_rows = len(stats.get("raw_table") or []) > 0
    return jsonify({**stats, "has_data": has_rows})


@app.route("/api/date_index")
def get_dates():
    """日期索引 JSON：供前端填充年份、月份与按月的可选日期；has_data 表示表中是否有任意记录。"""
    index = get_date_index()
    has_rows = expense_row_count() > 0
    return jsonify({"has_data": has_rows, "date_index": index})


if __name__ == "__main__":
    init_db()
    print("数据库初始化完成")
    print("启动服务器...")
    app.run(debug=False, host="0.0.0.0", port=8000)
