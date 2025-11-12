#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""测试IP语言检测功能"""

from language import lang

def test_ip_detection():
    """测试IP语言检测功能"""

    # 测试用例
    test_cases = [
        # (IP地址, 国家代码, 期望语言, 描述)
        ("8.8.8.8", "US", "en", "Google DNS (美国)"),
        ("1.1.1.1", "AU", "en", "Cloudflare DNS (澳大利亚)"),
        ("208.67.222.222", "US", "en", "OpenDNS (美国)"),
        ("9.9.9.9", "US", "en", "Quad9 DNS (美国)"),
        ("1.2.4.8", "CN", "zh", "中国DNS"),
        ("0.0.0.0", None, "en", "空IP测试"),
    ]

    print("🧪 测试IP语言检测功能")
    print("=" * 50)

    for ip, expected_country, expected_lang, description in test_cases:
        try:
            # 检测语言
            detected_lang = lang.detect_language_from_ip(ip)

            print(f"🌍 {description}")
            print(f"   IP: {ip}")
            print(f"   检测到语言: {detected_lang}")
            print(f"   期望语言: {expected_lang}")
            print(f"   结果: {'✅ 通过' if detected_lang == expected_lang else '❌ 失败'}")
            print("-" * 30)

        except Exception as e:
            print(f"❌ {description} - 检测失败: {str(e)}")
            print("-" * 30)

    print("\n🎯 测试完成")
    print("\n📍 部署到服务器后，可以通过VPN测试IP自动切换:")
    print("   - 连接美国VPN → 应显示英文界面")
    print("   - 连接英国VPN → 应显示英文界面")
    print("   - 连接中国VPN → 应显示中文界面")

if __name__ == "__main__":
    test_ip_detection()