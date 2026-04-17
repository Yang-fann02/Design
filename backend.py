import sqlite3
import pandas as pd
from flask import Flask, render_template, jsonify, request
import os

app = Flask(__name__)
# 从环境变量获取数据库路径，默认使用当前目录下的student_expense_record.db
DATABASE = os.environ.get('DATABASE_PATH', 'student_expense_record.db')


def get_db():
    # 获取数据库路径
    db_path = os.environ.get('DATABASE_PATH', 'student_expense_record.db')
    # 如果路径不是绝对路径，拼接为绝对路径（基于当前文件所在目录）
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
    # 建立SQLite数据库连接
    conn = sqlite3.connect(db_path)
    # 设置行工厂，使查询结果可以通过列名访问（如row['date']）
    conn.row_factory = sqlite3.Row
    return conn

# 数据库初始化函数
def init_db():
    conn = get_db()
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL
        )
        '''
    )
    conn.commit()
    conn.close()

# 获取所有开支记录函数
def get_all_expenses():
    conn = get_db()
    # 查询expenses表的日期、类别、金额，按日期排序
    rows = conn.execute('SELECT date, category, amount FROM expenses ORDER BY date').fetchall()
    conn.close()
    if not rows:
        return pd.DataFrame()
    # 将查询结果转换为字典列表，键名为中文（日期、类别、金额）
    data = [{'日期': r['date'], '类别': r['category'], '金额': r['amount']} for r in rows]
    return pd.DataFrame(data)

# 统计分析函数
def get_statistics(start_date=None, end_date=None): # 可选的开始和结束日期参数
    df = get_all_expenses()
     # 如果数据为空，返回包含所有统计指标的字典
    if df.empty:
        return {
            'total_expense': 0,
            'daily_average': 0,
            'category_expense': {},
            'daily_trend': {},
            'date_range': {'min': None, 'max': None},
            'raw_table': []
        }
    # 将金额列转换为数值类型，日期列转换为datetime格式再转回字符串
    if '金额' in df.columns:
        df['金额'] = pd.to_numeric(df['金额'], errors='coerce') # 转换为数字，无法转换的变为NaN
    if '日期' in df.columns:
        df['日期'] = pd.to_datetime(df['日期'], errors='coerce').dt.strftime('%Y-%m-%d') # 格式化日期
    # 删除日期或金额为空的行
    df = df.dropna(subset=['日期', '金额'])
    # 根据日期范围筛选数据
    if start_date:
        df = df[df['日期'] >= start_date]
    if end_date:
        df = df[df['日期'] <= end_date]
    # 再次检查筛选后是否为空
    if df.empty:
        return {
            'total_expense': 0,
            'daily_average': 0,
            'category_expense': {},
            'daily_trend': {},
            'date_range': {'min': None, 'max': None},
            'raw_table': []
        }
    # 计算总支出和日均支出，保留2位小数
    total = round(df['金额'].sum(), 2) # 总支出
    avg = round(df['金额'].mean(), 2) # 日均支出
    # 按类别分组统计支出
    category_data = df.groupby('类别')['金额'].sum().round(2).to_dict() # 各类别支出总额
    category_data = {str(k): round(float(v), 2) for k, v in category_data.items()} # 转换键为字符串
    # 按日期分组统计支出
    daily_data = df.groupby('日期')['金额'].sum().round(2).to_dict() # 每日支出总额
    daily_data = {str(k): round(float(v), 2) for k, v in daily_data.items()} 
    # 获取日期范围
    dates = sorted(df['日期'].unique()) # 获取所有不重复的日期并排序
    date_min = dates[0] if dates else None # 最早日期
    date_max = dates[-1] if dates else None # 最晚日期
    # 处理表格数据，将NaN替换为空字符串
    table_data = df.fillna('').to_dict(orient='records')
    for row in table_data:
        for key, val in row.items():
            if key == '金额' and val and val != 'nan':
                # 处理金额列
                try:
                    row[key] = round(float(val), 2) # 保留2位小数
                except:
                    pass
    # 返回完整的统计结果
    return {
        'total_expense': total, # 总支出
        'daily_average': avg, # 日均支出
        'category_expense': category_data, # 各类别支出
        'daily_trend': daily_data, # 每日支出趋势
        'date_range': {'min': date_min, 'max': date_max}, # 日期范围
        'raw_table': table_data # 原始表格数据
    }

# 日期索引函数
def get_date_index():
    df = get_all_expenses() # 获取所有开支数据
    # 如果数据为空或没有日期列，返回空的索引结构
    if df.empty or '日期' not in df.columns:
        return {
            'years': [], # 年份列表
            'months_by_year': {}, # 每个年份包含的月份
            'days_by_year_month': {}, # 每个年月包含的日期
            'date_range': {'min': None, 'max': None} # 日期范围
        }
    # 转换日期格式为YYYY-MM-DD字符串
    dates = pd.to_datetime(df['日期'], errors='coerce').dropna().dt.strftime('%Y-%m-%d')
    uniq = sorted(set(dates.tolist())) # 获取唯一日期并排序
    if not uniq:
        return {
            'years': [],
            'months_by_year': {},
            'days_by_year_month': {},
            'date_range': {'min': None, 'max': None}
        }
    # 提取所有不重复的年份
    years = sorted({int(d[0:4]) for d in uniq if len(d) >= 10})
    months_by_year = {str(y): [] for y in years} # 初始化每个年份的月份列表
    days_by_year_month = {} # 初始化每个年月的日期列表
    # 遍历所有日期，提取年、月、日信息
    for ds in uniq:
        if len(ds) < 10: # 日期格式不正确则跳过
            continue
        y, m, d = ds[0:4], ds[5:7], ds[8:10] # 提取年、月、日部分
        if not (y.isdigit() and m.isdigit() and d.isdigit()): # 验证是否为有效数字
            continue
        mi, di = int(m), int(d) # 转换为整数
        if mi not in months_by_year[y]: # 如果月份不在该年的列表中
            months_by_year[y].append(mi) # 添加月份
        ym = f"{y}-{m}" # 年月组合键
        if ym not in days_by_year_month: # 如果该年月不在字典中
            days_by_year_month[ym] = [] # 初始化日期列表
        if di not in days_by_year_month[ym]: # 如果日期不在列表中
            days_by_year_month[ym].append(di) # 添加日期
    # 对月份和日期进行排序
    for y in months_by_year:
        months_by_year[y] = sorted(months_by_year[y])
    for ym in days_by_year_month:
        days_by_year_month[ym] = sorted(days_by_year_month[ym])
    return {
        'years': years, # 年份列表
        'months_by_year': months_by_year, # 每个年份包含的月份
        'days_by_year_month': days_by_year_month, # 每个年月包含的日期
        'date_range': {'min': uniq[0], 'max': uniq[-1]} # 日期范围
    }

# Flask路由定义
@app.route('/')
def index():
    return render_template('frontend.html') # 渲染并返回frontend.html模板

# 统计API路由
@app.route('/api/statistics')
def get_stats():
    start_date = request.args.get('start_date') # 从URL参数获取开始日期
    end_date = request.args.get('end_date') # 从URL参数获取结束日期
    stats = get_statistics(start_date=start_date, end_date=end_date) # 调用统计函数
    return jsonify({**stats, 'has_data': True}) # 返回JSON格式的统计结果

# 日期索引API路由
@app.route('/api/date_index')
def get_dates():
    index = get_date_index() # 获取日期索引
    return jsonify({'has_data': True, 'date_index': index}) # 返回JSON格式的索引数据


if __name__ == '__main__':
    init_db()
    print("数据库初始化完成")
    print("启动服务器...")
    app.run(debug=False, host='0.0.0.0', port=8000)
