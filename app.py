from flask import Flask, render_template, request, redirect, url_for,session
import mysql.connector

app = Flask(__name__)

import secrets

secret_key = secrets.token_hex(16)
print(secret_key)

app.secret_key = secret_key

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '*****', #change based on your database password
    'database': 'eventify'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/form_template.html', methods=['GET', 'POST'])
def create_event():
    if 'email' in session:
        if request.method == 'POST':
            try:
                connection = mysql.connector.connect(**db_config)
                cursor = connection.cursor()

                eventname = request.form['eventname']
                eventDate = request.form['eventDate']
                location = request.form['location']
                description = request.form['description']
                organizer = request.form['organizer']
                contactPhone = request.form['contactPhone']
                email = request.form['email']

                sql = """
                INSERT INTO Events (eventname, eventDate, location, description, organizer, contactPhone,email)
                VALUES (%s, %s, %s, %s, %s, %s,%s)
                """
                values = (eventname, eventDate, location, description, organizer, contactPhone,email)

                cursor.execute(sql, values)
                connection.commit()

                cursor.close()
                connection.close()

                return render_template('eventcreated.html')

            except mysql.connector.Error as e:
                print(f"Error: {e}")
                return 'Error creating event'
        
        return render_template('form_template.html')
    else:
        return render_template('login.html')
@app.route('/login.html', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()

            email = request.form['email']
            password = request.form['password']

            cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
            user = cursor.fetchone()

            if user:
                session['email'] = email
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Invalid email or password!')

        except mysql.connector.Error as e:
            print(f"Error: {e}")
            return render_template('login.html', error='Error logging in. Please try again.')

        finally:
            cursor.close()
            connection.close()

    return render_template('login.html')

@app.route('/signup.html', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()

            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirmPassword']

            if not email or not password or not confirm_password:
                return "All fields are required!", 400

            if password != confirm_password:
                return "Passwords do not match!", 400

            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            existing_user = cursor.fetchone()

            if existing_user:
                return "User already exists!", 400

            sql = 'INSERT INTO users (email, password) VALUES (%s, %s)'
            cursor.execute(sql, (email, password))
            connection.commit()

            cursor.close()
            connection.close()

            return 'User created successfully!'

        except mysql.connector.Error as e:
            print(f"Error: {e}")
            return 'Error creating user'

    return render_template('signup.html')
def get_db_connection():
    connection = mysql.connector.connect(**db_config)
    return connection

@app.route('/events.html')
def show_events():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM events WHERE eventDate>CURRENT_DATE")
    events = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('events.html', events=events)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'email' in session:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM events")
        events = cursor.fetchall()
        cursor.close()
        
        if request.method == 'POST':
            event_id = request.form['event_id']
            name = request.form['name']
            email = request.form['email']
            phone = request.form['phone']
            year = request.form.getlist('year')
            branch = request.form['branch']
            section = request.form['section']

            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO registrations (event_id, name, email, phone, year, branch, section)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (event_id, name, email, phone, ','.join(year), branch, section))
            connection.commit()
            
            registration_id = cursor.lastrowid
            

            
            cursor.close()
            connection.close()

            return redirect(url_for('confirmation', registration_id=registration_id, event_id=event_id))
        else:
            connection.close()
            return render_template('register_form.html', events=events)
    else:
        return render_template('login.html')

@app.route('/confirmation')
def confirmation():
    registration_id = request.args.get('registration_id')
    event_id = request.args.get('event_id')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT eventname FROM events WHERE eventId = %s", (event_id,))
    event = cursor.fetchone()
    cursor.close()
    connection.close()
    
    return render_template('confirmation.html', registration_id=registration_id, event=event)
def get_user_created_events(user_email):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM events WHERE email = %s", (user_email,))
    created_events = cursor.fetchall()
    cursor.close()
    connection.close()
    return created_events

def get_user_registered_events(user_email):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT events.* FROM events 
        INNER JOIN registrations ON events.eventId = registrations.event_id 
        WHERE registrations.email = %s
    """, (user_email,))
    registered_events = cursor.fetchall()
    cursor.close()
    connection.close()
    return registered_events
@app.route('/dashboard')
def dashboard():
    if 'email' in session:
        user_email = session['email']
        created_events = get_user_created_events(user_email)
        registered_events = get_user_registered_events(user_email)
        return render_template('dashboard.html', created_events=created_events, registered_events=registered_events,email=user_email)
    else:
        return redirect(url_for('login'))
    
def get_registrations(event_id):
    connection = get_db_connection()  
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM registrations WHERE event_id = %s", (event_id,))
    registrations = cursor.fetchall()
    cursor.close()
    connection.close()
    return registrations

@app.route('/registrations.html/<int:event_id>')
def registrations(event_id):
    registrations = get_registrations(event_id)
    return render_template('registrations.html', registrations=registrations,event_id=event_id)
@app.route('/registrationsfilter/<int:event_id>')
def registrationsfilter(event_id):
    query = "SELECT * FROM registrations WHERE event_id = %s"
    params = [event_id]

    if 'year' in request.args and request.args['year']:
        query += " AND year LIKE %s"
        params.append(f"%{request.args['year']}%")
    if 'branch' in request.args and request.args['branch']:
        query += " AND branch LIKE %s"
        params.append(f"%{request.args['branch']}%")
    if 'section' in request.args and request.args['section']:
        query += " AND section LIKE %s"
        params.append(f"%{request.args['section']}%")

    connection = get_db_connection()
    cur = connection.cursor(dictionary=True)
    cur.execute(query, params)
    registrations = cur.fetchall()
    cur.close()

    return render_template('registrations.html', registrations=registrations,event_id=event_id)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))
if __name__ == '__main__':
    app.run(debug=True)
