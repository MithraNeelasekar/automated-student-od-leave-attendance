"""
Admin & HOD Routes for Student OD & Leave Approval System.
Handles executive dashboard, request management with filters, student/faculty CRUD,
and reporting analytics with CSV export.
"""

from flask import Blueprint, request, jsonify, Response
import io
import csv
from database import get_db_connection, hash_password
from routes.auth_routes import get_current_user
from services.approval_service import hod_process_request, get_request_details_with_timeline

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

def require_admin(req):
    user = get_current_user(req)
    if not user or user.get('role') != 'HOD_ADMIN':
        return None
    return user

@admin_bp.route('/dashboard', methods=['GET'])
def get_admin_dashboard():
    user = require_admin(request)
    if not user:
        return jsonify({'error': 'Unauthorized. Admin/HOD privileges required.'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM faculty")
    total_faculty = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM subjects")
    total_subjects = cursor.fetchone()[0]

    cursor.execute("""
        SELECT 
            SUM(CASE WHEN status IN ('PENDING_FACULTY', 'PENDING_HOD') THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN status = 'PENDING_FACULTY' THEN 1 ELSE 0 END) as pending_faculty,
            SUM(CASE WHEN status = 'PENDING_HOD' THEN 1 ELSE 0 END) as pending_hod,
            SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) as approved_count,
            SUM(CASE WHEN status IN ('REJECTED_FACULTY', 'REJECTED_HOD') THEN 1 ELSE 0 END) as rejected_count,
            SUM(CASE WHEN request_type = 'OD' THEN 1 ELSE 0 END) as total_od,
            SUM(CASE WHEN request_type = 'LEAVE' THEN 1 ELSE 0 END) as total_leave,
            COUNT(id) as total_requests
        FROM requests
    """)
    req_stats = cursor.fetchone()

    # Department Average Attendance
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN status IN ('PRESENT', 'ON_DUTY') THEN 1 ELSE 0 END) as present_count,
            COUNT(*) as total_count
        FROM attendance
    """)
    att_stats = cursor.fetchone()
    present_cnt = att_stats['present_count'] or 0
    total_cnt = att_stats['total_count'] or 0
    avg_attendance = round((present_cnt / total_cnt * 100), 1) if total_cnt > 0 else 100.0

    conn.close()

    return jsonify({
        'total_students': total_students,
        'total_faculty': total_faculty,
        'total_subjects': total_subjects,
        'pending_requests': req_stats['pending_count'] or 0,
        'pending_faculty': req_stats['pending_faculty'] or 0,
        'pending_hod': req_stats['pending_hod'] or 0,
        'approved_requests': req_stats['approved_count'] or 0,
        'rejected_requests': req_stats['rejected_count'] or 0,
        'total_od': req_stats['total_od'] or 0,
        'total_leave': req_stats['total_leave'] or 0,
        'total_requests': req_stats['total_requests'] or 0,
        'average_attendance': avg_attendance
    }), 200

@admin_bp.route('/requests', methods=['GET'])
def get_all_requests():
    user = require_admin(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT r.*, s.name as student_name, s.register_number, s.department, s.year, s.section,
               s.email as student_email, s.phone as student_phone,
               f.name as mentor_name,
               (SELECT remarks FROM approvals WHERE request_id = r.id AND approver_role = 'FACULTY' ORDER BY id DESC LIMIT 1) as faculty_remarks,
               (SELECT remarks FROM approvals WHERE request_id = r.id AND approver_role = 'HOD_ADMIN' ORDER BY id DESC LIMIT 1) as hod_remarks
        FROM requests r
        JOIN students s ON r.student_id = s.id
        LEFT JOIN faculty f ON s.mentor_faculty_id = f.id
        WHERE 1=1
    """
    params = []

    # Dynamic query filters
    dept = request.args.get('department')
    if dept:
        query += " AND s.department = ?"
        params.append(dept)

    year = request.args.get('year')
    if year:
        query += " AND s.year = ?"
        params.append(year)

    sec = request.args.get('section')
    if sec:
        query += " AND s.section = ?"
        params.append(sec)

    req_type = request.args.get('request_type')
    if req_type:
        query += " AND r.request_type = ?"
        params.append(req_type)

    status = request.args.get('status')
    if status:
        query += " AND r.status = ?"
        params.append(status)

    search = request.args.get('search')
    if search:
        query += " AND (s.name LIKE ? OR s.register_number LIKE ? OR r.request_code LIKE ? OR r.event_name LIKE ?)"
        s_pattern = f"%{search}%"
        params.extend([s_pattern, s_pattern, s_pattern, s_pattern])

    query += " ORDER BY r.created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return jsonify({'requests': [dict(r) for r in rows]}), 200

@admin_bp.route('/requests/<int:request_id>/approve', methods=['PUT'])
def approve_request(request_id):
    user = require_admin(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    remarks = data.get('remarks', 'Approved by HOD. Attendance integration applied.')

    try:
        result = hod_process_request(
            request_id=request_id,
            hod_user_id=user['id'],
            action='APPROVE',
            remarks=remarks
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f"Failed to approve request: {str(e)}"}), 500

@admin_bp.route('/requests/<int:request_id>/reject', methods=['PUT'])
def reject_request(request_id):
    user = require_admin(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    remarks = data.get('remarks', '').strip()

    if not remarks:
        return jsonify({'error': 'Remarks are mandatory when rejecting a request.'}), 400

    try:
        result = hod_process_request(
            request_id=request_id,
            hod_user_id=user['id'],
            action='REJECT',
            remarks=remarks
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f"Failed to reject request: {str(e)}"}), 500

# ==================== STUDENT MANAGEMENT CRUD ====================

@admin_bp.route('/students', methods=['GET'])
def get_students():
    user = require_admin(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, u.username, u.status as account_status,
               f.name as mentor_name,
               (SELECT COUNT(*) FROM attendance a WHERE a.student_id = s.id AND a.status IN ('PRESENT', 'ON_DUTY')) as effective_present,
               (SELECT COUNT(*) FROM attendance a WHERE a.student_id = s.id) as total_classes
        FROM students s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN faculty f ON s.mentor_faculty_id = f.id
        ORDER BY s.register_number ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    students = []
    for r in rows:
        d = dict(r)
        present = d.pop('effective_present', 0) or 0
        total = d.pop('total_classes', 0) or 0
        d['attendance_percentage'] = round((present / total * 100), 1) if total > 0 else 100.0
        students.append(d)

    return jsonify({'students': students}), 200

@admin_bp.route('/students', methods=['POST'])
def add_student():
    user = require_admin(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    regno = data.get('register_number', '').strip().upper()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    dept = data.get('department', 'CSE').strip()
    year = int(data.get('year', 3))
    section = data.get('section', 'A').strip().upper()
    phone = data.get('phone', '').strip()
    mentor_id = data.get('mentor_faculty_id')
    username = data.get('username') or regno.lower()
    password = data.get('password') or 'password123'

    if not regno or not name or not email:
        return jsonify({'error': 'Register number, Name, and Email are required.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Create user account
        pwd_hash = hash_password(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, email, full_name, status)
            VALUES (?, ?, 'STUDENT', ?, ?, 'ACTIVE')
        """, (username, pwd_hash, email, name))
        u_id = cursor.lastrowid

        # Create student profile
        cursor.execute("""
            INSERT INTO students (user_id, register_number, name, department, year, section, email, phone, mentor_faculty_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (u_id, regno, name, dept, year, section, email, phone, mentor_id))
        st_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return jsonify({'message': f'Student {name} ({regno}) created successfully.', 'id': st_id}), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Failed to create student: {str(e)}'}), 400

@admin_bp.route('/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    user = require_admin(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    name = data.get('name')
    dept = data.get('department')
    year = data.get('year')
    section = data.get('section')
    email = data.get('email')
    phone = data.get('phone')
    mentor_id = data.get('mentor_faculty_id')
    status = data.get('status', 'ACTIVE')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM students WHERE id = ?", (student_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Student not found'}), 404
    u_id = row['user_id']

    cursor.execute("""
        UPDATE students
        SET name = COALESCE(?, name),
            department = COALESCE(?, department),
            year = COALESCE(?, year),
            section = COALESCE(?, section),
            email = COALESCE(?, email),
            phone = COALESCE(?, phone),
            mentor_faculty_id = ?
        WHERE id = ?
    """, (name, dept, year, section, email, phone, mentor_id, student_id))

    cursor.execute("""
        UPDATE users
        SET full_name = COALESCE(?, full_name),
            email = COALESCE(?, email),
            status = COALESCE(?, status)
        WHERE id = ?
    """, (name, email, status, u_id))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Student updated successfully.'}), 200

@admin_bp.route('/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    user = require_admin(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id, name, register_number FROM students WHERE id = ?", (student_id,))
    st = cursor.fetchone()
    if not st:
        conn.close()
        return jsonify({'error': 'Student not found'}), 404

    cursor.execute("DELETE FROM users WHERE id = ?", (st['user_id'],))
    conn.commit()
    conn.close()

    return jsonify({'message': f"Student {st['name']} ({st['register_number']}) deleted."}), 200

# ==================== FACULTY MANAGEMENT CRUD ====================

@admin_bp.route('/faculty', methods=['GET'])
def get_faculty_list():
    user = require_admin(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.*, u.username, u.status as account_status,
               (SELECT COUNT(*) FROM students s WHERE s.mentor_faculty_id = f.id) as mentored_students_count,
               (SELECT COUNT(*) FROM subjects sub WHERE sub.faculty_id = f.id) as assigned_subjects_count
        FROM faculty f
        JOIN users u ON f.user_id = u.id
        ORDER BY f.name ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    return jsonify({'faculty': [dict(r) for r in rows]}), 200

@admin_bp.route('/faculty', methods=['POST'])
def add_faculty():
    user = require_admin(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    fac_code = data.get('faculty_id', '').strip().upper()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    dept = data.get('department', 'CSE').strip()
    desig = data.get('designation', 'Assistant Professor').strip()
    phone = data.get('phone', '').strip()
    username = data.get('username') or fac_code.lower()
    password = data.get('password') or 'password123'

    if not fac_code or not name or not email:
        return jsonify({'error': 'Faculty ID, Name, and Email are required.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        pwd_hash = hash_password(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, email, full_name, status)
            VALUES (?, ?, 'FACULTY', ?, ?, 'ACTIVE')
        """, (username, pwd_hash, email, name))
        u_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO faculty (user_id, faculty_id, name, department, designation, email, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (u_id, fac_code, name, dept, desig, email, phone))
        f_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return jsonify({'message': f'Faculty {name} ({fac_code}) created successfully.', 'id': f_id}), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Failed to create faculty: {str(e)}'}), 400

@admin_bp.route('/faculty/<int:faculty_id>', methods=['PUT'])
def update_faculty(faculty_id):
    user = require_admin(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    name = data.get('name')
    dept = data.get('department')
    desig = data.get('designation')
    email = data.get('email')
    phone = data.get('phone')
    status = data.get('status', 'ACTIVE')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM faculty WHERE id = ?", (faculty_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Faculty member not found'}), 404
    u_id = row['user_id']

    cursor.execute("""
        UPDATE faculty
        SET name = COALESCE(?, name),
            department = COALESCE(?, department),
            designation = COALESCE(?, designation),
            email = COALESCE(?, email),
            phone = COALESCE(?, phone)
        WHERE id = ?
    """, (name, dept, desig, email, phone, faculty_id))

    cursor.execute("""
        UPDATE users
        SET full_name = COALESCE(?, full_name),
            email = COALESCE(?, email),
            status = COALESCE(?, status)
        WHERE id = ?
    """, (name, email, status, u_id))

    conn.commit()
    conn.close()

    return jsonify({'message': 'Faculty updated successfully.'}), 200

@admin_bp.route('/faculty/<int:faculty_id>', methods=['DELETE'])
def delete_faculty(faculty_id):
    user = require_admin(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id, name, faculty_id FROM faculty WHERE id = ?", (faculty_id,))
    f = cursor.fetchone()
    if not f:
        conn.close()
        return jsonify({'error': 'Faculty member not found'}), 404

    cursor.execute("DELETE FROM users WHERE id = ?", (f['user_id'],))
    conn.commit()
    conn.close()

    return jsonify({'message': f"Faculty {f['name']} deleted."}), 200

# ==================== SUBJECTS & REPORTS ====================

@admin_bp.route('/subjects', methods=['GET'])
def get_subjects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, f.name as faculty_name
        FROM subjects s
        LEFT JOIN faculty f ON s.faculty_id = f.id
        ORDER BY s.subject_code ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify({'subjects': [dict(r) for r in rows]}), 200

@admin_bp.route('/reports', methods=['GET'])
def generate_reports():
    user = require_admin(request)
    if not user:
        return jsonify({'error': 'Unauthorized'}), 403

    report_type = request.args.get('type', 'requests')  # requests | attendance | student_summary
    dept = request.args.get('department')
    year = request.args.get('year')
    status = request.args.get('status')
    export_csv = request.args.get('export', 'false').lower() == 'true'

    conn = get_db_connection()
    cursor = conn.cursor()

    if report_type == 'attendance':
        query = """
            SELECT s.register_number, s.name as student_name, s.department, s.year, s.section,
                   sub.subject_code, sub.subject_name,
                   COUNT(a.id) as total_classes,
                   SUM(CASE WHEN a.status = 'PRESENT' THEN 1 ELSE 0 END) as present_count,
                   SUM(CASE WHEN a.status = 'ON_DUTY' THEN 1 ELSE 0 END) as od_count,
                   SUM(CASE WHEN a.status = 'ABSENT' THEN 1 ELSE 0 END) as absent_count
            FROM students s
            CROSS JOIN subjects sub ON s.department = sub.department AND s.year = sub.year
            LEFT JOIN attendance a ON s.id = a.student_id AND sub.id = a.subject_id
            WHERE 1=1
        """
        params = []
        if dept:
            query += " AND s.department = ?"
            params.append(dept)
        if year:
            query += " AND s.year = ?"
            params.append(year)
        query += " GROUP BY s.id, sub.id ORDER BY s.register_number, sub.subject_code"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        records = []
        for r in rows:
            d = dict(r)
            effective = (d['present_count'] or 0) + (d['od_count'] or 0)
            total = d['total_classes'] or 0
            d['effective_percentage'] = round((effective / total * 100), 1) if total > 0 else 100.0
            records.append(d)

        if export_csv:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                'register_number', 'student_name', 'department', 'year', 'section',
                'subject_code', 'subject_name', 'total_classes', 'present_count', 'od_count', 'absent_count', 'effective_percentage'
            ])
            writer.writeheader()
            writer.writerows(records)
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={"Content-disposition": "attachment; filename=attendance_report.csv"}
            )
        return jsonify({'report_type': 'attendance', 'data': records}), 200

    else:
        # Default: Requests Report
        query = """
            SELECT r.request_code, r.request_type, r.start_date, r.end_date, r.status,
                   r.event_name, r.event_type, r.leave_type, r.reason, r.attendance_updated,
                   s.register_number, s.name as student_name, s.department, s.year, s.section,
                   r.created_at
            FROM requests r
            JOIN students s ON r.student_id = s.id
            WHERE 1=1
        """
        params = []
        if dept:
            query += " AND s.department = ?"
            params.append(dept)
        if year:
            query += " AND s.year = ?"
            params.append(year)
        if status:
            query += " AND r.status = ?"
            params.append(status)
        query += " ORDER BY r.created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        records = [dict(r) for r in rows]

        if export_csv:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                'request_code', 'register_number', 'student_name', 'department', 'year', 'section',
                'request_type', 'start_date', 'end_date', 'status', 'event_name', 'event_type', 'leave_type', 'reason', 'attendance_updated', 'created_at'
            ])
            writer.writeheader()
            writer.writerows(records)
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={"Content-disposition": "attachment; filename=od_leave_report.csv"}
            )
        return jsonify({'report_type': 'requests', 'data': records}), 200
