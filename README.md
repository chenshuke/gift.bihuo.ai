# 必火AI兑换码领取系统

一个简单的微信公众号兑换码领取系统，支持用户通过微信授权领取唯一兑换码，管理员可以轻松管理兑换码的导入和使用情况。

## 功能特点

- 🔐 **微信OAuth授权**：用户需要微信授权才能领取，防止薅羊毛
- 🎫 **唯一兑换码**：每个微信用户只能领取一个兑换码
- 📊 **管理后台**：实时查看兑换码使用统计，支持批量导入和导出
- 🚀 **简单部署**：适配宝塔面板，一键部署
- 📱 **移动友好**：响应式设计，完美适配手机端

## 系统架构

- **后端**：Flask + SQLite
- **前端**：Bootstrap + JavaScript
- **部署**：Nginx + uWSGI
- **服务器**：宝塔面板

## 快速开始

### 1. 环境准备

确保服务器已安装：
- Python 3.8+
- Nginx
- SQLite

### 2. 部署步骤

1. **下载代码到服务器**
```bash
cd /www/wwwroot
git clone https://github.com/your-repo/gift.bihuoai.com.git
cd gift.bihuoai.com
```

2. **配置环境**
```bash
# 复制配置文件
cp .env.example .env

# 编辑配置文件，填入微信公众号信息
vi .env
```

3. **执行部署脚本**
```bash
chmod +x deploy.sh
./deploy.sh
```

4. **配置Nginx**
- 在宝塔面板中添加站点 `gift.bihuoai.com`
- 将 `nginx.conf` 的内容复制到站点配置中
- 重载Nginx配置

### 3. 配置说明

编辑 `.env` 文件，配置以下参数：

```env
# 微信公众号配置
WECHAT_APPID=wx1234567890abcdef
WECHAT_SECRET=abcdef1234567890abcdef1234567890

# 域名配置
DOMAIN=https://gift.bihuoai.com

# 安全密钥（请修改）
SECRET_KEY=your-very-secret-key-here
```

## 使用说明

### 用户端

1. 用户访问 `https://gift.bihuoai.com`
2. 点击"微信授权领取"按钮
3. 完成微信OAuth授权
4. 自动分配未使用的兑换码
5. 用户可复制兑换码到剪贴板

### 管理端

访问 `https://gift.bihuoai.com/admin` 进入管理后台：

1. **导入兑换码**：批量导入预生成的兑换码
2. **查看统计**：实时查看总数、已使用、剩余数量
3. **领取记录**：查看最近的领取记录
4. **导出数据**：导出所有兑换码使用情况

### 兑换码导入格式

在管理后台的导入框中，每行输入一个兑换码：

```
CODE001
CODE002
CODE003
...
```

## API接口

### 用户相关

- `GET /` - 主页
- `GET /claim` - 开始领取流程
- `GET /callback` - 微信授权回调
- `GET /check_and_claim` - 检查并领取兑换码

### 管理相关

- `GET /admin` - 管理后台
- `GET /admin/stats` - 获取统计数据
- `POST /admin/import` - 导入兑换码
- `GET /admin/export` - 导出数据

## 数据库结构

### codes表
- `id` - 主键
- `code` - 兑换码（唯一）
- `is_used` - 是否已使用
- `created_at` - 创建时间
- `claimed_at` - 领取时间
- `claimed_by_openid` - 领取用户OpenID

### users表
- `id` - 主键
- `openid` - 微信OpenID（唯一）
- `nickname` - 用户昵称
- `avatar_url` - 头像链接
- `created_at` - 创建时间

## 常见问题

### Q: 如何获取微信公众号的AppID和Secret？
A: 登录微信公众平台 -> 开发 -> 基本配置 -> 开发者ID(AppID) 和 开发者密码(AppSecret)

### Q: 微信授权失败怎么办？
A: 检查域名配置是否正确，确保在微信公众平台配置了正确的授权回调域名

### Q: 兑换码用完了怎么办？
A: 在管理后台批量导入新的兑换码即可

### Q: 如何重置某个用户的领取状态？
A: 直接在数据库中删除对应的领取记录，或修改代码添加重置功能

## 安全建议

1. 定期更改 `SECRET_KEY`
2. 为管理后台添加访问密码
3. 定期备份数据库文件
4. 使用HTTPS部署
5. 限制管理后台的访问IP

## 技术支持

如有问题或建议，请提交Issue或联系开发者。

## 许可证

MIT License