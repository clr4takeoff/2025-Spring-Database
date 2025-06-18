# 필요한 모듈 불러오기
import oracledb  # Oracle DB 연결
import smtplib   # 이메일 전송
import uuid      # 고유 예약 ID 생성
import os        # 시스템 환경 접근
from datetime import datetime, timedelta  # 날짜/시간 계산
from email.mime.text import MIMEText      # 이메일 본문 생성
from email.utils import formataddr        # 이메일 주소 포맷팅
from dotenv import load_dotenv            # .env 파일에서 환경변수 불러오기


# 데이터베이스 연결 함수
def get_connection():
    return oracledb.connect(
        user="TP",
        password="tp1234",
        dsn="localhost:1521/XE"
    )

# 사용자 로그인 인증
def verify_user(email, password):
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT cno, name, email FROM CUSTOMER 
        WHERE email = :email AND passwd = :passwd
    """
    cur.execute(query, {'email': email, 'passwd': password})
    result = cur.fetchone()

    cur.close()
    conn.close()
    return result

# 조건에 맞는 항공편 조회
def get_flights(cursor, filters):
    query = """
        SELECT 
            a.airline, a.flightNo, a.departureAirport, a.arrivalAirport,
            TO_CHAR(a.departureDateTime, 'YYYY-MM-DD HH24:MI'),
            TO_CHAR(a.arrivalDateTime, 'YYYY-MM-DD HH24:MI'),
            s.price,
            GET_REMAINING_SEATS(s.flightNo, s.departureDateTime, s.seatClass) AS remaining_seats,
            s.seatClass
        FROM AIRPLANE a
        JOIN SEATS s ON a.flightNo = s.flightNo AND a.departureDateTime = s.departureDateTime
        WHERE 1=1
        AND a.departureDateTime > SYSTIMESTAMP
    """

    params = {'cno': filters.get('cno')}  # 사용자 번호

    # 필터 조건 추가
    if filters.get("departure"):
        query += " AND a.departureAirport = :departure"
        params["departure"] = filters["departure"]
    if filters.get("arrival"):
        query += " AND a.arrivalAirport = :arrival"
        params["arrival"] = filters["arrival"]
    if filters.get("date"):
        query += " AND TO_CHAR(a.departureDateTime, 'YYYY.MM.DD.') = :date"
        params["date"] = filters["date"]
    if filters.get("seat_class"):
        query += " AND s.seatClass = :seat_class"
        params["seat_class"] = filters["seat_class"]

    # 중복 예약 제거 조건
    query += """
        AND NOT EXISTS (
            SELECT 1 FROM RESERVE r
            WHERE r.flightNo = a.flightNo
              AND r.departureDateTime = a.departureDateTime
              AND r.seatClass = s.seatClass
              AND r.cno = :cno
        )
    """

    # 정렬 조건
    sort_by = filters.get("sort_by", "price") # 기본값은 가격

    if sort_by == 'departure':
        query += " ORDER BY a.departureDateTime"
    else:
        query += " ORDER BY s.price"

    cursor.execute(query, params)
    return cursor.fetchall()

# 사용자 예약 목록 조회
def get_reservations(cursor, cno):
    query = """
        SELECT 
            a.airline, a.flightNo, a.departureAirport, a.arrivalAirport,
            TO_CHAR(a.departureDateTime, 'YYYY-MM-DD HH24:MI'),
            TO_CHAR(a.arrivalDateTime, 'YYYY-MM-DD HH24:MI'),
            r.seatClass, r.payment
        FROM RESERVE r
        JOIN SEATS s ON r.flightNo = s.flightNo 
                    AND r.departureDateTime = s.departureDateTime 
                    AND r.seatClass = s.seatClass
        JOIN AIRPLANE a ON r.flightNo = a.flightNo 
                       AND r.departureDateTime = a.departureDateTime
        WHERE r.cno = :cno
        ORDER BY a.departureDateTime
    """
    cursor.execute(query, {'cno': cno})
    return cursor.fetchall()

# 예약 및 취소 내역 통합 조회 (필터 포함)
def get_user_reservations(cno, start_date, end_date, view_type):
    conn = get_connection()
    cur = conn.cursor()

    params = {'cno': cno}
    queries = []

    has_date_filter = bool(start_date and end_date)
    if has_date_filter:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
            params['start_date'] = start_date_obj
            params['end_date'] = end_date_obj
        except ValueError:
            print("[DEBUG] 날짜 형식 오류:", start_date, end_date)
            return []

    # 예약 내역
    if view_type in ('all', 'reserve'):
        reserve_query = """
            SELECT 
                a.airline, r.flightNo, a.departureAirport, a.arrivalAirport,
                TO_CHAR(a.departureDateTime, 'YYYY-MM-DD HH24:MI'),
                TO_CHAR(a.arrivalDateTime, 'YYYY-MM-DD HH24:MI'),
                r.seatClass, r.payment,
                TO_CHAR(r.reserveDateTime, 'YYYY-MM-DD HH24:MI'),
                '예약',
                NULL
            FROM RESERVE r
            JOIN AIRPLANE a ON r.flightNo = a.flightNo AND r.departureDateTime = a.departureDateTime
            WHERE r.cno = :cno
        """
        if has_date_filter:
            reserve_query += " AND r.reserveDateTime BETWEEN :start_date AND :end_date"
        queries.append(reserve_query)

    # 취소 내역
    if view_type in ('all', 'cancel'):
        cancel_query = """
            SELECT 
                a.airline, c.flightNo, a.departureAirport, a.arrivalAirport,
                TO_CHAR(a.departureDateTime, 'YYYY-MM-DD HH24:MI'),
                TO_CHAR(a.arrivalDateTime, 'YYYY-MM-DD HH24:MI'),
                c.seatClass, c.refund,
                TO_CHAR(c.cancelDateTime, 'YYYY-MM-DD HH24:MI'),
                '취소',
                TO_CHAR(c.cancelDateTime, 'YYYY-MM-DD HH24:MI')
            FROM CANCEL c
            JOIN AIRPLANE a ON c.flightNo = a.flightNo AND c.departureDateTime = a.departureDateTime
            WHERE c.cno = :cno
        """
        if has_date_filter:
            cancel_query += " AND c.cancelDateTime BETWEEN :start_date AND :end_date"
        queries.append(cancel_query)

    if not queries:
        return []

    full_query = " UNION ALL ".join(queries) + " ORDER BY 5"

    cur.execute(full_query, params)
    results = cur.fetchall()

    cur.close()
    conn.close()
    return results

# 관리자 여부 확인
def is_admin(cno):
    return cno.startswith('C0')  # 고객번호가 'C0'으로 시작하면 관리자

# 고객별 예약 취소율 조회: admin 전용
def get_cancel_ratio():
    conn = get_connection()
    cur = conn.cursor()
    query = """
    SELECT c.cno, c.name,
        COUNT(DISTINCT r.flightNo) AS total_reserves,
        COUNT(DISTINCT ca.flightNo) AS total_cancels,
        CASE WHEN COUNT(DISTINCT r.flightNo) = 0 THEN 0
             ELSE ROUND(COUNT(DISTINCT ca.flightNo) / COUNT(DISTINCT r.flightNo), 2)
        END AS cancel_ratio
    FROM CUSTOMER c
    LEFT JOIN RESERVE r ON c.cno = r.cno
    LEFT JOIN CANCEL ca ON c.cno = ca.cno
    WHERE c.cno NOT LIKE 'C0%'
    GROUP BY c.cno, c.name
    ORDER BY cancel_ratio DESC NULLS LAST
    """
    cur.execute(query)
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result

# 고객별 예약 금액 순위 조회: admin 전용
def get_payment_rank():
    conn = get_connection()
    cur = conn.cursor()
    query = """
    SELECT r.cno, r.reserveDateTime, r.payment,
           RANK() OVER (
               PARTITION BY r.cno
               ORDER BY r.payment DESC
           ) AS payment_rank
    FROM RESERVE r
    JOIN CUSTOMER c ON r.cno = c.cno
    WHERE c.cno NOT LIKE 'C0%'
    """
    cur.execute(query)
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result

# 항공편 예약 함수
def make_reservation(flight_no, departure_datetime_str, seat_class, cno):
    """
    항공편 예약 함수.
    좌석 정보를 확인 후 예약 테이블에 저장한다.
    잔여 좌석 계산은 Oracle Stored Function에 위임.
    """
    from datetime import datetime
    reserve_id = str(uuid.uuid4())

    reserve_datetime = datetime.now()
    conn = get_connection()
    cur = conn.cursor()

    try:
        # 시간 문자열 포맷 보정
        if len(departure_datetime_str) == 16:
            departure_datetime_str += ":00"
        
        # 중복 시간대 예약 여부 확인
        cur.execute("""
            SELECT 1
            FROM RESERVE r
            JOIN AIRPLANE a1 ON r.flightNo = a1.flightNo AND r.departureDateTime = a1.departureDateTime
            JOIN AIRPLANE a2 ON a2.flightNo = :flight_no AND a2.departureDateTime = TO_TIMESTAMP(:departure_datetime, 'YYYY-MM-DD HH24:MI:SS')
            WHERE r.cno = :cno
            AND a1.departureDateTime = a2.departureDateTime
            AND a1.arrivalDateTime = a2.arrivalDateTime
        """, {
            'flight_no': flight_no,
            'departure_datetime': departure_datetime_str,
            'cno': cno
        })
        if cur.fetchone():
            return False, "동일 시간대의 예약 노선이 이미 존재합니다. 중복 예약은 불가능합니다."


        # 잔여 좌석 확인
        cur.execute("""
            SELECT GET_REMAINING_SEATS(:flight_no, TO_TIMESTAMP(:departure_datetime, 'YYYY-MM-DD HH24:MI:SS'), :seat_class)
            FROM dual
        """, {
            'flight_no': flight_no,
            'departure_datetime': departure_datetime_str,
            'seat_class': seat_class
        })
        row = cur.fetchone()
        remaining_seats = row[0] if row else 0

        if remaining_seats <= 0:
            return False, "해당 클래스의 좌석이 매진되었습니다."

        # 가격 조회
        cur.execute("""
            SELECT price FROM SEATS
            WHERE flightNo = :flight_no 
              AND departureDateTime = TO_TIMESTAMP(:departure_datetime, 'YYYY-MM-DD HH24:MI:SS') 
              AND seatClass = :seat_class
        """, {
            'flight_no': flight_no,
            'departure_datetime': departure_datetime_str,
            'seat_class': seat_class
        })
        price_row = cur.fetchone()
        if not price_row:
            return False, "해당 좌석 정보를 찾을 수 없습니다."
        price = price_row[0]

        # 예약 테이블에 삽입
        cur.execute("""
            INSERT INTO RESERVE (reserveId, flightNo, departureDateTime, seatClass, payment, reserveDateTime, cno)
            VALUES (:reserve_id, :flight_no, TO_TIMESTAMP(:departure_datetime, 'YYYY-MM-DD HH24:MI:SS'),
                    :seat_class, :payment, TO_TIMESTAMP(:reserve_time, 'YYYY-MM-DD HH24:MI:SS'), :cno)
        """, {
            'reserve_id': reserve_id,
            'flight_no': flight_no,
            'departure_datetime': departure_datetime_str,
            'seat_class': seat_class,
            'payment': price,
            'reserve_time': reserve_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'cno': cno
        })

        conn.commit()
        return True, "예약이 완료되었습니다."

    except Exception as e:
        conn.rollback()
        return False, f"예약 중 오류 발생: {str(e)}"
    finally:
        cur.close()
        conn.close()


# 예약 취소 함수
def cancel_reservation(flight_no, departure_datetime_str, cno):
    """
    예약 취소 함수.
    주어진 항공편 번호, 출발일시, 고객 번호를 기반으로 예약을 취소하고, 
    취소 수수료를 계산하여 환불을 처리한다.
    """
    from datetime import datetime
    conn = get_connection()
    cur = conn.cursor()

    try:
        print("[DEBUG] 사용자 정보 확인 - cno:", cno)

        # 출발 시간이 현재보다 이전이면 취소 불가
        departure_datetime = datetime.strptime(departure_datetime_str, "%Y-%m-%d %H:%M")
        now = datetime.now()

        if departure_datetime < now:
            return False, "이미 출발한 항공편은 취소할 수 없습니다."
        

        # 예약 정보 조회
        cur.execute("""
            SELECT reserveId, seatClass, payment
            FROM RESERVE
            WHERE flightNo = :flight_no AND departureDateTime = TO_TIMESTAMP(:departure_datetime, 'YYYY-MM-DD HH24:MI') 
                AND cno = :cno
        """, {
            'flight_no': flight_no,
            'departure_datetime': departure_datetime_str,
            'cno': cno
        })
        row = cur.fetchone()

        if not row:
            return False, "예약 정보를 찾을 수 없습니다."

        reserve_id, seat_class, payment = row

        # 중복 취소 확인
        reserve_id, seat_class, payment = row

        cur.execute("""
            SELECT 1 FROM CANCEL WHERE reserveId = :reserve_id
        """, {'reserve_id': reserve_id})
        if cur.fetchone():
            return False, "이미 취소된 예약입니다."


        # 취소 수수료 계산
        days_diff = (departure_datetime.date() - now.date()).days
        if days_diff >= 15:
            fee = 150000
        elif 4 <= days_diff <= 14:
            fee = 180000
        elif 1 <= days_diff <= 3:
            fee = 250000
        else:  # same-day 취소 시 전액 수수료
            fee = payment
        refund = max(0, payment - fee)

        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # 취소 테이블에 기록
        cur.execute("""
            INSERT INTO CANCEL (reserveId, flightNo, departureDateTime, seatClass, refund, cancelDateTime, cno)
            VALUES (:reserve_id, :flight_no, TO_TIMESTAMP(:departure_datetime, 'YYYY-MM-DD HH24:MI'), 
                    :seat_class, :refund, TO_TIMESTAMP(:cancel_time, 'YYYY-MM-DD HH24:MI:SS'), :cno)
        """, {
            'reserve_id': reserve_id,
            'flight_no': flight_no,
            'departure_datetime': departure_datetime_str,
            'seat_class': seat_class,
            'refund': refund,
            'cancel_time': now_str,
            'cno': cno
        })

        # 예약 테이블에서 삭제
        cur.execute("""
            DELETE FROM RESERVE
            WHERE flightNo = :flight_no AND departureDateTime = TO_TIMESTAMP(:departure_datetime, 'YYYY-MM-DD HH24:MI') AND seatClass = :seat_class AND cno = :cno
        """, {
            'flight_no': flight_no,
            'departure_datetime': departure_datetime_str,
            'seat_class': seat_class,
            'cno': cno
        })

        conn.commit()

        # 사용자에게 반환할 메시지
        msg = f"예약이 취소되었습니다.\n총 결제금액: {payment:,}원\n취소 수수료: {fee:,}원\n환불 금액: {refund:,}원"
        return True, msg

    except Exception as e:
        conn.rollback()
        return False, f"오류 발생: {str(e)}"
    finally:
        cur.close()
        conn.close()


# 예약 요청 처리 + 이메일 전송 호출
def process_reservation_request(flight_no, departure_datetime, seat_class, cno, user_name, user_email):
    """
    예약 처리 후 이메일 전송까지 담당하는 함수.
    예약 성공 시 예약 정보를 이메일로 전송한다.
    """
    success, msg = make_reservation(flight_no, departure_datetime, seat_class, cno)

    if not success:
        return False, msg

    # 항공편 상세 정보 조회
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            a.airline, a.departureAirport, a.arrivalAirport,
            TO_CHAR(a.departureDateTime, 'YYYY-MM-DD HH24:MI'),
            TO_CHAR(a.arrivalDateTime, 'YYYY-MM-DD HH24:MI'),
            s.price
        FROM AIRPLANE a
        JOIN SEATS s ON a.flightNo = s.flightNo AND a.departureDateTime = s.departureDateTime
        WHERE a.flightNo = :flight_no AND a.departureDateTime = TO_TIMESTAMP(:departure_datetime, 'YYYY-MM-DD HH24:MI')
              AND s.seatClass = :seat_class
    """, {
        'flight_no': flight_no,
        'departure_datetime': departure_datetime,
        'seat_class': seat_class
    })
    row = cur.fetchone()
    cur.close()
    conn.close()

    # 이메일 전송
    if row and user_email:
        flight_info = {
            'airline': row[0],
            'flight_no': flight_no,
            'departure_airport': row[1],
            'arrival_airport': row[2],
            'departure_time': row[3],
            'arrival_time': row[4],
            'seat_class': seat_class,
            'price': row[5]
        }

        email_success, email_msg = send_reservation_email(user_email, user_name, flight_info)
        print("[EMAIL]", email_msg)

    return True, msg


# 이메일 전송 함수
def send_reservation_email(to_email, name, flight_info):
    """
    예약 완료 이메일을 전송하는 함수.
    """
    try:
        load_dotenv()  # 환경 변수 로드 (.env 파일)
        smtp_user = os.getenv('SMTP_USER')
        smtp_pass = os.getenv('SMTP_PASS')
        sender_name = "C-AIR"

        # 메일 제목 및 본문 생성
        subject = f"[예약 확인] {flight_info['airline']} 항공편 예약 완료"
        body = f"""
        {name} 고객님, 항공편 예약이 완료되었습니다.

        - 항공사: {flight_info['airline']}
        - 항공편 번호: {flight_info['flight_no']}
        - 출발지: {flight_info['departure_airport']}
        - 도착지: {flight_info['arrival_airport']}
        - 출발 시간: {flight_info['departure_time']}
        - 도착 시간: {flight_info['arrival_time']}
        - 좌석 클래스: {flight_info['seat_class']}
        - 결제 금액: {flight_info['price']:,}원

        감사합니다.
        """

        # 메일 메시지 구성
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = formataddr((sender_name, smtp_user))
        msg['To'] = to_email

        # SMTP 서버를 통해 이메일 발송
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        return True, f"{to_email} 주소로 이메일을 전송했습니다."

    except Exception as e:
        return False, f"이메일 전송 실패: {str(e)}"
