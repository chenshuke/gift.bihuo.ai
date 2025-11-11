#!/bin/bash

# 部署脚本 - 适用于宝塔面板环境

echo "开始部署必火AI兑换码系统..."

# 设置项目路径
PROJECT_PATH="/www/wwwroot/gift.bihuoai.com"
PYTHON_PATH="/www/server/python_manager/versions/3.8.12/bin/python3"
PIP_PATH="/www/server/python_manager/versions/3.8.12/bin/pip3"

# 检查Python是否存在
if [ ! -f "$PYTHON_PATH" ]; then
    echo "错误：Python路径不存在，请检查Python版本"
    exit 1
fi

# 进入项目目录
cd $PROJECT_PATH

# 安装依赖
echo "安装Python依赖..."
$PIP_PATH install -r requirements.txt

# 复制配置文件（如果不存在）
if [ ! -f ".env" ]; then
    echo "创建配置文件..."
    cp .env.example .env
    echo "请编辑 .env 文件，配置微信公众号信息"
fi

# 创建必要的目录
mkdir -p /var/log/uwsgi
mkdir -p /tmp

# 设置文件权限
chown -R www:www $PROJECT_PATH
chmod +x wsgi.py

# 初始化数据库
echo "初始化数据库..."
$PYTHON_PATH -c "from app import init_database; init_database()"

# 启动uWSGI服务
echo "启动uWSGI服务..."
/www/server/python_manager/versions/3.8.12/bin/uwsgi --ini uwsgi.ini --daemonize

echo "部署完成！"
echo ""
echo "下一步操作："
echo "1. 编辑 .env 文件，配置微信公众号AppID和Secret"
echo "2. 在宝塔面板中添加站点 gift.bihuoai.com"
echo "3. 将 nginx.conf 的内容添加到站点的Nginx配置中"
echo "4. 访问 https://gift.bihuoai.com/admin 查看管理后台"
echo ""
echo "管理后台功能："
echo "- 导入兑换码"
echo "- 查看使用统计"
echo "- 导出使用数据"