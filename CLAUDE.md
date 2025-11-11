# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目本质

全球通用兑换码发放系统（国际版）。用户填写调研问卷后获得唯一兑换码，无需注册或登录。

## 核心架构

- **技术栈**: Flask + SQLite + FingerprintJS + uWSGI + Nginx
- **主应用**: `app.py` - 所有路由和业务逻辑
- **数据库**: SQLite (`gift_codes.db`) - 四张表: codes、users、surveys、ip_limits
- **模板**: `templates/` - 前端HTML页面
- **部署**: 宝塔面板环境（支持全球访问）

## 关键业务流程

1. **领取流程**: 访问首页 → 自动采集设备指纹 → 填写问卷（含邮箱）→ 四层验证 → 分配兑换码
2. **数据库设计**:
   - `codes`: 兑换码及使用状态（claimed_by_fingerprint）
   - `users`: 用户信息（device_fingerprint/email/ip_address）
   - `surveys`: 调研数据（邮箱/职业/问题等）
   - `ip_limits`: IP限制记录（防刷）

## 四层防刷机制

1. **设备指纹**（FingerprintJS）- 浏览器唯一标识
2. **邮箱唯一性** - 每个邮箱只能领取一次
3. **IP日限制** - 单IP每天最多5次成功领取（可配置）
4. **IP时限** - 单IP每小时最多3次尝试（可配置）

## 开发命令

### 本地开发
```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python init_db.py
# 或访问 /init_database_now

# 启动开发服务器
python app.py  # 默认端口1688
```

### 生产部署
```bash
# 完整部署(宝塔环境)
chmod +x deploy.sh
./deploy.sh

# 启动uWSGI
uwsgi --ini uwsgi.ini --daemonize

# 查看日志
tail -f /var/log/uwsgi/gift_bihuoai.log
```

## 配置管理

环境变量通过`.env`文件加载(不在版本控制中):
- `DOMAIN` - 部署域名
- `SECRET_KEY` - Flask session密钥
- `ADMIN_PASSWORD` - 管理后台密码
- `API_TOKEN` - API访问令牌
- `IP_HOURLY_LIMIT` - 单IP每小时尝试次数（默认3）
- `IP_DAILY_SUCCESS` - 单IP每天成功领取次数（默认5）

配置加载逻辑在`app.py:load_env()`和`config.py`

## 重要路由

**用户端**:
- `/` - 主页（直接显示领取页面）
- `/check_and_claim` - 显示调研问卷
- `/submit_survey` - 提交调研并领取（POST）

**管理端** (需登录):
- `/admin/login` - 管理员登录
- `/admin` - 管理面板
- `/admin/stats` - 统计数据（含IP限制信息）
- `/admin/import` - 导入兑换码（POST）
- `/admin/export` - 导出兑换码JSON
- `/admin/export_surveys` - 导出调研JSON
- `/admin/export_surveys_csv` - 导出调研CSV
- `/admin/reset_user` - 重置用户领取状态（POST, 需fingerprint或email）
- `/admin/delete` - 删除兑换码（POST）

**API接口** (需token):
- `/api/surveys` - 获取问卷数据（支持日期过滤）
- `/api/surveys/stats` - 统计分析（职业/问题分布）

## 核心防刷函数

### `validate_claim_eligibility(fingerprint, email, ip)`
四层验证，返回 `(is_valid: bool, error_msg: str)`

```python
# 第1层：设备指纹检查
# 第2层：邮箱唯一性检查
# 第3层：IP每日成功次数限制（默认5次）
# 第4层：IP每小时尝试次数限制（默认3次）
```

### `record_ip_attempt(ip_address, success=False)`
记录IP尝试，自动清理昔日数据

### `get_client_ip()`
获取真实IP，支持X-Forwarded-For和X-Real-IP

## 数据库操作注意事项

- 使用`get_db_connection()`获取连接，设置UTF-8编码
- 分配兑换码使用事务确保原子性(`assign_code_to_user(fingerprint)`)
- 时间戳使用`datetime('now', 'localtime')`获取北京时间
- 关键字段：
  - `device_fingerprint`: VARCHAR(64) - 设备指纹哈希
  - `email`: VARCHAR(255) UNIQUE - 用户邮箱
  - `claimed_by_fingerprint`: VARCHAR(64) - 领取者指纹

## 前端设备指纹

- **库**: FingerprintJS 3.x (CDN)
- **采集位置**: `survey.html` 页面加载时
- **存储**: 隐藏表单字段 `device_fingerprint`
- **降级方案**: 生成 `fallback_` + 随机ID
- **前端检测**: LocalStorage `has_claimed` 标记

## 已移除的功能（v2.0国际版）

- ❌ 微信OAuth授权（/claim, /callback等10+路由）
- ❌ 小程序跳转（result.html中）
- ❌ 关注检查
- ❌ 微信昵称/头像
- ❌ 手机号（改为邮箱）

## 管理员权限

- 装饰器: `@admin_required` (基于session)
- 登录: `/admin/login` 验证ADMIN_PASSWORD
- API接口: `@api_token_required` (任意非空token)

## 部署环境

- 宝塔面板Python项目管理器
- Python 3.8+
- uWSGI socket: `/tmp/gift_bihuoai.sock`
- 日志: `/var/log/uwsgi/gift_bihuoai.log`
- **全球CDN**: 使用jsdelivr CDN加载FingerprintJS

## 数据库迁移

执行迁移脚本（从v1.0微信版升级到v2.0国际版）:
```bash
python migrate_database.py
```

迁移内容：
- 添加 device_fingerprint/email/ip_address 字段
- 创建 ip_limits 表
- 将现有 openid 数据迁移到 fingerprint

## 文件结构要点

- `app.py` - 主应用（已移除微信依赖）
- `migrate_database.py` - 数据库迁移脚本
- `wsgi.py` - uWSGI入口
- `uwsgi.ini` - uWSGI配置(4进程2线程)
- `nginx.conf` - Nginx反向代理配置
- `templates/survey.html` - 调研表单（含FingerprintJS）
- `templates/result.html` - 领取结果页（已移除小程序跳转）
