from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # 예시 로그인 조건
        if email == 'admin@cnu.ac.kr' and password == '1234':
            session['user'] = email
            return redirect('/flight_search')  # 성공 시 이동
        else:
            error = '아이디 또는 비밀번호가 올바르지 않습니다.'

    return render_template('login.html', error=error)

if __name__ == '__main__':
    app.run(debug=True)
