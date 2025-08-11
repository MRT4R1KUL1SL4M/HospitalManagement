# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import yaml

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database connection details from config.py are loaded here
app.config.from_pyfile('config.py')

# Initialize MySQL
mysql = MySQL(app)

# --- Helper Functions ---
def get_db_connection():
    return mysql.connection

def get_cursor():
    return mysql.connection.cursor()

# --- Main Page ---
@app.route('/')
def index():
    return render_template('index.html')

# --- User (Patient) Routes ---

@app.route('/user/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        full_name = request.form['full_name']
        
        cur = get_cursor()
        cur.execute("INSERT INTO users(username, password, email, full_name) VALUES(%s, %s, %s, %s)", (username, password, email, full_name))
        mysql.connection.commit()
        cur.close()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('user_login'))
    return render_template('user_register.html')

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = get_cursor()
        cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cur.fetchone()
        cur.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = 'user'
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
            
    return render_template('user_login.html')

@app.route('/user/dashboard')
def user_dashboard():
    if 'role' not in session or session['role'] != 'user':
        return redirect(url_for('user_login'))
    return render_template('user_dashboard.html')

@app.route('/user/doctors')
def browse_doctors():
    if 'role' not in session or session['role'] != 'user':
        return redirect(url_for('user_login'))
    cur = get_cursor()
    cur.execute("SELECT id, full_name, department, specialization FROM doctors WHERE status = 'Approved'")
    doctors = cur.fetchall()
    cur.close()
    return render_template('browse_doctors.html', doctors=doctors)

@app.route('/user/book_appointment/<int:doctor_id>', methods=['GET', 'POST'])
def book_appointment(doctor_id):
    if 'role' not in session or session['role'] != 'user':
        return redirect(url_for('user_login'))
    
    if request.method == 'POST':
        user_id = session['user_id']
        app_date = request.form['date']
        app_time = request.form['time']
        reason = request.form['reason']
        
        cur = get_cursor()
        cur.execute("INSERT INTO appointments(user_id, doctor_id, appointment_date, appointment_time, reason) VALUES(%s, %s, %s, %s, %s)", (user_id, doctor_id, app_date, app_time, reason))
        mysql.connection.commit()
        cur.close()
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('user_appointments'))
        
    cur = get_cursor()
    cur.execute("SELECT full_name FROM doctors WHERE id = %s", (doctor_id,))
    doctor_name = cur.fetchone()[0]
    cur.close()
    return render_template('book_appointment.html', doctor_id=doctor_id, doctor_name=doctor_name)

@app.route('/user/appointments')
def user_appointments():
    if 'role' not in session or session['role'] != 'user':
        return redirect(url_for('user_login'))
    
    user_id = session['user_id']
    cur = get_cursor()
    cur.execute("""
        SELECT a.id, d.full_name, a.appointment_date, a.appointment_time, a.status 
        FROM appointments a 
        JOIN doctors d ON a.doctor_id = d.id 
        WHERE a.user_id = %s
    """, (user_id,))
    appointments = cur.fetchall()
    cur.close()
    return render_template('user_appointments.html', appointments=appointments)

@app.route('/user/prescriptions')
def user_prescriptions():
    if 'role' not in session or session['role'] != 'user':
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    cur = get_cursor()
    cur.execute("""
        SELECT p.id, d.full_name, p.prescription_text, p.date_issued
        FROM prescriptions p
        JOIN doctors d ON p.doctor_id = d.id
        WHERE p.user_id = %s
    """, (user_id,))
    prescriptions = cur.fetchall()
    cur.close()
    return render_template('user_prescriptions.html', prescriptions=prescriptions)

# --- Doctor Routes ---

@app.route('/doctor/register', methods=['GET', 'POST'])
def doctor_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        email = request.form['email']
        department = request.form['department']
        specialization = request.form['specialization']

        cur = get_cursor()
        cur.execute("""
            INSERT INTO doctors(username, password, full_name, email, department, specialization) 
            VALUES(%s, %s, %s, %s, %s, %s)
        """, (username, password, full_name, email, department, specialization))
        mysql.connection.commit()
        cur.close()
        
        flash('Registration successful! Your application is under review.', 'success')
        return redirect(url_for('doctor_login'))
        
    return render_template('doctor_register.html')

@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = get_cursor()
        cur.execute("SELECT * FROM doctors WHERE username = %s AND password = %s AND status = 'Approved'", (username, password))
        doctor = cur.fetchone()
        cur.close()
        
        if doctor:
            session['doctor_id'] = doctor[0]
            session['username'] = doctor[1]
            session['role'] = 'doctor'
            return redirect(url_for('doctor_dashboard'))
        else:
            flash('Invalid credentials or your account is not approved yet.', 'danger')
    return render_template('doctor_login.html')

@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('doctor_login'))
    return render_template('doctor_dashboard.html')

@app.route('/doctor/appointments')
def doctor_appointments():
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('doctor_login'))

    doctor_id = session['doctor_id']
    cur = get_cursor()
    cur.execute("""
        SELECT a.id, u.full_name, a.appointment_date, a.appointment_time, a.status, u.id
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        WHERE a.doctor_id = %s
    """, (doctor_id,))
    appointments = cur.fetchall()
    cur.close()
    return render_template('doctor_appointments.html', appointments=appointments)

@app.route('/doctor/patient/<int:user_id>')
def view_patient(user_id):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('doctor_login'))

    cur = get_cursor()
    cur.execute("SELECT full_name, email, phone_number, address FROM users WHERE id = %s", (user_id,))
    patient = cur.fetchone()
    cur.execute("""
        SELECT a.appointment_date, a.reason, p.prescription_text
        FROM appointments a
        LEFT JOIN prescriptions p ON a.id = p.appointment_id
        WHERE a.user_id = %s AND a.doctor_id = %s
        ORDER BY a.appointment_date DESC
    """, (user_id, session['doctor_id']))
    history = cur.fetchall()
    cur.close()
    return render_template('view_patient.html', patient=patient, history=history)


@app.route('/doctor/write_prescription/<int:appointment_id>', methods=['GET', 'POST'])
def write_prescription(appointment_id):
    if 'role' not in session or session['role'] != 'doctor':
        return redirect(url_for('doctor_login'))

    if request.method == 'POST':
        prescription_text = request.form['prescription']
        
        cur = get_cursor()
        cur.execute("SELECT user_id FROM appointments WHERE id = %s", (appointment_id,))
        result = cur.fetchone()
        if not result:
            flash('Appointment not found!', 'danger')
            return redirect(url_for('doctor_appointments'))
        
        user_id = result[0]
        doctor_id = session['doctor_id']

        cur.execute("INSERT INTO prescriptions(appointment_id, user_id, doctor_id, prescription_text) VALUES(%s, %s, %s, %s)", 
                    (appointment_id, user_id, doctor_id, prescription_text))
        cur.execute("UPDATE appointments SET status = 'Completed' WHERE id = %s", (appointment_id,))
        mysql.connection.commit()
        cur.close()

        flash('Prescription saved successfully!', 'success')
        return redirect(url_for('doctor_appointments'))

    return render_template('write_prescription.html', appointment_id=appointment_id)

# --- Admin Routes ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = get_cursor()
        cur.execute("SELECT * FROM admins WHERE username = %s AND password = %s", (username, password))
        admin = cur.fetchone()
        cur.close()
        
        if admin:
            session['admin_id'] = admin[0]
            session['username'] = admin[1]
            session['role'] = 'admin'
            session['is_super_admin'] = admin[4]
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
            
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    
    cur = get_cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM doctors")
    total_doctors = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cur.fetchone()[0]
    cur.close()
    
    stats = {
        'total_users': total_users,
        'total_doctors': total_doctors,
        'total_appointments': total_appointments
    }
    return render_template('admin_dashboard.html', stats=stats)

@app.route('/admin/doctors', methods=['GET', 'POST'])
def manage_doctors():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        email = request.form['email']
        department = request.form['department']
        specialization = request.form['specialization']

        cur = get_cursor()
        cur.execute("""
            INSERT INTO doctors(username, password, full_name, email, department, specialization, status) 
            VALUES(%s, %s, %s, %s, %s, %s, 'Approved')
        """, (username, password, full_name, email, department, specialization))
        mysql.connection.commit()
        cur.close()
        flash('Doctor added successfully!', 'success')
        return redirect(url_for('manage_doctors'))

    cur = get_cursor()
    cur.execute("SELECT * FROM doctors")
    doctors = cur.fetchall()
    cur.close()
    return render_template('manage_doctors.html', doctors=doctors)

@app.route('/admin/doctors/delete/<int:doctor_id>')
def delete_doctor(doctor_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    
    cur = get_cursor()
    cur.execute("DELETE FROM doctors WHERE id = %s", (doctor_id,))
    mysql.connection.commit()
    cur.close()
    flash('Doctor removed successfully!', 'success')
    return redirect(url_for('manage_doctors'))

@app.route('/admin/approve_doctors')
def approve_doctors():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    
    cur = get_cursor()
    cur.execute("SELECT * FROM doctors WHERE status = 'Pending'")
    pending_doctors = cur.fetchall()
    cur.close()
    
    return render_template('admin_approve_doctors.html', pending_doctors=pending_doctors)

@app.route('/admin/handle_doctor_approval/<int:doctor_id>')
def handle_doctor_approval(doctor_id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    
    action = request.args.get('action')
    
    cur = get_cursor()
    if action == 'approve':
        cur.execute("UPDATE doctors SET status = 'Approved' WHERE id = %s", (doctor_id,))
        flash('Doctor approved successfully!', 'success')
    elif action == 'reject':
        cur.execute("DELETE FROM doctors WHERE id = %s", (doctor_id,))
        flash('Doctor application rejected.', 'warning')
        
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('approve_doctors'))

@app.route('/admin/users')
def manage_users():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))
    
    cur = get_cursor()
    cur.execute("SELECT id, username, email, full_name, created_at FROM users")
    users = cur.fetchall()
    cur.close()
    return render_template('manage_users.html', users=users)

@app.route('/admin/appointments')
def monitor_appointments():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('admin_login'))

    cur = get_cursor()
    cur.execute("""
        SELECT a.id, u.full_name, d.full_name, a.appointment_date, a.appointment_time, a.status
        FROM appointments a
        JOIN users u ON a.user_id = u.id
        JOIN doctors d ON a.doctor_id = d.id
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    """)
    appointments = cur.fetchall()
    cur.close()
    return render_template('monitor_appointments.html', appointments=appointments)

@app.route('/admin/admins', methods=['GET', 'POST'])
def manage_admins():
    if 'role' not in session or session['role'] != 'admin' or not session.get('is_super_admin'):
        flash('You do not have permission to manage admins.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        email = request.form['email']
        
        cur = get_cursor()
        cur.execute("INSERT INTO admins(username, password, full_name, email) VALUES(%s, %s, %s, %s)",
                    (username, password, full_name, email))
        mysql.connection.commit()
        cur.close()
        flash('Admin added successfully!', 'success')
        return redirect(url_for('manage_admins'))
        
    cur = get_cursor()
    cur.execute("SELECT id, username, full_name, email FROM admins WHERE id != %s", (session['admin_id'],))
    admins = cur.fetchall()
    cur.close()
    return render_template('manage_admins.html', admins=admins)


# --- Logout ---
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)