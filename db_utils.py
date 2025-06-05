# db_utils.py
import oracledb

# Oracle 연결 함수
def get_connection():
    return oracledb.connect(
        user="TP",
        password="tp1234",
        dsn="localhost:1521/XE"
    )

# 로그인 검증
def verify_user(cursor, email, password):
    clean_email = email.strip()
    clean_password = password.strip()
    print(f"[DEBUG] Trying: '{clean_email}' / '{clean_password}'")

    query = """
        SELECT cno, name FROM CUSTOMER 
        WHERE email = :email AND passwd = :passwd
    """
    cursor.execute(query, {'email': clean_email, 'passwd': clean_password})
    user = cursor.fetchone()
    print("[DEBUG] Query result:", user)
    return user


# 추후 추가 가능: 항공편 조회, 예약, 취소 등

def print_all_customers(cursor):
    cursor.execute("SELECT email, passwd FROM CUSTOMER")
    rows = cursor.fetchall()
    print("[DEBUG] CUSTOMER 테이블 내용:")
    for email, passwd in rows:
        print(f"  - {email} / {passwd}")
