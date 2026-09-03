"""
Validation of frontend assets, templates, CSS, JS scripts, and live HTTP responses.
"""

import os
import sys
import unittest
import urllib.request
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app

class AssetAndFlowValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_frontend_index_html_loaded(self):
        """Verify frontend index.html renders with title and core containers."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Automated Student OD & Leave Approval', html)
        self.assertIn('login-view', html)
        self.assertIn('app-shell', html)
        self.assertIn('modal-apply-od', html)
        self.assertIn('modal-apply-leave', html)
        self.assertIn('modal-faculty-review', html)
        self.assertIn('modal-admin-review', html)

    def test_frontend_css_loaded(self):
        """Verify CSS stylesheet is served properly."""
        res = self.client.get('/css/style.css')
        self.assertEqual(res.status_code, 200)
        css = res.data.decode('utf-8')
        self.assertIn('--primary', css)
        self.assertIn('.badge-status', css)
        self.assertIn('.progress-fill', css)

    def test_frontend_js_modules_loaded(self):
        """Verify all JS modules are accessible and non-empty."""
        modules = ['api.js', 'auth.js', 'student.js', 'faculty.js', 'admin.js', 'notifications.js', 'reports.js', 'app.js']
        for mod in modules:
            res = self.client.get(f'/js/{mod}')
            self.assertEqual(res.status_code, 200, f"Failed to load /js/{mod}")
            self.assertGreater(len(res.data), 50, f"Module /js/{mod} is too small")

    def test_live_server_http_port_5000(self):
        """Verify live background server responds over HTTP port 5000."""
        req = urllib.request.Request("http://127.0.0.1:5000/")
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)
            content = response.read().decode('utf-8')
            self.assertIn('EduPortal ERP', content)

if __name__ == '__main__':
    unittest.main()
