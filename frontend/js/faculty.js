/**
 * Faculty Module: Dashboard, Request Review & Approval Workflow
 */

const FacultyModule = {
  currentRequestId: null,
  cachedPendingRequests: [],

  init() {
    this.bindEvents();
  },

  bindEvents() {
    const approveBtn = document.getElementById('faculty-modal-approve-btn');
    if (approveBtn) {
      approveBtn.addEventListener('click', () => this.submitReview('APPROVE'));
    }

    const rejectBtn = document.getElementById('faculty-modal-reject-btn');
    if (rejectBtn) {
      rejectBtn.addEventListener('click', () => this.submitReview('REJECT'));
    }
  },

  async loadDashboard() {
    const user = API.getCurrentUser();
    if (!user || user.role !== 'FACULTY') return;

    try {
      const [stats, pendingData] = await Promise.all([
        API.get('/faculty/dashboard'),
        API.get('/faculty/requests/pending')
      ]);

      this.renderKPIs(stats);
      this.cachedPendingRequests = pendingData.requests || [];
      this.renderPendingTable(this.cachedPendingRequests);
    } catch (err) {
      console.error('Error loading faculty dashboard', err);
    }
  },

  renderKPIs(stats) {
    const studentsEl = document.getElementById('faculty-kpi-students');
    const pendingOdEl = document.getElementById('faculty-kpi-pending-od');
    const pendingLeaveEl = document.getElementById('faculty-kpi-pending-leave');
    const approvedEl = document.getElementById('faculty-kpi-approved');
    const rejectedEl = document.getElementById('faculty-kpi-rejected');

    if (studentsEl) studentsEl.textContent = stats.total_students || 0;
    if (pendingOdEl) pendingOdEl.textContent = stats.pending_od || 0;
    if (pendingLeaveEl) pendingLeaveEl.textContent = stats.pending_leave || 0;
    if (approvedEl) approvedEl.textContent = stats.approved_requests || 0;
    if (rejectedEl) rejectedEl.textContent = stats.rejected_requests || 0;
  },

  renderPendingTable(requests) {
    const tbody = document.getElementById('faculty-pending-tbody');
    if (!tbody) return;

    if (!requests || requests.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5 text-muted"><i class="fas fa-check-circle text-success fs-3 mb-2 d-block"></i>No pending requests in your queue. All caught up!</td></tr>`;
      return;
    }

    tbody.innerHTML = requests.map(r => {
      const typeBadge = r.request_type === 'OD' 
        ? '<span class="badge badge-od"><i class="fas fa-award me-1"></i>OD</span>'
        : '<span class="badge badge-leave"><i class="fas fa-calendar-minus me-1"></i>Leave</span>';

      const attPerc = r.student_attendance_percentage || 100.0;
      const attColor = attPerc >= 75 ? 'success' : (attPerc >= 65 ? 'warning' : 'danger');

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
            <div class="small text-muted text-truncate" style="max-width: 200px;">${r.reason}</div>
          </td>
          <td class="small fw-semibold text-nowrap">${dateRange}</td>
          <td>
            <span class="badge bg-${attColor}-subtle text-${attColor} fw-bold">
              ${attPerc}% Attendance
            </span>
          </td>
          <td>
            <button class="btn btn-sm btn-primary-custom" onclick="FacultyModule.openReviewModal(${r.id})">
              <i class="fas fa-tasks me-1"></i>Review
            </button>
          </td>
        </tr>
      `;
    }).join('');
  },

  async openReviewModal(requestId) {
    this.currentRequestId = requestId;
    const req = this.cachedPendingRequests.find(r => r.id === requestId);
    if (!req) return;

    document.getElementById('faculty-modal-req-code').textContent = req.request_code;
    document.getElementById('faculty-modal-student').textContent = `${req.student_name} (${req.register_number})`;
    document.getElementById('faculty-modal-class').textContent = `${req.department} - Year ${req.year} Section ${req.section}`;
    document.getElementById('faculty-modal-type').textContent = `${req.request_type} - ${req.event_name || req.leave_type || ''}`;
    document.getElementById('faculty-modal-dates').textContent = `${req.start_date} to ${req.end_date}`;
    document.getElementById('faculty-modal-reason').textContent = req.reason;
    document.getElementById('faculty-modal-remarks').value = '';

    const docContainer = document.getElementById('faculty-modal-doc-preview');
    if (req.document_name) {
      docContainer.innerHTML = `
        <div class="d-flex align-items-center justify-content-between p-2 border rounded bg-light">
          <div class="d-flex align-items-center gap-2">
            <i class="fas fa-file-pdf text-danger fs-4"></i>
            <div>
              <div class="small fw-bold">${req.document_name}</div>
              <div class="text-muted" style="font-size: 0.72rem;">Attached supporting proof</div>
            </div>
          </div>
          <a href="${req.document_path || '#'}" target="_blank" class="btn btn-sm btn-outline-primary">
            <i class="fas fa-eye me-1"></i>Inspect File
          </a>
        </div>
      `;
    } else {
      docContainer.innerHTML = `<span class="text-muted small">No supporting document attached.</span>`;
    }

    const modal = new bootstrap.Modal(document.getElementById('modal-faculty-review'));
    modal.show();
  },

  async submitReview(action) {
    if (!this.currentRequestId) return;

    const remarksInput = document.getElementById('faculty-modal-remarks');
    const remarks = remarksInput ? remarksInput.value.trim() : '';

    if (action === 'REJECT' && !remarks) {
      App.showToast('Please provide mandatory remarks explaining why the request is rejected.', 'warning');
      remarksInput?.focus();
      return;
    }

    try {
      const endpoint = action === 'APPROVE' 
        ? `/faculty/requests/${this.currentRequestId}/approve`
        : `/faculty/requests/${this.currentRequestId}/reject`;

      const response = await API.put(endpoint, { remarks });
      App.showToast(response.message, 'success');

      const modal = bootstrap.Modal.getInstance(document.getElementById('modal-faculty-review'));
      if (modal) modal.hide();

      // Refresh dashboard
      await this.loadDashboard();
    } catch (err) {
      App.showToast(err.message || 'Action failed.', 'danger');
    }
  }
};
