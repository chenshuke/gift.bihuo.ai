#!/bin/bash
# 安全部署脚本 - 保护数据库和配置文件

echo "🚀 开始安全部署..."

# 1. 创建备份目录
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# 2. 备份重要文件
echo "📦 备份重要数据..."
if [ -f "gift_codes.db" ]; then
    cp gift_codes.db $BACKUP_DIR/
    echo "✅ 数据库已备份到 $BACKUP_DIR/gift_codes.db"
fi

if [ -f ".env" ]; then
    cp .env $BACKUP_DIR/
    echo "✅ 配置文件已备份到 $BACKUP_DIR/.env"
fi

# 3. 停止服务
echo "⏹️  停止当前服务..."
pkill -f "python main.py" 2>/dev/null || echo "服务未运行"
sleep 2

# 4. 更新代码文件（排除数据库和配置）
echo "🔄 更新代码文件..."
# 这里你需要手动上传新的代码文件
# 或者使用 rsync/scp 等工具

# 5. 检查配置文件
if [ ! -f ".env" ]; then
    echo "⚠️  .env 文件不存在，从备份恢复..."
    cp $BACKUP_DIR/.env .env 2>/dev/null || echo "❌ 备份中也没有.env文件，请手动配置"
fi

# 6. 检查数据库
if [ ! -f "gift_codes.db" ]; then
    echo "⚠️  数据库文件不存在，从备份恢复..."
    cp $BACKUP_DIR/gift_codes.db gift_codes.db 2>/dev/null || echo "初始化新数据库..."
fi

# 7. 安装依赖
if [ -f "requirements.txt" ]; then
    echo "📚 更新Python依赖..."
    pip install -r requirements.txt
fi

# 8. 重启服务
echo "🎯 重启服务..."
nohup python main.py > app.log 2>&1 &
sleep 3

# 9. 检查服务状态
if pgrep -f "python main.py" > /dev/null; then
    echo "✅ 服务启动成功！"
    echo "📊 备份文件保存在: $BACKUP_DIR/"
else
    echo "❌ 服务启动失败，请检查日志"
    tail -20 app.log
fi