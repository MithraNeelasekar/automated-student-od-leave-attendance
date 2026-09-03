"""
Authentication Routes for Student OD & Leave Management.
Provides role-based login, authentication tokens, session info, and profile resolution.
"""

from flask import Blueprint, request, jsonify, session
import secrets
from database import get_db_connection, hash_password

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Simple in-memory token store for token-based authorization headers
TOKEN_STORE = {}

def get_current_user(req):
    """Resolve user from Authorization header or session."""
    auth_header = req.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        user_info = TOKEN_STORE.get(token)
        if user_info:
            return user_info

    # Fallback to session
    user_id = session.get('user_id')
    if user_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, email, full_name, status FROM users WHERE id = ?", (user_id,))
        u = cursor.fetchone()
        conn.close()
        if u:
            return dict(u)
    return None

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    identifier = data.get('username', '').strip()
    password = data.get('password', '').strip()
    if not identifier or not password:
        return jsonify({'error': 'Username/email and password are required.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Find user by username or email
    pwd_hash = hash_password(password)
    cursor.execute("""
        SELECT id, username, role, email, full_name, status
        FROM users
        WHERE (username = ? OR email = ?) AND password_hash = ?
    """, (identifier, identifier, pwd_hash))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({'error': 'Invalid username/email or password.'}), 401

    user_dict = dict(user)

    if user_dict['status'] != 'ACTIVE':
        conn.close()
        return jsonify({'error': 'Your account has been deactivated. Please contact administrator.'}), 403

    # Fetch role-specific details
    profile = {}
    if user_dict['role'] == 'STUDENT':
        cursor.execute("""
            SELECT s.*, f.name as mentor_name, f.email as mentor_email
            FROM students s
            LEFT JOIN faculty f ON s.mentor_faculty_id = f.id
            WHERE s.user_id = ?
        """, (user_dict['id'],))
        st = cursor.fetchone()
        if st:
            profile = dict(st)
    elif user_dict['role'] == 'FACULTY':
        cursor.execute("SELECT * FROM faculty WHERE user_id = ?", (user_dict['id'],))
        fc = cursor.fetchone()
        if fc:
            profile = dict(fc)

    conn.close()

    # Generate token
    token = secrets.token_hex(24)
    user_data = {
        'id': user_dict['id'],
        'username': user_dict['username'],
        'role': user_dict['role'],
        'email': user_dict['email'],
        'full_name': user_dict['full_name'],
        'profile': profile
    }
    TOKEN_STORE[token] = user_data
    session['user_id'] = user_dict['id']

    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': user_data
    }), 200

@auth_bp.route('/me', methods=['GET'])
def me():
    current_user = get_current_user(request)
    if not current_user:
        return jsonify({'error': 'Unauthorized. Please log in.'}), 401
    return jsonify({'user': current_user}), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        TOKEN_STORE.pop(token, None)
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email:
        return jsonify({'error': 'Email is required.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, full_name FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'No account found with this email address.'}), 404

    # In this prototype, do not reveal or expose passwords. A production system
    # should send a time-limited reset link through the institution's email service.
    return jsonify({
        'message': 'If an active account exists for this email, password reset instructions will be sent through the registered institutional email.'
    }), 200
