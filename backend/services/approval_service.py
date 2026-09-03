"""
Approval workflow service for Student OD and Leave Management.
Coordinates state transitions, audit logging, notifications, and attendance integration.
"""

from datetime import datetime, date
from database import get_db_connection
from services.attendance_service import integrate_approved_od_attendance
from services.notification_service import create_notification

def generate_request_code(request_type: str) -> str:
    """Generate sequential unique code like OD-2026-004 or LV-2026-003."""
    prefix = "OD" if request_type == 'OD' else "LV"
    year = datetime.now().year
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM requests 
        WHERE request_type = ? AND strftime('%Y', created_at) = ?
    """, (request_type, str(year)))
    count = cursor.fetchone()[0] + 1
    conn.close()
    return f"{prefix}-{year}-{count:03d}"

def submit_request(student_id: int, user_id: int, data: dict, doc_name: str = None, doc_path: str = None) -> dict:
    """
    Validate and submit a new OD or Leave request by a student.
    Enforces business rules:
      - Valid date format and end_date >= start_date
      - Duplicate prevention for overlapping active requests
      - Initial status: PENDING_FACULTY
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    req_type = data.get('request_type', '').upper()
    if req_type not in ('OD', 'LEAVE'):
        conn.close()
        raise ValueError("Invalid request type. Must be 'OD' or 'LEAVE'.")

    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date') or start_date_str
    reason = data.get('reason', '').strip()

    if not start_date_str or not reason:
        conn.close()
        raise ValueError("Start date and reason are required fields.")

    try:
        s_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        e_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        conn.close()
        raise ValueError("Dates must be in YYYY-MM-DD format.")

    if e_date < s_date:
        conn.close()
        raise ValueError("End date cannot be earlier than start date.")

    # Check for duplicate overlapping active requests for this student
    cursor.execute("""
        SELECT request_code, start_date, end_date, status
        FROM requests
        WHERE student_id = ? 
          AND status IN ('PENDING_FACULTY', 'PENDING_HOD', 'APPROVED')
          AND NOT (end_date < ? OR start_date > ?)
    """, (student_id, start_date_str, end_date_str))
    conflict = cursor.fetchone()
    if conflict:
        conn.close()
        raise ValueError(f"Overlapping request {conflict['request_code']} ({conflict['status']}) already exists for dates {conflict['start_date']} to {conflict['end_date']}.")

    # Fetch student and mentor faculty info
    cursor.execute("""
        SELECT s.name, s.register_number, s.mentor_faculty_id, f.user_id as mentor_user_id, f.name as mentor_name
        FROM students s
        LEFT JOIN faculty f ON s.mentor_faculty_id = f.id
        WHERE s.id = ?
    """, (student_id,))
    student_info = cursor.fetchone()
    if not student_info:
        conn.close()
        raise ValueError("Student profile not found.")

    req_code = generate_request_code(req_type)

    event_name = data.get('event_name', '')
    event_type = data.get('event_type', '')
    venue = data.get('venue', '')
    leave_type = data.get('leave_type', '')
    student_remarks = data.get('remarks', '')

    cursor.execute("""
        INSERT INTO requests (
            request_code, student_id, request_type, start_date, end_date,
            event_name, event_type, venue, leave_type, reason,
            document_name, document_path, status, attendance_updated, student_remarks
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, 'PENDING_FACULTY', 0, ?
        )
    """, (
        req_code, student_id, req_type, start_date_str, end_date_str,
        event_name, event_type, venue, leave_type, reason,
        doc_name, doc_path, student_remarks
    ))
    request_id = cursor.lastrowid

    # Create initial submission approval entry
    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks)
        VALUES (?, ?, 'STUDENT', 'SUBMITTED', 'Request submitted by student')
    """, (request_id, user_id))

    conn.commit()
    conn.close()

    # Create notifications
    create_notification(
        user_id=user_id,
        title=f"{req_type} Request Submitted",
        message=f"Your {req_type} request {req_code} has been successfully submitted and is pending faculty review.",
        link=req_code
    )

    if student_info['mentor_user_id']:
        create_notification(
            user_id=student_info['mentor_user_id'],
            title=f"New {req_type} Request from {student_info['name']}",
            message=f"Student {student_info['name']} ({student_info['register_number']}) submitted request {req_code} for your review.",
            link=req_code
        )

    return {
        'id': request_id,
        'request_code': req_code,
        'status': 'PENDING_FACULTY',
        'message': f"{req_type} request {req_code} submitted successfully."
    }

def faculty_process_request(request_id: int, faculty_user_id: int, action: str, remarks: str) -> dict:
    """
    Faculty approves or rejects a pending request.
    - APPROVE: Transitions to PENDING_HOD, forwards to HOD.
    - REJECT: Requires remarks, transitions to REJECTED_FACULTY, halts workflow.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT role, status FROM users WHERE id = ?", (faculty_user_id,))
    actor = cursor.fetchone()
    if not actor or actor['role'] != 'FACULTY' or actor['status'] != 'ACTIVE':
        conn.close()
        raise ValueError('Only an active faculty account can process faculty approvals.')

    cursor.execute("""
        SELECT r.id, r.request_code, r.request_type, r.status, r.student_id,
               s.user_id as student_user_id, s.name as student_name, s.register_number,
               u.full_name as faculty_name
        FROM requests r
        JOIN students s ON r.student_id = s.id
        LEFT JOIN users u ON u.id = ?
        WHERE r.id = ?
    """, (faculty_user_id, request_id))
    req = cursor.fetchone()

    if not req:
        conn.close()
        raise ValueError("Request not found.")

    cursor.execute("""
        SELECT 1 FROM students s
        JOIN faculty f ON s.mentor_faculty_id = f.id
        WHERE s.id = ? AND f.user_id = ?
    """, (req['student_id'], faculty_user_id))
    if not cursor.fetchone():
        conn.close()
        raise ValueError('This faculty member is not assigned to the student request.')

    if req['status'] != 'PENDING_FACULTY':
        conn.close()
        raise ValueError(f"Request {req['request_code']} is in status '{req['status']}', cannot be processed by faculty.")

    action = action.upper()
    if action not in ('APPROVE', 'REJECT'):
        conn.close()
        raise ValueError("Action must be 'APPROVE' or 'REJECT'.")

    if action == 'REJECT' and not (remarks and remarks.strip()):
        conn.close()
        raise ValueError("Remarks are mandatory when rejecting a request.")

    new_status = 'PENDING_HOD' if action == 'APPROVE' else 'REJECTED_FACULTY'
    approval_action = 'FACULTY_APPROVED' if action == 'APPROVE' else 'FACULTY_REJECTED'

    cursor.execute("""
        UPDATE requests 
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_status, request_id))

    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks)
        VALUES (?, ?, 'FACULTY', ?, ?)
    """, (request_id, faculty_user_id, approval_action, remarks or 'Approved and forwarded to HOD'))

    # Fetch HOD user ID for forwarding notification if approved
    cursor.execute("SELECT id FROM users WHERE role = 'HOD_ADMIN' LIMIT 1")
    hod_row = cursor.fetchone()
    hod_user_id = hod_row['id'] if hod_row else None

    conn.commit()
    conn.close()

    faculty_name = req['faculty_name'] or 'Faculty'

    # Notify student
    if action == 'APPROVE':
        create_notification(
            user_id=req['student_user_id'],
            title=f"Request {req['request_code']} Approved by Faculty",
            message=f"Your {req['request_type']} request {req['request_code']} was approved by {faculty_name} and forwarded to HOD for final approval.",
            link=req['request_code']
        )
        if hod_user_id:
            create_notification(
                user_id=hod_user_id,
                title=f"OD/Leave Request Forwarded by Faculty",
                message=f"Faculty {faculty_name} approved request {req['request_code']} ({req['student_name']}) and forwarded it for your final sanction.",
                link=req['request_code']
            )
    else:
        create_notification(
            user_id=req['student_user_id'],
            title=f"Request {req['request_code']} Rejected by Faculty",
            message=f"Your {req['request_type']} request {req['request_code']} was rejected by {faculty_name}. Remarks: {remarks}",
            link=req['request_code']
        )

    return {
        'id': request_id,
        'request_code': req['request_code'],
        'status': new_status,
        'action': approval_action,
        'message': f"Request {req['request_code']} successfully {'forwarded to HOD' if action == 'APPROVE' else 'rejected'}."
    }

def hod_process_request(request_id: int, hod_user_id: int, action: str, remarks: str) -> dict:
    """
    HOD / Admin grants final approval or rejects.
    - APPROVE:
      * Sets status to APPROVED
      * Automatically runs Attendance Integration Engine for OD requests
      * Dispatches notifications
    - REJECT:
      * Requires remarks
      * Sets status to REJECTED_HOD
      * Stops workflow and notifies student
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT role, status FROM users WHERE id = ?", (hod_user_id,))
    actor = cursor.fetchone()
    if not actor or actor['role'] != 'HOD_ADMIN' or actor['status'] != 'ACTIVE':
        conn.close()
        raise ValueError('Only an active HOD/Admin account can process final approvals.')

    cursor.execute("""
        SELECT r.id, r.request_code, r.request_type, r.status, r.student_id, r.attendance_updated,
               s.user_id as student_user_id, s.name as student_name, s.register_number,
               u.full_name as hod_name
        FROM requests r
        JOIN students s ON r.student_id = s.id
        LEFT JOIN users u ON u.id = ?
        WHERE r.id = ?
    """, (hod_user_id, request_id))
    req = cursor.fetchone()

    if not req:
        conn.close()
        raise ValueError("Request not found.")

    if req['status'] != 'PENDING_HOD':
        conn.close()
        raise ValueError(f"Request {req['request_code']} is in status '{req['status']}', cannot be processed for final approval.")

    action = action.upper()
    if action not in ('APPROVE', 'REJECT'):
        conn.close()
        raise ValueError("Action must be 'APPROVE' or 'REJECT'.")

    if action == 'REJECT' and not (remarks and remarks.strip()):
        conn.close()
        raise ValueError("Remarks are mandatory when rejecting a request.")

    new_status = 'APPROVED' if action == 'APPROVE' else 'REJECTED_HOD'
    approval_action = 'HOD_APPROVED' if action == 'APPROVE' else 'HOD_REJECTED'

    cursor.execute("""
        UPDATE requests 
        SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_status, request_id))

    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks)
        VALUES (?, ?, 'HOD_ADMIN', ?, ?)
    """, (request_id, hod_user_id, approval_action, remarks or 'Final approval granted by HOD/Admin'))

    conn.commit()
    conn.close()

    integration_result = None
    # If approved and OD, trigger attendance integration
    if action == 'APPROVE' and req['request_type'] == 'OD':
        integration_result = integrate_approved_od_attendance(request_id, hod_user_id)

    # Notify student
    if action == 'APPROVE':
        if req['request_type'] == 'OD' and integration_result and integration_result.get('records_updated', 0) > 0:
            notif_msg = f"Your OD request {req['request_code']} received final approval from HOD. {integration_result['records_updated']} subject attendance periods have been credited as On-Duty."
        else:
            notif_msg = f"Your {req['request_type']} request {req['request_code']} received final approval from HOD."

        create_notification(
            user_id=req['student_user_id'],
            title=f"{req['request_type']} Request Approved by HOD",
            message=notif_msg,
            link=req['request_code']
        )
    else:
        create_notification(
            user_id=req['student_user_id'],
            title=f"{req['request_type']} Request Rejected by HOD",
            message=f"Your {req['request_type']} request {req['request_code']} was rejected by HOD. Remarks: {remarks}",
            link=req['request_code']
        )

    return {
        'id': request_id,
        'request_code': req['request_code'],
        'status': new_status,
        'action': approval_action,
        'integration': integration_result,
        'message': f"Request {req['request_code']} successfully {'approved' if action == 'APPROVE' else 'rejected'} by HOD."
    }

def get_request_details_with_timeline(request_id: int):
    """Retrieve complete request details along with student info and full approval audit trail."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.*, s.name as student_name, s.register_number, s.department, s.year, s.section,
               s.email as student_email, s.phone as student_phone,
               f.name as mentor_name
        FROM requests r
        JOIN students s ON r.student_id = s.id
        LEFT JOIN faculty f ON s.mentor_faculty_id = f.id
        WHERE r.id = ?
    """, (request_id,))
    req = cursor.fetchone()

    if not req:
        conn.close()
        return None

    # Fetch approval timeline
    cursor.execute("""
        SELECT a.id, a.action, a.approver_role, a.remarks, a.action_date,
               u.full_name as approver_name, u.username as approver_username
        FROM approvals a
        LEFT JOIN users u ON a.approver_id = u.id
        WHERE a.request_id = ?
        ORDER BY a.action_date ASC, a.id ASC
    """, (request_id,))
    approvals = cursor.fetchall()

    conn.close()

    return {
        'request': dict(req),
        'timeline': [dict(a) for a in approvals]
    }
