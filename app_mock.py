"""
Mock 版本后端 - 用于本地测试前端，不需要数据库

使用方法：
python app_mock.py

然后访问 http://localhost:5000
"""

from flask import Flask, request, jsonify, render_template
import random
import time

app = Flask(__name__)

# Mock 数据
mock_users = {}
mock_resumes = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/user/login', methods=['POST'])
def user_login():
    phone = request.json.get('phone')
    if phone not in mock_users:
        mock_users[phone] = {
            'id': len(mock_users) + 1,
            'phone': phone,
            'free_count': 3,
            'balance': 0.0
        }
    return jsonify({'success': True, 'user': mock_users[phone]})

@app.route('/api/user/info', methods=['GET'])
def get_user_info():
    phone = request.args.get('phone')
    if phone in mock_users:
        return jsonify({'success': True, 'user': mock_users[phone]})
    return jsonify({'success': False, 'error': '用户不存在'}), 404

@app.route('/api/generate-template', methods=['POST'])
def generate_template():
    time.sleep(2)  # 模拟 API 调用
    user_id = request.json.get('user_id')
    job_title = request.json.get('job_title')
    years_exp = request.json.get('years_exp')

    # 找到用户
    user = None
    for u in mock_users.values():
        if u['id'] == user_id:
            user = u
            break

    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    cost = 0
    if user['free_count'] > 0:
        user['free_count'] -= 1
    elif user['balance'] >= 5:
        user['balance'] -= 5
        cost = 5
    else:
        return jsonify({'success': False, 'error': '余额不足，请充值'}), 400

    template = f"""# {job_title}简历

## 个人信息
- 姓名：张三
- 工作年限：{years_exp}年
- 手机：138****8000
- 邮箱：example@email.com

## 个人总结
拥有{years_exp}年{job_title}经验，专注于构建高性能、高可用的系统。

## 工作经历

### XX公司 | {job_title}
**2020.01 - 至今**

- 负责核心业务系统的设计与开发
- 优化系统性能，提升响应速度30%
- 带领团队完成多个重点项目

### YY公司 | 初级工程师
**2018.06 - 2019.12**

- 参与产品功能开发
- 学习并掌握核心技术栈
- 协助团队完成项目交付

## 技能清单
- 编程语言：Python, Java, JavaScript
- 框架：Django, Spring Boot, React
- 数据库：MySQL, PostgreSQL, Redis
- 工具：Git, Docker, Linux

## 项目经验

### 项目A：电商平台
**技术栈**：Python + Django + PostgreSQL

- 设计并实现订单处理系统
- 日均处理订单10万+
- 系统稳定性达99.9%

### 项目B：数据分析平台
**技术栈**：Python + Pandas + Elasticsearch

- 构建实时数据分析系统
- 支持TB级数据查询
- 查询响应时间<1秒
"""

    return jsonify({
        'success': True,
        'template': template,
        'cost': cost,
        'user': {'free_count': user['free_count'], 'balance': user['balance']}
    })

@app.route('/api/optimize', methods=['POST'])
def optimize_resume():
    time.sleep(3)  # 模拟 API 调用
    user_id = int(request.form.get('user_id'))

    # 找到用户
    user = None
    for u in mock_users.values():
        if u['id'] == user_id:
            user = u
            break

    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    if user['balance'] < 10:
        return jsonify({'success': False, 'error': '余额不足，请充值'}), 400

    user['balance'] -= 10

    result = {
        'analysis': '您的简历整体结构清晰，但存在以下问题：\n1. 工作经历描述过于简单，缺少量化数据\n2. 技能清单过于宽泛，建议突出核心技能\n3. 项目经验需要更详细的技术细节\n\n建议：增加具体的工作成果和数据支撑，突出个人贡献。',
        'score': 75,
        'versions': [
            {
                'title': '版本1：传统格式优化',
                'description': '保持原有风格，优化表达和关键词',
                'content': '# 张三\n\n## 个人信息\n工作年限：5年 | 手机：138****8000\n\n## 工作经历\n\n### XX公司 | Python后端工程师\n2020.01 - 至今\n\n- 负责核心交易系统开发，日均处理订单50万+，系统可用性99.95%\n- 优化数据库查询性能，将关键接口响应时间从800ms降至200ms\n- 主导微服务架构改造，服务拆分为12个独立模块，提升系统可维护性\n\n...'
            },
            {
                'title': '版本2：现代简约风格',
                'description': '简洁明了，突出核心能力',
                'content': '# 张三 | Python后端工程师\n\n**5年经验 · 高并发系统 · 微服务架构**\n\n## 核心技能\nPython · Django · PostgreSQL · Redis · Docker · Kubernetes\n\n## 工作亮点\n\n**XX公司** (2020 - 至今)\n- 🚀 日均50万订单处理，99.95%可用性\n- ⚡ 接口性能优化，响应时间降低75%\n- 🏗️ 微服务架构改造，12个独立服务\n\n...'
            },
            {
                'title': '版本3：ATS友好版本',
                'description': '优化关键词，适合招聘系统筛选',
                'content': '# 张三\n\n## 专业技能\nPython开发 | Django框架 | RESTful API | PostgreSQL数据库 | Redis缓存 | Docker容器化 | Kubernetes编排 | 微服务架构 | 高并发系统 | 性能优化\n\n## 工作经验\n\n### Python后端工程师 | XX科技有限公司\n2020年1月 - 至今\n\n职责描述：\n- 后端系统开发：使用Python和Django框架开发RESTful API\n- 数据库设计：PostgreSQL数据库设计与优化\n- 性能优化：系统性能调优，提升响应速度\n- 架构设计：微服务架构设计与实施\n\n...'
            }
        ]
    }

    return jsonify({
        'success': True,
        'result': result,
        'cost': 10,
        'user': {'balance': user['balance']}
    })

@app.route('/api/recharge/create', methods=['POST'])
def create_recharge_order():
    order_no = f"RCH{int(time.time())}{random.randint(1000, 9999)}"
    return jsonify({'success': True, 'order_no': order_no})

@app.route('/api/resumes/history', methods=['GET'])
def get_resume_history():
    return jsonify({
        'success': True,
        'resumes': [
            {
                'id': 1,
                'resume_type': 'template',
                'job_title': 'Python工程师',
                'ai_score': None,
                'created_at': '2026-02-13T10:30:00'
            },
            {
                'id': 2,
                'resume_type': 'optimize',
                'job_title': None,
                'ai_score': 85,
                'created_at': '2026-02-12T15:20:00'
            }
        ]
    })

@app.route('/api/export-pdf', methods=['POST'])
def export_pdf():
    time.sleep(1)
    user_id = request.json.get('user_id')

    # 找到用户
    user = None
    for u in mock_users.values():
        if u['id'] == user_id:
            user = u
            break

    if not user:
        return jsonify({'success': False, 'error': '用户不存在'}), 404

    if user['balance'] < 2:
        return jsonify({'success': False, 'error': '余额不足，请充值'}), 400

    user['balance'] -= 2

    return jsonify({
        'success': True,
        'pdf_url': '/static/pdfs/mock_resume.pdf',
        'cost': 2,
        'user': {'balance': user['balance']}
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Mock 服务器启动成功")
    print("=" * 60)
    print("访问地址：http://localhost:5000")
    print("说明：这是 Mock 版本，不需要数据库，用于测试前端")
    print("=" * 60)
    app.run(debug=False, port=5001)
