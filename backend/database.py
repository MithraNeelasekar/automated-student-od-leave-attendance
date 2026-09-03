"""
Database layer for Student OD and Leave Approval with Attendance Integration.
Supports SQLite out of the box and provides MySQL compatibility.
"""

import sqlite3
import hashlib
import os
from datetime import datetime, date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'od_leave_system.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = "od_leave_secret_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def init_db(force_reseed=False):
    """Initialize database tables and seed with rich demo data if empty or forced."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if force_reseed:
        cursor.executescript("""
            DROP TABLE IF EXISTS notifications;
            DROP TABLE IF EXISTS attendance;
            DROP TABLE IF EXISTS approvals;
            DROP TABLE IF EXISTS requests;
            DROP TABLE IF EXISTS subjects;
            DROP TABLE IF EXISTS faculty;
            DROP TABLE IF EXISTS students;
            DROP TABLE IF EXISTS users;
        """)

    # Create Tables
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('STUDENT', 'FACULTY', 'HOD_ADMIN')),
            email TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            faculty_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            designation TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            register_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            year INTEGER NOT NULL,
            section TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            mentor_faculty_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (mentor_faculty_id) REFERENCES faculty(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT UNIQUE NOT NULL,
            subject_name TEXT NOT NULL,
            department TEXT NOT NULL,
            year INTEGER NOT NULL,
            semester INTEGER NOT NULL,
            faculty_id INTEGER,
            total_classes INTEGER NOT NULL DEFAULT 40,
            FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_code TEXT UNIQUE NOT NULL,
            student_id INTEGER NOT NULL,
            request_type TEXT NOT NULL CHECK(request_type IN ('OD', 'LEAVE')),
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            event_name TEXT,
            event_type TEXT,
            venue TEXT,
            leave_type TEXT,
            reason TEXT NOT NULL,
            document_name TEXT,
            document_path TEXT,
            status TEXT NOT NULL DEFAULT 'PENDING_FACULTY' 
                CHECK(status IN ('PENDING_FACULTY', 'PENDING_HOD', 'APPROVED', 'REJECTED_FACULTY', 'REJECTED_HOD')),
            attendance_updated INTEGER NOT NULL DEFAULT 0,
            student_remarks TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER NOT NULL,
            approver_id INTEGER NOT NULL,
            approver_role TEXT NOT NULL CHECK(approver_role IN ('STUDENT', 'FACULTY', 'HOD_ADMIN')),
            action TEXT NOT NULL CHECK(action IN ('SUBMITTED', 'FACULTY_APPROVED', 'FACULTY_REJECTED', 'HOD_APPROVED', 'HOD_REJECTED')),
            remarks TEXT,
            action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE,
            FOREIGN KEY (approver_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            attendance_date DATE NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('PRESENT', 'ABSENT', 'ON_DUTY')),
            source TEXT NOT NULL DEFAULT 'REGULAR' CHECK(source IN ('REGULAR', 'OD_INTEGRATION')),
            request_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE SET NULL,
            UNIQUE(student_id, subject_id, attendance_date)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            link TEXT,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)

    # Check if seed data is needed
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        seed_data(cursor)

    conn.commit()
    conn.close()

def seed_data(cursor):
    """Seed comprehensive realistic demo data: 10 students, 3 faculty, 1 HOD, 5 subjects, attendance & requests."""
    pwd = hash_password("password123")

    # 1. Create HOD / Admin user
    cursor.execute("""
        INSERT INTO users (username, password_hash, role, email, full_name)
        VALUES ('admin', ?, 'HOD_ADMIN', 'hod.cse@college.edu', 'Dr. K. Balasubramanian (HOD)')
    """, (pwd,))
    hod_user_id = cursor.lastrowid

    # 2. Create 3 Faculty Members
    faculty_data = [
        ('faculty1', 'prof.ramesh@college.edu', 'Prof. Ramesh Kumar', 'FAC001', 'CSE', 'Associate Professor & Class Advisor (3A)', '9876543210'),
        ('faculty2', 'dr.ananya@college.edu', 'Dr. Ananya Sharma', 'FAC002', 'CSE', 'Assistant Professor & Mentor (3A)', '9876543211'),
        ('faculty3', 'prof.venkat@college.edu', 'Prof. S. Venkatesh', 'FAC003', 'CSE', 'Associate Professor & Class Advisor (3B)', '9876543212'),
    ]

    faculty_ids = []
    for uname, email, name, fac_code, dept, desig, phone in faculty_data:
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, email, full_name)
            VALUES (?, ?, 'FACULTY', ?, ?)
        """, (uname, pwd, email, name))
        u_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO faculty (user_id, faculty_id, name, department, designation, email, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (u_id, fac_code, name, dept, desig, email, phone))
        faculty_ids.append(cursor.lastrowid)

    # 3. Create 5 Subjects for 3rd Year CSE (Semester 5)
    subjects_data = [
        ('CS3501', 'Data Structures & Algorithms', 'CSE', 3, 5, faculty_ids[0], 45),
        ('CS3502', 'Database Management Systems', 'CSE', 3, 5, faculty_ids[1], 42),
        ('CS3503', 'Operating Systems', 'CSE', 3, 5, faculty_ids[0], 40),
        ('CS3504', 'Computer Networks', 'CSE', 3, 5, faculty_ids[2], 38),
        ('CS3505', 'Software Engineering & Agile', 'CSE', 3, 5, faculty_ids[1], 35),
    ]

    subject_ids = []
    for code, name, dept, yr, sem, fac_id, total_cls in subjects_data:
        cursor.execute("""
            INSERT INTO subjects (subject_code, subject_name, department, year, semester, faculty_id, total_classes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (code, name, dept, yr, sem, fac_id, total_cls))
        subject_ids.append(cursor.lastrowid)

    # 4. Create 10 Students (3rd Year CSE, Sections A & B)
    students_data = [
        ('student1', 'aarav.patel@student.college.edu', 'Aarav Patel', '22CS001', 'CSE', 3, 'A', '9123456701', faculty_ids[0]),
        ('student2', 'bhavya.sharma@student.college.edu', 'Bhavya Sharma', '22CS002', 'CSE', 3, 'A', '9123456702', faculty_ids[0]),
        ('student3', 'chirag.reddy@student.college.edu', 'Chirag Reddy', '22CS003', 'CSE', 3, 'A', '9123456703', faculty_ids[0]),
        ('student4', 'divya.krishnan@student.college.edu', 'Divya Krishnan', '22CS004', 'CSE', 3, 'A', '9123456704', faculty_ids[1]),
        ('student5', 'eshwar.narayanan@student.college.edu', 'Eshwar Narayanan', '22CS005', 'CSE', 3, 'A', '9123456705', faculty_ids[1]),
        ('student6', 'farhan.khan@student.college.edu', 'Farhan Khan', '22CS006', 'CSE', 3, 'B', '9123456706', faculty_ids[2]),
        ('student7', 'gayathri.menon@student.college.edu', 'Gayathri Menon', '22CS007', 'CSE', 3, 'B', '9123456707', faculty_ids[2]),
        ('student8', 'harish.raghavan@student.college.edu', 'Harish Raghavan', '22CS008', 'CSE', 3, 'B', '9123456708', faculty_ids[2]),
        ('student9', 'ishita.deshmukh@student.college.edu', 'Ishita Deshmukh', '22CS009', 'CSE', 3, 'B', '9123456709', faculty_ids[0]),
        ('student10', 'jayant.verma@student.college.edu', 'Jayant Verma', '22CS010', 'CSE', 3, 'B', '9123456710', faculty_ids[1]),
    ]

    student_records = []
    for uname, email, name, regno, dept, yr, sec, phone, mentor_id in students_data:
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, email, full_name)
            VALUES (?, ?, 'STUDENT', ?, ?)
        """, (uname, pwd, email, name))
        u_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO students (user_id, register_number, name, department, year, section, email, phone, mentor_faculty_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (u_id, regno, name, dept, yr, sec, email, phone, mentor_id))
        student_id = cursor.lastrowid
        student_records.append({
            'student_id': student_id,
            'user_id': u_id,
            'regno': regno,
            'name': name,
            'mentor_id': mentor_id
        })

    # 5. Populate Baseline Attendance for Past 20 Class Days across all 5 subjects
    start_history_date = date(2026, 8, 3)
    curr_date = start_history_date
    class_dates = []
    while len(class_dates) < 20:
        if curr_date.weekday() < 5:  # Monday to Friday
            class_dates.append(curr_date)
        curr_date += timedelta(days=1)

    for s_idx, st in enumerate(student_records):
        st_id = st['student_id']
        for sub_id in subject_ids:
            for d_idx, dt in enumerate(class_dates):
                # Realistic patterns: mostly present, occasional absence
                status = 'PRESENT'
                if (s_idx * 3 + d_idx + sub_id) % 7 == 0:
                    status = 'ABSENT'
                
                cursor.execute("""
                    INSERT INTO attendance (student_id, subject_id, attendance_date, status, source)
                    VALUES (?, ?, ?, ?, 'REGULAR')
                """, (st_id, sub_id, dt.strftime('%Y-%m-%d'), status))

    # 6. Seed Sample Requests (OD and Leave)
    # Request 1: APPROVED OD for Student 1 (Aarav Patel) with attendance already auto-integrated
    od1_start = '2026-08-10'
    od1_end = '2026-08-10'
    cursor.execute("""
        INSERT INTO requests (
            request_code, student_id, request_type, start_date, end_date,
            event_name, event_type, venue, reason, document_name, document_path,
            status, attendance_updated, student_remarks, created_at
        ) VALUES (
            'OD-2026-001', ?, 'OD', ?, ?,
            'National Smart India Hackathon 2026', 'Hackathon / Tech Competition',
            'IIT Madras Research Park, Chennai', 'Participated and won 2nd prize in AI/ML category representing our college.',
            'hackathon_certificate.pdf', '/uploads/sample_cert.pdf',
            'APPROVED', 1, 'Event brochure and certificate attached.', '2026-08-08 10:30:00'
        )
    """, (student_records[0]['student_id'], od1_start, od1_end))
    r1_id = cursor.lastrowid

    # Approvals for Request 1
    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks, action_date)
        VALUES (?, ?, 'STUDENT', 'SUBMITTED', 'Submitted for verification', '2026-08-08 10:30:00')
    """, (r1_id, student_records[0]['user_id']))
    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks, action_date)
        VALUES (?, 2, 'FACULTY', 'FACULTY_APPROVED', 'Verified participation certificate. Recommended for OD.', '2026-08-09 11:15:00')
    """, (r1_id,))
    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks, action_date)
        VALUES (?, ?, 'HOD_ADMIN', 'HOD_APPROVED', 'Approved. Excellent achievement. Attendance updated.', '2026-08-09 15:00:00')
    """, (r1_id, hod_user_id))

    # Update attendance for OD-2026-001 (Mark as ON_DUTY with source OD_INTEGRATION)
    for sub_id in subject_ids:
        cursor.execute("""
            INSERT OR REPLACE INTO attendance (student_id, subject_id, attendance_date, status, source, request_id)
            VALUES (?, ?, ?, 'ON_DUTY', 'OD_INTEGRATION', ?)
        """, (student_records[0]['student_id'], sub_id, od1_start, r1_id))

    # Request 2: PENDING_FACULTY OD for Student 1 (Aarav Patel)
    cursor.execute("""
        INSERT INTO requests (
            request_code, student_id, request_type, start_date, end_date,
            event_name, event_type, venue, reason, document_name, document_path,
            status, attendance_updated, student_remarks, created_at
        ) VALUES (
            'OD-2026-002', ?, 'OD', '2026-09-08', '2026-09-09',
            'IEEE International Conference on Cloud Computing', 'Paper Presentation',
            'Anna University, Guindy', 'Oral research paper presentation titled "Edge AI in Smart Attendance".',
            'ieee_acceptance_letter.pdf', '/uploads/sample_paper.pdf',
            'PENDING_FACULTY', 0, 'Acceptance letter and registration receipt attached.', '2026-09-01 09:15:00'
        )
    """, (student_records[0]['student_id'],))
    r2_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks, action_date)
        VALUES (?, ?, 'STUDENT', 'SUBMITTED', 'Submitted for review', '2026-09-01 09:15:00')
    """, (r2_id, student_records[0]['user_id']))

    # Request 3: PENDING_HOD OD for Student 2 (Bhavya Sharma)
    cursor.execute("""
        INSERT INTO requests (
            request_code, student_id, request_type, start_date, end_date,
            event_name, event_type, venue, reason, document_name, document_path,
            status, attendance_updated, student_remarks, created_at
        ) VALUES (
            'OD-2026-003', ?, 'OD', '2026-09-10', '2026-09-10',
            'Inter-College Sports Meet 2026', 'Sports & Athletics',
            'Jawaharlal Nehru Stadium', 'Representing College Badminton Women Singles in finals.',
            'sports_selection_letter.pdf', '/uploads/sports.pdf',
            'PENDING_HOD', 0, 'Physical Director authorization letter attached.', '2026-09-01 14:00:00'
        )
    """, (student_records[1]['student_id'],))
    r3_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks, action_date)
        VALUES (?, ?, 'STUDENT', 'SUBMITTED', 'Submitted', '2026-09-01 14:00:00')
    """, (r3_id, student_records[1]['user_id']))
    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks, action_date)
        VALUES (?, 2, 'FACULTY', 'FACULTY_APPROVED', 'Verified sports circular. Forwarded to HOD for sanctioning.', '2026-09-02 10:30:00')
    """, (r3_id,))

    # Request 4: REJECTED_FACULTY Leave for Student 3 (Chirag Reddy)
    cursor.execute("""
        INSERT INTO requests (
            request_code, student_id, request_type, start_date, end_date,
            leave_type, reason, document_name, document_path,
            status, attendance_updated, student_remarks, created_at
        ) VALUES (
            'LV-2026-001', ?, 'LEAVE', '2026-08-18', '2026-08-19',
            'Personal Leave', 'Attending cousin marriage in native place.',
            'invitation_card.jpg', '/uploads/wedding.jpg',
            'REJECTED_FACULTY', 0, 'Wedding invitation enclosed.', '2026-08-16 11:00:00'
        )
    """, (student_records[2]['student_id'],))
    r4_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks, action_date)
        VALUES (?, ?, 'STUDENT', 'SUBMITTED', 'Submitted', '2026-08-16 11:00:00')
    """, (r4_id, student_records[2]['user_id']))
    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks, action_date)
        VALUES (?, 2, 'FACULTY', 'FACULTY_REJECTED', 'Internal assessment exam scheduled on 18th August. Personal leave cannot be permitted.', '2026-08-17 09:30:00')
    """, (r4_id,))

    # Request 5: APPROVED Leave for Student 4 (Divya Krishnan)
    cursor.execute("""
        INSERT INTO requests (
            request_code, student_id, request_type, start_date, end_date,
            leave_type, reason, document_name, document_path,
            status, attendance_updated, student_remarks, created_at
        ) VALUES (
            'LV-2026-002', ?, 'LEAVE', '2026-08-25', '2026-08-26',
            'Medical Leave', 'Viral fever and prescribed 2 days bed rest.',
            'medical_prescription.pdf', '/uploads/medical.pdf',
            'APPROVED', 0, 'Doctor prescription attached.', '2026-08-24 16:00:00'
        )
    """, (student_records[3]['student_id'],))
    r5_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks, action_date)
        VALUES (?, ?, 'STUDENT', 'SUBMITTED', 'Submitted medical leave', '2026-08-24 16:00:00')
    """, (r5_id, student_records[3]['user_id']))
    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks, action_date)
        VALUES (?, 3, 'FACULTY', 'FACULTY_APPROVED', 'Medical certificate verified. Recommended.', '2026-08-25 09:00:00')
    """, (r5_id,))
    cursor.execute("""
        INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks, action_date)
        VALUES (?, ?, 'HOD_ADMIN', 'HOD_APPROVED', 'Sanctioned medical leave.', '2026-08-25 11:30:00')
    """, (r5_id, hod_user_id))

    # 7. Seed Initial Notifications
    notifications_data = [
        (student_records[0]['user_id'], 'OD Request Approved & Attendance Credited', 'Your OD request OD-2026-001 has been approved by HOD. 5 subject attendance periods credited as On-Duty.', 'OD-2026-001'),
        (student_records[0]['user_id'], 'OD Request Under Faculty Review', 'Your OD request OD-2026-002 for IEEE Conference is pending review with Prof. Ramesh Kumar.', 'OD-2026-002'),
        (student_records[1]['user_id'], 'Faculty Approved OD Request', 'Your OD request OD-2026-003 was approved by Prof. Ramesh Kumar and forwarded to HOD for final approval.', 'OD-2026-003'),
        (student_records[2]['user_id'], 'Leave Request Rejected', 'Your Leave request LV-2026-001 was rejected by Faculty: Internal Assessment Exam conflict.', 'LV-2026-001'),
        (2, 'New OD Request Submitted', 'Student Aarav Patel (22CS001) submitted a new OD request OD-2026-002 for your review.', 'OD-2026-002'),
        (hod_user_id, 'OD Request Forwarded for Final Approval', 'Faculty Prof. Ramesh Kumar forwarded OD request OD-2026-003 (Bhavya Sharma) for your sanction.', 'OD-2026-003'),
    ]

    for uid, title, msg, link in notifications_data:
        cursor.execute("""
            INSERT INTO notifications (user_id, title, message, link, is_read)
            VALUES (?, ?, ?, ?, 0)
        """, (uid, title, msg, link))

if __name__ == '__main__':
    print("Initializing and seeding database...")
    init_db(force_reseed=True)
    print(f"Database initialized successfully at: {DB_PATH}")
