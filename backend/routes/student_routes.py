"""
Student Routes for Student OD & Leave Approval System.
"""

from flask import Blueprint, request, jsonify, current_app
import os
import uuid
from database import get_db_connection
from routes.auth_routes import get_current_user
from services.approval_service import submit_request, get_request_details_with_timeline
from services.attendance_service import get_student_attendance_summary, get_student_attendance_history

student_bp = Blueprint('students', __name__, url_prefix='/api')

def resolve_student_id(current_user):
    """Get the student table ID corresponding to the authenticated user."""
    if current_user.get('role') != 'STUDENT':
        return None
    profile = current_user.get('profile', {})
    if profile.get('id'):
        return profile['id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM students WHERE user_id = ?", (current_user['id'],))
    row = cursor.fetchone()
    conn.close()
    return row['id'] if row else None

@student_bp.route('/students/<int:student_id>', methods=['GET'])
def get_student_profile(student_id):
    current_user = get_current_user(request)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    # Authorization guard: Student can only view their own profile, unless faculty or admin
    if current_user['role'] == 'STUDENT':
        own_id = resolve_student_id(current_user)
        if own_id != student_id:
            return jsonify({'error': 'Access denied. You can only view your own profile.'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, u.username, u.email as user_email, u.status as user_status,
               f.name as mentor_name, f.email as mentor_email, f.phone as mentor_phone
        FROM students s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN faculty f ON s.mentor_faculty_id = f.id
        WHERE s.id = ?
    """, (student_id,))
    student = cursor.fetchone()
    conn.close()

    if not student:
        return jsonify({'error': 'Student not found'}), 404

    return jsonify({'student': dict(student)}), 200

@student_bp.route('/students/<int:student_id>/attendance', methods=['GET'])
def get_student_attendance(student_id):
    current_user = get_current_user(request)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    if current_user['role'] == 'STUDENT':
        own_id = resolve_student_id(current_user)
        if own_id != student_id:
            return jsonify({'error': 'Access denied'}), 403

    summary = get_student_attendance_summary(student_id)
    if not summary:
        return jsonify({'error': 'Student not found'}), 404

    return jsonify(summary), 200

@student_bp.route('/students/<int:student_id>/history', methods=['GET'])
def get_student_history(student_id):
    current_user = get_current_user(request)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    if current_user['role'] == 'STUDENT':
        own_id = resolve_student_id(current_user)
        if own_id != student_id:
            return jsonify({'error': 'Access denied'}), 403

    subject_id = request.args.get('subject_id', type=int)
    history = get_student_attendance_history(student_id, subject_id)
    return jsonify({'history': history}), 200

@student_bp.route('/requests', methods=['POST'])
def create_request():
    current_user = get_current_user(request)
    if not current_user or current_user['role'] != 'STUDENT':
        return jsonify({'error': 'Only logged-in students can submit requests.'}), 403

    student_id = resolve_student_id(current_user)
    if not student_id:
        return jsonify({'error': 'Student profile not associated with this account.'}), 400

    # Handle both multipart/form-data and JSON
    doc_name = None
    doc_path = None
    data = {}

    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
        if 'document' in request.files:
            file = request.files['document']
            if file and file.filename:
                ext = os.path.splitext(file.filename)[1].lower()
                allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx']
                if ext not in allowed_extensions:
                    return jsonify({'error': f'Invalid file format. Allowed: {", ".join(allowed_extensions)}'}), 400

                doc_name = file.filename
                unique_filename = f"{uuid.uuid4().hex[:10]}_{doc_name}"
                upload_dir = os.path.join(current_app.root_path, 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                full_path = os.path.join(upload_dir, unique_filename)
                file.save(full_path)
                doc_path = f"/uploads/{unique_filename}"

    try:
        result = submit_request(
            student_id=student_id,
            user_id=current_user['id'],
            data=data,
            doc_name=doc_name or data.get('document_name', 'supporting_document.pdf'),
            doc_path=doc_path or data.get('document_path', '/uploads/sample_cert.pdf')
        )
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@student_bp.route('/requests/my', methods=['GET'])
def get_my_requests():
    current_user = get_current_user(request)
    if not current_user or current_user['role'] != 'STUDENT':
        return jsonify({'error': 'Unauthorized'}), 403

    student_id = resolve_student_id(current_user)
    if not student_id:
        return jsonify({'error': 'Student profile not found'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*,
               (SELECT remarks FROM approvals WHERE request_id = r.id AND approver_role = 'FACULTY' ORDER BY id DESC LIMIT 1) as faculty_remarks,
               (SELECT remarks FROM approvals WHERE request_id = r.id AND approver_role = 'HOD_ADMIN' ORDER BY id DESC LIMIT 1) as hod_remarks
        FROM requests r
        WHERE r.student_id = ?
        ORDER BY r.created_at DESC
    """, (student_id,))
    rows = cursor.fetchall()
    conn.close()

    # Format response with counts
    requests_list = [dict(row) for row in rows]
    pending_count = sum(1 for r in requests_list if r['status'] in ('PENDING_FACULTY', 'PENDING_HOD'))
    approved_count = sum(1 for r in requests_list if r['status'] == 'APPROVED')
    rejected_count = sum(1 for r in requests_list if r['status'] in ('REJECTED_FACULTY', 'REJECTED_HOD'))

    return jsonify({
        'requests': requests_list,
        'stats': {
            'total': len(requests_list),
            'pending': pending_count,
            'approved': approved_count,
            'rejected': rejected_count
        }
    }), 200

@student_bp.route('/requests/<int:request_id>', methods=['GET'])
def get_request_by_id(request_id):
    current_user = get_current_user(request)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    details = get_request_details_with_timeline(request_id)
    if not details:
        return jsonify({'error': 'Request not found'}), 404

    # Security check: if student, ensure it's their request
    if current_user['role'] == 'STUDENT':
        own_id = resolve_student_id(current_user)
        if details['request']['student_id'] != own_id:
            return jsonify({'error': 'Access denied'}), 403

    return jsonify(details), 200
