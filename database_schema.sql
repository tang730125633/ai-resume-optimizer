-- ============================================
-- AI 简历优化器 - 数据库表结构设计
-- ============================================
-- 数据库：PostgreSQL
-- 创建时间：2026-02-13
-- 版本：v1.0
-- ============================================

-- ============================================
-- 表 1：用户表 (users)
-- 用途：存储用户基本信息和使用次数
-- ============================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,                      -- 用户ID（自动递增）
    phone VARCHAR(11) UNIQUE NOT NULL,          -- 手机号（唯一，用于登录）
    free_count INT DEFAULT 3,                   -- 剩余免费生成次数
    balance DECIMAL(10,2) DEFAULT 0.00,         -- 账户余额（元）
    total_recharged DECIMAL(10,2) DEFAULT 0.00, -- 累计充值金额
    total_generated INT DEFAULT 0,              -- 累计生成模板次数
    total_optimized INT DEFAULT 0,              -- 累计优化简历次数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 注册时间
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 最后登录时间
    is_active BOOLEAN DEFAULT TRUE              -- 账号是否激活
);

-- 创建索引（加快查询速度）
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_created_at ON users(created_at);

-- ============================================
-- 表 2：简历记录表 (resumes)
-- 用途：存储用户的简历内容和AI处理结果
-- ============================================
CREATE TABLE resumes (
    id SERIAL PRIMARY KEY,                      -- 简历记录ID
    user_id INT NOT NULL,                       -- 关联用户ID
    resume_type VARCHAR(20) NOT NULL,           -- 类型：template(模板) / optimize(优化)

    -- 原始内容
    original_content TEXT,                      -- 原始简历内容（优化时有值）
    job_title VARCHAR(100),                     -- 职位名称（生成模板时有值）
    years_experience INT,                       -- 工作年限（生成模板时有值）

    -- AI 生成内容
    ai_analysis TEXT,                           -- AI 分析报告（优化时有值）
    ai_score INT,                               -- AI 评分 0-100（优化时有值）
    generated_content TEXT,                     -- 生成的模板内容（生成时有值）
    optimized_versions JSONB,                   -- 优化版本（JSON格式，优化时有值）
                                                -- 格式：[{title, description, content}, ...]

    -- 状态信息
    is_paid BOOLEAN DEFAULT FALSE,              -- 是否付费
    is_exported BOOLEAN DEFAULT FALSE,          -- 是否已导出PDF
    pdf_url VARCHAR(500),                       -- PDF文件URL（如果已导出）

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX idx_resumes_user_id ON resumes(user_id);
CREATE INDEX idx_resumes_type ON resumes(resume_type);
CREATE INDEX idx_resumes_created_at ON resumes(created_at);

-- ============================================
-- 表 3：支付订单表 (orders)
-- 用途：记录用户的付费订单
-- ============================================
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,                      -- 订单ID
    order_no VARCHAR(32) UNIQUE NOT NULL,       -- 订单号（唯一）
    user_id INT NOT NULL,                       -- 关联用户ID
    order_type VARCHAR(20) NOT NULL,            -- 订单类型：recharge(充值)/consume(消费)

    -- 订单信息
    amount DECIMAL(10,2) NOT NULL,              -- 订单金额（元）
    description VARCHAR(200),                   -- 订单描述
    payment_method VARCHAR(20),                 -- 支付方式：wechat/alipay/balance
    status VARCHAR(20) DEFAULT 'pending',       -- 状态：pending/paid/failed/refunded

    -- 时间信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    paid_at TIMESTAMP,                          -- 支付时间
    expired_at TIMESTAMP,                       -- 过期时间（未支付订单30分钟过期）

    -- 外键约束
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_order_no ON orders(order_no);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- ============================================
-- 表 4：操作日志表 (activity_logs)
-- 用途：记录用户的关键操作（可选，用于数据分析）
-- ============================================
CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,                      -- 日志ID
    user_id INT,                                -- 用户ID（可为空，未登录用户）
    action VARCHAR(50) NOT NULL,                -- 操作类型：login/generate/optimize/export/pay
    details JSONB,                              -- 操作详情（JSON格式）
    ip_address VARCHAR(45),                     -- IP地址
    user_agent TEXT,                            -- 浏览器信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 创建索引
CREATE INDEX idx_logs_user_id ON activity_logs(user_id);
CREATE INDEX idx_logs_action ON activity_logs(action);
CREATE INDEX idx_logs_created_at ON activity_logs(created_at);

-- ============================================
-- 初始化数据（可选）
-- ============================================

-- 插入测试用户
INSERT INTO users (phone, free_count, balance) VALUES
('13800138000', 3, 0.00),
('13900139000', 1, 50.00);

-- ============================================
-- 常用查询示例
-- ============================================

-- 1. 查询用户信息和剩余次数
-- SELECT id, phone, free_count, balance FROM users WHERE phone = '13800138000';

-- 2. 查询用户的所有简历记录
-- SELECT * FROM resumes WHERE user_id = 1 ORDER BY created_at DESC;

-- 3. 查询用户的付费订单
-- SELECT * FROM orders WHERE user_id = 1 AND status = 'paid' ORDER BY paid_at DESC;

-- 4. 统计今日新增用户数
-- SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE;

-- 5. 统计今日生成模板次数
-- SELECT COUNT(*) FROM resumes WHERE resume_type = 'template' AND DATE(created_at) = CURRENT_DATE;

-- 6. 统计今日付费订单金额
-- SELECT SUM(amount) FROM orders WHERE status = 'paid' AND DATE(paid_at) = CURRENT_DATE;

-- ============================================
-- 表关系说明
-- ============================================
-- users (1) ----< (N) resumes     一个用户可以有多条简历记录
-- users (1) ----< (N) orders      一个用户可以有多个订单
-- users (1) ----< (N) activity_logs  一个用户可以有多条操作日志
-- resumes (1) ----< (1) orders    一个简历记录可以关联一个订单（可选）

-- ============================================
-- 数据库维护
-- ============================================

-- 清理过期未支付订单（可以设置定时任务）
-- DELETE FROM orders WHERE status = 'pending' AND expired_at < CURRENT_TIMESTAMP;

-- 备份数据库
-- pg_dump -U username -d database_name > backup.sql

-- 恢复数据库
-- psql -U username -d database_name < backup.sql
