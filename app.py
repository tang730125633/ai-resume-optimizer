from flask import Flask, request, jsonify, send_file, render_template
from flask.views import MethodView
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.utils import secure_filename
from docx import Document
import PyPDF2
import requests
import json
import markdown
from datetime import datetime
import random
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from contextlib import contextmanager

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PDF_FOLDER'] = 'static/pdfs'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PDF_FOLDER'], exist_ok=True)

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyBjQgTtUnODK8Pd14J-fXweIa0NezoPL2A')
ADMIN_KEY = os.getenv('ADMIN_KEY', 'admin-secret-key-2026')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/ai_resume_optimizer')

# Database connection pool
@contextmanager
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def generate_order_no(prefix):
    """生成订单号: 前缀 + 时间戳 + 随机4位数"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_num = random.randint(1000, 9999)
    return f"{prefix}{timestamp}{random_num}"

def extract_text_from_docx(file_path):
    """从DOCX文件提取文本"""
    doc = Document(file_path)
    return '\n'.join([para.text for para in doc.paragraphs])

def extract_text_from_pdf(file_path):
    """从PDF文件提取文本"""
    text = []
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text.append(page.extract_text())
    return '\n'.join(text)

def generate_template_with_gemini(job_title, years_exp):
    """使用Gemini生成简历模板"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""为一位{years_exp}年经验的{job_title}生成一份专业简历模板，用Markdown格式输出。
包含：个人信息、个人总结、工作经历（2段）、技能清单、项目经验（2个）。
要求简洁专业，突出核心能力和成果。"""

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload)
    result = response.json()

    if 'candidates' not in result:
        raise Exception(f"Gemini API 返回异常: {result}")

    return result['candidates'][0]['content']['parts'][0]['text']

def analyze_resume_with_gemini(resume_text):
    """使用Gemini分析简历"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    prompt = f"""请分析以下简历，并提供：
1. 简历的主要问题和改进建议
2. 给出一个综合评分（0-100分）
3. 生成3个优化版本的简历内容：
   - 版本1：传统格式优化（保持原有风格，优化表达和关键词）
   - 版本2：现代简约风格（简洁明了，突出核心能力）
   - 版本3：ATS友好版本（优化关键词，适合招聘系统筛选）

简历内容：
{resume_text}

请以JSON格式返回，包含：
{{
  "analysis": "分析报告",
  "score": 85,
  "versions": [
    {{"title": "版本1：传统格式优化", "description": "说明", "content": "优化后的简历内容"}},
    {{"title": "版本2：现代简约风格", "description": "说明", "content": "优化后的简历内容"}},
    {{"title": "版本3：ATS友好版本", "description": "说明", "content": "优化后的简历内容"}}
  ]
}}"""

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload)
    result = response.json()

    if 'candidates' not in result:
        raise Exception(f"Gemini API 返回异常: {result}")

    text = result['candidates'][0]['content']['parts'][0]['text']

    # 清洗 markdown 代码块
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()

    return json.loads(text)

def generate_pdf_from_markdown(content, output_path):
    """从Markdown内容生成PDF（reportlab实现）"""
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    # 注册中文字体（Railway 容器内使用系统字体）
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/System/Library/Fonts/STHeiti Light.ttc',
    ]
    font_registered = False
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont('CustomFont', fp))
                font_registered = True
                break
            except Exception:
                continue

    base_font = 'CustomFont' if font_registered else 'Helvetica'

    styles = {
        'h1': ParagraphStyle('h1', fontName=base_font, fontSize=20, textColor=colors.HexColor('#2563eb'),
                             spaceAfter=12, spaceBefore=6, leading=26),
        'h2': ParagraphStyle('h2', fontName=base_font, fontSize=14, textColor=colors.HexColor('#1e40af'),
                             spaceAfter=8, spaceBefore=14, leading=20),
        'h3': ParagraphStyle('h3', fontName=base_font, fontSize=12, textColor=colors.HexColor('#374151'),
                             spaceAfter=6, spaceBefore=8, leading=16),
        'body': ParagraphStyle('body', fontName=base_font, fontSize=10, textColor=colors.HexColor('#333333'),
                               spaceAfter=4, leading=15),
    }

    story = []
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 4))
        elif line.startswith('# '):
            story.append(Paragraph(line[2:], styles['h1']))
            story.append(HRFlowable(width='100%', thickness=2, color=colors.HexColor('#2563eb'), spaceAfter=6))
        elif line.startswith('## '):
            story.append(Paragraph(line[3:], styles['h2']))
        elif line.startswith('### '):
            story.append(Paragraph(line[4:], styles['h3']))
        elif line.startswith('- ') or line.startswith('* '):
            story.append(Paragraph(f'• {line[2:]}', styles['body']))
        else:
            story.append(Paragraph(line, styles['body']))

    doc.build(story)

# ============================================
# API 路由
# ============================================

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/api/user/login', methods=['POST'])
def user_login():
    """用户登录/注册"""
    data = request.json
    phone = data.get('phone')

    if not phone or len(phone) != 11:
        return jsonify({'success': False, 'error': '手机号格式错误'}), 400

    with get_db_connection() as conn:
        cur = conn.cursor()

        # 查询用户是否存在
        cur.execute('SELECT id, phone, free_count, balance FROM users WHERE phone = %s', (phone,))
        user = cur.fetchone()

        if user:
            # 更新最后登录时间
            cur.execute('UPDATE users SET last_login = NOW() WHERE id = %s', (user['id'],))
        else:
            # 注册新用户
            cur.execute('''
                INSERT INTO users (phone, free_count, balance)
                VALUES (%s, 3, 0.00)
                RETURNING id, phone, free_count, balance
            ''', (phone,))
            user = cur.fetchone()

        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'phone': user['phone'],
                'free_count': user['free_count'],
                'balance': float(user['balance'])
            }
        })

@app.route('/api/user/info', methods=['GET'])
def get_user_info():
    """获取用户信息"""
    phone = request.args.get('phone')

    if not phone:
        return jsonify({'success': False, 'error': '缺少手机号参数'}), 400

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute('SELECT id, phone, free_count, balance FROM users WHERE phone = %s', (phone,))
        user = cur.fetchone()

        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'phone': user['phone'],
                'free_count': user['free_count'],
                'balance': float(user['balance'])
            }
        })

@app.route('/api/generate-template', methods=['POST'])
def generate_template():
    """生成简历模板"""
    data = request.json
    user_id = data.get('user_id')
    job_title = data.get('job_title', 'Python后端工程师')
    years_exp = data.get('years_exp', 3)

    if not user_id:
        return jsonify({'success': False, 'error': '缺少用户ID'}), 400

    with get_db_connection() as conn:
        cur = conn.cursor()

        # 查询用户状态
        cur.execute('SELECT free_count, balance FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()

        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        cost = 0

        # 判断扣费方式
        if user['free_count'] > 0:
            # 使用免费次数
            cur.execute('UPDATE users SET free_count = free_count - 1, total_generated = total_generated + 1 WHERE id = %s', (user_id,))
            cost = 0
        elif user['balance'] >= 5.00:
            # 扣除余额
            order_no = generate_order_no('CSM')
            cur.execute('''
                INSERT INTO orders (order_no, user_id, order_type, amount, description, payment_method, status, paid_at)
                VALUES (%s, %s, 'consume', 5.00, '生成模板', 'balance', 'paid', NOW())
            ''', (order_no, user_id))
            cur.execute('UPDATE users SET balance = balance - 5.00, total_generated = total_generated + 1 WHERE id = %s', (user_id,))
            cost = 5
        else:
            return jsonify({'success': False, 'error': '余额不足，请充值'}), 400

        # 调用 Gemini API 生成
        try:
            import traceback
            template = generate_template_with_gemini(job_title, years_exp)

            # 保存到数据库
            cur.execute('''
                INSERT INTO resumes (user_id, resume_type, job_title, years_experience, generated_content, is_paid)
                VALUES (%s, 'template', %s, %s, %s, %s)
            ''', (user_id, job_title, years_exp, template, cost > 0))

            # 获取更新后的用户信息
            cur.execute('SELECT free_count, balance FROM users WHERE id = %s', (user_id,))
            updated_user = cur.fetchone()

            return jsonify({
                'success': True,
                'template': template,
                'cost': cost,
                'user': {
                    'free_count': updated_user['free_count'],
                    'balance': float(updated_user['balance'])
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': f'生成失败: {str(e)}', 'detail': traceback.format_exc()}), 500

@app.route('/api/optimize', methods=['POST'])
def optimize_resume():
    """优化简历（multipart/form-data）"""
    user_id = request.form.get('user_id')

    if not user_id:
        return jsonify({'success': False, 'error': '缺少用户ID'}), 400

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未上传文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '文件名为空'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            # 检查余额
            cur.execute('SELECT balance FROM users WHERE id = %s', (user_id,))
            user = cur.fetchone()

            if not user:
                return jsonify({'success': False, 'error': '用户不存在'}), 404

            if user['balance'] < 10.00:
                return jsonify({'success': False, 'error': '余额不足，请充值'}), 400

            # 扣除余额
            order_no = generate_order_no('CSM')
            cur.execute('''
                INSERT INTO orders (order_no, user_id, order_type, amount, description, payment_method, status, paid_at)
                VALUES (%s, %s, 'consume', 10.00, '优化简历', 'balance', 'paid', NOW())
            ''', (order_no, user_id))
            cur.execute('UPDATE users SET balance = balance - 10.00, total_optimized = total_optimized + 1 WHERE id = %s', (user_id,))

            # 提取文件文本
            if filename.endswith('.docx'):
                resume_text = extract_text_from_docx(filepath)
            elif filename.endswith('.pdf'):
                resume_text = extract_text_from_pdf(filepath)
            else:
                return jsonify({'success': False, 'error': '不支持的文件格式，请上传PDF或DOCX'}), 400

            # 调用 Gemini API 分析
            result = analyze_resume_with_gemini(resume_text)

            # 保存到数据库
            cur.execute('''
                INSERT INTO resumes (user_id, resume_type, original_content, ai_analysis, ai_score, optimized_versions, is_paid)
                VALUES (%s, 'optimize', %s, %s, %s, %s, true)
            ''', (user_id, resume_text, result['analysis'], result.get('score', 0), json.dumps(result['versions'])))

            # 获取更新后的用户余额
            cur.execute('SELECT balance FROM users WHERE id = %s', (user_id,))
            updated_user = cur.fetchone()

            return jsonify({
                'success': True,
                'result': {
                    'analysis': result['analysis'],
                    'score': result.get('score', 0),
                    'versions': result['versions']
                },
                'cost': 10,
                'user': {
                    'balance': float(updated_user['balance'])
                }
            })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route('/api/recharge/create', methods=['POST'])
def create_recharge_order():
    """创建充值订单"""
    data = request.json
    user_id = data.get('user_id')
    amount = data.get('amount')

    if not user_id or not amount:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    valid_amounts = [50, 100, 200, 500]
    if float(amount) not in valid_amounts:
        return jsonify({'success': False, 'error': f'充值金额必须为 {valid_amounts} 之一'}), 400

    with get_db_connection() as conn:
        cur = conn.cursor()

        # 验证用户存在
        cur.execute('SELECT id FROM users WHERE id = %s', (user_id,))
        if not cur.fetchone():
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        order_no = generate_order_no('RCH')
        cur.execute('''
            INSERT INTO orders (order_no, user_id, order_type, amount, description, status)
            VALUES (%s, %s, 'recharge', %s, %s, 'pending')
        ''', (order_no, user_id, amount, f'充值{amount}元'))

        return jsonify({
            'success': True,
            'order_no': order_no
        })


@app.route('/api/admin/confirm-recharge', methods=['POST'])
def confirm_recharge():
    """管理员确认充值"""
    data = request.json
    order_no = data.get('order_no')
    admin_key = data.get('admin_key')

    if admin_key != ADMIN_KEY:
        return jsonify({'success': False, 'error': '无权限'}), 403

    if not order_no:
        return jsonify({'success': False, 'error': '缺少订单号'}), 400

    with get_db_connection() as conn:
        cur = conn.cursor()

        # 查询订单
        cur.execute('SELECT user_id, amount, status FROM orders WHERE order_no = %s', (order_no,))
        order = cur.fetchone()

        if not order:
            return jsonify({'success': False, 'error': '订单不存在'}), 404

        if order['status'] != 'pending':
            return jsonify({'success': False, 'error': f'订单状态异常: {order["status"]}'}), 400

        # 更新订单状态
        cur.execute('UPDATE orders SET status = %s, paid_at = NOW() WHERE order_no = %s', ('paid', order_no))

        # 增加用户余额
        cur.execute('''
            UPDATE users
            SET balance = balance + %s, total_recharged = total_recharged + %s
            WHERE id = %s
        ''', (order['amount'], order['amount'], order['user_id']))

        # 获取更新后的余额
        cur.execute('SELECT balance FROM users WHERE id = %s', (order['user_id'],))
        updated_user = cur.fetchone()

        return jsonify({
            'success': True,
            'message': f'充值成功，已增加余额 {float(order["amount"])} 元',
            'user': {
                'balance': float(updated_user['balance'])
            }
        })


@app.route('/api/resumes/history', methods=['GET'])
def get_resume_history():
    """获取简历历史记录"""
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({'success': False, 'error': '缺少用户ID'}), 400

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT id, resume_type, job_title, ai_score, created_at
            FROM resumes
            WHERE user_id = %s
            ORDER BY created_at DESC
        ''', (user_id,))
        resumes = cur.fetchall()

        return jsonify({
            'success': True,
            'resumes': [
                {
                    'id': r['id'],
                    'resume_type': r['resume_type'],
                    'job_title': r['job_title'],
                    'ai_score': r['ai_score'],
                    'created_at': r['created_at'].isoformat() if r['created_at'] else None
                }
                for r in resumes
            ]
        })


@app.route('/api/export-pdf', methods=['POST'])
def export_pdf():
    """导出PDF"""
    data = request.json
    user_id = data.get('user_id')
    content = data.get('content')

    if not user_id or not content:
        return jsonify({'success': False, 'error': '缺少必要参数'}), 400

    with get_db_connection() as conn:
        cur = conn.cursor()

        # 查询用户状态（包括免费次数）
        cur.execute('SELECT free_count, balance FROM users WHERE id = %s', (user_id,))
        user = cur.fetchone()

        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        cost = 0

        # 判断扣费方式
        if user['free_count'] > 0:
            # 有免费次数，导出PDF免费
            cost = 0
        elif user['balance'] >= 2.00:
            # 没有免费次数，扣除余额
            order_no = generate_order_no('CSM')
            cur.execute('''
                INSERT INTO orders (order_no, user_id, order_type, amount, description, payment_method, status, paid_at)
                VALUES (%s, %s, 'consume', 2.00, '导出PDF', 'balance', 'paid', NOW())
            ''', (order_no, user_id))
            cur.execute('UPDATE users SET balance = balance - 2.00 WHERE id = %s', (user_id,))
            cost = 2
        else:
            return jsonify({'success': False, 'error': '余额不足，请充值'}), 400

        # 生成PDF
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        pdf_filename = f"resume_{user_id}_{timestamp}.pdf"
        pdf_path = os.path.join(app.config['PDF_FOLDER'], pdf_filename)

        try:
            generate_pdf_from_markdown(content, pdf_path)
        except Exception as e:
            return jsonify({'success': False, 'error': f'PDF生成失败: {str(e)}'}), 500

        pdf_url = f"/static/pdfs/{pdf_filename}"

        # 获取更新后的余额
        cur.execute('SELECT balance FROM users WHERE id = %s', (user_id,))
        updated_user = cur.fetchone()

        return jsonify({
            'success': True,
            'pdf_url': pdf_url,
            'cost': 2,
            'user': {
                'balance': float(updated_user['balance'])
            }
        })


if __name__ == '__main__':
    app.run(debug=True, port=5000)

