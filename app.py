from flask import Flask, request, redirect, render_template, url_for, session
from db_utils import get_connection, verify_user, get_flights, get_user_reservations, is_admin, get_cancel_ratio, get_payment_rank

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

    email = request.form['email']
    password = request.form['password']
    user = verify_user(cursor, email, password)

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
        'sort_by': request.args.get('sort_by')
    }

    flights = get_flights(cursor, filters)
    return render_template('flight_search.html', flights=flights, name=session['name'])

@app.route('/flight_check', methods=['GET', 'POST'])
def flight_check():
    if 'cno' not in session:
        return redirect(url_for('login'))

    cno = session['cno']
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    view_type = request.args.get('view_type', 'reserve')

    reservations = get_user_reservations(cno, start_date, end_date, view_type)

    return render_template('flight_check.html', reservations=reservations)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/admin')
def admin_page():
    if 'cno' not in session or not is_admin(session['cno']):
        return redirect(url_for('login'))

    view = request.args.get('view', 'cancel')  # 기본값: 취소율

    if view == 'cancel':
        result = get_cancel_ratio()  # → db_utils 함수
    elif view == 'payment':
        result = get_payment_rank()
    else:
        result = []

    return render_template('admin.html', name=session['name'], view=view, results=result)


if __name__ == '__main__':
    app.run(debug=True)
