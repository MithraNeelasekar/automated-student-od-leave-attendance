/**
 * Master Application Controller & Router
 */

const App = {
  init() {
    Auth.init();
    StudentModule.init();
    FacultyModule.init();
    AdminModule.init();
    NotificationsModule.init();
    ReportsModule.init();

    this.bindGlobalEvents();
  },

  bindGlobalEvents() {
    // Sidebar Navigation Links
    document.querySelectorAll('.nav-link-custom[data-view]').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const viewName = link.getAttribute('data-view');
        this.switchView(viewName);

        // On mobile, close sidebar after clicking
        const sidebar = document.querySelector('.sidebar');
        if (sidebar && window.innerWidth <= 992) {
          sidebar.classList.remove('show');
        }
      });
    });

    // Mobile Sidebar Toggle Button
    const menuToggle = document.getElementById('menu-toggle-btn');
    if (menuToggle) {
      menuToggle.addEventListener('click', () => {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) sidebar.classList.toggle('show');
      });
    }


  },

  switchView(viewId) {
    // Update active state on nav links
    document.querySelectorAll('.nav-link-custom').forEach(l => {
      l.classList.toggle('active', l.getAttribute('data-view') === viewId);
    });

    // Hide all view containers
    document.querySelectorAll('.view-section').forEach(sec => {
      sec.classList.add('d-none');
    });

    // Show target view container
    const target = document.getElementById(`view-${viewId}`);
    if (target) {
      target.classList.remove('d-none');
    }

    // Update Topbar Title
    const titleMap = {
      'student-dashboard': 'Student Portal & Dashboard',
      'student-attendance': 'Attendance & OD Credit Tracking',
      'student-requests': 'My OD & Leave Requests',
      'faculty-dashboard': 'Faculty Approval & Mentorship Portal',
      'faculty-all-requests': 'Department Requests History',
      'admin-dashboard': 'HOD & Executive Administration Portal',
      'admin-students': 'Student Management',
      'admin-faculty': 'Faculty Management',
      'admin-reports': 'OD, Leave & Attendance Analytics Reports'
    };

    const titleEl = document.getElementById('topbar-page-title');
    if (titleEl && titleMap[viewId]) {
      titleEl.textContent = titleMap[viewId];
    }

    // Trigger data reload depending on target view
    if (viewId === 'admin-reports') {
      ReportsModule.generateReport();
    } else if (viewId === 'student-attendance') {
      StudentModule.loadProfileAndAttendance();
    } else if (viewId === 'student-requests') {
      StudentModule.loadMyRequests();
    } else if (viewId === 'admin-students') {
      AdminModule.loadStudents();
    } else if (viewId === 'admin-faculty') {
      AdminModule.loadFaculty();
    }
  },

  showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;

    const iconMap = {
      success: 'fa-check-circle',
      danger: 'fa-exclamation-triangle',
      warning: 'fa-exclamation-circle',
      info: 'fa-info-circle'
    };

    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-bg-${type} border-0 show shadow-lg mb-2`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    toastEl.innerHTML = `
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center gap-2">
          <i class="fas ${iconMap[type] || 'fa-info-circle'} fs-5"></i>
          <div>${message}</div>
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    `;

    toastContainer.appendChild(toastEl);
    setTimeout(() => {
      toastEl.classList.remove('show');
      setTimeout(() => toastEl.remove(), 400);
    }, 4500);
  }
};

// Start application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
