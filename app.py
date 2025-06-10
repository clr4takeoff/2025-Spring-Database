from flask import Flask, request, redirect, render_template, url_for, session, Response
from db_utils import get_connection, verify_user, get_flights, get_user_reservations, is_admin, get_cancel_ratio, get_payment_rank, cancel_reservation, make_reservation, process_reservation_request
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = 'your_secret_key'

conn = get_connection()
cursor = conn.cursor()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form['email'].strip()
    password = request.form['password'].strip()
    user = verify_user(email, password)

    if not user:
        return render_template('login.html', error="이메일 또는 비밀번호가 잘못되었습니다.")

    session['cno'] = user[0]
    session['name'] = user[1]
    session['email'] = user[2]

    if is_admin(user[0]):
        return redirect(url_for('admin_page'))
    else:
        return redirect(url_for('flight_search'))

@app.route('/flight_search', methods=['GET'])
def flight_search():
    if 'cno' not in session:
        return redirect(url_for('login'))

    filters = {
    'departure': request.args.get('departure'),
    'arrival': request.args.get('arrival'),
    'date': request.args.get('date'),
    'seat_class': request.args.get('seat_class'),
    'sort_by': request.args.get('sort_by'),
    'cno': session['cno'] 
    }


    flights = get_flights(cursor, filters)
    return render_template('flight_search.html', flights=flights, name=session['name'])



@app.route('/flight_check', methods=['GET', 'POST'])
def flight_check():
    if 'cno' not in session:
        return redirect(url_for('login'))

    cno = session['cno']

    if request.method == 'POST':
        flight_no = request.form['flight_no']
        departure_datetime_str = request.form['departure_datetime']

        success, message = cancel_reservation(flight_no, departure_datetime_str, cno)

        # 메시지를 쿼리스트링으로 전달
        encoded_msg = quote(message)
        return redirect(url_for('flight_check') + f"?msg={encoded_msg}")

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    view_type = request.args.get('view_type', 'reserve')
    message = request.args.get('message', None)

    reservations = get_user_reservations(cno, start_date, end_date, view_type)

    return render_template('flight_check.html', reservations=reservations, message=message)




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

    success, msg = process_reservation_request(
        flight_no, departure_datetime, seat_class,
        cno, user_name, user_email
    )

    if success:
        return redirect(url_for('flight_check', msg=quote(msg)))
    else:
        return Response(f"""
            <script>alert("{msg}"); window.history.back();</script>
        """, mimetype='text/html')  




@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))




@app.route('/admin')
def admin_page():
    if 'cno' not in session or not is_admin(session['cno']):
        return redirect(url_for('login'))

    view = request.args.get('view', 'cancel')

    if view == 'cancel':
        result = get_cancel_ratio()
    elif view == 'payment':
        result = get_payment_rank()
    else:
        result = []

    return render_template('admin.html', name=session['name'], view=view, results=result)


if __name__ == '__main__':
    app.run(debug=True)