/**
 * Student Module: Dashboard, Apply OD/Leave, My Requests, and Attendance Breakdown
 */

const StudentModule = {
  currentStudentId: null,
  cachedRequests: [],

  init() {
    this.bindEvents();
  },

  bindEvents() {
    // OD Form Submission
    const odForm = document.getElementById('form-apply-od');
    if (odForm) {
      odForm.addEventListener('submit', (e) => this.handleApplyOD(e));
    }

    // Leave Form Submission
    const leaveForm = document.getElementById('form-apply-leave');
    if (leaveForm) {
      leaveForm.addEventListener('submit', (e) => this.handleApplyLeave(e));
    }

    // Search and Filter in Requests Table
    const searchInput = document.getElementById('student-req-search');
    if (searchInput) {
      searchInput.addEventListener('input', () => this.filterRequestsTable());
    }

    const typeFilter = document.getElementById('student-req-type-filter');
    if (typeFilter) {
      typeFilter.addEventListener('change', () => this.filterRequestsTable());
    }

    const statusFilter = document.getElementById('student-req-status-filter');
    if (statusFilter) {
      statusFilter.addEventListener('change', () => this.filterRequestsTable());
    }
  },

  async loadDashboard() {
    const user = API.getCurrentUser();
    if (!user || user.role !== 'STUDENT') return;

    this.currentStudentId = user.profile ? user.profile.id : null;
    if (!this.currentStudentId) {
      try {
        const meData = await API.get('/auth/me');
        if (meData.user && meData.user.profile) {
          this.currentStudentId = meData.user.profile.id;
          API.setCurrentUser(meData.user);
        }
      } catch (err) {
        console.error('Failed to resolve student ID', err);
      }
    }

    if (this.currentStudentId) {
      await Promise.all([
        this.loadProfileAndAttendance(),
        this.loadMyRequests()
      ]);
    }
  },

  async loadProfileAndAttendance() {
    if (!this.currentStudentId) return;

    try {
      const data = await API.get(`/students/${this.currentStudentId}/attendance`);
      this.renderProfileBanner(data.student, data.overall);
      this.renderAttendanceKPIs(data.overall);
      this.renderSubjectAttendance(data.subjects);
      this.loadAttendanceHistory();
    } catch (err) {
      console.error('Error loading attendance', err);
    }
  },

  renderProfileBanner(student, overall) {
    const bannerName = document.getElementById('student-banner-name');
    const bannerMeta = document.getElementById('student-banner-meta');
    const bannerAvatar = document.getElementById('student-banner-avatar');

    if (bannerName) bannerName.textContent = student.name;
    if (bannerAvatar) {
      bannerAvatar.textContent = student.name.split(' ').map(n => n[0]).slice(0, 2).join('');
    }

    if (bannerMeta) {
      bannerMeta.innerHTML = `
        <div class="banner-meta-item"><i class="fas fa-id-card"></i> <strong>Reg No:</strong> ${student.register_number}</div>
        <div class="banner-meta-item"><i class="fas fa-graduation-cap"></i> <strong>Dept & Year:</strong> ${student.department} - Year ${student.year} (Sec ${student.section})</div>
        <div class="banner-meta-item"><i class="fas fa-user-tie"></i> <strong>Mentor:</strong> ${student.mentor_name || 'Class Advisor'}</div>
        <div class="banner-meta-item"><i class="fas fa-envelope"></i> ${student.email}</div>
      `;
    }
  },

  renderAttendanceKPIs(overall) {
    const percEl = document.getElementById('student-kpi-overall-perc');
    const attendedEl = document.getElementById('student-kpi-attended');
    const odEl = document.getElementById('student-kpi-od');
    const totalEl = document.getElementById('student-kpi-total');

    if (percEl) {
      percEl.textContent = `${overall.percentage}%`;
      percEl.className = `stat-value text-${overall.status_color}`;
    }
    if (attendedEl) attendedEl.textContent = overall.total_attended;
    if (odEl) odEl.textContent = overall.approved_od;
    if (totalEl) totalEl.textContent = overall.total_conducted;
  },

  renderSubjectAttendance(subjects) {
    const tbody = document.getElementById('student-subjects-tbody');
    if (!tbody) return;

    if (!subjects || subjects.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No subject attendance records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = subjects.map(s => `
      <tr>
        <td>
          <div class="fw-bold">${s.subject_name}</div>
          <div class="small text-muted font-monospace">${s.subject_code}</div>
        </td>
        <td class="small text-muted">${s.faculty_name}</td>
        <td class="text-center fw-semibold">${s.total_conducted}</td>
        <td class="text-center text-success fw-semibold">${s.classes_attended}</td>
        <td class="text-center">
          <span class="badge ${s.approved_od > 0 ? 'badge-od' : 'bg-light text-muted'}">
            +${s.approved_od} OD
          </span>
        </td>
        <td class="text-center text-danger fw-semibold">${s.classes_absent}</td>
        <td style="min-width: 170px;">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <span class="fw-bold text-${s.status_color}">${s.attendance_percentage}%</span>
            <span class="small badge bg-${s.status_color}-subtle text-${s.status_color}">${s.status_label}</span>
          </div>
          <div class="progress-container">
            <div class="progress-fill ${s.status_color}" style="width: ${Math.min(s.attendance_percentage, 100)}%;"></div>
          </div>
        </td>
      </tr>
    `).join('');
  },

  async loadAttendanceHistory() {
    const tbody = document.getElementById('student-history-tbody');
    if (!tbody || !this.currentStudentId) return;

    try {
      const data = await API.get(`/students/${this.currentStudentId}/history`);
      const history = data.history || [];

      if (history.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-3 text-muted">No daily attendance logs.</td></tr>`;
        return;
      }

      tbody.innerHTML = history.slice(0, 15).map(h => {
        let statusBadge = '';
        if (h.status === 'PRESENT') {
          statusBadge = '<span class="badge bg-success-subtle text-success"><i class="fas fa-check me-1"></i>Present</span>';
        } else if (h.status === 'ON_DUTY') {
          statusBadge = `<span class="badge badge-od"><i class="fas fa-award me-1"></i>On-Duty (${h.request_code || 'Approved OD'})</span>`;
        } else {
          statusBadge = '<span class="badge bg-danger-subtle text-danger"><i class="fas fa-times me-1"></i>Absent</span>';
        }

        const sourceLabel = h.source === 'OD_INTEGRATION'
          ? `<span class="badge bg-primary-subtle text-primary small"><i class="fas fa-sync-alt me-1"></i>Auto OD Credit</span>`
          : `<span class="text-muted small">Regular Class</span>`;

        return `
          <tr>
            <td class="fw-semibold">${h.attendance_date}</td>
            <td>
              <div>${h.subject_name}</div>
              <small class="text-muted">${h.subject_code}</small>
            </td>
            <td>${statusBadge}</td>
            <td>${sourceLabel}</td>
            <td>${h.request_code ? `<button class="btn btn-sm btn-link p-0 text-decoration-none" onclick="StudentModule.viewRequestDetailsByCode('${h.request_code}')">${h.request_code}</button>` : '—'}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      console.error('Error loading history', err);
    }
  },

  async loadMyRequests() {
    try {
      const data = await API.get('/requests/my');
      this.cachedRequests = data.requests || [];
      this.renderRequestsKPIs(data.stats);
      this.filterRequestsTable();
    } catch (err) {
      console.error('Error loading requests', err);
    }
  },

  renderRequestsKPIs(stats) {
    const pendingEl = document.getElementById('student-kpi-pending-req');
    const approvedEl = document.getElementById('student-kpi-approved-req');
    const rejectedEl = document.getElementById('student-kpi-rejected-req');

    if (pendingEl) pendingEl.textContent = stats ? stats.pending : 0;
    if (approvedEl) approvedEl.textContent = stats ? stats.approved : 0;
    if (rejectedEl) rejectedEl.textContent = stats ? stats.rejected : 0;
  },

  filterRequestsTable() {
    const tbody = document.getElementById('student-requests-tbody');
    if (!tbody) return;

    const search = (document.getElementById('student-req-search')?.value || '').toLowerCase();
    const type = document.getElementById('student-req-type-filter')?.value || '';
    const status = document.getElementById('student-req-status-filter')?.value || '';

    let filtered = this.cachedRequests.filter(r => {
      const matchSearch = !search || 
        r.request_code.toLowerCase().includes(search) || 
        (r.event_name && r.event_name.toLowerCase().includes(search)) || 
        r.reason.toLowerCase().includes(search);
      const matchType = !type || r.request_type === type;
      const matchStatus = !status || r.status === status;
      return matchSearch && matchType && matchStatus;
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-muted">No matching requests found.</td></tr>`;
      return;
    }

    tbody.innerHTML = filtered.map(r => {
      let statusBadge = '';
      if (r.status === 'PENDING_FACULTY') {
        statusBadge = '<span class="badge-status badge-pending"><i class="fas fa-clock"></i> Pending Faculty</span>';
      } else if (r.status === 'PENDING_HOD') {
        statusBadge = '<span class="badge-status badge-faculty-approved"><i class="fas fa-user-check"></i> Pending HOD</span>';
      } else if (r.status === 'APPROVED') {
        statusBadge = '<span class="badge-status badge-approved"><i class="fas fa-check-circle"></i> Approved</span>';
      } else {
        statusBadge = '<span class="badge-status badge-rejected"><i class="fas fa-times-circle"></i> Rejected</span>';
      }

      const typeBadge = r.request_type === 'OD' 
        ? '<span class="badge badge-od"><i class="fas fa-award me-1"></i>OD</span>'
        : '<span class="badge badge-leave"><i class="fas fa-calendar-minus me-1"></i>Leave</span>';

      const dateStr = r.start_date === r.end_date ? r.start_date : `${r.start_date} to ${r.end_date}`;
      const titleStr = r.request_type === 'OD' ? (r.event_name || 'OD Event') : (r.leave_type || 'Leave');

      return `
        <tr>
          <td class="fw-bold font-monospace text-primary">${r.request_code}</td>
          <td>${typeBadge}</td>
          <td>
            <div class="fw-semibold">${titleStr}</div>
            <div class="small text-muted text-truncate" style="max-width: 200px;">${r.reason}</div>
          </td>
          <td class="small fw-semibold text-nowrap">${dateStr}</td>
          <td>${statusBadge}</td>
          <td>
            ${r.attendance_updated 
              ? '<span class="badge bg-success-subtle text-success small"><i class="fas fa-check-double me-1"></i>Auto-Credited</span>' 
              : '<span class="text-muted small">Not Applied</span>'}
          </td>
          <td class="small text-muted">${r.created_at.split(' ')[0]}</td>
          <td>
            <button class="btn btn-sm btn-outline-primary" onclick="StudentModule.viewRequestDetails(${r.id})">
              <i class="fas fa-eye me-1"></i>View
            </button>
          </td>
        </tr>
      `;
    }).join('');
  },

  async handleApplyOD(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');

    const formData = new FormData(form);
    formData.append('request_type', 'OD');

    // Validation
    const startDate = formData.get('start_date');
    const endDate = formData.get('end_date') || startDate;
    const eventName = formData.get('event_name');
    const reason = formData.get('reason');

    if (!startDate || !eventName || !reason) {
      App.showToast('Please fill in all mandatory OD fields.', 'warning');
      return;
    }

    if (endDate < startDate) {
      App.showToast('End date cannot be earlier than start date.', 'danger');
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Submitting...';
    }

    try {
      const response = await API.post('/requests', formData);
      App.showToast(`OD Request ${response.request_code} submitted successfully!`, 'success');
      form.reset();
      
      const modal = bootstrap.Modal.getInstance(document.getElementById('modal-apply-od'));
      if (modal) modal.hide();

      // Refresh dashboard
      await this.loadDashboard();
    } catch (err) {
      App.showToast(err.message || 'Failed to submit OD request.', 'danger');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Submit OD Request';
      }
    }
  },

  async handleApplyLeave(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');

    const formData = new FormData(form);
    formData.append('request_type', 'LEAVE');

    const startDate = formData.get('start_date');
    const endDate = formData.get('end_date') || startDate;
    const leaveType = formData.get('leave_type');
    const reason = formData.get('reason');

    if (!startDate || !leaveType || !reason) {
      App.showToast('Please fill in all required Leave fields.', 'warning');
      return;
    }

    if (endDate < startDate) {
      App.showToast('End date cannot be earlier than start date.', 'danger');
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Submitting...';
    }

    try {
      const response = await API.post('/requests', formData);
      App.showToast(`Leave Request ${response.request_code} submitted successfully!`, 'success');
      form.reset();

      const modal = bootstrap.Modal.getInstance(document.getElementById('modal-apply-leave'));
      if (modal) modal.hide();

      // Refresh dashboard
      await this.loadDashboard();
    } catch (err) {
      App.showToast(err.message || 'Failed to submit Leave request.', 'danger');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Submit Leave Request';
      }
    }
  },

  async viewRequestDetails(requestId) {
    try {
      const data = await API.get(`/requests/${requestId}`);
      this.renderRequestDetailsModal(data);
      const modal = new bootstrap.Modal(document.getElementById('modal-request-details'));
      modal.show();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  },

  viewRequestDetailsByCode(requestCode) {
    const found = this.cachedRequests.find(r => r.request_code === requestCode);
    if (found) {
      this.viewRequestDetails(found.id);
    }
  },

  renderRequestDetailsModal(data) {
    const req = data.request;
    const timeline = data.timeline || [];

    document.getElementById('modal-req-code').textContent = req.request_code;
    document.getElementById('modal-req-type-badge').innerHTML = req.request_type === 'OD'
      ? '<span class="badge badge-od">ON DUTY (OD)</span>'
      : '<span class="badge badge-leave">LEAVE</span>';

    // Status Badge
    let statusBadge = '';
    if (req.status === 'PENDING_FACULTY') {
      statusBadge = '<span class="badge-status badge-pending">Pending Faculty Review</span>';
    } else if (req.status === 'PENDING_HOD') {
      statusBadge = '<span class="badge-status badge-faculty-approved">Forwarded to HOD</span>';
    } else if (req.status === 'APPROVED') {
      statusBadge = '<span class="badge-status badge-approved">Approved</span>';
    } else {
      statusBadge = '<span class="badge-status badge-rejected">Rejected</span>';
    }
    document.getElementById('modal-req-status-badge').innerHTML = statusBadge;

    // Student Info
    document.getElementById('modal-req-student-info').innerHTML = `
      <div class="row g-2">
        <div class="col-sm-6"><strong>Student:</strong> ${req.student_name} (${req.register_number})</div>
        <div class="col-sm-6"><strong>Department:</strong> ${req.department} - Year ${req.year} (${req.section})</div>
        <div class="col-sm-6"><strong>Email:</strong> ${req.student_email || '—'}</div>
        <div class="col-sm-6"><strong>Class Advisor/Mentor:</strong> ${req.mentor_name || 'Assigned Faculty'}</div>
      </div>
    `;

    // Request Details
    let detailsHtml = `
      <div class="row g-2">
        <div class="col-sm-6"><strong>Dates:</strong> ${req.start_date} to ${req.end_date}</div>
        <div class="col-sm-6"><strong>Submitted On:</strong> ${req.created_at}</div>
    `;

    if (req.request_type === 'OD') {
      detailsHtml += `
        <div class="col-sm-6"><strong>Event Name:</strong> ${req.event_name || '—'}</div>
        <div class="col-sm-6"><strong>Event Type:</strong> ${req.event_type || '—'}</div>
        <div class="col-12"><strong>Venue:</strong> ${req.venue || '—'}</div>
      `;
    } else {
      detailsHtml += `
        <div class="col-sm-6"><strong>Leave Type:</strong> ${req.leave_type || '—'}</div>
      `;
    }

    detailsHtml += `
        <div class="col-12 mt-2"><strong>Reason / Description:</strong><br><div class="p-2 bg-light rounded mt-1">${req.reason}</div></div>
    `;

    if (req.student_remarks) {
      detailsHtml += `<div class="col-12 mt-2"><strong>Student Remarks:</strong><br><div class="small text-muted">${req.student_remarks}</div></div>`;
    }

    if (req.document_name) {
      detailsHtml += `
        <div class="col-12 mt-2">
          <strong>Supporting Document:</strong><br>
          <div class="d-inline-flex align-items-center gap-2 mt-1 p-2 border rounded bg-white">
            <i class="fas fa-file-pdf text-danger fs-5"></i>
            <span class="small fw-semibold">${req.document_name}</span>
            <a href="${req.document_path || '#'}" target="_blank" class="btn btn-sm btn-outline-primary ms-2">
              <i class="fas fa-external-link-alt me-1"></i>View File
            </a>
          </div>
        </div>
      `;
    }

    detailsHtml += `</div>`;
    document.getElementById('modal-req-details-content').innerHTML = detailsHtml;

    // Attendance Integration Status
    const attStatusEl = document.getElementById('modal-req-attendance-status');
    if (attStatusEl) {
      if (req.attendance_updated) {
        attStatusEl.innerHTML = `
          <div class="alert alert-success d-flex align-items-center mb-0 py-2">
            <i class="fas fa-check-double fs-4 me-3"></i>
            <div>
              <div class="fw-bold">Attendance Integrated Automatically</div>
              <div class="small">Class periods during this approved OD were converted to On-Duty credit.</div>
            </div>
          </div>
        `;
      } else if (req.status === 'APPROVED' && req.request_type === 'LEAVE') {
        attStatusEl.innerHTML = `
          <div class="alert alert-info py-2 mb-0 small">
            <i class="fas fa-info-circle me-1"></i> Leave request approved for record and sanction.
          </div>
        `;
      } else {
        attStatusEl.innerHTML = `
          <div class="alert alert-secondary py-2 mb-0 small">
            <i class="fas fa-shield-alt me-1"></i> Attendance is untouched during pending review. Updates automatically upon final HOD approval.
          </div>
        `;
      }
    }

    // Render Timeline Stepper
    const timelineEl = document.getElementById('modal-req-timeline');
    if (timelineEl) {
      timelineEl.innerHTML = timeline.map(step => {
        let icon = '<i class="fas fa-check"></i>';
        let stepClass = 'completed';

        if (step.action.includes('REJECTED')) {
          icon = '<i class="fas fa-times"></i>';
          stepClass = 'rejected';
        } else if (step.action === 'SUBMITTED') {
          icon = '<i class="fas fa-paper-plane"></i>';
        }

        return `
          <div class="timeline-step ${stepClass}">
            <div class="timeline-step-icon">${icon}</div>
            <div class="timeline-title">${step.action.replace('_', ' ')}</div>
            <div class="timeline-meta">${step.approver_name || step.approver_role} &bull; ${step.action_date}</div>
            ${step.remarks ? `<div class="timeline-remarks"><i class="fas fa-comment-dots me-1 text-primary"></i> ${step.remarks}</div>` : ''}
          </div>
        `;
      }).join('');
    }
  }
};
