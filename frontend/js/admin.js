/**
 * Admin / HOD Module: Executive Dashboard, Request Sanctions, Student & Faculty CRUD
 */

const AdminModule = {
  currentRequestId: null,
  cachedRequests: [],
  cachedStudents: [],
  cachedFaculty: [],

  init() {
    this.bindEvents();
  },

  bindEvents() {
    // Request Filtering
    ['admin-filter-dept', 'admin-filter-year', 'admin-filter-type', 'admin-filter-status'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('change', () => this.loadRequests());
    });

    const searchInput = document.getElementById('admin-search-req');
    if (searchInput) {
      searchInput.addEventListener('input', () => this.loadRequests());
    }

    // Admin Review Modal Buttons
    const approveBtn = document.getElementById('admin-modal-approve-btn');
    if (approveBtn) {
      approveBtn.addEventListener('click', () => this.submitReview('APPROVE'));
    }

    const rejectBtn = document.getElementById('admin-modal-reject-btn');
    if (rejectBtn) {
      rejectBtn.addEventListener('click', () => this.submitReview('REJECT'));
    }

    // Add Student Form
    const addStudentForm = document.getElementById('form-add-student');
    if (addStudentForm) {
      addStudentForm.addEventListener('submit', (e) => this.handleAddStudent(e));
    }

    // Edit Student Form
    const editStudentForm = document.getElementById('form-edit-student');
    if (editStudentForm) {
      editStudentForm.addEventListener('submit', (e) => this.handleEditStudent(e));
    }

    // Add Faculty Form
    const addFacultyForm = document.getElementById('form-add-faculty');
    if (addFacultyForm) {
      addFacultyForm.addEventListener('submit', (e) => this.handleAddFaculty(e));
    }

    // Edit Faculty Form
    const editFacultyForm = document.getElementById('form-edit-faculty');
    if (editFacultyForm) {
      editFacultyForm.addEventListener('submit', (e) => this.handleEditFaculty(e));
    }
  },

  async loadDashboard() {
    const user = API.getCurrentUser();
    if (!user || user.role !== 'HOD_ADMIN') return;

    try {
      const stats = await API.get('/admin/dashboard');
      this.renderKPIs(stats);
      await Promise.all([
        this.loadRequests(),
        this.loadStudents(),
        this.loadFaculty()
      ]);
    } catch (err) {
      console.error('Error loading admin dashboard', err);
    }
  },

  renderKPIs(stats) {
    const studentsEl = document.getElementById('admin-kpi-students');
    const facultyEl = document.getElementById('admin-kpi-faculty');
    const pendingEl = document.getElementById('admin-kpi-pending');
    const approvedEl = document.getElementById('admin-kpi-approved');
    const rejectedEl = document.getElementById('admin-kpi-rejected');
    const avgAttEl = document.getElementById('admin-kpi-avg-att');

    if (studentsEl) studentsEl.textContent = stats.total_students || 0;
    if (facultyEl) facultyEl.textContent = stats.total_faculty || 0;
    if (pendingEl) pendingEl.textContent = stats.pending_requests || 0;
    if (approvedEl) approvedEl.textContent = stats.approved_requests || 0;
    if (rejectedEl) rejectedEl.textContent = stats.rejected_requests || 0;
    if (avgAttEl) avgAttEl.textContent = `${stats.average_attendance || 0}%`;
  },

  async loadRequests() {
    const params = {
      department: document.getElementById('admin-filter-dept')?.value || '',
      year: document.getElementById('admin-filter-year')?.value || '',
      request_type: document.getElementById('admin-filter-type')?.value || '',
      status: document.getElementById('admin-filter-status')?.value || '',
      search: document.getElementById('admin-search-req')?.value || ''
    };

    try {
      const data = await API.get('/admin/requests', params);
      this.cachedRequests = data.requests || [];
      this.renderRequestsTable(this.cachedRequests);
    } catch (err) {
      console.error('Error loading admin requests', err);
    }
  },

  renderRequestsTable(requests) {
    const tbody = document.getElementById('admin-requests-tbody');
    if (!tbody) return;

    if (!requests || requests.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center py-5 text-muted">No requests matching criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = requests.map(r => {
      let statusBadge = '';
      if (r.status === 'PENDING_FACULTY') {
        statusBadge = '<span class="badge-status badge-pending">Pending Faculty</span>';
      } else if (r.status === 'PENDING_HOD') {
        statusBadge = '<span class="badge-status badge-faculty-approved">Pending HOD</span>';
      } else if (r.status === 'APPROVED') {
        statusBadge = '<span class="badge-status badge-approved">Approved</span>';
      } else {
        statusBadge = '<span class="badge-status badge-rejected">Rejected</span>';
      }

      const typeBadge = r.request_type === 'OD' 
        ? '<span class="badge badge-od"><i class="fas fa-award me-1"></i>OD</span>'
        : '<span class="badge badge-leave"><i class="fas fa-calendar-minus me-1"></i>Leave</span>';

      const dateRange = r.start_date === r.end_date ? r.start_date : `${r.start_date} to ${r.end_date}`;

      return `
        <tr>
          <td class="fw-bold font-monospace text-primary">${r.request_code}</td>
          <td>
            <div class="fw-bold">${r.student_name}</div>
            <div class="small text-muted font-monospace">${r.register_number} (${r.department} - ${r.year}${r.section})</div>
          </td>
          <td>${typeBadge}</td>
          <td>
            <div class="fw-semibold">${r.request_type === 'OD' ? (r.event_name || 'OD Event') : (r.leave_type || 'Leave')}</div>
            <div class="small text-muted text-truncate" style="max-width: 180px;">${r.reason}</div>
          </td>
          <td class="small fw-semibold text-nowrap">${dateRange}</td>
          <td>${statusBadge}</td>
          <td>
            ${r.attendance_updated 
              ? '<span class="badge bg-success-subtle text-success small"><i class="fas fa-check-double me-1"></i>Auto-Credited</span>' 
              : '<span class="text-muted small">Not Applied</span>'}
          </td>
          <td>
            <div class="btn-group btn-group-sm">
              <button class="btn btn-outline-primary" onclick="StudentModule.viewRequestDetails(${r.id})" title="View Details">
                <i class="fas fa-eye"></i>
              </button>
              ${(r.status === 'PENDING_HOD' || r.status === 'PENDING_FACULTY') ? `
                <button class="btn btn-primary" onclick="AdminModule.openSanctionModal(${r.id})" title="Sanction Request">
                  <i class="fas fa-gavel me-1"></i>Review
                </button>
              ` : ''}
            </div>
          </td>
        </tr>
      `;
    }).join('');
  },

  openSanctionModal(requestId) {
    this.currentRequestId = requestId;
    const req = this.cachedRequests.find(r => r.id === requestId);
    if (!req) return;

    document.getElementById('admin-modal-req-code').textContent = req.request_code;
    document.getElementById('admin-modal-student').textContent = `${req.student_name} (${req.register_number}) - ${req.department} Year ${req.year}`;
    document.getElementById('admin-modal-type').textContent = `${req.request_type} (${req.event_name || req.leave_type || ''})`;
    document.getElementById('admin-modal-dates').textContent = `${req.start_date} to ${req.end_date}`;
    document.getElementById('admin-modal-reason').textContent = req.reason;
    document.getElementById('admin-modal-faculty-remarks').textContent = req.faculty_remarks || 'None recorded.';
    document.getElementById('admin-modal-remarks').value = '';

    const modal = new bootstrap.Modal(document.getElementById('modal-admin-review'));
    modal.show();
  },

  async submitReview(action) {
    if (!this.currentRequestId) return;

    const remarksInput = document.getElementById('admin-modal-remarks');
    const remarks = remarksInput ? remarksInput.value.trim() : '';

    if (action === 'REJECT' && !remarks) {
      App.showToast('Please provide mandatory remarks explaining rejection.', 'warning');
      remarksInput?.focus();
      return;
    }

    try {
      const endpoint = action === 'APPROVE'
        ? `/admin/requests/${this.currentRequestId}/approve`
        : `/admin/requests/${this.currentRequestId}/reject`;

      const response = await API.put(endpoint, { remarks });
      
      if (response.integration && response.integration.records_updated > 0) {
        App.showToast(`Request Approved! Automated Attendance Engine credited ${response.integration.records_updated} subject periods as On-Duty.`, 'success');
      } else {
        App.showToast(response.message, 'success');
      }

      const modal = bootstrap.Modal.getInstance(document.getElementById('modal-admin-review'));
      if (modal) modal.hide();

      await this.loadDashboard();
    } catch (err) {
      App.showToast(err.message || 'Sanction action failed.', 'danger');
    }
  },

  // ==================== STUDENT CRUD ====================

  async loadStudents() {
    try {
      const data = await API.get('/admin/students');
      this.cachedStudents = data.students || [];
      this.renderStudentsTable(this.cachedStudents);
    } catch (err) {
      console.error('Error loading students', err);
    }
  },

  renderStudentsTable(students) {
    const tbody = document.getElementById('admin-students-tbody');
    if (!tbody) return;

    if (!students || students.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No student records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = students.map(s => {
      const attColor = s.attendance_percentage >= 75 ? 'success' : (s.attendance_percentage >= 65 ? 'warning' : 'danger');

      return `
        <tr>
          <td class="fw-bold font-monospace">${s.register_number}</td>
          <td>
            <div class="fw-bold">${s.name}</div>
            <div class="small text-muted">${s.email} &bull; ${s.phone || '—'}</div>
          </td>
          <td>${s.department}</td>
          <td>Year ${s.year} (${s.section})</td>
          <td class="small text-muted">${s.mentor_name || 'Unassigned'}</td>
          <td>
            <span class="badge bg-${attColor}-subtle text-${attColor} fw-bold">
              ${s.attendance_percentage}%
            </span>
          </td>
          <td>
            <div class="btn-group btn-group-sm">
              <button class="btn btn-outline-secondary" onclick="AdminModule.openEditStudentModal(${s.id})" title="Edit Student">
                <i class="fas fa-edit"></i>
              </button>
              <button class="btn btn-outline-danger" onclick="AdminModule.deleteStudent(${s.id})" title="Delete Student">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  },

  async handleAddStudent(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
      const response = await API.post('/admin/students', data);
      App.showToast(response.message, 'success');
      form.reset();
      bootstrap.Modal.getInstance(document.getElementById('modal-add-student')).hide();
      await this.loadStudents();
      await this.loadDashboard();
    } catch (err) {
      App.showToast(err.message || 'Failed to create student.', 'danger');
    }
  },

  openEditStudentModal(studentId) {
    const student = this.cachedStudents.find(s => s.id === studentId);
    if (!student) return;

    document.getElementById('edit-student-id').value = student.id;
    document.getElementById('edit-student-regno').value = student.register_number;
    document.getElementById('edit-student-name').value = student.name;
    document.getElementById('edit-student-dept').value = student.department;
    document.getElementById('edit-student-year').value = student.year;
    document.getElementById('edit-student-section').value = student.section;
    document.getElementById('edit-student-email').value = student.email;
    document.getElementById('edit-student-phone').value = student.phone || '';

    // Populate mentor options
    const mentorSelect = document.getElementById('edit-student-mentor');
    if (mentorSelect) {
      mentorSelect.innerHTML = `<option value="">-- Select Mentor --</option>` +
        this.cachedFaculty.map(f => `<option value="${f.id}" ${f.id === student.mentor_faculty_id ? 'selected' : ''}>${f.name} (${f.department})</option>`).join('');
    }

    const modal = new bootstrap.Modal(document.getElementById('modal-edit-student'));
    modal.show();
  },

  async handleEditStudent(e) {
    e.preventDefault();
    const form = e.target;
    const studentId = document.getElementById('edit-student-id').value;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
      const response = await API.put(`/admin/students/${studentId}`, data);
      App.showToast(response.message, 'success');
      bootstrap.Modal.getInstance(document.getElementById('modal-edit-student')).hide();
      await this.loadStudents();
    } catch (err) {
      App.showToast(err.message || 'Failed to update student.', 'danger');
    }
  },

  async deleteStudent(studentId) {
    if (!confirm('Are you sure you want to delete this student and their associated records?')) return;

    try {
      const response = await API.delete(`/admin/students/${studentId}`);
      App.showToast(response.message, 'success');
      await this.loadStudents();
      await this.loadDashboard();
    } catch (err) {
      App.showToast(err.message || 'Failed to delete student.', 'danger');
    }
  },

  // ==================== FACULTY CRUD ====================

  async loadFaculty() {
    try {
      const data = await API.get('/admin/faculty');
      this.cachedFaculty = data.faculty || [];
      this.renderFacultyTable(this.cachedFaculty);

      // Populate Mentor dropdown in Add Student modal
      const addMentorSelect = document.getElementById('add-student-mentor');
      if (addMentorSelect) {
        addMentorSelect.innerHTML = `<option value="">-- Select Mentor --</option>` +
          this.cachedFaculty.map(f => `<option value="${f.id}">${f.name} (${f.department})</option>`).join('');
      }
    } catch (err) {
      console.error('Error loading faculty', err);
    }
  },

  renderFacultyTable(facultyList) {
    const tbody = document.getElementById('admin-faculty-tbody');
    if (!tbody) return;

    if (!facultyList || facultyList.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No faculty records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = facultyList.map(f => `
      <tr>
        <td class="fw-bold font-monospace">${f.faculty_id}</td>
        <td>
          <div class="fw-bold">${f.name}</div>
          <div class="small text-muted">${f.email} &bull; ${f.phone || '—'}</div>
        </td>
        <td>${f.department}</td>
        <td class="small text-muted">${f.designation}</td>
        <td class="text-center">
          <span class="badge bg-primary-subtle text-primary fw-bold">
            ${f.mentored_students_count || 0} Students
          </span>
        </td>
        <td>
          <div class="btn-group btn-group-sm">
            <button class="btn btn-outline-secondary" onclick="AdminModule.openEditFacultyModal(${f.id})" title="Edit Faculty">
              <i class="fas fa-edit"></i>
            </button>
            <button class="btn btn-outline-danger" onclick="AdminModule.deleteFaculty(${f.id})" title="Delete Faculty">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  },

  async handleAddFaculty(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
      const response = await API.post('/admin/faculty', data);
      App.showToast(response.message, 'success');
      form.reset();
      bootstrap.Modal.getInstance(document.getElementById('modal-add-faculty')).hide();
      await this.loadFaculty();
      await this.loadDashboard();
    } catch (err) {
      App.showToast(err.message || 'Failed to create faculty member.', 'danger');
    }
  },

  openEditFacultyModal(facultyId) {
    const fac = this.cachedFaculty.find(f => f.id === facultyId);
    if (!fac) return;

    document.getElementById('edit-faculty-id').value = fac.id;
    document.getElementById('edit-faculty-code').value = fac.faculty_id;
    document.getElementById('edit-faculty-name').value = fac.name;
    document.getElementById('edit-faculty-dept').value = fac.department;
    document.getElementById('edit-faculty-desig').value = fac.designation;
    document.getElementById('edit-faculty-email').value = fac.email;
    document.getElementById('edit-faculty-phone').value = fac.phone || '';

    const modal = new bootstrap.Modal(document.getElementById('modal-edit-faculty'));
    modal.show();
  },

  async handleEditFaculty(e) {
    e.preventDefault();
    const form = e.target;
    const facultyId = document.getElementById('edit-faculty-id').value;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    try {
      const response = await API.put(`/admin/faculty/${facultyId}`, data);
      App.showToast(response.message, 'success');
      bootstrap.Modal.getInstance(document.getElementById('modal-edit-faculty')).hide();
      await this.loadFaculty();
    } catch (err) {
      App.showToast(err.message || 'Failed to update faculty.', 'danger');
    }
  },

  async deleteFaculty(facultyId) {
    if (!confirm('Are you sure you want to delete this faculty member?')) return;

    try {
      const response = await API.delete(`/admin/faculty/${facultyId}`);
      App.showToast(response.message, 'success');
      await this.loadFaculty();
      await this.loadDashboard();
    } catch (err) {
      App.showToast(err.message || 'Failed to delete faculty.', 'danger');
    }
  }
};
