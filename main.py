#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 添加项目路径到系统路径
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_path)

from app import app, init_database

# 初始化数据库
init_database()

if __name__ == '__main__':
    # 从环境变量获取端口，宝塔会自动设置
    port = int(os.environ.get('PORT', 1688))
    app.run(debug=False, host='0.0.0.0', port=port)