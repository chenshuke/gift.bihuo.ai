import sqlite3

conn = sqlite3.connect('gift_codes.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== 检查数据库状态 ===\n")

# 检查users表
cursor.execute('SELECT COUNT(*) as cnt FROM users')
print(f"users表记录数: {cursor.fetchone()['cnt']}")

cursor.execute('SELECT COUNT(*) as cnt FROM users WHERE device_fingerprint IS NOT NULL')
print(f"有device_fingerprint的记录: {cursor.fetchone()['cnt']}")

cursor.execute('SELECT * FROM users LIMIT 5')
print(f"\nusers表前5条记录:")
for row in cursor.fetchall():
    print(f"  {dict(row)}")

# 检查surveys表
cursor.execute('SELECT COUNT(*) as cnt FROM surveys')
print(f"\nsurveys表记录数: {cursor.fetchone()['cnt']}")

cursor.execute('SELECT * FROM surveys LIMIT 3')
print(f"\nsurveys表前3条记录:")
for row in cursor.fetchall():
    print(f"  {dict(row)}")

# 检查codes表
cursor.execute('SELECT COUNT(*) as cnt FROM codes WHERE is_used = TRUE')
print(f"\n已使用的兑换码: {cursor.fetchone()['cnt']}")

cursor.execute('SELECT COUNT(*) as cnt FROM codes WHERE is_used = FALSE')
print(f"未使用的兑换码: {cursor.fetchone()['cnt']}")

conn.close()
