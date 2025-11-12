#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""测试真实新加坡IP的语言检测"""

from language import lang

def test_real_sg_ip():
    """测试真实新加坡IP的语言检测"""

    sg_ip = "165.21.83.245"  # 新加坡真实IP

    print("🧪 测试真实新加坡IP语言检测")
    print("=" * 50)
    print(f"🌍 新加坡IP: {sg_ip}")

    # 检测语言
    detected_lang = lang.detect_language_from_ip(sg_ip)
    expected_lang = "en"  # 新加坡应该显示英文

    status = "✅ 通过" if detected_lang == expected_lang else "❌ 失败"

    print(f"   期望语言: {expected_lang} ({'中文' if expected_lang == 'zh' else '英文'})")
    print(f"   检测语言: {detected_lang} ({'中文' if detected_lang == 'zh' else '英文'})")
    print(f"   结果: {status}")

    if detected_lang == expected_lang:
        print(f"\n✅ 新加坡IP测试通过！将显示英文界面。")
    else:
        print(f"\n❌ 新加坡IP测试失败！需要检查逻辑。")

if __name__ == "__main__":
    test_real_sg_ip()