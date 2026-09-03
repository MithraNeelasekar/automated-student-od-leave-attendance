"""
Attendance Integration Service.
Handles automatic attendance updates on approved OD requests, ensures idempotency,
and provides subject-wise & overall attendance analytics.
"""

from datetime import datetime, date, timedelta
from database import get_db_connection

def get_student_attendance_summary(student_id: int):
    """
    Compute comprehensive subject-wise and overall attendance metrics for a student.
    Formula:
      Attended Count = Classes with status 'PRESENT'
      OD Count       = Classes with status 'ON_DUTY'
      Absent Count   = Classes with status 'ABSENT'
      Total Tracked  = Attended + OD + Absent
      Effective Present = Attended + OD
      Attendance %   = (Effective Present / Total Tracked) * 100
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get student info
    cursor.execute("""
        SELECT s.id, s.register_number, s.name, s.department, s.year, s.section, s.user_id,
               f.name as mentor_name
        FROM students s
        LEFT JOIN faculty f ON s.mentor_faculty_id = f.id
        WHERE s.id = ?
    """, (student_id,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        return None

    # Get all subjects for this student's department and year
    cursor.execute("""
        SELECT sub.id, sub.subject_code, sub.subject_name, sub.department, sub.year, sub.semester,
               sub.total_classes, f.name as faculty_name
        FROM subjects sub
        LEFT JOIN faculty f ON sub.faculty_id = f.id
        WHERE sub.department = ? AND sub.year = ?
        ORDER BY sub.subject_code
    """, (student['department'], student['year']))
    subjects = cursor.fetchall()

    subject_summaries = []
    total_conducted = 0
    total_attended = 0
    total_od = 0
    total_absent = 0

    for sub in subjects:
        sub_id = sub['id']
        cursor.execute("""
            SELECT 
                COUNT(*) as total_classes_marked,
                SUM(CASE WHEN status = 'PRESENT' THEN 1 ELSE 0 END) as present_count,
                SUM(CASE WHEN status = 'ON_DUTY' THEN 1 ELSE 0 END) as od_count,
                SUM(CASE WHEN status = 'ABSENT' THEN 1 ELSE 0 END) as absent_count
            FROM attendance
            WHERE student_id = ? AND subject_id = ?
        """, (student_id, sub_id))
        att_row = cursor.fetchone()

        marked_classes = att_row['total_classes_marked'] or 0
        present_cnt = att_row['present_count'] or 0
        od_cnt = att_row['od_count'] or 0
        absent_cnt = att_row['absent_count'] or 0

        effective_present = present_cnt + od_cnt
        percentage = round((effective_present / marked_classes * 100), 1) if marked_classes > 0 else 100.0

        # Progress bar color logic
        if percentage >= 75.0:
            status_color = "success"
            status_label = "Good"
        elif percentage >= 65.0:
            status_color = "warning"
            status_label = "Warning (< 75%)"
        else:
            status_color = "danger"
            status_label = "Critical Defaulter"

        subject_summaries.append({
            'subject_id': sub_id,
            'subject_code': sub['subject_code'],
            'subject_name': sub['subject_name'],
            'faculty_name': sub['faculty_name'] or 'Not Assigned',
            'total_conducted': marked_classes,
            'classes_attended': present_cnt,
            'approved_od': od_cnt,
            'classes_absent': absent_cnt,
            'effective_present': effective_present,
            'attendance_percentage': percentage,
            'status_color': status_color,
            'status_label': status_label
        })

        total_conducted += marked_classes
        total_attended += present_cnt
        total_od += od_cnt
        total_absent += absent_cnt

    overall_effective = total_attended + total_od
    overall_percentage = round((overall_effective / total_conducted * 100), 1) if total_conducted > 0 else 100.0

    conn.close()

    return {
        'student': dict(student),
        'overall': {
            'total_conducted': total_conducted,
            'total_attended': total_attended,
            'approved_od': total_od,
            'total_absent': total_absent,
            'effective_present': overall_effective,
            'percentage': overall_percentage,
            'status_color': "success" if overall_percentage >= 75.0 else ("warning" if overall_percentage >= 65.0 else "danger"),
            'is_eligible': overall_percentage >= 75.0
        },
        'subjects': subject_summaries
    }

def get_student_attendance_history(student_id: int, subject_id: int = None, limit: int = 50):
    """Retrieve detailed per-day attendance logs for audit and student tracking."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT a.id, a.attendance_date, a.status, a.source, a.request_id,
               sub.subject_code, sub.subject_name,
               r.request_code, r.event_name, r.request_type
        FROM attendance a
        JOIN subjects sub ON a.subject_id = sub.id
        LEFT JOIN requests r ON a.request_id = r.id
        WHERE a.student_id = ?
    """
    params = [student_id]

    if subject_id:
        query += " AND a.subject_id = ?"
        params.append(subject_id)

    query += " ORDER BY a.attendance_date DESC, sub.subject_code ASC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def integrate_approved_od_attendance(request_id: int, approver_user_id: int) -> dict:
    """
    Core Attendance Integration Engine.
    Triggered when HOD/Admin gives final approval to an OD request.

    Guarantees:
    1. STRICT IDEMPOTENCY: If request.attendance_updated == 1, reject duplicate run.
    2. Identifies all weekdays in [start_date, end_date].
    3. Finds all enrolled subjects for the student's department & year.
    4. Upserts attendance records: sets status = 'ON_DUTY', source = 'OD_INTEGRATION', request_id = request_id.
    5. Sets requests.attendance_updated = 1.
    6. Logs audit trail and returns number of updated class periods.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Fetch request details with student info
    cursor.execute("""
        SELECT r.id, r.request_code, r.student_id, r.request_type, r.start_date, r.end_date,
               r.status, r.attendance_updated, r.event_name,
               s.department, s.year, s.user_id as student_user_id, s.name as student_name
        FROM requests r
        JOIN students s ON r.student_id = s.id
        WHERE r.id = ?
    """, (request_id,))
    req = cursor.fetchone()

    if not req:
        conn.close()
        raise ValueError("Request not found.")

    if req['request_type'] != 'OD':
        conn.close()
        return {'success': True, 'message': 'Leave requests do not alter attendance directly.', 'records_updated': 0}

    if req['attendance_updated'] == 1:
        conn.close()
        return {
            'success': False,
            'message': f"Idempotency Guard: Attendance for request {req['request_code']} has already been integrated.",
            'records_updated': 0,
            'already_integrated': True
        }

    # 2. Compute date range (inclusive)
    start_dt = datetime.strptime(req['start_date'], '%Y-%m-%d').date()
    end_dt = datetime.strptime(req['end_date'], '%Y-%m-%d').date()

    if end_dt < start_dt:
        conn.close()
        raise ValueError("Invalid date range in request.")

    # Generate dates excluding weekends
    target_dates = []
    curr = start_dt
    while curr <= end_dt:
        if curr.weekday() < 5:  # Monday to Friday
            target_dates.append(curr.strftime('%Y-%m-%d'))
        curr += timedelta(days=1)

    if not target_dates:
        # If event was on a weekend, OD applies on the start date
        target_dates.append(req['start_date'])

    # 3. Find student's subjects
    cursor.execute("""
        SELECT id, subject_code, subject_name
        FROM subjects
        WHERE department = ? AND year = ?
    """, (req['department'], req['year']))
    subjects = cursor.fetchall()

    if not subjects:
        conn.close()
        raise ValueError(f"No subjects found for department {req['department']} year {req['year']}.")

    records_count = 0
    student_id = req['student_id']

    # 4. Upsert attendance records for each date and subject
    for t_date in target_dates:
        for sub in subjects:
            sub_id = sub['id']
            cursor.execute("""
                INSERT INTO attendance (student_id, subject_id, attendance_date, status, source, request_id)
                VALUES (?, ?, ?, 'ON_DUTY', 'OD_INTEGRATION', ?)
                ON CONFLICT(student_id, subject_id, attendance_date) 
                DO UPDATE SET 
                    status = 'ON_DUTY',
                    source = 'OD_INTEGRATION',
                    request_id = excluded.request_id
            """, (student_id, sub_id, t_date, request_id))
            records_count += 1

    # 5. Mark attendance_updated = 1 in requests
    cursor.execute("""
        UPDATE requests
        SET attendance_updated = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (request_id,))

    conn.commit()
    conn.close()

    return {
        'success': True,
        'message': f"Attendance successfully updated. Credited {records_count} subject periods as On-Duty.",
        'records_updated': records_count,
        'request_code': req['request_code'],
        'student_user_id': req['student_user_id'],
        'student_name': req['student_name']
    }
