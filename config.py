import os

class Config:
    # 域名配置
    DOMAIN = os.environ.get('DOMAIN', 'https://gift.bihuoai.com')

    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-me-in-production')

    # 数据库配置
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'gift_codes.db')

    # 管理员访问密码
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

    # API访问令牌
    API_TOKEN = os.environ.get('API_TOKEN', 'bihuoai-api-token-2024')

    # IP限制配置（防刷）
    IP_HOURLY_LIMIT = int(os.environ.get('IP_HOURLY_LIMIT', 3))  # 单IP每小时尝试次数
    IP_DAILY_SUCCESS = int(os.environ.get('IP_DAILY_SUCCESS', 5))  # 单IP每天成功领取次数

# 从配置文件加载配置
def load_config():
    """从环境变量或配置文件加载配置"""
    config = Config()
    
    # 尝试从本地配置文件加载（如果存在）
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
                    setattr(config, key, value)
    except FileNotFoundError:
        pass
    
    return config