# 部署指南 - 全球通用兑换码系统 v2.0

## 🚀 快速部署（新项目）

### 1. 环境准备
```bash
# 需要Python 3.8+
python --version

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量
创建`.env`文件：
```env
DOMAIN=https://gift.bihuoai.com
SECRET_KEY=your-very-secret-key-here-change-me
ADMIN_PASSWORD=your-admin-password
API_TOKEN=your-api-token-2024

# IP限制配置（可选，有默认值）
IP_HOURLY_LIMIT=3
IP_DAILY_SUCCESS=5
```

### 3. 初始化数据库
```bash
python init_db.py
```

### 4. 启动应用
```bash
# 开发环境
python app.py

# 生产环境（宝塔）
uwsgi --ini uwsgi.ini --daemonize
```

### 5. 导入兑换码
访问 `https://your-domain.com/admin` 登录管理后台，在管理页面导入兑换码。

---

## 🔄 从v1.0（微信版）升级到v2.0（国际版）

### ⚠️ 升级前准备

1. **备份数据库**
```bash
cp gift_codes.db gift_codes.db.backup_$(date +%Y%m%d)
```

2. **备份app.py**
```bash
cp app.py app.py.backup
```

### 升级步骤

#### 步骤1: 执行数据库迁移
```bash
python migrate_database.py
```

**确认提示后输入 `yes`**

迁移脚本会：
- ✅ 添加新字段（device_fingerprint, email, ip_address等）
- ✅ 创建ip_limits表
- ✅ 将现有openid数据迁移到fingerprint（基于哈希）
- ✅ 保留旧字段（openid, phone_number）作为备份

#### 步骤2: 更新代码
```bash
# 如果是git管理的项目
git pull

# 或者手动替换文件
# - app.py（核心应用）
# - config.py（配置文件）
# - templates/survey.html（调研表单）
# - templates/result.html（结果页面）
```

#### 步骤3: 更新环境变量
编辑`.env`文件，移除微信相关配置：
```env
# ❌ 移除这些配置
# WECHAT_APPID=...
# WECHAT_SECRET=...
# MINIPROGRAM_APPID=...
# MINIPROGRAM_PATH=...

# ✅ 添加新配置
IP_HOURLY_LIMIT=3
IP_DAILY_SUCCESS=5
```

#### 步骤4: 重启服务
```bash
# 如果使用uWSGI
pkill uwsgi
uwsgi --ini uwsgi.ini --daemonize

# 如果使用systemd
systemctl restart gift-bihuoai
```

#### 步骤5: 验证升级
访问网站，测试：
1. 访问首页，检查是否自动采集设备指纹（打开浏览器控制台）
2. 填写调研表单（使用邮箱而非手机号）
3. 提交后检查是否正常分配兑换码
4. 登录管理后台，检查数据是否正常显示

---

## 📊 迁移后的数据对应关系

| 旧字段（v1.0） | 新字段（v2.0） | 说明 |
|--------------|--------------|------|
| openid | device_fingerprint | 用户唯一标识 |
| phone_number | email | 联系方式 |
| claimed_by_openid | claimed_by_fingerprint | 兑换码领取者 |
| - | ip_address | 新增：用户IP |
| - | ip_limits表 | 新增：防刷记录 |

---

## 🔧 常见问题

### Q1: 迁移后旧用户能否继续领取？
**A**: 旧用户的openid已被迁移为device_fingerprint，无法重复领取。如需重置，使用管理后台的"重置用户"功能，输入其邮箱。

### Q2: 设备指纹的准确度如何？
**A**: FingerprintJS准确度约99.5%。隐私模式或VPN可能绕过，但结合邮箱+IP限制可有效防刷。

### Q3: 如何调整IP限制策略？
**A**: 修改`.env`文件中的 `IP_HOURLY_LIMIT` 和 `IP_DAILY_SUCCESS`，然后重启服务。

### Q4: 数据库迁移失败怎么办？
**A**:
1. 恢复备份：`cp gift_codes.db.backup gift_codes.db`
2. 检查错误信息
3. 确保Python版本>=3.8
4. 重新执行迁移脚本

### Q5: 如何删除旧的微信相关字段？
**A**: 迁移后旧字段仍保留作为备份。确认无误后可手动删除：
```sql
sqlite3 gift_codes.db
ALTER TABLE users DROP COLUMN openid;
ALTER TABLE users DROP COLUMN nickname;
ALTER TABLE users DROP COLUMN avatar_url;
ALTER TABLE users DROP COLUMN phone_number;
```

---

## 🛡️ 安全建议

1. **定期备份数据库**
```bash
# 添加到crontab，每天备份
0 2 * * * cp /path/to/gift_codes.db /path/to/backups/gift_codes_$(date +\%Y\%m\%d).db
```

2. **限制管理后台访问**
- 使用强密码（ADMIN_PASSWORD）
- 考虑添加IP白名单（Nginx配置）

3. **监控异常流量**
```bash
# 查看IP限制日志
sqlite3 gift_codes.db "SELECT * FROM ip_limits ORDER BY success_count DESC LIMIT 20"
```

4. **HTTPS部署**
确保使用HTTPS，保护用户数据传输。

---

## 📝 回滚方案

如果升级后出现问题，可回滚到v1.0：

1. 恢复数据库备份
```bash
cp gift_codes.db.backup gift_codes.db
```

2. 恢复app.py
```bash
cp app.py.backup app.py
```

3. 重启服务
```bash
systemctl restart gift-bihuoai
```

---

## 🎯 验收测试清单

升级完成后，依次测试：

- [ ] 访问首页，页面正常加载
- [ ] 浏览器控制台显示"设备指纹已生成"
- [ ] 填写完整表单，提交成功
- [ ] 显示兑换码，复制按钮工作正常
- [ ] 同一设备再次访问，提示"已领取过"
- [ ] 同一邮箱提交，提示"邮箱已被使用"
- [ ] 管理后台登录正常
- [ ] 管理后台统计数据正确显示
- [ ] 导出CSV功能正常
- [ ] API接口 `/api/surveys` 返回正确数据

---

## 📞 技术支持

- 问题反馈：提交Issue
- 文档：参考CLAUDE.md
- 日志位置：`/var/log/uwsgi/gift_bihuoai.log`
