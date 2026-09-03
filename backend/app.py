"""
Flask Backend Application Server for:
Automated Student OD and Leave Approval with Attendance Integration
"""

import os
from flask import Flask, jsonify, send_from_directory, send_file
from flask_cors import CORS
from database import init_db

# Import blueprints
from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.faculty_routes import faculty_bp
from routes.admin_routes import admin_bp
from routes.attendance_routes import attendance_bp
from routes.notification_routes import notification_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')

def create_app():
    app = Flask(__name__, static_folder=FRONTEND_DIR)
    app.config['SECRET_KEY'] = 'od_leave_system_super_secret_jwt_key_2026'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

    # Enable CORS for all REST APIs
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Ensure uploads directory exists
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    # Initialize DB with demo data
    init_db(force_reseed=False)

    # Register API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(notification_bp)

    # Global Error Handlers (Clean, user-friendly responses without exposing internal stack traces)
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Bad Request', 'message': str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'error': 'Unauthorized', 'message': 'Authentication required.'}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'error': 'Forbidden', 'message': 'You do not have permission to perform this action.'}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not Found', 'message': 'The requested resource was not found.'}), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected error occurred. Please try again later.'}), 500

    # Static file serving for uploads
    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(UPLOADS_DIR, filename)

    # Static frontend delivery
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        if path != "" and os.path.exists(os.path.join(FRONTEND_DIR, path)):
            return send_from_directory(FRONTEND_DIR, path)
        else:
            index_path = os.path.join(FRONTEND_DIR, 'index.html')
            if os.path.exists(index_path):
                return send_file(index_path)
            return jsonify({'status': 'online', 'message': 'Student OD/Leave System API Backend is running.'})

    return app

if __name__ == '__main__':
    import sys
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    print("=" * 70)
    print("Student OD & Leave Approval with Attendance Integration")
    print(f"Server running locally at: http://127.0.0.1:{port}")
    print("=" * 70)
    app.run(host='0.0.0.0', port=port, debug=False)
