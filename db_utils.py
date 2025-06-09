import oracledb
from datetime import datetime,  timedelta

def get_connection():
    return oracledb.connect(
        user="TP",
        password="tp1234",
        dsn="localhost:1521/XE"
    )


def verify_user(email, password):
    conn = get_connection()
    cur = conn.cursor()

    print("[DEBUG] 입력된 email:", email)
    print("[DEBUG] 입력된 password:", password)

    query = """
        SELECT cno, name FROM CUSTOMER 
        WHERE email = :email AND passwd = :passwd
    """
    cur.execute(query, {'email': email, 'passwd': password})
    result = cur.fetchone()

    print("[DEBUG] 쿼리 결과:", result)

    cur.close()
    conn.close()
    return result


def get_flights(cursor, filters):
    query = """
        SELECT 
            a.airline, a.flightNo, a.departureAirport, a.arrivalAirport,
            TO_CHAR(a.departureDateTime, 'YYYY-MM-DD HH24:MI'),
            TO_CHAR(a.arrivalDateTime, 'YYYY-MM-DD HH24:MI'),
            s.price, s.no_of_seats, s.seatClass
        FROM AIRPLANE a
        JOIN SEATS s ON a.flightNo = s.flightNo AND a.departureDateTime = s.departureDateTime
        WHERE 1=1
    """
    params = {'cno': filters.get('cno')}

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

    # 중복 예약 제거
    query += """
        AND NOT EXISTS (
            SELECT 1 FROM RESERVE r
            WHERE r.flightNo = a.flightNo
              AND r.departureDateTime = a.departureDateTime
              AND r.seatClass = s.seatClass
              AND r.cno = :cno
        )
    """

    sort_by = filters.get("sort_by")
    if sort_by == 'price':
        query += " ORDER BY s.price"
    elif sort_by == 'departure':
        query += " ORDER BY a.departureDateTime"
    else:
        query += " ORDER BY a.departureDateTime"

    cursor.execute(query, params)
    return cursor.fetchall()


def get_reservations(cursor, cno):
    query = """
        SELECT 
            a.airline, a.flightNo, a.departureAirport, a.arrivalAirport,
            TO_CHAR(a.departureDateTime, 'YYYY-MM-DD HH24:MI'),
            TO_CHAR(a.arrivalDateTime, 'YYYY-MM-DD HH24:MI'),
            r.payment
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

def get_user_reservations(cno, start_date, end_date, view_type):
    from datetime import datetime, timedelta

    conn = get_connection()
    cur = conn.cursor()

    params = {'cno': cno}
    queries = []

    # 날짜 파라미터 처리
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

    # 예약 내역 쿼리
    if view_type in ('all', 'reserve'):
        reserve_query = """
            SELECT 
                a.airline, r.flightNo, a.departureAirport, a.arrivalAirport,
                TO_CHAR(a.departureDateTime, 'YYYY-MM-DD HH24:MI'),
                TO_CHAR(a.arrivalDateTime, 'YYYY-MM-DD HH24:MI'),
                r.payment,
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

    # 취소 내역 쿼리
    if view_type in ('all', 'cancel'):
        cancel_query = """
            SELECT 
                a.airline, c.flightNo, a.departureAirport, a.arrivalAirport,
                TO_CHAR(a.departureDateTime, 'YYYY-MM-DD HH24:MI'),
                TO_CHAR(a.arrivalDateTime, 'YYYY-MM-DD HH24:MI'),
                c.refund,
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

    print("[DEBUG] 최종 쿼리:", full_query)
    print("[DEBUG] 바인딩 파라미터:", params)

    cur.execute(full_query, params)
    results = cur.fetchall()

    cur.close()
    conn.close()
    return results



def is_admin(cno):
    return cno.startswith('C0')


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
    GROUP BY c.cno, c.name
    ORDER BY cancel_ratio DESC NULLS LAST
    """
    cur.execute(query)
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result


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
    """
    cur.execute(query)
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result


def cancel_reservation(flight_no, departure_datetime_str, cno):
    from datetime import datetime
    conn = get_connection()
    cur = conn.cursor()

    try:
        departure_datetime = datetime.strptime(departure_datetime_str, "%Y-%m-%d %H:%M")
        now = datetime.now()

        if departure_datetime < now:
            return False, "이미 출발한 항공편은 취소할 수 없습니다."

        cur.execute("""
            SELECT seatClass, payment
            FROM RESERVE
            WHERE flightNo = :flight_no AND departureDateTime = TO_TIMESTAMP(:departure_datetime, 'YYYY-MM-DD HH24:MI') AND cno = :cno
        """, {
            'flight_no': flight_no,
            'departure_datetime': departure_datetime_str,
            'cno': cno
        })
        row = cur.fetchone()

        if not row:
            return False, "예약 정보를 찾을 수 없습니다."

        seat_class, payment = row

        # 수수료 계산
        days_diff = (departure_datetime.date() - now.date()).days
        if days_diff >= 15:
            fee = 150000
        elif 4 <= days_diff <= 14:
            fee = 180000
        elif 1 <= days_diff <= 3:
            fee = 250000
        else:  # same-day
            fee = payment  # 전액 수수료
        refund = max(0, payment - fee)

        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # INSERT into CANCEL
        cur.execute("""
            INSERT INTO CANCEL (flightNo, departureDateTime, seatClass, refund, cancelDateTime, cno)
            VALUES (:flight_no, TO_TIMESTAMP(:departure_datetime, 'YYYY-MM-DD HH24:MI'), :seat_class, :refund, TO_TIMESTAMP(:cancel_time, 'YYYY-MM-DD HH24:MI:SS'), :cno)
        """, {
            'flight_no': flight_no,
            'departure_datetime': departure_datetime_str,
            'seat_class': seat_class,
            'refund': refund,
            'cancel_time': now_str,
            'cno': cno
        })

        # DELETE from RESERVE
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

        # 사용자에게 보여줄 메시지
        msg = f"예약이 취소되었습니다.\n총 결제금액: {payment:,}원\n취소 수수료: {fee:,}달러\n환불 금액: {refund:,}달러"
        return True, msg

    except Exception as e:
        conn.rollback()
        return False, f"오류 발생: {str(e)}"
    finally:
        cur.close()
        conn.close()


def make_reservation(flight_no, departure_datetime_str, seat_class, cno):
    from datetime import datetime

    reserve_datetime = datetime.now()
    conn = get_connection()
    cur = conn.cursor()

    try:
        print("[DEBUG] flight_no:", flight_no)
        print("[DEBUG] departure_datetime_str:", departure_datetime_str)
        print("[DEBUG] seat_class:", seat_class)

        if len(departure_datetime_str) == 16:
            departure_datetime_str += ":00"

        cur.execute("""
            SELECT price, no_of_seats FROM SEATS
            WHERE flightNo = :flight_no 
              AND departureDateTime = TO_TIMESTAMP(:departure_datetime, 'YYYY-MM-DD HH24:MI:SS') 
              AND seatClass = :seat_class
        """, {
            'flight_no': flight_no,
            'departure_datetime': departure_datetime_str,
            'seat_class': seat_class
        })

        row = cur.fetchone()
        if not row:
            return False, "해당 좌석 정보를 찾을 수 없습니다."

        price, available_seats = row
        if available_seats <= 0:
            return False, "해당 클래스의 좌석이 매진되었습니다."

        cur.execute("""
            INSERT INTO RESERVE (flightNo, departureDateTime, seatClass, payment, reserveDateTime, cno)
            VALUES (:flight_no, TO_TIMESTAMP(:departure_datetime, 'YYYY-MM-DD HH24:MI:SS'), :seat_class, :payment, TO_TIMESTAMP(:reserve_time, 'YYYY-MM-DD HH24:MI:SS'), :cno)
        """, {
            'flight_no': flight_no,
            'departure_datetime': departure_datetime_str,
            'seat_class': seat_class,
            'payment': price,
            'reserve_time': reserve_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'cno': cno
        })

        cur.execute("""
            UPDATE SEATS
            SET no_of_seats = no_of_seats - 1
            WHERE flightNo = :flight_no 
              AND departureDateTime = TO_TIMESTAMP(:departure_datetime, 'YYYY-MM-DD HH24:MI:SS') 
              AND seatClass = :seat_class
        """, {
            'flight_no': flight_no,
            'departure_datetime': departure_datetime_str,
            'seat_class': seat_class
        })

        conn.commit()
        return True, "예약이 완료되었습니다."

    except Exception as e:
        conn.rollback()
        return False, f"예약 중 오류 발생: {str(e)}"
    finally:
        cur.close()
        conn.close()
