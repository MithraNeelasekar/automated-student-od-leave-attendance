"""
Attendance Direct Routes for Student OD & Leave Approval System.
"""

from flask import Blueprint, request, jsonify
from database import get_db_connection
from routes.auth_routes import get_current_user
from services.attendance_service import get_student_attendance_summary, get_student_attendance_history

attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/attendance')

@attendance_bp.route('/student/<int:student_id>', methods=['GET'])
def get_attendance(student_id):
    current_user = get_current_user(request)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    summary = get_student_attendance_summary(student_id)
    if not summary:
        return jsonify({'error': 'Student not found'}), 404

    return jsonify(summary), 200

@attendance_bp.route('/update', methods=['POST'])
def manual_update_attendance():
    """Manual single attendance record update by Faculty or Admin with validation."""
    current_user = get_current_user(request)
    if not current_user or current_user['role'] not in ('FACULTY', 'HOD_ADMIN'):
        return jsonify({'error': 'Unauthorized. Only faculty/admin can update attendance.'}), 403

    data = request.get_json() or {}
    student_id = data.get('student_id')
    subject_id = data.get('subject_id')
    att_date = data.get('attendance_date')
    status = data.get('status', '').upper()

    if not student_id or not subject_id or not att_date or not status:
        return jsonify({'error': 'student_id, subject_id, attendance_date, and status are required.'}), 400

    if status not in ('PRESENT', 'ABSENT', 'ON_DUTY'):
        return jsonify({'error': "Status must be 'PRESENT', 'ABSENT', or 'ON_DUTY'."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO attendance (student_id, subject_id, attendance_date, status, source)
        VALUES (?, ?, ?, ?, 'REGULAR')
        ON CONFLICT(student_id, subject_id, attendance_date)
        DO UPDATE SET status = excluded.status, source = 'REGULAR', request_id = NULL
    """, (student_id, subject_id, att_date, status))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Attendance record updated successfully.'}), 200
