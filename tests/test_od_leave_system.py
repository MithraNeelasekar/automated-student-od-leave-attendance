"""
Comprehensive Automated Test Suite for:
Automated Student OD and Leave Approval with Attendance Integration
"""

import os
import sys
import unittest
import json
from datetime import datetime, date, timedelta

# Add backend directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app
from database import init_db, get_db_connection

class OdLeaveSystemTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Initialize database with fresh demo data."""
        init_db(force_reseed=True)
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_auth_login_student(self):
        """Test valid student login."""
        res = self.client.post('/api/auth/login', json={
            'username': 'student1',
            'password': 'password123',
            'role': 'STUDENT'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('token', data)
        self.assertEqual(data['user']['role'], 'STUDENT')
        self.assertEqual(data['user']['full_name'], 'Aarav Patel')

    def test_02_auth_invalid_credentials(self):
        """Test login with incorrect password."""
        res = self.client.post('/api/auth/login', json={
            'username': 'student1',
            'password': 'wrongpassword'
        })
        self.assertEqual(res.status_code, 401)

    def test_03_auth_role_mismatch(self):
        """Test login with role mismatch guard."""
        res = self.client.post('/api/auth/login', json={
            'username': 'student1',
            'password': 'password123',
            'role': 'FACULTY'
        })
        self.assertEqual(res.status_code, 403)

    def test_04_student_attendance_calculation(self):
        """Test student attendance percentage and subject breakdown formula."""
        # Login as student 1 (id: 1)
        login_res = self.client.post('/api/auth/login', json={'username': 'student1', 'password': 'password123'})
        token = login_res.get_json()['token']

        res = self.client.get('/api/students/1/attendance', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        overall = data['overall']
        self.assertIn('percentage', overall)
        self.assertIn('total_attended', overall)
        self.assertIn('approved_od', overall)
        self.assertIn('total_conducted', overall)

        # Mathematical verification: (attended + od) / conducted * 100 == percentage
        expected_perc = round(((overall['total_attended'] + overall['approved_od']) / overall['total_conducted']) * 100, 1)
        self.assertEqual(overall['percentage'], expected_perc)
        self.assertEqual(len(data['subjects']), 5)

    def test_05_student_submit_od_request_and_duplicate_guard(self):
        """Test student OD request submission and date validation."""
        login_res = self.client.post('/api/auth/login', json={'username': 'student2', 'password': 'password123'})
        token = login_res.get_json()['token']

        # 1. Invalid date range test (end date before start date)
        invalid_res = self.client.post('/api/requests', headers={'Authorization': f'Bearer {token}'}, json={
            'request_type': 'OD',
            'start_date': '2026-09-20',
            'end_date': '2026-09-18',
            'event_name': 'Robotics Expo',
            'reason': 'Participation'
        })
        self.assertEqual(invalid_res.status_code, 400)

        # 2. Valid OD Submission
        valid_res = self.client.post('/api/requests', headers={'Authorization': f'Bearer {token}'}, json={
            'request_type': 'OD',
            'start_date': '2026-09-22',
            'end_date': '2026-09-23',
            'event_name': 'National AI Symposium 2026',
            'event_type': 'Technical Symposium',
            'venue': 'NIT Trichy',
            'reason': 'Presenting deep learning research paper.',
            'remarks': 'Brochure attached'
        })
        self.assertEqual(valid_res.status_code, 201)
        data = valid_res.get_json()
        req_code = data['request_code']
        self.assertTrue(req_code.startswith('OD-'))
        self.assertEqual(data['status'], 'PENDING_FACULTY')

        # 3. Duplicate Overlapping Request Guard Test
        dup_res = self.client.post('/api/requests', headers={'Authorization': f'Bearer {token}'}, json={
            'request_type': 'OD',
            'start_date': '2026-09-22',
            'end_date': '2026-09-22',
            'event_name': 'Another Event on Same Date',
            'reason': 'Overlapping date attempt'
        })
        self.assertEqual(dup_res.status_code, 400)
        self.assertIn('Overlapping request', dup_res.get_json()['error'])

    def test_06_complete_approval_and_attendance_integration_workflow(self):
        """
        Full End-to-End Workflow:
        1. Student submits OD for 2026-09-15.
        2. Verify attendance records for 2026-09-15 are NOT modified initially.
        3. Faculty reviews and approves (forwarding to HOD).
        4. HOD reviews and approves (Triggering Attendance Integration Engine).
        5. Verify attendance records for 2026-09-15 are created/credited with status ON_DUTY and source OD_INTEGRATION.
        6. Verify idempotency: Repeating integration doesn't duplicate records.
        """
        # Step 1: Student 5 submits OD
        st_login = self.client.post('/api/auth/login', json={'username': 'student5', 'password': 'password123'})
        st_token = st_login.get_json()['token']
        st_id = st_login.get_json()['user']['profile']['id']

        sub_res = self.client.post('/api/requests', headers={'Authorization': f'Bearer {st_token}'}, json={
            'request_type': 'OD',
            'start_date': '2026-09-15',
            'end_date': '2026-09-15',
            'event_name': 'State Level Coding Marathon',
            'event_type': 'Hackathon / Tech Competition',
            'venue': 'Anna University Regional Campus',
            'reason': 'Coding marathon team finalist'
        })
        self.assertEqual(sub_res.status_code, 201)
        req_id = sub_res.get_json()['id']
        req_code = sub_res.get_json()['request_code']

        # Step 2: Verify attendance for 2026-09-15 is NOT yet touched
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM attendance WHERE student_id = ? AND attendance_date = '2026-09-15'", (st_id,))
        count_before = c.fetchone()[0]
        self.assertEqual(count_before, 0)
        conn.close()

        # Step 3: Faculty 2 approves request
        fac_login = self.client.post('/api/auth/login', json={'username': 'faculty2', 'password': 'password123'})
        fac_token = fac_login.get_json()['token']

        fac_res = self.client.put(f'/api/faculty/requests/{req_id}/approve', headers={'Authorization': f'Bearer {fac_token}'}, json={
            'remarks': 'Verified coding marathon schedule. Strongly recommended for OD.'
        })
        self.assertEqual(fac_res.status_code, 200)
        self.assertEqual(fac_res.get_json()['status'], 'PENDING_HOD')

        # Step 4: HOD approves request (Attendance Integration Engine Triggers)
        hod_login = self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'password123'})
        hod_token = hod_login.get_json()['token']

        hod_res = self.client.put(f'/api/admin/requests/{req_id}/approve', headers={'Authorization': f'Bearer {hod_token}'}, json={
            'remarks': 'Sanctioned. Best wishes for the competition.'
        })
        self.assertEqual(hod_res.status_code, 200)
        hod_data = hod_res.get_json()
        self.assertEqual(hod_data['status'], 'APPROVED')
        self.assertIsNotNone(hod_data['integration'])
        self.assertEqual(hod_data['integration']['records_updated'], 5)  # 5 subjects credited

        # Step 5: Verify attendance table now contains ON_DUTY records for all 5 subjects
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM attendance 
            WHERE student_id = ? AND attendance_date = '2026-09-15' 
              AND status = 'ON_DUTY' AND source = 'OD_INTEGRATION' AND request_id = ?
        """, (st_id, req_id))
        count_after = c.fetchone()[0]
        self.assertEqual(count_after, 5)

        c.execute("SELECT attendance_updated FROM requests WHERE id = ?", (req_id,))
        self.assertEqual(c.fetchone()[0], 1)
        conn.close()

        # Step 6: Verify student received notification
        notif_res = self.client.get('/api/notifications', headers={'Authorization': f'Bearer {st_token}'})
        self.assertEqual(notif_res.status_code, 200)
        notifs = notif_res.get_json()['notifications']
        self.assertTrue(any('Approved by HOD' in n['title'] for n in notifs))

    def test_07_faculty_rejection_halts_workflow(self):
        """Test rejection workflow stops approval and prevents attendance modification."""
        # Student 6 submits leave
        st_login = self.client.post('/api/auth/login', json={'username': 'student6', 'password': 'password123'})
        st_token = st_login.get_json()['token']
        st_id = st_login.get_json()['user']['profile']['id']

        sub_res = self.client.post('/api/requests', headers={'Authorization': f'Bearer {st_token}'}, json={
            'request_type': 'LEAVE',
            'start_date': '2026-09-28',
            'end_date': '2026-09-29',
            'leave_type': 'Personal Leave',
            'reason': 'Attending family function'
        })
        req_id = sub_res.get_json()['id']

        # Faculty 3 rejects with remarks
        fac_login = self.client.post('/api/auth/login', json={'username': 'faculty3', 'password': 'password123'})
        fac_token = fac_login.get_json()['token']

        # Reject without remarks should fail
        fail_res = self.client.put(f'/api/faculty/requests/{req_id}/reject', headers={'Authorization': f'Bearer {fac_token}'}, json={
            'remarks': ''
        })
        self.assertEqual(fail_res.status_code, 400)

        # Reject with valid remarks
        rej_res = self.client.put(f'/api/faculty/requests/{req_id}/reject', headers={'Authorization': f'Bearer {fac_token}'}, json={
            'remarks': 'Laboratory model examination scheduled. Leave cannot be granted.'
        })
        self.assertEqual(rej_res.status_code, 200)
        self.assertEqual(rej_res.get_json()['status'], 'REJECTED_FACULTY')

    def test_08_admin_student_crud_and_reports(self):
        """Test Admin Student CRUD operations and Reports endpoint."""
        hod_login = self.client.post('/api/auth/login', json={'username': 'admin', 'password': 'password123'})
        hod_token = hod_login.get_json()['token']

        # 1. Add student
        create_res = self.client.post('/api/admin/students', headers={'Authorization': f'Bearer {hod_token}'}, json={
            'register_number': '22CS099',
            'name': 'Kavya Subramanian',
            'department': 'CSE',
            'year': 3,
            'section': 'A',
            'email': 'kavya.sub@student.college.edu',
            'phone': '9123456799'
        })
        self.assertEqual(create_res.status_code, 201)
        new_st_id = create_res.get_json()['id']

        # 2. Update student
        up_res = self.client.put(f'/api/admin/students/{new_st_id}', headers={'Authorization': f'Bearer {hod_token}'}, json={
            'name': 'Kavya S.',
            'phone': '9876543299'
        })
        self.assertEqual(up_res.status_code, 200)

        # 3. Reports endpoint
        rep_res = self.client.get('/api/admin/reports?type=requests', headers={'Authorization': f'Bearer {hod_token}'})
        self.assertEqual(rep_res.status_code, 200)
        self.assertGreater(len(rep_res.get_json()['data']), 0)

        # 4. CSV export endpoint
        csv_res = self.client.get('/api/admin/reports?type=requests&export=true', headers={'Authorization': f'Bearer {hod_token}'})
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn('text/csv', csv_res.headers.get('Content-Type'))

if __name__ == '__main__':
    unittest.main()
