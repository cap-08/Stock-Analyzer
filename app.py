from flask import Flask, render_template, request, redirect, url_for, session
import yfinance as yf
import plotly.graph_objs as go
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'key'

# ---------- DATABASE SETUP ----------
def init_db():
    with sqlite3.connect("portfolio.db") as conn:
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        stock TEXT,
                        type TEXT,
                        units INTEGER,
                        price REAL,
                        date TEXT,
                        FOREIGN KEY(user_id) REFERENCES users(id))''')
        conn.commit()

init_db()

# ---------- STOCK DATA ----------
def get_stock_data(symbol="^NSEI"):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="12mo", interval="1d")
    if hist.empty:
        return None
    last = hist.iloc[-1]
    graph = go.Figure()
    graph.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='Close'))
    graph.update_layout(template='plotly_dark', title=f"{symbol} - 12 Month Trend", 
                        xaxis_title="Date", yaxis_title="Price (₹)")
    graph_html = graph.to_html(full_html=False)
    return {
        "symbol": symbol,
        "price": round(last['Close'], 2),
        "high": round(hist['High'].max(), 2),
        "low": round(hist['Low'].min(), 2),
        "graph": graph_html
    }

# ---------- ROUTES ----------
@app.route('/')
def index():
    stock = get_stock_data("^NSEI")
    return render_template('index.html', stock=stock)

@app.route('/search', methods=['POST'])
def search():
    symbol = request.form['symbol'].upper() + ".NS"
    stock = get_stock_data(symbol)
    if stock:
        return render_template('index.html', stock=stock)
    else:
        return render_template('index.html', error="Invalid stock symbol")

@app.route('/buy', methods=['POST'])
def buy():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    stock = request.form['stock']
    units = int(request.form['units'])
    price = float(request.form['price'])
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect("portfolio.db") as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO transactions (user_id, stock, type, units, price, date) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, stock, "Buy", units, price, date))
        conn.commit()

    return redirect(url_for('portfolio'))

@app.route('/sell', methods=['POST'])
def sell():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    stock = request.form['stock']
    units = int(request.form['units'])
    price = float(request.form['price'])
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect("portfolio.db") as conn:
        cur = conn.cursor()

        # Calculate total bought - sold to check current holdings
        cur.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN type='Buy' THEN units ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN type='Sell' THEN units ELSE 0 END), 0)
            FROM transactions WHERE user_id=? AND stock=?""", (user_id, stock))
        owned_units = cur.fetchone()[0]

        if owned_units < units:
            return render_template('portfolio.html', username=session['username'], 
                                   transactions=get_user_transactions(user_id),
                                   error=f"Not enough units to sell ({owned_units} available).")

        # Record the sell transaction
        cur.execute("INSERT INTO transactions (user_id, stock, type, units, price, date) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, stock, "Sell", units, price, date))
        conn.commit()

    return redirect(url_for('portfolio'))

def get_user_transactions(user_id):
    with sqlite3.connect("portfolio.db") as conn:
        cur = conn.cursor()
        cur.execute("SELECT stock, type, units, price, date FROM transactions WHERE user_id = ?", (user_id,))
        return cur.fetchall()

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        with sqlite3.connect("portfolio.db") as conn:
            cur = conn.cursor()
            try:
                cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                return redirect(url_for('login'))
            except:
                return render_template('signup.html', error="Username already exists")
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect("portfolio.db") as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, password FROM users WHERE username = ?", (username,))
            user = cur.fetchone()
            if user and check_password_hash(user[1], password):
                session['user_id'] = user[0]
                session['username'] = username
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    transactions = get_user_transactions(user_id)

    # Calculate current holdings
    holdings = {}
    for stock, ttype, units, price, date in transactions:
        if stock not in holdings:
            holdings[stock] = 0
        holdings[stock] += units if ttype == "Buy" else -units

    holdings = {k: v for k, v in holdings.items() if v > 0}

    return render_template('portfolio.html',
                           username=session['username'],
                           transactions=transactions,
                           holdings=holdings)
    
if __name__ == '__main__':
    app.run(debug=True)
