"""
Entry-point launcher for Student OD and Leave Approval System with Attendance Integration.
"""

import os
import sys

# Ensure UTF-8 output encoding for windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 75)
    print("AUTOMATED STUDENT OD & LEAVE APPROVAL WITH ATTENDANCE INTEGRATION")
    print(f"Server running locally at: http://127.0.0.1:{port}")
    print("=" * 75)
    app.run(host='127.0.0.1', port=port, debug=False)
