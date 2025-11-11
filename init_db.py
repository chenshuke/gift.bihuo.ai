#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
单独运行此文件来初始化数据库
"""

import os
import sys

# 添加项目路径到系统路径
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

from app import init_database

if __name__ == '__main__':
    try:
        print("开始初始化数据库...")
        init_database()
        print("✓ 数据库初始化成功！")
        print("✓ 创建了以下表：")
        print("  - codes（兑换码表）")
        print("  - users（用户表）")
        
        # 检查数据库文件是否创建
        db_file = 'gift_codes.db'
        if os.path.exists(db_file):
            size = os.path.getsize(db_file)
            print(f"✓ 数据库文件已创建：{db_file} (大小: {size} bytes)")
        else:
            print("✗ 数据库文件未找到")
            
    except Exception as e:
        print(f"✗ 数据库初始化失败：{e}")
        sys.exit(1)