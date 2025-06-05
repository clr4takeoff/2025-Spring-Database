# db.py
import oracledb

conn = oracledb.connect(
    user="madang",
    password="madang",
    dsn="localhost/XE"  # 혹은 IP주소/XE
)

cursor = conn.cursor()
cursor.execute("SELECT * FROM BOOK")

for row in cursor:
    print(row)

conn.close()
