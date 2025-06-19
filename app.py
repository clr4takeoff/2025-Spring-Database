from flask import Flask, request, redirect, render_template, url_for, session, Response
from db_utils import (
    get_connection, verify_user, get_flights, get_user_reservations, is_admin,
    get_cancel_ratio, get_payment_rank, cancel_reservation, process_reservation_request
)
from urllib.parse import quote
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션을 위한 비밀 키 설정

# 데이터베이스 연결
conn = get_connection()
cursor = conn.cursor()

# 루트 경로 접근 시 로그인 페이지로 리디렉션
@app.route('/')
def index():
    return redirect(url_for('login'))

# 로그인 페이지
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')  # 로그인 폼 렌더링

    # POST 요청인 경우 로그인 시도
    email = request.form['email'].strip()
    password = request.form['password'].strip()
    user = verify_user(email, password)

    # 인증 실패 시 에러 메시지 반환
    if not user:
        return render_template('login.html', error="이메일 또는 비밀번호가 잘못되었습니다.")

    # 인증 성공 시 세션에 사용자 정보 저장
    session['cno'] = user[0]
    session['name'] = user[1]
    session['email'] = user[2]

    # 관리자 여부에 따라 페이지 분기
    if is_admin(user[0]):
        return redirect(url_for('admin_page'))
    else:
        return redirect(url_for('flight_search'))

# 항공편 검색 페이지
@app.route('/flight_search', methods=['GET'])
def flight_search():
    if 'cno' not in session:
        return redirect(url_for('login'))

    # 검색 필터 수집
    filters = {
        'departure': request.args.get('departure'),
        'arrival': request.args.get('arrival'),
        'date': request.args.get('date'),
        'seat_class': request.args.get('seat_class'),
        'sort_by': request.args.get('sort_by'),
        'cno': session['cno']
    }

    # 항공편 정보 검색
    flights = get_flights(cursor, filters)
    return render_template('flight_search.html', flights=flights, name=session['name'])

# 예약 내역 확인 및 예약 취소 처리
@app.route('/flight_check', methods=['GET', 'POST'])
def flight_check():
    if 'cno' not in session:
        return redirect(url_for('login'))

    cno = session['cno']

    # POST: 예약 취소 처리
    if request.method == 'POST':
        flight_no = request.form['flight_no']
        departure_datetime_str = request.form['departure_datetime']
        success, message = cancel_reservation(flight_no, departure_datetime_str, cno)

        # 메시지를 세션에 저장 후 리디렉션
        session['popup_message'] = message
        return redirect(url_for('flight_check'))

    # GET: 예약/취소 내역 조회
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    view_type = request.args.get('view_type', 'reserve')

    # 세션에서 메시지 꺼내고 즉시 삭제 (한 번만 표시되도록)
    message = session.pop('popup_message', None)

    # 날짜 유효성 검사
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            if end_dt < start_dt:
                session['popup_message'] = "잘못된 날짜 범위입니다. 시작일은 종료일보다 이전이어야 합니다."
                return redirect(url_for('flight_check', view_type=view_type))
        except ValueError:
            session['popup_message'] = "날짜 형식이 올바르지 않습니다."
            return redirect(url_for('flight_check', view_type=view_type))

    reservations = get_user_reservations(cno, start_date, end_date, view_type)
    return render_template('flight_check.html', reservations=reservations, popup_message=message)


# 항공편 예약 처리
@app.route('/make_reservation', methods=['POST'])
def make_reservation_route():
    if 'cno' not in session:
        return redirect(url_for('login'))

    flight_no = request.form['flight_no']
    departure_datetime = request.form['departure_datetime']
    seat_class = request.form['seat_class']
    cno = session['cno']
    user_name = session.get('name')
    user_email = session.get('email')

    # 예약 요청 처리
    success, msg = process_reservation_request(
        flight_no, departure_datetime, seat_class,
        cno, user_name, user_email
    )

    # 성공 시 예약 내역 페이지로 리디렉션, 실패 시 알림
    if success:
        return redirect(url_for('flight_check', msg=quote(msg)))
    else:
        return Response(f"""
            <script>alert("{msg}"); window.history.back();</script>
        """, mimetype='text/html')

# 로그아웃 처리
@app.route('/logout')
def logout():
    session.clear()  # 세션 초기화
    return redirect(url_for('login'))

# 관리자 페이지
@app.route('/admin')
def admin_page():
    # 로그인되어 있지 않거나 관리자가 아닌 경우 로그인 페이지로 리디렉션
    if 'cno' not in session or not is_admin(session['cno']):
        return redirect(url_for('login'))

    # 관리자 페이지에서 보여줄 통계 정보 선택
    view = request.args.get('view', 'cancel')

    if view == 'cancel':
        result = get_cancel_ratio()  # 예약 취소율
    elif view == 'payment':
        result = get_payment_rank()  # 사용자 결제 랭킹
    else:
        result = []

    return render_template('admin.html', name=session['name'], view=view, results=result)

# 애플리케이션 실행
if __name__ == '__main__':
    app.run(debug=True)
