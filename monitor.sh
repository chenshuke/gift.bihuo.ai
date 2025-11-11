#!/bin/bash

# 系统监控脚本

echo "=== 必火AI兑换码系统状态检查 ==="
echo "检查时间: $(date)"
echo ""

# 检查uWSGI进程
echo "1. 检查uWSGI进程:"
if pgrep -f "uwsgi.*gift" > /dev/null; then
    echo "   ✓ uWSGI 进程运行正常"
else
    echo "   ✗ uWSGI 进程未运行"
    echo "   尝试重启..."
    cd /www/wwwroot/gift.bihuoai.com
    /www/server/python_manager/versions/3.8.12/bin/uwsgi --ini uwsgi.ini --daemonize /var/log/uwsgi/gift_bihuoai.log
fi

# 检查Nginx状态
echo ""
echo "2. 检查Nginx状态:"
if systemctl is-active --quiet nginx; then
    echo "   ✓ Nginx 运行正常"
else
    echo "   ✗ Nginx 未运行"
fi

# 检查网站响应
echo ""
echo "3. 检查网站响应:"
if curl -s -o /dev/null -w "%{http_code}" https://gift.bihuoai.com | grep -q "200"; then
    echo "   ✓ 网站响应正常"
else
    echo "   ✗ 网站响应异常"
fi

# 检查数据库文件
echo ""
echo "4. 检查数据库:"
if [ -f "/www/wwwroot/gift.bihuoai.com/gift_codes.db" ]; then
    size=$(stat -c%s "/www/wwwroot/gift.bihuoai.com/gift_codes.db")
    echo "   ✓ 数据库文件存在 (大小: ${size} bytes)"
else
    echo "   ✗ 数据库文件不存在"
fi

# 检查日志大小
echo ""
echo "5. 检查日志文件:"
if [ -f "/var/log/uwsgi/gift_bihuoai.log" ]; then
    size=$(stat -c%s "/var/log/uwsgi/gift_bihuoai.log")
    if [ $size -gt 104857600 ]; then  # 100MB
        echo "   ⚠ 日志文件过大 (${size} bytes)，建议清理"
    else
        echo "   ✓ 日志文件大小正常"
    fi
fi

echo ""
echo "=== 检查完成 ==="