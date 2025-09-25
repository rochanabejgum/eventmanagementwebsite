from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import secrets

app = Flask(__name__)

secret_key = secrets.token_hex(16)
app.secret_key = secret_key

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '******',
    'database': 'eventify'
}

def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/form_template.html', methods=['GET', 'POST'])
def create_event():
    if 'email' in session:
        if request.method == 'POST':
            connection = get_db_connection()
            if connection is None:
                return 'Error connecting to database', 500
            
            cursor = connection.cursor()

            try:
                eventname = request.form['eventname']
                eventDate = request.form['eventDate']
                location = request.form['location']
                description = request.form['description']
                organizer = session['email']
                contactPhone = request.form['contactPhone']

                sql = """
                INSERT INTO events (eventname, eventDate, location, description, organizer, contactPhone)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                values = (eventname, eventDate, location, description, organizer, contactPhone)

                cursor.execute(sql, values)
                connection.commit()

                return render_template('eventcreated.html')

            except mysql.connector.Error as e:
                print(f"Error: {e}")
                return 'Error creating event', 500
            finally:
                cursor.close()
                connection.close()
        
        return render_template('form_template.html')
    else:
        return redirect(url_for('login'))

@app.route('/login.html', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        connection = get_db_connection()
        if connection is None:
            return render_template('login.html', error='Database connection error.')
        
        cursor = connection.cursor()
        
        try:
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
        connection = get_db_connection()
        if connection is None:
            return 'Error connecting to database', 500

        cursor = connection.cursor()
        
        try:
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

            return 'User created successfully!'
        except mysql.connector.Error as e:
            print(f"Error: {e}")
            return 'Error creating user', 500
        finally:
            cursor.close()
            connection.close()

    return render_template('signup.html')

@app.route('/events.html')
def show_events():
    connection = get_db_connection()
    if connection is None:
        return 'Error connecting to database', 500
    
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM events WHERE eventDate > CURRENT_DATE")
        events = cursor.fetchall()
        return render_template('events.html', events=events)
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return 'Error fetching events', 500
    finally:
        cursor.close()
        connection.close()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'email' in session:
        connection = get_db_connection()
        if connection is None:
            return 'Error connecting to database', 500
            
        cursor = connection.cursor(dictionary=True)
        
        try:
            cursor.execute("SELECT * FROM events")
            events = cursor.fetchall()
        except mysql.connector.Error as e:
            print(f"Error: {e}")
            connection.close()
            return 'Error fetching events', 500
        
        if request.method == 'POST':
            try:
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
                
                return redirect(url_for('confirmation', registration_id=registration_id, event_id=event_id))
            except mysql.connector.Error as e:
                print(f"Error: {e}")
                return 'Error during registration', 500
            finally:
                cursor.close()
                connection.close()
        else:
            connection.close()
            return render_template('register_form.html', events=events)
    else:
        return redirect(url_for('login'))

@app.route('/confirmation')
def confirmation():
    registration_id = request.args.get('registration_id')
    event_id = request.args.get('event_id')

    connection = get_db_connection()
    if connection is None:
        return 'Error connecting to database', 500

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT eventname FROM events WHERE eventId = %s", (event_id,))
        event = cursor.fetchone()
        return render_template('confirmation.html', registration_id=registration_id, event=event)
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return 'Error fetching confirmation details', 500
    finally:
        cursor.close()
        connection.close()

def get_user_created_events(user_email):
    connection = get_db_connection()
    if connection is None:
        return []
    
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM events WHERE organizer = %s", (user_email,))
        created_events = cursor.fetchall()
        return created_events
    except mysql.connector.Error as e:
        print(f"Error fetching user-created events: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

def get_user_registered_events(user_email):
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT events.* FROM events 
            INNER JOIN registrations ON events.eventId = registrations.event_id 
            WHERE registrations.email = %s
        """, (user_email,))
        registered_events = cursor.fetchall()
        return registered_events
    except mysql.connector.Error as e:
        print(f"Error fetching user-registered events: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

@app.route('/dashboard')
def dashboard():
    if 'email' in session:
        user_email = session['email']
        created_events = get_user_created_events(user_email)
        registered_events = get_user_registered_events(user_email)
        return render_template('dashboard.html', created_events=created_events, registered_events=registered_events, email=user_email)
    else:
        return redirect(url_for('login'))
    
def get_registrations(event_id):
    connection = get_db_connection()
    if connection is None:
        return []

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM registrations WHERE event_id = %s", (event_id,))
        registrations = cursor.fetchall()
        return registrations
    except mysql.connector.Error as e:
        print(f"Error fetching registrations: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

@app.route('/registrations.html/<int:event_id>')
def registrations_page(event_id):
    registrations = get_registrations(event_id)
    return render_template('registrations.html', registrations=registrations, event_id=event_id)

@app.route('/registrationsfilter/<int:event_id>')
def registrations_filter(event_id):
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
    if connection is None:
        return 'Error connecting to database', 500

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        registrations = cursor.fetchall()
        return render_template('registrations.html', registrations=registrations, event_id=event_id)
    except mysql.connector.Error as e:
        print(f"Error during filtered search: {e}")
        return 'Error fetching filtered data', 500
    finally:
        cursor.close()
        connection.close()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)