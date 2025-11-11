from flask import Flask, request, jsonify, render_template, redirect, session
from functools import wraps
import sqlite3
import json
import time
import hashlib
import requests
from datetime import datetime
import os
from urllib.parse import quote

# 导入语言支持
from language import lang, LANGUAGES

app = Flask(__name__)

# 全局CORS处理
@app.after_request
def after_request(response):
    # 为所有API路径添加CORS头
    if request.path.startswith('/api/'):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# 添加静态文件路由
@app.route('/static/<filename>')
def static_files(filename):
    return app.send_static_file(filename)


# 从环境变量或配置文件读取配置
DOMAIN = os.environ.get('DOMAIN', 'https://gift.bihuoai.com')
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-me')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
API_TOKEN = os.environ.get('API_TOKEN', 'bihuoai-api-token-2024')  # API访问令牌

# IP限制配置
IP_HOURLY_LIMIT = int(os.environ.get('IP_HOURLY_LIMIT', 3))  # 单IP每小时尝试次数
IP_DAILY_SUCCESS = int(os.environ.get('IP_DAILY_SUCCESS', 5))  # 单IP每天成功领取次数

app.secret_key = SECRET_KEY

# 语言检测和切换
def get_current_language():
    """获取当前语言"""
    # 优先使用session中的语言设置
    if 'language' in session:
        return session['language']

    # 根据IP地址自动检测语言
    ip_address = get_client_ip()
    detected_lang = lang.detect_language_from_ip(ip_address)

    # 将检测结果保存到session
    session['language'] = detected_lang
    return detected_lang

def set_language(language):
    """设置语言"""
    if language in ['zh', 'en']:
        session['language'] = language
        return True
    return False

# 尝试从.env文件读取配置
def load_env():
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
                    globals()[key] = value
    except FileNotFoundError:
        pass

# 加载配置
load_env()

def init_database():
    """初始化数据库（国际版纯净结构）"""
    conn = sqlite3.connect('gift_codes.db')
    conn.execute("PRAGMA encoding='UTF-8';")
    cursor = conn.cursor()

    # 创建兑换码表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code VARCHAR(32) UNIQUE NOT NULL,
            is_used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            claimed_at TIMESTAMP NULL,
            claimed_by_fingerprint VARCHAR(64) NULL
        )
    ''')

    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_fingerprint VARCHAR(64) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            ip_address VARCHAR(45),
            fingerprint_data TEXT,
            user_agent TEXT,
            last_claim_attempt TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建调研表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS surveys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_fingerprint VARCHAR(64) NOT NULL,
            email VARCHAR(255) NOT NULL,
            name VARCHAR(100),
            country VARCHAR(100),
            has_used_digital_human VARCHAR(10),
            problems TEXT,
            profession VARCHAR(50),
            custom_profession VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建IP限制表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ip_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address VARCHAR(45) NOT NULL,
            attempt_count INTEGER DEFAULT 1,
            success_count INTEGER DEFAULT 0,
            first_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建索引
    try:
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ip_address ON ip_limits(ip_address)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_attempt ON ip_limits(last_attempt)')
    except sqlite3.OperationalError:
        pass

    # 数据库迁移：为已存在的surveys表添加name字段
    try:
        cursor.execute("ALTER TABLE surveys ADD COLUMN name VARCHAR(100)")
    except sqlite3.OperationalError:
        # 字段已存在，忽略
        pass

    # 数据库迁移：为已存在的surveys表添加country字段
    try:
        cursor.execute("ALTER TABLE surveys ADD COLUMN country VARCHAR(100)")
    except sqlite3.OperationalError:
        # 字段已存在，忽略
        pass

    conn.commit()
    conn.close()

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect('gift_codes.db')
    conn.execute("PRAGMA encoding='UTF-8';")  # 设置数据库编码为UTF-8
    conn.row_factory = sqlite3.Row
    return conn

def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated_function

def api_token_required(f):
    """API访问令牌验证装饰器 - 任何token都可以访问"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # OPTIONS请求不需要验证
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)

        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': '缺少Authorization头'}), 401

        # 任何非空token都允许访问
        if token.strip() == '':
            return jsonify({'error': 'Authorization头不能为空'}), 401

        return f(*args, **kwargs)
    return decorated_function

def get_client_ip():
    """获取客户端真实IP（支持代理）"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr

def record_ip_attempt(ip_address, success=False):
    """记录IP尝试"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 查找今天的记录
    cursor.execute('''
        SELECT * FROM ip_limits
        WHERE ip_address = ?
        AND date(last_attempt) = date('now', 'localtime')
    ''', (ip_address,))

    record = cursor.fetchone()

    if record:
        # 更新现有记录
        new_attempt_count = record['attempt_count'] + 1
        new_success_count = record['success_count'] + (1 if success else 0)

        cursor.execute('''
            UPDATE ip_limits
            SET attempt_count = ?,
                success_count = ?,
                last_attempt = datetime('now', 'localtime')
            WHERE id = ?
        ''', (new_attempt_count, new_success_count, record['id']))
    else:
        # 创建新记录
        cursor.execute('''
            INSERT INTO ip_limits (ip_address, attempt_count, success_count)
            VALUES (?, 1, ?)
        ''', (ip_address, 1 if success else 0))

    conn.commit()
    conn.close()

def validate_claim_eligibility(fingerprint, email, ip):
    """验证领取资格（四层防护）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 第1层：设备指纹检查
    cursor.execute('SELECT * FROM users WHERE device_fingerprint = ?', (fingerprint,))
    if cursor.fetchone():
        conn.close()
        return False, '该设备已领取过兑换码'

    # 第2层：邮箱检查
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    if cursor.fetchone():
        conn.close()
        return False, '该邮箱已被使用'

    # 第3层：IP每日成功次数限制
    cursor.execute('''
        SELECT success_count
        FROM ip_limits
        WHERE ip_address = ?
        AND date(last_attempt) = date('now', 'localtime')
    ''', (ip,))

    ip_record = cursor.fetchone()
    if ip_record and ip_record['success_count'] >= IP_DAILY_SUCCESS:
        conn.close()
        return False, f'该IP今日领取次数已达上限（{IP_DAILY_SUCCESS}次）'

    # 第4层：IP每小时尝试次数限制
    cursor.execute('''
        SELECT COUNT(*) as recent_count
        FROM ip_limits
        WHERE ip_address = ?
        AND datetime(last_attempt) > datetime('now', '-1 hour', 'localtime')
    ''', (ip,))

    recent = cursor.fetchone()
    if recent and recent['recent_count'] >= IP_HOURLY_LIMIT:
        conn.close()
        return False, '请求过于频繁，请稍后再试'

    conn.close()
    return True, 'OK'

@app.route('/')
def index():
    """主页"""
    current_lang = get_current_language()
    return render_template('index.html', lang=current_lang)

@app.route('/check_and_claim')
def check_and_claim():
    """调研问卷页面"""
    current_lang = get_current_language()
    return render_template('survey.html', lang=current_lang)

@app.route('/result')
def result():
    """领取结果页面（独立路由，支持刷新）"""
    current_lang = get_current_language()

    # 从session中获取结果数据
    success = session.get('result_success', False)
    code = session.get('result_code', '')
    message = session.get('result_message', '')

    # 如果没有数据，说明是直接访问，跳转到首页
    if not success and not code and not message:
        return redirect('/')

    return render_template('result.html', success=success, code=code, message=message, lang=current_lang)

@app.route('/set_language/<language>')
def set_language_route(language):
    """设置语言"""
    if set_language(language):
        # 获取来源页面，避免循环重定向
        referrer = request.referrer
        if referrer and request.host in referrer:
            return redirect(referrer)
        return redirect('/')
    else:
        return redirect('/')

@app.route('/api/translations/<language>')
def get_translations(language):
    """获取翻译数据API"""
    if language not in ['zh', 'en']:
        return jsonify({'error': 'Language not supported'}), 400

    # 读取翻译文件
    translations_file = f'translations/{language}.json'
    if os.path.exists(translations_file):
        with open(translations_file, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        return jsonify(translations)
    else:
        return jsonify({'error': 'Translation file not found'}), 404

def assign_code_to_user(fingerprint):
    """为用户分配兑换码（返回结果数据）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 二次检查：确保用户没有已领取的兑换码（防止并发访问）
    cursor.execute('SELECT code FROM codes WHERE claimed_by_fingerprint = ?', (fingerprint,))
    existing_code = cursor.fetchone()

    if existing_code:
        conn.close()
        return {
            'success': True,
            'code': existing_code['code'],
            'message': '您已经领取过兑换码了！'
        }

    # 获取一个未使用的兑换码
    cursor.execute('SELECT * FROM codes WHERE is_used = FALSE AND claimed_by_fingerprint IS NULL LIMIT 1')
    available_code = cursor.fetchone()

    if not available_code:
        conn.close()
        return {
            'success': False,
            'code': '',
            'message': '抱歉，兑换码已经全部领完了！'
        }

    # 使用事务确保原子性操作
    try:
        # 分配兑换码给用户 - 使用北京时间，同时确保兑换码仍然可用
        cursor.execute('''
            UPDATE codes
            SET is_used = TRUE, claimed_at = datetime('now', 'localtime'), claimed_by_fingerprint = ?
            WHERE id = ? AND is_used = FALSE AND claimed_by_fingerprint IS NULL
        ''', (fingerprint, available_code['id']))

        # 检查是否成功更新（防止其他请求同时占用了这个兑换码）
        if cursor.rowcount == 0:
            conn.close()
            return {
                'success': False,
                'code': '',
                'message': '兑换码已被占用，请重试！'
            }

        conn.commit()
        conn.close()
    except Exception as e:
        conn.rollback()
        conn.close()
        return {
            'success': False,
            'code': '',
            'message': '系统繁忙，请稍后重试！'
        }

    return {
        'success': True,
        'code': available_code['code'],
        'message': '恭喜您！成功领取兑换码！'
    }

@app.route('/submit_survey', methods=['POST'])
def submit_survey():
    """提交调研数据并领取兑换码"""
    # 获取设备指纹和IP
    fingerprint = request.form.get('device_fingerprint', '').strip()
    email = request.form.get('email', '').strip()
    name = request.form.get('name', '').strip()
    country = request.form.get('country', '').strip()
    ip_address = get_client_ip()
    user_agent = request.headers.get('User-Agent', '')

    # 获取表单数据
    has_used_digital_human = request.form.get('has_used_digital_human', '').strip()
    problems = request.form.getlist('problems')  # 多选项
    profession = request.form.get('profession', '').strip()
    custom_profession = request.form.get('custom_profession', '').strip()

    # 获取当前语言
    current_lang = get_current_language()

    # 错误信息字典
    error_messages = {
        'zh': {
            'complete_info': '请填写完整信息',
            'select_problem': '请至少选择一个希望解决的问题',
            'email_invalid': '请输入正确的邮箱地址',
            'fill_profession': '请填写您的具体职业'
        },
        'en': {
            'complete_info': 'Please complete all required information',
            'select_problem': 'Please select at least one problem you want to solve',
            'email_invalid': 'Please enter a valid email address',
            'fill_profession': 'Please specify your profession'
        }
    }

    # 基础数据验证
    if not all([fingerprint, email, name, country, has_used_digital_human, profession]):
        return render_template('survey.html', error=error_messages[current_lang]['complete_info'], lang=current_lang)

    if not problems:
        return render_template('survey.html', error=error_messages[current_lang]['select_problem'], lang=current_lang)

    # 邮箱格式验证
    import re
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return render_template('survey.html', error=error_messages[current_lang]['email_invalid'], lang=current_lang)

    # 如果选择其他岗位，必须填写自定义职业
    if profession == '其它岗位' and not custom_profession:
        return render_template('survey.html', error=error_messages[current_lang]['fill_profession'], lang=current_lang)

    # 四层验证
    record_ip_attempt(ip_address, success=False)  # 记录尝试
    is_eligible, error_message = validate_claim_eligibility(fingerprint, email, ip_address)

    if not is_eligible:
        # 如果是已领取的设备或邮箱，直接跳转到结果页显示已有兑换码
        if '该设备已领取过兑换码' in error_message or '该邮箱已被使用' in error_message:
            # 查询已有兑换码
            conn_check = get_db_connection()
            cursor_check = conn_check.cursor()

            # 先尝试通过设备指纹查询
            cursor_check.execute('SELECT code FROM codes WHERE claimed_by_fingerprint = ?', (fingerprint,))
            existing_code = cursor_check.fetchone()

            # 如果设备指纹没找到，通过邮箱查询
            if not existing_code:
                cursor_check.execute('''
                    SELECT c.code FROM codes c
                    JOIN users u ON c.claimed_by_fingerprint = u.device_fingerprint
                    WHERE u.email = ?
                ''', (email,))
                existing_code = cursor_check.fetchone()

            conn_check.close()

            if existing_code:
                # 将已有兑换码存储到session并跳转
                session['result_success'] = True
                session['result_code'] = existing_code['code']
                session['result_message'] = '您已经领取过兑换码了！'
                return redirect('/result')

        # 其他错误（IP限制等）显示错误信息
        return render_template('survey.html', error=error_message)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 将多选问题转为字符串存储
        problems_str = ','.join(problems)

        # 保存用户信息到users表
        cursor.execute('''
            INSERT INTO users
            (device_fingerprint, email, ip_address, user_agent, created_at, last_claim_attempt)
            VALUES (?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
        ''', (fingerprint, email, ip_address, user_agent))

        # 保存调研数据 - 使用北京时间
        cursor.execute('''
            INSERT INTO surveys
            (device_fingerprint, email, name, country, has_used_digital_human, problems, profession, custom_profession, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        ''', (fingerprint, email, name, country, has_used_digital_human, problems_str, profession, custom_profession))

        conn.commit()
        conn.close()

        # 记录成功领取
        record_ip_attempt(ip_address, success=True)

        # 分配兑换码
        result = assign_code_to_user(fingerprint)

        # 将结果存储到session
        session['result_success'] = result['success']
        session['result_code'] = result['code']
        session['result_message'] = result['message']

        # 重定向到结果页面
        return redirect('/result')

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"保存调研数据失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('survey.html', error='提交失败，请重试')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """管理员登录"""
    if request.method == 'POST':
        password = request.form.get('password') or request.json.get('password', '')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect('/admin') if request.form.get('password') else jsonify({'success': True})
        else:
            if request.form.get('password'):
                return render_template('admin_login.html', error='密码错误')
            else:
                return jsonify({'success': False, 'message': '密码错误'}), 401
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """管理员登出"""
    session.pop('admin_logged_in', None)
    return redirect('/admin/login')

@app.route('/admin')
@admin_required
def admin():
    """管理后台"""
    return render_template('admin.html')

@app.route('/admin/stats')
@admin_required
def admin_stats():
    """获取统计信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 总兑换码数量
    cursor.execute('SELECT COUNT(*) as total FROM codes')
    total_codes = cursor.fetchone()['total']
    
    # 已领取数量
    cursor.execute('SELECT COUNT(*) as used FROM codes WHERE is_used = TRUE')
    used_codes = cursor.fetchone()['used']
    
    # 剩余数量
    remaining_codes = total_codes - used_codes
    
    # 调研人数
    cursor.execute('SELECT COUNT(*) as survey_count FROM surveys')
    survey_count = cursor.fetchone()['survey_count']
    
    # 最近领取记录
    cursor.execute('''
        SELECT c.code, c.claimed_at,
               COALESCE(u.email, '未知用户') as email,
               u.device_fingerprint
        FROM codes c
        LEFT JOIN users u ON c.claimed_by_fingerprint = u.device_fingerprint
        WHERE c.is_used = TRUE
        ORDER BY c.claimed_at DESC
        LIMIT 10
    ''')
    recent_claims = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'total_codes': total_codes,
        'used_codes': used_codes,
        'remaining_codes': remaining_codes,
        'survey_count': survey_count,
        'recent_claims': [dict(row) for row in recent_claims]
    })

@app.route('/admin/import', methods=['POST'])
@admin_required
def import_codes():
    """导入兑换码"""
    data = request.get_json()
    codes_text = data.get('codes', '')
    
    if not codes_text.strip():
        return jsonify({'error': '请提供兑换码列表'}), 400
    
    # 将文本按行分割，过滤空行
    codes = [code.strip() for code in codes_text.strip().split('\n') if code.strip()]
    
    if not codes:
        return jsonify({'error': '请提供有效的兑换码'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    success_count = 0
    error_count = 0
    
    for code in codes:
        try:
            cursor.execute('INSERT INTO codes (code) VALUES (?)', (code.strip(),))
            success_count += 1
        except sqlite3.IntegrityError:
            error_count += 1  # 重复的兑换码
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'imported_count': success_count,
        'duplicate_count': error_count,
        'message': f'成功导入 {success_count} 个兑换码，{error_count} 个重复'
    })

@app.route('/admin/export')
@admin_required
def export_codes():
    """导出兑换码使用情况"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.code, c.is_used, c.claimed_at, u.email, u.device_fingerprint, u.ip_address
        FROM codes c
        LEFT JOIN users u ON c.claimed_by_fingerprint = u.device_fingerprint
        ORDER BY c.id
    ''')
    
    codes = cursor.fetchall()
    conn.close()
    
    # 转换为字典并确保字符串正确编码
    result = []
    for row in codes:
        row_dict = dict(row)
        # 确保邮箱字段正确编码
        if row_dict['email']:
            row_dict['email'] = str(row_dict['email'])
        result.append(row_dict)
    
    response = app.response_class(
        response=json.dumps(result, ensure_ascii=False, indent=2),
        status=200,
        mimetype='application/json; charset=utf-8'
    )
    return response

@app.route('/admin/export_surveys')
@admin_required
def export_surveys():
    """导出调研数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.device_fingerprint, s.email, s.name, s.country, s.has_used_digital_human, s.problems,
               s.profession, s.custom_profession, s.created_at,
               u.ip_address, c.code
        FROM surveys s
        LEFT JOIN users u ON s.device_fingerprint = u.device_fingerprint
        LEFT JOIN codes c ON s.device_fingerprint = c.claimed_by_fingerprint
        ORDER BY s.created_at DESC
    ''')

    surveys = cursor.fetchall()
    conn.close()

    # 转换为字典并确保字符串正确编码
    result = []
    for row in surveys:
        row_dict = dict(row)
        # 确保字符串字段正确编码
        for key in ['email', 'name', 'country', 'problems', 'profession', 'custom_profession', 'has_used_digital_human']:
            if row_dict.get(key):
                row_dict[key] = str(row_dict[key])
        result.append(row_dict)
    
    response = app.response_class(
        response=json.dumps(result, ensure_ascii=False, indent=2),
        status=200,
        mimetype='application/json; charset=utf-8'
    )
    return response

@app.route('/admin/export_surveys_csv')
@admin_required
def export_surveys_csv():
    """导出调研数据为CSV格式"""
    import csv
    import io
    from datetime import datetime
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.device_fingerprint, s.email, s.name, s.country, s.has_used_digital_human,
               s.problems, s.profession, s.custom_profession, s.created_at,
               u.ip_address, c.code
        FROM surveys s
        LEFT JOIN users u ON s.device_fingerprint = u.device_fingerprint
        LEFT JOIN codes c ON s.device_fingerprint = c.claimed_by_fingerprint
        ORDER BY s.created_at DESC
    ''')

    surveys = cursor.fetchall()
    conn.close()

    # 创建CSV文件内容
    output = io.StringIO()
    writer = csv.writer(output)

    # 写入表头
    headers = ['设备指纹', '邮箱', '昵称', '国家/地区', '是否使用过数字人', '希望解决的问题',
               '职业', '自定义职业', '提交时间', 'IP地址', '兑换码']
    writer.writerow(headers)

    # 写入数据
    for survey in surveys:
        row = [
            survey['device_fingerprint'] or '',
            survey['email'] or '未知用户',
            survey['name'] or '',
            survey['country'] or '',
            survey['has_used_digital_human'] or '',
            survey['problems'] or '',
            survey['profession'] or '',
            survey['custom_profession'] or '',
            survey['created_at'] or '',
            survey['ip_address'] or '',
            survey['code'] or ''
        ]
        writer.writerow(row)
    
    # 准备响应
    output.seek(0)
    csv_content = output.getvalue()
    output.close()
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"survey_data_{timestamp}.csv"
    
    response = app.response_class(
        response=csv_content.encode('utf-8-sig'),  # 使用UTF-8 BOM确保Excel正确显示中文
        status=200,
        mimetype='text/csv; charset=utf-8'
    )
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@app.route('/admin/delete', methods=['POST'])
@admin_required
def delete_codes():
    """删除兑换码"""
    data = request.get_json()
    action = data.get('action', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if action == 'delete_unused':
        # 删除未使用的兑换码
        cursor.execute('DELETE FROM codes WHERE is_used = FALSE')
        deleted_count = cursor.rowcount
        message = f'已删除 {deleted_count} 个未使用的兑换码'
        
    elif action == 'delete_used':
        # 删除已使用的兑换码
        cursor.execute('DELETE FROM codes WHERE is_used = TRUE')
        deleted_count = cursor.rowcount
        message = f'已删除 {deleted_count} 个已使用的兑换码'
        
    elif action == 'delete_all':
        # 删除所有兑换码
        cursor.execute('DELETE FROM codes')
        deleted_count = cursor.rowcount
        message = f'已删除所有 {deleted_count} 个兑换码'
        
    elif action == 'delete_specific':
        # 删除指定兑换码
        codes_to_delete = data.get('codes', [])
        if not codes_to_delete:
            return jsonify({'success': False, 'message': '请指定要删除的兑换码'}), 400
        
        placeholders = ','.join('?' * len(codes_to_delete))
        cursor.execute(f'DELETE FROM codes WHERE code IN ({placeholders})', codes_to_delete)
        deleted_count = cursor.rowcount
        message = f'已删除 {deleted_count} 个指定的兑换码'
        
    else:
        conn.close()
        return jsonify({'success': False, 'message': '无效的删除操作'}), 400
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': message,
        'deleted_count': deleted_count
    })

@app.route('/admin/reset_user', methods=['POST'])
@admin_required
def reset_user():
    """重置用户领取状态（允许用户重新领取）"""
    data = request.get_json()
    fingerprint = data.get('fingerprint', '')
    email = data.get('email', '')

    if not fingerprint and not email:
        return jsonify({'success': False, 'message': '请提供设备指纹或邮箱'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # 构建查询条件
    if fingerprint:
        condition = 'claimed_by_fingerprint = ?'
        param = fingerprint
    else:
        # 通过email查找fingerprint
        cursor.execute('SELECT device_fingerprint FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return jsonify({'success': False, 'message': '未找到该用户'}), 404
        condition = 'claimed_by_fingerprint = ?'
        param = user['device_fingerprint']

    # 将该用户的兑换码重置为未使用状态
    cursor.execute(f'''
        UPDATE codes
        SET is_used = FALSE, claimed_at = NULL, claimed_by_fingerprint = NULL
        WHERE {condition}
    ''', (param,))

    reset_count = cursor.rowcount

    # 同时清除该用户的调研数据和用户记录
    cursor.execute(f'DELETE FROM surveys WHERE device_fingerprint = ?', (param,))
    cursor.execute(f'DELETE FROM users WHERE device_fingerprint = ?', (param,))

    conn.commit()
    conn.close()

    if reset_count > 0:
        return jsonify({
            'success': True,
            'message': f'已重置用户领取状态，释放了 {reset_count} 个兑换码'
        })
    else:
        return jsonify({
            'success': False,
            'message': '未找到该用户的领取记录'
        })


@app.route('/init_database_now')
def init_database_now():
    """临时的数据库初始化接口（仅用于部署时）"""
    try:
        init_database()
        return jsonify({
            'success': True,
            'message': '数据库初始化成功！',
            'tables': ['codes', 'users']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'数据库初始化失败: {str(e)}'
        }), 500

# ==================== API接口区域 ====================

@app.route('/api/surveys', methods=['GET', 'OPTIONS'])
@api_token_required
def api_get_surveys():
    # 处理OPTIONS预检请求
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    """获取问卷数据API接口"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取查询参数
        start_date = request.args.get('start_date')  # YYYY-MM-DD格式
        end_date = request.args.get('end_date')  # YYYY-MM-DD格式
        
        # 构建基础查询
        base_query = '''
            SELECT s.device_fingerprint, s.email, s.has_used_digital_human,
                   s.problems, s.profession, s.custom_profession, s.created_at, c.code,
                   c.claimed_at, c.is_used, u.ip_address
            FROM surveys s
            LEFT JOIN users u ON s.device_fingerprint = u.device_fingerprint
            LEFT JOIN codes c ON s.device_fingerprint = c.claimed_by_fingerprint
        '''
        
        # 添加日期过滤条件
        conditions = []
        params = []
        
        if start_date:
            conditions.append("date(s.created_at) >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("date(s.created_at) <= ?")
            params.append(end_date)
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        base_query += " ORDER BY s.created_at DESC"
        
        cursor.execute(base_query, params)
        surveys = cursor.fetchall()
        
        total_count = len(surveys)
        
        conn.close()
        
        # 转换为字典格式
        result = []
        for survey in surveys:
            survey_dict = {
                'device_fingerprint': survey['device_fingerprint'],
                'email': survey['email'],
                'ip_address': survey['ip_address'],
                'has_used_digital_human': survey['has_used_digital_human'],
                'problems': survey['problems'],
                'profession': survey['profession'],
                'custom_profession': survey['custom_profession'],
                'created_at': survey['created_at'],
                'exchange_code': survey['code'],
                'exchange_time': survey['claimed_at'],
                'code_used': bool(survey['is_used']) if survey['is_used'] is not None else None
            }
            result.append(survey_dict)
        
        response = jsonify({
            'success': True,
            'data': result,
            'total': total_count,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # 添加CORS头
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }), 500

@app.route('/api/surveys/stats', methods=['GET', 'OPTIONS'])
@api_token_required
def api_get_survey_stats():
    # 处理OPTIONS预检请求
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    """获取问卷统计数据API接口"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 基础统计
        cursor.execute('SELECT COUNT(*) as total FROM surveys')
        total_surveys = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as total FROM codes WHERE is_used = TRUE')
        codes_used = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as total FROM codes')
        total_codes = cursor.fetchone()['total']
        
        # 按日期统计
        cursor.execute('''
            SELECT date(created_at) as survey_date, COUNT(*) as count
            FROM surveys
            GROUP BY date(created_at)
            ORDER BY survey_date DESC
            LIMIT 30
        ''')
        daily_stats = cursor.fetchall()
        
        # 问题分析
        cursor.execute('''
            SELECT problems, COUNT(*) as count
            FROM surveys
            WHERE problems IS NOT NULL AND problems != ''
            GROUP BY problems
            ORDER BY count DESC
            LIMIT 10
        ''')
        problem_stats = cursor.fetchall()
        
        # 职业分析
        cursor.execute('''
            SELECT profession, COUNT(*) as count
            FROM surveys
            WHERE profession IS NOT NULL AND profession != ''
            GROUP BY profession
            ORDER BY count DESC
        ''')
        profession_stats = cursor.fetchall()
        
        conn.close()
        
        response = jsonify({
            'success': True,
            'stats': {
                'total_surveys': total_surveys,
                'codes_used': codes_used,
                'total_codes': total_codes,
                'codes_remaining': total_codes - codes_used,
                'daily_surveys': [dict(row) for row in daily_stats],
                'problem_distribution': [dict(row) for row in problem_stats],
                'profession_distribution': [dict(row) for row in profession_stats]
            },
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # 添加CORS头
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }), 500

if __name__ == '__main__':
    init_database()
    # 宝塔Python项目管理器会自动分配端口，这里使用动态端口
    port = int(os.environ.get('PORT', 8000))  # 改为8000或其他未占用端口
    app.run(debug=False, host='0.0.0.0', port=port)