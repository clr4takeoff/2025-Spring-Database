from flask import Flask, request, redirect, render_template, url_for, session
from db_utils import get_connection, verify_user, get_flights, get_user_reservations

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

    if user:
        session['cno'] = user[0]
        session['name'] = user[1]
        return redirect(url_for('flight_search'))
    else:
        return render_template('login.html', error='Invalid email or password')

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

if __name__ == '__main__':
    app.run(debug=True)
