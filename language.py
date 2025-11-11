# 多语言支持模块

import json
import os

class LanguageSupport:
    def __init__(self):
        self.translations = {}
        self.load_translations()

    def load_translations(self):
        """加载翻译文件"""
        translations_dir = os.path.join(os.path.dirname(__file__), 'translations')

        # 加载中文
        zh_file = os.path.join(translations_dir, 'zh.json')
        if os.path.exists(zh_file):
            with open(zh_file, 'r', encoding='utf-8') as f:
                self.translations['zh'] = json.load(f)

        # 加载英文
        en_file = os.path.join(translations_dir, 'en.json')
        if os.path.exists(en_file):
            with open(en_file, 'r', encoding='utf-8') as f:
                self.translations['en'] = json.load(f)

    def get_translation(self, key, lang='zh'):
        """获取翻译"""
        if lang not in self.translations:
            lang = 'zh'

        keys = key.split('.')
        value = self.translations[lang]

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            # 如果翻译不存在，返回键名
            return key

    def detect_language_from_ip(self, ip_address):
        """根据IP地址检测语言"""
        if not ip_address:
            return 'zh'

        try:
            import requests

            # 使用免费的IP地理位置API
            response = requests.get(f'http://ip-api.com/json/{ip_address}?fields=countryCode', timeout=2)
            data = response.json()

            if data.get('status') == 'success':
                country_code = data.get('countryCode', '').upper()

                # 根据国家码判断语言
                chinese_countries = ['CN', 'TW', 'HK', 'MO', 'SG']
                english_countries = ['US', 'GB', 'CA', 'AU', 'NZ', 'IE', 'ZA']

                if country_code in chinese_countries:
                    return 'zh'
                elif country_code in english_countries:
                    return 'en'
                else:
                    # 其他国家默认英文
                    return 'en'
        except:
            pass

        # 默认中文
        return 'zh'

# 全局实例
lang = LanguageSupport()

def t(key, lang='zh'):
    """翻译函数的简写"""
    return lang.get_translation(key, lang)

# 语言映射
LANGUAGES = {
    'zh': '中文',
    'en': 'English'
}