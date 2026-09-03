-- =========================================================================
-- Realistic Demo Seed Data for College OD & Leave System
-- =========================================================================

USE college_od_leave_db;

-- 1. Insert HOD / Admin User (Password: password123)
-- SHA-256 hash: b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49
INSERT INTO users (id, username, password_hash, role, email, full_name, status) VALUES
(1, 'admin', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'HOD_ADMIN', 'hod.cse@college.edu', 'Dr. K. Balasubramanian (HOD)', 'ACTIVE');

-- 2. Insert Faculty Users & Profiles
INSERT INTO users (id, username, password_hash, role, email, full_name, status) VALUES
(2, 'faculty1', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'FACULTY', 'prof.ramesh@college.edu', 'Prof. Ramesh Kumar', 'ACTIVE'),
(3, 'faculty2', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'FACULTY', 'dr.ananya@college.edu', 'Dr. Ananya Sharma', 'ACTIVE'),
(4, 'faculty3', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'FACULTY', 'prof.venkat@college.edu', 'Prof. S. Venkatesh', 'ACTIVE');

INSERT INTO faculty (id, user_id, faculty_id, name, department, designation, email, phone) VALUES
(1, 2, 'FAC001', 'Prof. Ramesh Kumar', 'CSE', 'Associate Professor & Class Advisor (3A)', 'prof.ramesh@college.edu', '9876543210'),
(2, 3, 'FAC002', 'Dr. Ananya Sharma', 'CSE', 'Assistant Professor & Mentor (3A)', 'dr.ananya@college.edu', '9876543211'),
(3, 4, 'FAC003', 'Prof. S. Venkatesh', 'CSE', 'Associate Professor & Class Advisor (3B)', 'prof.venkat@college.edu', '9876543212');

-- 3. Insert Subjects (3rd Year CSE - Semester 5)
INSERT INTO subjects (id, subject_code, subject_name, department, year, semester, faculty_id, total_classes) VALUES
(1, 'CS3501', 'Data Structures & Algorithms', 'CSE', 3, 5, 1, 45),
(2, 'CS3502', 'Database Management Systems', 'CSE', 3, 5, 2, 42),
(3, 'CS3503', 'Operating Systems', 'CSE', 3, 5, 1, 40),
(4, 'CS3504', 'Computer Networks', 'CSE', 3, 5, 3, 38),
(5, 'CS3505', 'Software Engineering & Agile', 'CSE', 3, 5, 2, 35);

-- 4. Insert 10 Students Users & Profiles
INSERT INTO users (id, username, password_hash, role, email, full_name, status) VALUES
(5, 'student1', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'STUDENT', 'aarav.patel@student.college.edu', 'Aarav Patel', 'ACTIVE'),
(6, 'student2', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'STUDENT', 'bhavya.sharma@student.college.edu', 'Bhavya Sharma', 'ACTIVE'),
(7, 'student3', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'STUDENT', 'chirag.reddy@student.college.edu', 'Chirag Reddy', 'ACTIVE'),
(8, 'student4', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'STUDENT', 'divya.krishnan@student.college.edu', 'Divya Krishnan', 'ACTIVE'),
(9, 'student5', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'STUDENT', 'eshwar.narayanan@student.college.edu', 'Eshwar Narayanan', 'ACTIVE'),
(10, 'student6', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'STUDENT', 'farhan.khan@student.college.edu', 'Farhan Khan', 'ACTIVE'),
(11, 'student7', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'STUDENT', 'gayathri.menon@student.college.edu', 'Gayathri Menon', 'ACTIVE'),
(12, 'student8', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'STUDENT', 'harish.raghavan@student.college.edu', 'Harish Raghavan', 'ACTIVE'),
(13, 'student9', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'STUDENT', 'ishita.deshmukh@student.college.edu', 'Ishita Deshmukh', 'ACTIVE'),
(14, 'student10', 'b8d53b27be6393b45e998782f07d2f9543be2fe434c0e668c281315998a4da49', 'STUDENT', 'jayant.verma@student.college.edu', 'Jayant Verma', 'ACTIVE');

INSERT INTO students (id, user_id, register_number, name, department, year, section, email, phone, mentor_faculty_id) VALUES
(1, 5, '22CS001', 'Aarav Patel', 'CSE', 3, 'A', 'aarav.patel@student.college.edu', '9123456701', 1),
(2, 6, '22CS002', 'Bhavya Sharma', 'CSE', 3, 'A', 'bhavya.sharma@student.college.edu', '9123456702', 1),
(3, 7, '22CS003', 'Chirag Reddy', 'CSE', 3, 'A', 'chirag.reddy@student.college.edu', '9123456703', 1),
(4, 8, '22CS004', 'Divya Krishnan', 'CSE', 3, 'A', 'divya.krishnan@student.college.edu', '9123456704', 2),
(5, 9, '22CS005', 'Eshwar Narayanan', 'CSE', 3, 'A', 'eshwar.narayanan@student.college.edu', '9123456705', 2),
(6, 10, '22CS006', 'Farhan Khan', 'CSE', 3, 'B', 'farhan.khan@student.college.edu', '9123456706', 3),
(7, 11, '22CS007', 'Gayathri Menon', 'CSE', 3, 'B', 'gayathri.menon@student.college.edu', '9123456707', 3),
(8, 12, '22CS008', 'Harish Raghavan', 'CSE', 3, 'B', 'harish.raghavan@student.college.edu', '9123456708', 3),
(9, 13, '22CS009', 'Ishita Deshmukh', 'CSE', 3, 'B', 'ishita.deshmukh@student.college.edu', '9123456709', 1),
(10, 14, '22CS010', 'Jayant Verma', 'CSE', 3, 'B', 'jayant.verma@student.college.edu', '9123456710', 2);

-- 5. Insert Sample Requests (OD & Leave)
INSERT INTO requests (id, request_code, student_id, request_type, start_date, end_date, event_name, event_type, venue, reason, document_name, document_path, status, attendance_updated, student_remarks, created_at) VALUES
(1, 'OD-2026-001', 1, 'OD', '2026-08-10', '2026-08-10', 'National Smart India Hackathon 2026', 'Hackathon / Tech Competition', 'IIT Madras Research Park', 'Participated and secured 2nd place representing college.', 'hackathon_certificate.pdf', '/uploads/sample_cert.pdf', 'APPROVED', 1, 'Certificate attached.', '2026-08-08 10:30:00'),
(2, 'OD-2026-002', 1, 'OD', '2026-09-08', '2026-09-09', 'IEEE International Cloud Conference', 'Paper Presentation', 'Anna University, Guindy', 'Oral presentation of research paper on Edge AI.', 'ieee_paper.pdf', '/uploads/sample_paper.pdf', 'PENDING_FACULTY', 0, 'Acceptance letter enclosed.', '2026-09-01 09:15:00'),
(3, 'OD-2026-003', 2, 'OD', '2026-09-10', '2026-09-10', 'Inter-College Sports Meet 2026', 'Sports & Athletics', 'Jawaharlal Nehru Stadium', 'Badminton singles finals representing university.', 'sports_selection.pdf', '/uploads/sports.pdf', 'PENDING_HOD', 0, 'Physical director approval letter.', '2026-09-01 14:00:00'),
(4, 'LV-2026-001', 3, 'LEAVE', '2026-08-18', '2026-08-19', NULL, NULL, NULL, 'Attending cousin marriage in native place.', 'wedding_invite.jpg', '/uploads/wedding.jpg', 'REJECTED_FACULTY', 0, 'Personal leave.', '2026-08-16 11:00:00'),
(5, 'LV-2026-002', 4, 'LEAVE', '2026-08-25', '2026-08-26', NULL, NULL, NULL, 'Severe viral fever and medical rest.', 'medical_prescription.pdf', '/uploads/medical.pdf', 'APPROVED', 0, 'Doctor certificate.', '2026-08-24 16:00:00');

-- 6. Insert Approval Audit Records
INSERT INTO approvals (request_id, approver_id, approver_role, action, remarks, action_date) VALUES
(1, 5, 'STUDENT', 'SUBMITTED', 'Submitted request for verification', '2026-08-08 10:30:00'),
(1, 2, 'FACULTY', 'FACULTY_APPROVED', 'Verified participation certificate. Recommended for OD.', '2026-08-09 11:15:00'),
(1, 1, 'HOD_ADMIN', 'HOD_APPROVED', 'Approved. Excellent achievement. Attendance updated.', '2026-08-09 15:00:00'),
(2, 5, 'STUDENT', 'SUBMITTED', 'Submitted for review', '2026-09-01 09:15:00'),
(3, 6, 'STUDENT', 'SUBMITTED', 'Submitted', '2026-09-01 14:00:00'),
(3, 2, 'FACULTY', 'FACULTY_APPROVED', 'Verified sports circular. Forwarded to HOD.', '2026-09-02 10:30:00'),
(4, 7, 'STUDENT', 'SUBMITTED', 'Submitted', '2026-08-16 11:00:00'),
(4, 2, 'FACULTY', 'FACULTY_REJECTED', 'Internal assessment exam scheduled. Personal leave cannot be permitted.', '2026-08-17 09:30:00'),
(5, 8, 'STUDENT', 'SUBMITTED', 'Submitted medical leave', '2026-08-24 16:00:00'),
(5, 3, 'FACULTY', 'FACULTY_APPROVED', 'Medical certificate verified. Recommended.', '2026-08-25 09:00:00'),
(5, 1, 'HOD_ADMIN', 'HOD_APPROVED', 'Sanctioned medical leave.', '2026-08-25 11:30:00');
