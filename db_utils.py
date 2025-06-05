import oracledb

def get_connection():
    return oracledb.connect(
        user="TP",
        password="tp1234",
        dsn="localhost:1521/XE"
    )

def verify_user(cursor, email, password):
    query = """
        SELECT cno, name FROM CUSTOMER 
        WHERE email = :email AND passwd = :passwd
    """
    cursor.execute(query, {'email': email, 'passwd': password})
    return cursor.fetchone()

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
    conn = get_connection()
    cur = conn.cursor()

    base_conditions = "r.cno = :cno"
    cancel_conditions = "c.cno = :cno"
    params = {'cno': cno}

    if start_date and end_date:
        base_conditions += " AND r.departureDateTime BETWEEN :start_date AND :end_date"
        cancel_conditions += " AND c.departureDateTime BETWEEN :start_date AND :end_date"
        params['start_date'] = start_date
        params['end_date'] = end_date

    queries = []

    if view_type in ('all', 'reserve'):
        queries.append(f"""
            SELECT 
                a.airline, r.flightNo, a.departureAirport, a.arrivalAirport,
                TO_CHAR(a.departureDateTime, 'YYYY-MM-DD HH24:MI'),
                TO_CHAR(a.arrivalDateTime, 'YYYY-MM-DD HH24:MI'),
                r.payment,
                TO_CHAR(r.reserveDateTime, 'YYYY-MM-DD HH24:MI') AS reserveDate,
                '예약' AS status,
                NULL AS cancelDate
            FROM RESERVE r
            JOIN AIRPLANE a ON r.flightNo = a.flightNo AND r.departureDateTime = a.departureDateTime
            WHERE {base_conditions}
        """)

    if view_type in ('all', 'cancel'):
        queries.append(f"""
            SELECT 
                a.airline, c.flightNo, a.departureAirport, a.arrivalAirport,
                TO_CHAR(a.departureDateTime, 'YYYY-MM-DD HH24:MI'),
                TO_CHAR(a.arrivalDateTime, 'YYYY-MM-DD HH24:MI'),
                c.refund,
                TO_CHAR(c.cancelDateTime, 'YYYY-MM-DD HH24:MI') AS reserveDate,
                '취소' AS status,
                TO_CHAR(c.cancelDateTime, 'YYYY-MM-DD HH24:MI') AS cancelDate
            FROM CANCEL c
            JOIN AIRPLANE a ON c.flightNo = a.flightNo AND c.departureDateTime = a.departureDateTime
            WHERE {cancel_conditions}
        """)

    if not queries:
        return []

    full_query = " UNION ALL ".join(queries) + " ORDER BY 5"  # departureDateTime 기준 정렬
    cur.execute(full_query, params)
    results = cur.fetchall()

    cur.close()
    conn.close()
    return results
