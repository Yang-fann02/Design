"""
学生消费统计 Web 应用（Flask）。

提供首页单页模板、按条件统计的 JSON API，以及供前端日期筛选使用的日期索引 API。
数据库默认为同目录下的 SQLite 文件 student_expense_record.db，可通过环境变量 DATABASE_PATH 覆盖。
"""
import json
import os
import re
import sqlite3
import time
from datetime import datetime

import pandas as pd
import requests as http_requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import Flask, Response, jsonify, render_template, request

app = Flask(__name__)
# 开发时关闭静态文件缓存，修改 CSS/JS 后刷新即可看到最新资源（生产可用反向代理缓存替代）
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_AI_SECRETS_FILENAME = "ai_api_secrets.json"


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
    """
    初始化数据库：
    1. 若 expenses 表不存在则创建（含完整约束）。
    2. 若表已存在但 category 列缺少 NOT NULL 约束（旧库兼容），
       通过"重建表 + 迁移数据"的方式补全，保证零数据丢失。
    """
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            date     TEXT    NOT NULL,
            category TEXT    NOT NULL,
            amount   REAL    NOT NULL
        )
        """
    )
    conn.commit()

    # 检测 category 列是否已有 NOT NULL 约束；SQLite PRAGMA table_info 的 notnull 字段
    col_info = conn.execute("PRAGMA table_info(expenses)").fetchall()
    cat_col = next((c for c in col_info if c[1] == "category"), None)
    if cat_col is not None and cat_col[3] == 0:
        # category 列 notnull=0，需要补约束：SQLite 不支持 ALTER COLUMN，用重建表法
        conn.executescript(
            """
            BEGIN;
            -- 先将空 category 行置为「其他」，避免迁移时违反 NOT NULL
            UPDATE expenses SET category = '其他' WHERE category IS NULL OR category = '';
            -- 创建结构完整的临时表
            CREATE TABLE expenses_new (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                date     TEXT    NOT NULL,
                category TEXT    NOT NULL,
                amount   REAL    NOT NULL
            );
            -- 迁移全部数据
            INSERT INTO expenses_new (id, date, category, amount)
                SELECT id, date, category, amount FROM expenses;
            -- 替换原表
            DROP TABLE expenses;
            ALTER TABLE expenses_new RENAME TO expenses;
            COMMIT;
            """
        )

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


def _empty_stats():
    """返回无数据时的统计结果骨架。"""
    return {
        "total_expense": 0,
        "daily_average": 0,
        "category_expense": {},
        "daily_trend": {},
        "daily_detail": {},
        "date_range": {"min": None, "max": None},
        "raw_table": [],
    }


def get_all_categories():
    """
    读取 expenses 表中所有出现过的消费类别，返回去重升序列表。
    同时合并内置默认类别，确保下拉框总有基础选项。
    """
    default_cats = [
        "早饭", "午饭", "晚饭", "夜宵",
        "交通", "购物", "生活用品", "运动健身",
        "游戏", "话费充值", "娱乐", "社交聚餐",
        "学习", "旅行", "医疗", "其他"
    ]
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT category FROM expenses ORDER BY category"
    ).fetchall()
    conn.close()
    db_cats = [r["category"] for r in rows if r["category"]]
    merged = sorted(set(default_cats) | set(db_cats))
    return merged


def add_expense(date: str, category: str, amount: float):
    """
    向 expenses 表插入一条新消费记录。

    Args:
        date: 日期字符串，格式 YYYY-MM-DD。
        category: 消费类别。
        amount: 消费金额（浮点数）。
    Returns:
        新插入行的 id。
    """
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO expenses (date, category, amount) VALUES (?, ?, ?)",
        (date, category, round(float(amount), 2))
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_statistics(start_date=None, end_date=None, only_month=None, only_dom=None, only_category=None):
    """
    按筛选条件汇总消费数据，供前端图表与表格使用。

    筛选逻辑（互斥二选一）：
    - 当 only_month 为合法 1–12：不按公历年过滤，保留所有年份中该月的记录；若再传 only_dom（1–31），
      则进一步限定为「各年中该月的号数」，用于「无年份 + 月 + 日」筛选。
    - 否则：按 start_date / end_date 字符串（YYYY-MM-DD）与「日期」列做闭区间过滤；未传则不过滤该端。
    - only_category: 若传入则进一步按类别过滤。

    Args:
        start_date: 起始日期字符串，可与 end_date 单独或组合使用。
        end_date: 结束日期字符串。
        only_month: 公历月份 1–12，与 only_dom 搭配表示跨年的「月/日」筛选。
        only_dom: 公历日 1–31，仅在与 only_month 同时有效时生效。
        only_category: 消费类别字符串，传入时仅保留该类别记录。

    Returns:
        dict: total_expense, daily_average（总支出/有数据的不重复日期数）,
              category_expense, daily_trend, daily_detail, date_range{min,max}, raw_table（明细行列表）。
    """
    df = get_all_expenses()
    if df.empty:
        return _empty_stats()
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

    if only_category and str(only_category).strip():
        df = df[df["类别"] == str(only_category).strip()]

    if df.empty:
        return _empty_stats()

    total = round(df["金额"].sum(), 2)
    day_count = int(df["日期"].nunique())
    avg = round(total / day_count, 2) if day_count else 0

    category_data = df.groupby("类别")["金额"].sum().round(2).to_dict()
    category_data = {str(k): round(float(v), 2) for k, v in category_data.items()}

    daily_data = df.groupby("日期")["金额"].sum().round(2).to_dict()
    daily_data = {str(k): round(float(v), 2) for k, v in daily_data.items()}

    # 每日消费明细：{ "YYYY-MM-DD": [{"类别": "吃饭", "金额": 10}, ...], ... }
    daily_detail: dict = {}
    for _, row in df.sort_values(["日期", "类别"]).iterrows():
        d = str(row["日期"])
        if d not in daily_detail:
            daily_detail[d] = []
        daily_detail[d].append({
            "类别": str(row["类别"]),
            "金额": round(float(row["金额"]), 2)
        })

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
        "daily_detail": daily_detail,
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
    统计 JSON：查询参数 start_date、end_date、only_month、only_dom、only_category 传给 get_statistics；
    额外返回 has_data 表示筛选后 raw_table 是否非空。
    """
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    only_month = request.args.get("only_month")
    only_dom = request.args.get("only_dom")
    only_category = request.args.get("only_category")
    stats = get_statistics(
        start_date=start_date,
        end_date=end_date,
        only_month=only_month,
        only_dom=only_dom,
        only_category=only_category,
    )
    has_rows = len(stats.get("raw_table") or []) > 0
    return jsonify({**stats, "has_data": has_rows})


@app.route("/api/date_index")
def get_dates():
    """日期索引 JSON：供前端填充年份、月份与按月的可选日期；has_data 表示表中是否有任意记录。"""
    index = get_date_index()
    has_rows = expense_row_count() > 0
    return jsonify({"has_data": has_rows, "date_index": index})


@app.route("/api/categories")
def get_categories():
    """返回所有已出现过的消费类别（含内置默认类别）列表。"""
    return jsonify({"categories": get_all_categories()})


@app.route("/api/add_expense", methods=["POST"])
def api_add_expense():
    """
    新增消费记录接口。
    请求体 JSON: { "date": "YYYY-MM-DD", "category": "类别", "amount": 12.5 }
    返回: { "success": true, "id": <新行id> }
    """
    data = request.get_json(force=True, silent=True) or {}
    date = str(data.get("date", "")).strip()
    category = str(data.get("category", "")).strip()
    amount = data.get("amount")
    if not date or not category or amount is None:
        return jsonify({"success": False, "error": "date、category、amount 均不能为空"}), 400
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("金额必须大于 0")
    except (TypeError, ValueError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    new_id = add_expense(date, category, amount)
    return jsonify({"success": True, "id": new_id})


@app.route("/api/expenses_by_date")
def api_expenses_by_date():
    """
    按日期查询该日所有消费记录（含 id 字段，供变更页使用）。
    查询参数: date=YYYY-MM-DD
    返回: { "records": [{id, date, category, amount}, ...] }
    """
    date_str = request.args.get("date", "").strip()
    if not date_str:
        return jsonify({"records": []})
    conn = get_db()
    rows = conn.execute(
        "SELECT id, date, category, amount FROM expenses WHERE date=? ORDER BY id",
        (date_str,)
    ).fetchall()
    conn.close()
    return jsonify({"records": [
        {"id": r["id"], "date": r["date"], "category": r["category"], "amount": r["amount"]}
        for r in rows
    ]})


@app.route("/api/update_expense", methods=["POST"])
def api_update_expense():
    """
    更新单条消费记录。
    请求体 JSON: { "id": 123, "date": "YYYY-MM-DD", "category": "类别", "amount": 12.5 }
    返回: { "success": true }
    """
    data = request.get_json(force=True, silent=True) or {}
    row_id = data.get("id")
    date_val = str(data.get("date", "")).strip()
    category = str(data.get("category", "")).strip()
    amount = data.get("amount")
    if not row_id or not date_val or not category or amount is None:
        return jsonify({"success": False, "error": "id、date、category、amount 均不能为空"}), 400
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError("金额必须大于 0")
    except (TypeError, ValueError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    conn = get_db()
    conn.execute(
        "UPDATE expenses SET date=?, category=?, amount=? WHERE id=?",
        (date_val, category, round(amount, 2), int(row_id))
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/delete_expense", methods=["POST"])
def api_delete_expense():
    """
    删除单条消费记录。
    请求体 JSON: { "id": 123 }
    返回: { "success": true }
    """
    data = request.get_json(force=True, silent=True) or {}
    row_id = data.get("id")
    if not row_id:
        return jsonify({"success": False, "error": "id 不能为空"}), 400
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id=?", (int(row_id),))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


_MAX_RETRIES = 3


def _ai_secrets_file_path():
    """
    私钥配置文件路径。
    可选环境变量 AI_API_SECRETS_PATH：绝对路径，或相对于 backend.py 所在目录的相对路径。
    默认：与 backend.py 同目录的 ai_api_secrets.json（须加入 .gitignore，勿提交密钥）。
    """
    raw = (os.environ.get("AI_API_SECRETS_PATH") or "").strip()
    if raw:
        return raw if os.path.isabs(raw) else os.path.join(_BACKEND_DIR, raw)
    return os.path.join(_BACKEND_DIR, _DEFAULT_AI_SECRETS_FILENAME)


def _load_moark_ai_config():
    """
    从本地 JSON 读取 Moark/OpenAI 兼容接口配置，密钥不写在代码里。

    默认读取 ai_api_secrets.json，字段见同目录下 ai_api_secrets.example.json。
    若文件中未配置 api_key，再尝试环境变量 MOARK_API_KEY 或 OPENAI_API_KEY（可选回退）。
    """
    default_url = "https://api.moark.com/v1/chat/completions"
    default_model = "MiniMax-M2.7"
    url, key, model = default_url, "", default_model

    path = _ai_secrets_file_path()
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                key = str(data.get("api_key") or "").strip()
                u = str(data.get("api_url") or "").strip()
                if u:
                    url = u
                m = str(data.get("model") or "").strip()
                if m:
                    model = m
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            pass

    if not key:
        key = (os.environ.get("MOARK_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()

    return url, key, model


def _build_http_session():
    """构建带有自动重试的 HTTP Session，应对 SSL/连接瞬断。"""
    session = http_requests.Session()
    retry_strategy = Retry(
        total=_MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

_AI_SYSTEM_PROMPT = (
    "你是[学生消费统计及可视化平台]内置的 AI 消费分析助手。"
    "用户的真实消费数据已自动从数据库获取并附在下方，请直接基于数据回答，不要索要数据。"
    "回答要求：简洁精炼，用数字说话；给出具体可执行的建议；如数据不足直接说明。"
)

_MAX_HISTORY_TURNS = 30
_MAX_TOTAL_CHARS = 64000


def _expand_year(y_str):
    """将 2 位年份缩写扩展为 4 位：00-49→2000s，50-99→1900s；4 位原样返回。"""
    y = int(y_str)
    if y < 100:
        return 2000 + y if y < 50 else 1900 + y
    return y


def _month_end(y, mo):
    """返回 y 年 mo 月最后一天的日期字符串。"""
    if mo == 12:
        return f"{y}-12-31"
    nxt = datetime(y, mo + 1, 1) - pd.Timedelta(days=1)
    return nxt.strftime("%Y-%m-%d")


def _parse_time_range(text):
    """
    从用户消息文本中提取时间范围，返回 (start_date, end_date) 字符串。
    支持：2023年、23年、2023年3月、23年1月、23年1月5日/号、3月、3月15日、
          上个月、本月、最近一周、今天、昨天、7号/7日（需上下文补全）等。
    """
    today = datetime.today()

    # 年+月+日（2-4位年份）
    m = re.search(r"(\d{2,4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]", text)
    if m:
        y = _expand_year(m.group(1))
        d = f"{y}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        return d, d

    # 年+月（2-4位年份）
    m = re.search(r"(\d{2,4})\s*[年\-/]\s*(\d{1,2})\s*月?", text)
    if m:
        y, mo = _expand_year(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return f"{y}-{mo:02d}-01", _month_end(y, mo)

    # 仅年份（2-4位）
    m = re.search(r"(\d{2,4})\s*年", text)
    if m:
        y = _expand_year(m.group(1))
        return f"{y}-01-01", f"{y}-12-31"

    # 月+日（无年份，默认今年）
    m = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]", text)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            dt = f"{today.year}-{mo:02d}-{d:02d}"
            return dt, dt

    # 仅月份（无年份，默认今年）
    m = re.search(r"(\d{1,2})\s*月", text)
    if m:
        mo = int(m.group(1))
        if 1 <= mo <= 12:
            return f"{today.year}-{mo:02d}-01", _month_end(today.year, mo)

    # 仅日号（如"7号""7日"），需外部传入 hint_year / hint_month 补全，
    # 此处先返回特殊标记 ("__day_only__", day) 给调用方处理
    m = re.search(r"(?<!\d)(\d{1,2})\s*[日号]", text)
    if m:
        d = int(m.group(1))
        if 1 <= d <= 31:
            return "__day_only__", str(d)

    if re.search(r"上个?月|上月", text):
        first_this = today.replace(day=1)
        last_month_end = first_this - pd.Timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start.strftime("%Y-%m-%d"), last_month_end.strftime("%Y-%m-%d")

    if re.search(r"本月|这个?月", text):
        return today.replace(day=1).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    if re.search(r"最近\s*一?\s*周|近7天|过去7天", text):
        return (today - pd.Timedelta(days=7)).strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    if re.search(r"今天|今日", text):
        d = today.strftime("%Y-%m-%d")
        return d, d

    if re.search(r"昨天|昨日", text):
        return (today - pd.Timedelta(days=1)).strftime("%Y-%m-%d"), (today - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    return None, None


def _extract_year_month_hint(text):
    """
    从文本中提取年份和月份信息（仅提取，不组合完整范围），
    用于为后续追问中的"仅日号"提供上下文补全。
    返回 (year_int_or_None, month_int_or_None)。
    """
    year, month = None, None
    m = re.search(r"(\d{2,4})\s*[年\-/]\s*(\d{1,2})", text)
    if m:
        year = _expand_year(m.group(1))
        mo = int(m.group(2))
        if 1 <= mo <= 12:
            month = mo
        return year, month
    m = re.search(r"(\d{2,4})\s*年", text)
    if m:
        year = _expand_year(m.group(1))
    m = re.search(r"(\d{1,2})\s*月", text)
    if m:
        mo = int(m.group(1))
        if 1 <= mo <= 12:
            month = mo
    return year, month


def _parse_time_range_with_history(user_messages):
    """
    先从最后一条用户消息提取时间范围；若结果不完整（如仅有日号），
    则回溯历史消息提取年/月信息进行补全。
    """
    today = datetime.today()
    last_text = ""
    for m in reversed(user_messages):
        if m.get("role") == "user":
            last_text = m.get("content", "")
            break

    start, end = _parse_time_range(last_text)

    if start == "__day_only__":
        day = int(end)
        hint_year, hint_month = None, None
        for m in reversed(user_messages):
            if m.get("role") != "user":
                continue
            content = m.get("content", "")
            if content == last_text:
                continue
            hy, hm = _extract_year_month_hint(content)
            if hint_year is None and hy is not None:
                hint_year = hy
            if hint_month is None and hm is not None:
                hint_month = hm
            if hint_year is not None and hint_month is not None:
                break

        y = hint_year if hint_year else today.year
        mo = hint_month if hint_month else today.month
        d = f"{y}-{mo:02d}-{day:02d}"
        return d, d

    if start is not None:
        return start, end

    return None, None


def _parse_category(text):
    """从用户消息中提取消费类别关键词，返回匹配的类别名或 None。"""
    all_cats = get_all_categories()
    for cat in sorted(all_cats, key=len, reverse=True):
        if cat in text:
            return cat
    return None


def _build_expense_context(start_date=None, end_date=None, category=None):
    """
    根据时间范围和可选类别从数据库提取消费数据摘要。
    """
    df = get_all_expenses()
    if df.empty:
        return "【消费数据】暂无任何记录。"

    df["金额"] = pd.to_numeric(df["金额"], errors="coerce")
    df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
    df = df.dropna(subset=["日期", "金额"])
    if df.empty:
        return "【消费数据】暂无有效记录。"

    global_min = df["日期"].min().strftime("%Y-%m-%d")
    global_max = df["日期"].max().strftime("%Y-%m-%d")
    global_total = round(df["金额"].sum(), 2)

    filtered = df
    range_label = f"{global_min} ~ {global_max}（全部）"
    if start_date and end_date:
        filtered = filtered[(filtered["日期"] >= start_date) & (filtered["日期"] <= end_date)]
        range_label = f"{start_date} ~ {end_date}"

    cat_label = "全部类别"
    if category:
        filtered = filtered[filtered["类别"] == category]
        cat_label = category

    parts = [f"【消费数据 | 范围：{range_label} | 类别：{cat_label}】",
             f"全库 {global_min}~{global_max}，总计 {global_total} 元。"]

    if filtered.empty:
        parts.append("该条件下无消费记录。")
        return "\n".join(parts)

    total = round(filtered["金额"].sum(), 2)
    day_count = filtered["日期"].dt.date.nunique()
    daily_avg = round(total / day_count, 2) if day_count else 0
    record_count = len(filtered)
    parts.append(f"匹配 {record_count} 笔，合计 {total} 元，覆盖 {day_count} 天，日均 {daily_avg} 元。")

    if not category:
        cat_data = filtered.groupby("类别")["金额"].sum().round(2).sort_values(ascending=False)
        cat_lines = [f"{c} {v}元({round(v/total*100,1)}%)" for c, v in cat_data.items()]
        parts.append("类别明细：" + "、".join(cat_lines))
    else:
        if day_count <= 31:
            daily = filtered.groupby(filtered["日期"].dt.strftime("%Y-%m-%d"))["金额"].sum().round(2)
            d_lines = [f"{d}:{v}元" for d, v in daily.items()]
            parts.append(f"{category}逐日：" + "、".join(d_lines))

    if not category and day_count > 31:
        monthly = filtered.groupby(filtered["日期"].dt.to_period("M"))["金额"].sum().round(2)
        m_lines = [f"{p}:{v}元" for p, v in monthly.items()]
        parts.append("逐月消费：" + "、".join(m_lines))
    elif not category and day_count > 0:
        daily = filtered.groupby(filtered["日期"].dt.strftime("%m-%d"))["金额"].sum().round(2)
        d_lines = [f"{d}:{v}元" for d, v in daily.items()]
        parts.append("逐日消费：" + "、".join(d_lines))

    return "\n".join(parts)


def _trim_messages(messages):
    """
    裁剪对话历史，防止超出模型上下文窗口。
    策略：保留最近 _MAX_HISTORY_TURNS 条消息，且总字符数不超过 _MAX_TOTAL_CHARS。
    裁剪时始终保留最新的消息，从最早的开始丢弃，
    并确保裁剪后第一条消息是 user 角色（避免孤立的 assistant 回复）。
    """
    msgs = messages[-_MAX_HISTORY_TURNS * 2:]

    total = sum(len(m.get("content", "")) for m in msgs)
    while total > _MAX_TOTAL_CHARS and len(msgs) > 2:
        removed = msgs.pop(0)
        total -= len(removed.get("content", ""))

    while msgs and msgs[0].get("role") == "assistant":
        msgs.pop(0)

    return msgs


@app.route("/api/ai_chat", methods=["POST"])
def api_ai_chat():
    """
    AI 聊天 SSE 流式接口。逐 token 推送，前端即时渲染。
    请求体 JSON: { "messages": [{role, content}, ...] }
    返回: text/event-stream，每个 data 行为一段文本片段；最终发送 data: [DONE]。
    """
    data = request.get_json(force=True, silent=True) or {}
    user_messages = data.get("messages", [])
    if not user_messages:
        return jsonify({"error": "messages 不能为空"}), 400

    last_user_msg = ""
    for m in reversed(user_messages):
        if m.get("role") == "user":
            last_user_msg = m.get("content", "")
            break

    start_date, end_date = _parse_time_range_with_history(user_messages)

    category = _parse_category(last_user_msg)
    if category is None:
        for m in reversed(user_messages):
            if m.get("role") != "user":
                continue
            if m.get("content", "") == last_user_msg:
                continue
            category = _parse_category(m.get("content", ""))
            if category is not None:
                break

    expense_context = _build_expense_context(start_date, end_date, category)
    system_content = f"{_AI_SYSTEM_PROMPT}\n\n{expense_context}"

    trimmed = _trim_messages(user_messages)
    messages = [{"role": "system", "content": system_content}] + trimmed

    import json as _json

    def generate():
        api_url, api_key, model_name = _load_moark_ai_config()
        secrets_path = _ai_secrets_file_path()
        example_name = "ai_api_secrets.example.json"

        if not api_key:
            err = (
                "未配置 AI 密钥：请在 "
                + secrets_path
                + " 中填写 api_key（可复制同目录下 "
                + example_name
                + " 为 ai_api_secrets.json 后编辑）；该文件请勿提交到 Git。"
            )
            yield f"data: {_json.dumps({'error': err}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return

        request_payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
            "stream": True,
        }
        request_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        last_error = None
        for attempt in range(_MAX_RETRIES):
            try:
                session = _build_http_session()
                resp = session.post(
                    api_url,
                    headers=request_headers,
                    json=request_payload,
                    timeout=(15, 90),
                    stream=True,
                )
                if resp.status_code == 400:
                    body = resp.text.lower()
                    if "token" in body or "length" in body or "context" in body:
                        yield f"data: {_json.dumps({'error': '对话过长，请点击左上角清空按钮开始新对话'}, ensure_ascii=False)}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                resp.raise_for_status()

                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[len("data:"):].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = _json.loads(payload)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield f"data: {_json.dumps({'t': content}, ensure_ascii=False)}\n\n"
                    except (KeyError, IndexError, _json.JSONDecodeError):
                        continue

                yield "data: [DONE]\n\n"
                return

            except (http_requests.exceptions.SSLError,
                    http_requests.exceptions.ConnectionError) as exc:
                last_error = exc
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
            except http_requests.exceptions.Timeout:
                yield f"data: {_json.dumps({'error': 'AI 服务响应超时，请稍后再试'}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                return
            except Exception as exc:
                yield f"data: {_json.dumps({'error': f'AI 服务异常：{exc}'}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                return

        yield f"data: {_json.dumps({'error': f'AI 服务连接失败（已重试{_MAX_RETRIES}次），请检查网络后再试'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    init_db()
    print("数据库初始化完成")
    print("启动服务器...")
    app.run(debug=False, host="0.0.0.0", port=8000)
