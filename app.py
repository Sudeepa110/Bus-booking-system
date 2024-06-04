from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Sample bus data
buses = [
    {
        'bus_id': 1,
        'from': 'CityA',
        'to': 'CityB',
        'available_seats': 40,
        'price': 10.0
    },
    {
        'bus_id': 2,
        'from': 'CityC',
        'to': 'CityD',
        'available_seats': 50,
        'price': 15.0
    },
    {
        'bus_id': 3,
        'from': 'CityE',
        'to': 'CityF',
        'available_seats': 30,
        'price': 12.5
    }
]

# Initialize the database
def init_db():
    conn = sqlite3.connect('bookings.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER,
            username TEXT,
            from_city TEXT,
            to_city TEXT,
            date TEXT,
            time TEXT,
            seats INTEGER,
            price REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Utility function to connect to the database
def get_db_connection():
    conn = sqlite3.connect('bookings.db')
    conn.row_factory = sqlite3.Row
    return conn

# Decorator function to check if the user is authenticated
def login_required(route):
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('home'))
        return route(*args, **kwargs)
    return wrapper

# Home page
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('book_route'))
    return redirect(url_for('login'))

# Login endpoint
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['username'] = username
            return redirect(url_for('book_route'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    
    return render_template('login.html')

# Signup endpoint
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            flash('Username already exists')
            return redirect(url_for('signup'))
        conn.close()

        flash('Signup successful. Please login.')
        return redirect(url_for('login'))

    return render_template('signup.html')

# Logout endpoint
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Book a bus endpoint
@app.route('/book', methods=['GET', 'POST'], endpoint='book_route')
@login_required
def book():
    if request.method == 'POST':
        bus_id = int(request.form['bus_id'])
        selected_bus = next(bus for bus in buses if bus['bus_id'] == bus_id)
        seats = int(request.form['seats'])

        if seats > selected_bus['available_seats']:
            flash('Not enough available seats on the selected bus')
            return redirect(url_for('book_route'))

        booking = {
            'bus_id': bus_id,
            'username': session['username'],
            'from_city': selected_bus['from'],
            'to_city': selected_bus['to'],
            'date': request.form['date'],
            'time': request.form['time'],
            'seats': seats,
            'price': selected_bus['price'] * seats
        }

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bookings (bus_id, username, from_city, to_city, date, time, seats, price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (booking['bus_id'], booking['username'], booking['from_city'], booking['to_city'],
              booking['date'], booking['time'], booking['seats'], booking['price']))
        conn.commit()
        conn.close()

        selected_bus['available_seats'] -= seats
        flash('Booking successful')
        return redirect(url_for('view_booking_route'))
    
    return render_template('book.html', buses=buses)

# View bookings endpoint
@app.route('/view_booking', endpoint='view_booking_route')
@login_required
def view_booking():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bookings WHERE username = ?', (session['username'],))
    user_bookings = cursor.fetchall()
    conn.close()
    return render_template('view_booking.html', bookings=user_bookings)

# Cancel booking endpoint
@app.route('/cancel_booking', methods=['GET', 'POST'], endpoint='cancel_booking_route')
@login_required
def cancel_booking():
    if request.method == 'POST':
        bus_id = int(request.form['bus_id'])
        seats_to_cancel = int(request.form['seats'])

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM bookings WHERE bus_id = ? AND username = ?', (bus_id, session['username']))
        booking = cursor.fetchone()

        if not booking or seats_to_cancel > booking['seats']:
            flash('Cannot cancel more seats than booked or booking not found')
            conn.close()
            return redirect(url_for('cancel_booking_route'))

        new_seats = booking['seats'] - seats_to_cancel
        new_price = (booking['price'] / booking['seats']) * new_seats

        if new_seats == 0:
            cursor.execute('DELETE FROM bookings WHERE id = ?', (booking['id'],))
        else:
            cursor.execute('''
                UPDATE bookings SET seats = ?, price = ? WHERE id = ?
            ''', (new_seats, new_price, booking['id']))

        for bus in buses:
            if bus['bus_id'] == bus_id:
                bus['available_seats'] += seats_to_cancel
                break

        conn.commit()
        conn.close()

        flash('Booking cancelled successfully')
        return redirect(url_for('view_booking_route'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM bookings WHERE username = ?', (session['username'],))
    user_bookings = cursor.fetchall()
    conn.close()

    return render_template('cancel_booking.html', bookings=user_bookings)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
