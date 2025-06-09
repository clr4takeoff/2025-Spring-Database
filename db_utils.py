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
            s.price, s.no_of_seats
        FROM AIRPLANE a
        JOIN SEATS s ON a.flightNo = s.flightNo AND a.departureDateTime = s.departureDateTime
        WHERE 1=1
    """
    params = {}

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