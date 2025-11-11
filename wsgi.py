from app import app
from config import load_config

# 加载配置
config = load_config()

# 更新Flask配置
app.config.update(
    SECRET_KEY=config.SECRET_KEY,
)

# 更新全局变量
import app as app_module
app_module.WECHAT_APPID = config.WECHAT_APPID
app_module.WECHAT_SECRET = config.WECHAT_SECRET
app_module.DOMAIN = config.DOMAIN

if __name__ == "__main__":
    app.run()