from flask import Flask, request, redirect, render_template, url_for, session
from db_utils import get_connection, verify_user, print_all_customers

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# DB 연결 및 커서 초기화
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
    
    print_all_customers(cursor)
    user = verify_user(cursor, email, password)

    if user:
        session['cno'] = user[0]
        session['name'] = user[1]
        return redirect(url_for('flight_search'))
    else:
        return render_template('login.html', error='Invalid email or password')


@app.route('/flight_search')
def flight_search():
    if 'cno' not in session:
        return redirect(url_for('login'))
    return render_template('flight_search.html')


@app.route('/flight_check')
def flight_check():
    return render_template('flight_check.html')


if __name__ == '__main__':
    app.run(debug=True)
