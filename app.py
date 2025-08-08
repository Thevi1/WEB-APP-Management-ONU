from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Ganti dengan secret key yang aman

# Data dummy untuk testing
dummy_users = [
    {'email': 'admin@example.com', 'password': 'admin123', 'name': 'Admin Superadmin'},
    {'email': 'user@example.com', 'password': 'user123', 'name': 'Regular User'}
]

def generate_sample_devices():
    """Generate sample ONU devices data"""
    devices = []
    for i in range(100):
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
        
        # Check credentials
        user = next((user for user in dummy_users if user['email'] == email and user['password'] == password), None)
        
        if user:
            session['user'] = user
            flash('Login berhasil!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email atau password salah!', 'error')
    
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
        
        # Check if email already exists
        if any(user['email'] == email for user in dummy_users):
            flash('Email sudah terdaftar!', 'error')
            return render_template('signup.html')
        
        # Check if terms are accepted
        terms = request.form.get('terms')
        if not terms:
            flash('Anda harus menyetujui Terms and Conditions!', 'error')
            return render_template('signup.html')
        
        # Add new user (in real app, save to database)
        new_user = {'email': email, 'password': password, 'name': name}
        dummy_users.append(new_user)
        
        flash('Registrasi berhasil! Silakan login.', 'success')
        return redirect(url_for('login'))
    
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
    
    return render_template('dashboard.html', 
        onus=onu_data,
        total_olt=total_olt,
        total_odc=total_odc,
        total_odp=total_odp,
        total_onu=total_onu)

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
    app.run(debug=True)