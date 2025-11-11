#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库备份和恢复工具
"""

import os
import sqlite3
import json
from datetime import datetime
import shutil

def backup_database(db_path="gift_codes.db", backup_dir="database_backups"):
    """备份数据库"""
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return None
    
    # 创建备份目录
    os.makedirs(backup_dir, exist_ok=True)
    
    # 生成备份文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"gift_codes_backup_{timestamp}.db")
    json_backup = os.path.join(backup_dir, f"gift_codes_backup_{timestamp}.json")
    
    try:
        # 1. 复制数据库文件
        shutil.copy2(db_path, backup_file)
        print(f"✅ 数据库文件已备份到: {backup_file}")
        
        # 2. 导出为JSON格式（便于查看和跨平台）
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        backup_data = {
            "backup_time": datetime.now().isoformat(),
            "tables": {}
        }
        
        # 获取所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table['name']
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            # 转换为字典列表
            backup_data["tables"][table_name] = []
            for row in rows:
                backup_data["tables"][table_name].append(dict(row))
        
        conn.close()
        
        # 保存JSON备份
        with open(json_backup, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ JSON备份已保存到: {json_backup}")
        
        return backup_file, json_backup
        
    except Exception as e:
        print(f"❌ 备份失败: {str(e)}")
        return None

def list_backups(backup_dir="database_backups"):
    """列出所有备份文件"""
    if not os.path.exists(backup_dir):
        print("📂 备份目录不存在")
        return []
    
    backups = []
    for file in os.listdir(backup_dir):
        if file.endswith('.db'):
            file_path = os.path.join(backup_dir, file)
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            backups.append({
                'file': file,
                'path': file_path,
                'time': mod_time,
                'size': os.path.getsize(file_path)
            })
    
    # 按时间排序
    backups.sort(key=lambda x: x['time'], reverse=True)
    
    print("📋 数据库备份列表:")
    for i, backup in enumerate(backups):
        print(f"{i+1}. {backup['file']} - {backup['time']} ({backup['size']} bytes)")
    
    return backups

def restore_database(backup_file, target_db="gift_codes.db"):
    """从备份恢复数据库"""
    if not os.path.exists(backup_file):
        print(f"❌ 备份文件不存在: {backup_file}")
        return False
    
    try:
        # 备份当前数据库（如果存在）
        if os.path.exists(target_db):
            current_backup = f"{target_db}.before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(target_db, current_backup)
            print(f"🔄 当前数据库已备份到: {current_backup}")
        
        # 恢复数据库
        shutil.copy2(backup_file, target_db)
        print(f"✅ 数据库已从 {backup_file} 恢复")
        return True
        
    except Exception as e:
        print(f"❌ 恢复失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("🗄️ 数据库备份工具")
    print("1. 创建备份")
    print("2. 列出备份")
    print("3. 恢复备份")
    
    choice = input("请选择操作 (1-3): ").strip()
    
    if choice == "1":
        print("\n📦 正在创建备份...")
        result = backup_database()
        if result:
            print("✅ 备份完成")
        
    elif choice == "2":
        print("\n📋 查看备份列表...")
        list_backups()
        
    elif choice == "3":
        print("\n🔄 恢复数据库...")
        backups = list_backups()
        if backups:
            try:
                index = int(input(f"请选择要恢复的备份 (1-{len(backups)}): ")) - 1
                if 0 <= index < len(backups):
                    restore_database(backups[index]['path'])
                else:
                    print("❌ 选择无效")
            except ValueError:
                print("❌ 请输入有效数字")
    else:
        print("❌ 无效选择")