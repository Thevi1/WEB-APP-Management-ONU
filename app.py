from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import random
import math
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import pooling, Error
from dotenv import load_dotenv


app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Ganti dengan secret key yang aman
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
    minutes=int(os.environ.get('SESSION_LIFETIME_MINUTES', '30'))
)

# Konfigurasi MySQL dari environment variable (beri default agar mudah dicoba)
load_dotenv()
app.config['MYSQL_HOST'] = os.environ.get('DB_HOST')
app.config['MYSQL_USER'] = os.environ.get('DB_USER')
app.config['MYSQL_PASSWORD'] = os.environ.get('DB_PASSWORD')
app.config['MYSQL_DB'] = os.environ.get('DB_NAME')

# Timeout tidak-aktif (idle) dalam menit
SESSION_INACTIVITY_TIMEOUT_MINUTES = int(
    os.environ.get('SESSION_INACTIVITY_MINUTES', '15')
)

# Inisialisasi pool koneksi MySQL
db_config = {
    'host': app.config['MYSQL_HOST'],
    'user': app.config['MYSQL_USER'],
    'password': app.config['MYSQL_PASSWORD'],
    'database': app.config['MYSQL_DB'],
}

try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name='app_pool', pool_size=5, pool_reset_session=True, **db_config
    )
except Error as e:
    connection_pool = None
    print(f"Gagal inisialisasi pool DB: {e}")

def get_db_connection():
    if connection_pool is None:
        raise RuntimeError("Database connection pool tidak terinisialisasi")
    return connection_pool.get_connection()

def init_db():
    """Buat tabel users jika belum ada"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        conn.commit()
    except Exception as e:
        print(f"init_db error: {e}")
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

# # Data dummy untuk testing
# dummy_users = [
#     {'email': 'admin@example.com', 'password': 'admin123', 'name': 'Admin Superadmin'},
#     {'email': 'user@example.com', 'password': 'user123', 'name': 'Regular User'}
# ]

def generate_sample_devices():
    """Generate sample ONU devices data"""
    devices = []
    for i in range(500):
        device = {
            'id': i + 1,
            'serial_number': f"98:13:{random.randint(10,99)}:{random.randint(10,99)}:{random.randint(10,99)}:{random.randint(10,99)}",
            'mac_address': f"98:13:{random.randint(10,99)}:{random.randint(10,99)}:{random.randint(10,99)}:{random.randint(10,99)}",
            'status': random.choice(['ONLINE', 'OFFLINE']),
            'distance': f"0.{random.randint(100,900)}",
            'temperature': random.choice(['Low', 'Warning', 'Normal']),
            'rx_power': random.choice(['Lemah', 'Tinggi', 'Normal']),
            'tx_power': f"{random.randint(1,3)}.00",
            'rtt': random.randint(100, 600),
            'online_time': f"{random.randint(1,30)} {random.choice(['s', 'm', 'h'])}",
            'offline_time': f"-{random.randint(100,300)} {random.choice(['s', 'm', 'h'])}",
        'alarms': 'Normal',
            'vendor_model': 'Huawei/GT01',
        'pon_port': '-',
            'ip_address': f"192.168.100.{random.randint(0,254)}",
            'deregister': random.randint(0, 2),
            'map': '-',
            'abd': '-'
        }
        devices.append(device)
    return devices

# Data dummy untuk dashboard
onu_data = generate_sample_devices()

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.before_request
def enforce_session_policy():
    """Set sesi menjadi permanent dan cek idle-timeout."""
    session.permanent = True
    now = datetime.now(timezone.utc)
    last_activity_iso = session.get('last_activity')

    if last_activity_iso is not None:
        try:
            last_activity = datetime.fromisoformat(last_activity_iso)
        except Exception:
            last_activity = None

        # Normalisasi: jika value lama tanpa tzinfo (naive), anggap UTC
        if last_activity and last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)

        if last_activity and (now - last_activity).total_seconds() > (
            SESSION_INACTIVITY_TIMEOUT_MINUTES * 60
        ):
            session.clear()
            flash('Sesi berakhir karena tidak ada aktivitas. Silakan login kembali.', 'info')
            return redirect(url_for('login'))

    session['last_activity'] = now.isoformat()

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT id, name, email, password_hash FROM users WHERE email=%s LIMIT 1",
                (email,),
            )
            row = cursor.fetchone()
            if row and check_password_hash(row['password_hash'], password):
                session['user'] = {
                    'id': row['id'],
                    'email': row['email'],
                    'name': row['name'],
                }
                session['last_activity'] = datetime.now(timezone.utc).isoformat()
                flash('Login berhasil!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Email atau password salah!', 'error')
        except Exception as e:
            flash(f'Kesalahan server: {e}', 'error')
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Basic validation
        if password != confirm_password:
            flash('Password tidak cocok!', 'error')
            return render_template('signup.html')
        
        # Check if terms are accepted
        terms = request.form.get('terms')
        if not terms:
            flash('Anda harus menyetujui Terms and Conditions!', 'error')
            return render_template('signup.html')
        
        # Simpan user ke database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Cek apakah email sudah ada
            cursor.execute("SELECT 1 FROM users WHERE email=%s LIMIT 1", (email,))
            exists = cursor.fetchone()
            if exists:
                flash('Email sudah terdaftar!', 'error')
                return render_template('signup.html')

            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, password_hash),
            )
            conn.commit()

            flash('Registrasi berhasil! Silakan login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Kesalahan server: {e}', 'error')
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass
    
    return render_template('signup.html')
    
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Silakan login terlebih dahulu!', 'error')
        return redirect(url_for('login'))
    
    # Calculate totals
    total_olt = 5
    total_odc = 12
    total_odp = 48
    total_onu = len(onu_data)

    # Pagination params
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    try:
        per_page = int(request.args.get('per_page', 10))
    except ValueError:
        per_page = 10

    per_page = max(1, min(per_page, 100))  # batas aman
    total_pages = max(1, math.ceil(total_onu / per_page))
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    onus_page = onu_data[start:end]

    start_index = 0 if total_onu == 0 else start + 1
    end_index = 0 if total_onu == 0 else min(end, total_onu)
    has_prev = page > 1
    has_next = page < total_pages
    prev_page = page - 1 if has_prev else None
    next_page = page + 1 if has_next else None

    return render_template(
        'dashboard.html',
        onus=onus_page,
        total_olt=total_olt,
        total_odc=total_odc,
        total_odp=total_odp,
        total_onu=total_onu,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        start_index=start_index,
        end_index=end_index,
        has_prev=has_prev,
        has_next=has_next,
        prev_page=prev_page,
        next_page=next_page,
    )

@app.route('/device_management')
def device_management():
    if 'user' not in session:
        flash('Silakan login terlebih dahulu!', 'error')
        return redirect(url_for('login'))
    
    # Calculate totals
    total_olt = 5
    total_odc = 12
    total_odp = 48
    total_onu = len(onu_data)
    
    return render_template('device_management.html', 
        onus=onu_data,
        total_olt=total_olt,
        total_odc=total_odc,
        total_odp=total_odp,
        total_onu=total_onu)

@app.route('/billing_invoice')
def billing_invoice():
    if 'user' not in session:
        flash('Silakan login terlebih dahulu!', 'error')
        return redirect(url_for('login'))
    
    return render_template('billing_invoice.html')

@app.route('/voucher')
def voucher():
    if 'user' not in session:
        flash('Silakan login terlebih dahulu!', 'error')
        return redirect(url_for('login'))
    
    return render_template('voucher.html')

@app.route('/topologi')
def topologi():
    if 'user' not in session:
        flash('Silakan login terlebih dahulu!', 'error')
        return redirect(url_for('login'))
    
    return render_template('topologi.html')
    

@app.route('/setting')
def setting():
    if 'user' not in session:
        flash('Silakan login terlebih dahulu!', 'error')
        return redirect(url_for('login'))
    
    return render_template('setting.html')

@app.route('/profile')
def profile():
    if 'user' not in session:
        flash('Silakan login terlebih dahulu!', 'error')
        return redirect(url_for('login'))
    
    return render_template('profile.html')

@app.route('/logout-confirm')
def logout_confirm():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('logout.html')

@app.route('/logout')
def logout():
    # Clear all session data
    session.clear()
    flash('Anda telah berhasil logout!', 'info')
    return redirect(url_for('login'))

@app.route('/api/onus')
def api_onus():
    return {'onus': onu_data}

@app.route('/clear-flash')
def clear_flash():
    """Clear flash messages"""
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Inisialisasi DB pada startup
    try:
        init_db()
    except Exception as e:
        print(f"Lewati init_db karena error: {e}")

    app.run(debug=True)