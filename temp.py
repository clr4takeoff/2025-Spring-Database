from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('flight_search.html')

@app.route('/flight_search')
def flight_search():
    return render_template('flight_search.html')

@app.route('/flight_check')
def flight_check():
    return render_template('flight_check.html')

if __name__ == '__main__':
    app.run(debug=True)
