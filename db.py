# db.py
import oracledb

conn = oracledb.connect(
    user="TP",
    password="tp1234",
    dsn="localhost/XE"
)

cursor = conn.cursor()

# 테이블 존재 확인용 쿼리
cursor.execute("SELECT table_name FROM user_tables")

print("TP 계정이 소유한 테이블 목록:")
for row in cursor:
    print("-", row[0])

conn.close()
