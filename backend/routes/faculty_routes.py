"""
Faculty Routes for Student OD & Leave Approval System.
Handles faculty dashboard analytics, assigned student requests review, and approve/reject actions.
"""

from flask import Blueprint, request, jsonify
from database import get_db_connection
from routes.auth_routes import get_current_user
from services.approval_service import faculty_process_request, get_request_details_with_timeline
from services.attendance_service import get_student_attendance_summary

faculty_bp = Blueprint('faculty', __name__, url_prefix='/api/faculty')

def resolve_faculty_id(current_user):
    """Get the faculty table ID corresponding to the authenticated user."""
    if current_user.get('role') != 'FACULTY':
        return None
    profile = current_user.get('profile', {})
    if profile.get('id'):
        return profile['id']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM faculty WHERE user_id = ?", (current_user['id'],))
    row = cursor.fetchone()
    conn.close()
    return row['id'] if row else None

@faculty_bp.route('/dashboard', methods=['GET'])
def get_faculty_dashboard():
    current_user = get_current_user(request)
    if not current_user or current_user['role'] != 'FACULTY':
        return jsonify({'error': 'Unauthorized'}), 403

    fac_id = resolve_faculty_id(current_user)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query metrics for faculty's mentored / department students
    if fac_id:
        cursor.execute("SELECT COUNT(*) FROM students WHERE mentor_faculty_id = ?", (fac_id,))
        total_students = cursor.fetchone()[0]

        cursor.execute("""
            SELECT 
                SUM(CASE WHEN r.status = 'PENDING_FACULTY' AND r.request_type = 'OD' THEN 1 ELSE 0 END) as pending_od,
                SUM(CASE WHEN r.status = 'PENDING_FACULTY' AND r.request_type = 'LEAVE' THEN 1 ELSE 0 END) as pending_leave,
                SUM(CASE WHEN r.status = 'APPROVED' THEN 1 ELSE 0 END) as approved_count,
                SUM(CASE WHEN r.status IN ('REJECTED_FACULTY', 'REJECTED_HOD') THEN 1 ELSE 0 END) as rejected_count,
                COUNT(r.id) as total_requests
            FROM requests r
            JOIN students s ON r.student_id = s.id
            WHERE s.mentor_faculty_id = ?
        """, (fac_id,))
        stats = cursor.fetchone()
    else:
        conn.close()
        return jsonify({'error': 'Faculty profile is not associated with this account.'}), 403

    conn.close()

    return jsonify({
        'total_students': total_students,
        'pending_od': stats['pending_od'] or 0,
        'pending_leave': stats['pending_leave'] or 0,
        'total_pending': (stats['pending_od'] or 0) + (stats['pending_leave'] or 0),
        'approved_requests': stats['approved_count'] or 0,
        'rejected_requests': stats['rejected_count'] or 0,
        'total_requests': stats['total_requests'] or 0
    }), 200

@faculty_bp.route('/requests/pending', methods=['GET'])
def get_pending_requests():
    current_user = get_current_user(request)
    if not current_user or current_user['role'] != 'FACULTY':
        return jsonify({'error': 'Unauthorized'}), 403

    fac_id = resolve_faculty_id(current_user)
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT r.*, s.name as student_name, s.register_number, s.department, s.year, s.section,
               s.email as student_email, s.phone as student_phone,
               (SELECT COUNT(*) FROM attendance a WHERE a.student_id = s.id AND a.status IN ('PRESENT', 'ON_DUTY')) as attended_classes,
               (SELECT COUNT(*) FROM attendance a WHERE a.student_id = s.id) as total_marked_classes
        FROM requests r
        JOIN students s ON r.student_id = s.id
        WHERE r.status = 'PENDING_FACULTY'
    """
    params = []
    if fac_id:
        query += " AND (s.mentor_faculty_id = ? OR s.department = (SELECT department FROM faculty WHERE id = ?))"
        params.extend([fac_id, fac_id])

    query += " ORDER BY r.created_at ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        r_dict = dict(r)
        attended = r_dict.pop('attended_classes', 0) or 0
        total = r_dict.pop('total_marked_classes', 0) or 0
        r_dict['student_attendance_percentage'] = round((attended / total * 100), 1) if total > 0 else 100.0
        results.append(r_dict)

    return jsonify({'requests': results}), 200

@faculty_bp.route('/requests/all', methods=['GET'])
def get_all_faculty_requests():
    current_user = get_current_user(request)
    if not current_user or current_user['role'] != 'FACULTY':
        return jsonify({'error': 'Unauthorized'}), 403

    fac_id = resolve_faculty_id(current_user)
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT r.*, s.name as student_name, s.register_number, s.department, s.year, s.section
        FROM requests r
        JOIN students s ON r.student_id = s.id
    """
    params = []
    if fac_id:
        query += " WHERE s.mentor_faculty_id = ? OR s.department = (SELECT department FROM faculty WHERE id = ?)"
        params.extend([fac_id, fac_id])

    query += " ORDER BY r.created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return jsonify({'requests': [dict(r) for r in rows]}), 200

@faculty_bp.route('/requests/<int:request_id>/approve', methods=['PUT'])
def approve_request(request_id):
    current_user = get_current_user(request)
    if not current_user or current_user['role'] != 'FACULTY':
        return jsonify({'error': 'Unauthorized. Only faculty can approve.'}), 403

    data = request.get_json() or {}
    remarks = data.get('remarks', 'Recommended and forwarded to HOD.')

    # Verify that this faculty member is assigned to the request's student.
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM requests r
        JOIN students s ON r.student_id = s.id
        JOIN faculty f ON s.mentor_faculty_id = f.id
        WHERE r.id = ? AND f.user_id = ?
    """, (request_id, current_user['id']))
    assigned = cursor.fetchone()
    conn.close()
    if not assigned:
        return jsonify({'error': 'Forbidden. You are not the assigned faculty for this student.'}), 403

    try:
        result = faculty_process_request(
            request_id=request_id,
            faculty_user_id=current_user['id'],
            action='APPROVE',
            remarks=remarks
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f"Failed to approve request: {str(e)}"}), 500

@faculty_bp.route('/requests/<int:request_id>/reject', methods=['PUT'])
def reject_request(request_id):
    current_user = get_current_user(request)
    if not current_user or current_user['role'] != 'FACULTY':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    remarks = data.get('remarks', '').strip()

    if not remarks:
        return jsonify({'error': 'Remarks are mandatory when rejecting a request.'}), 400

    # Verify that this faculty member is assigned to the request's student.
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM requests r
        JOIN students s ON r.student_id = s.id
        JOIN faculty f ON s.mentor_faculty_id = f.id
        WHERE r.id = ? AND f.user_id = ?
    """, (request_id, current_user['id']))
    assigned = cursor.fetchone()
    conn.close()
    if not assigned:
        return jsonify({'error': 'Forbidden. You are not the assigned faculty for this student.'}), 403

    try:
        result = faculty_process_request(
            request_id=request_id,
            faculty_user_id=current_user['id'],
            action='REJECT',
            remarks=remarks
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f"Failed to reject request: {str(e)}"}), 500
