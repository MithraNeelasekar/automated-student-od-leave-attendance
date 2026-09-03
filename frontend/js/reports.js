/**
 * Reports & Analytics Module: Filterable Tables & CSV Export
 */

const ReportsModule = {
  init() {
    this.bindEvents();
  },

  bindEvents() {
    const genBtn = document.getElementById('report-generate-btn');
    if (genBtn) {
      genBtn.addEventListener('click', () => this.generateReport());
    }

    const exportBtn = document.getElementById('report-export-csv-btn');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => this.exportCSV());
    }
  },

  getParams() {
    return {
      type: document.getElementById('report-type-select')?.value || 'requests',
      department: document.getElementById('report-dept-select')?.value || '',
      year: document.getElementById('report-year-select')?.value || '',
      status: document.getElementById('report-status-select')?.value || ''
    };
  },

  async generateReport() {
    const params = this.getParams();
    const btn = document.getElementById('report-generate-btn');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';
    }

    try {
      const response = await API.get('/admin/reports', params);
      this.renderReportResults(response.report_type, response.data || []);
    } catch (err) {
      App.showToast(err.message || 'Failed to generate report.', 'danger');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-chart-bar me-2"></i>Generate Report';
      }
    }
  },

  renderReportResults(type, data) {
    const countEl = document.getElementById('report-result-count');
    if (countEl) countEl.textContent = `${data.length} records found`;

    const thead = document.getElementById('report-table-thead');
    const tbody = document.getElementById('report-table-tbody');

    if (!thead || !tbody) return;

    if (data.length === 0) {
      thead.innerHTML = '';
      tbody.innerHTML = `<tr><td class="text-center py-5 text-muted">No records match the selected report parameters.</td></tr>`;
      return;
    }

    if (type === 'attendance') {
      thead.innerHTML = `
        <tr>
          <th>Reg No</th>
          <th>Student Name</th>
          <th>Class</th>
          <th>Subject</th>
          <th class="text-center">Total Conducted</th>
          <th class="text-center">Present</th>
          <th class="text-center">Approved OD</th>
          <th class="text-center">Absent</th>
          <th>Effective Attendance</th>
        </tr>
      `;

      tbody.innerHTML = data.map(r => {
        const effColor = r.effective_percentage >= 75 ? 'success' : (r.effective_percentage >= 65 ? 'warning' : 'danger');
        return `
          <tr>
            <td class="fw-bold font-monospace">${r.register_number}</td>
            <td>${r.student_name}</td>
            <td>${r.department} - Y${r.year} (${r.section})</td>
            <td>${r.subject_name} <small class="text-muted">(${r.subject_code})</small></td>
            <td class="text-center fw-semibold">${r.total_classes}</td>
            <td class="text-center text-success">${r.present_count || 0}</td>
            <td class="text-center text-primary fw-bold">+${r.od_count || 0}</td>
            <td class="text-center text-danger">${r.absent_count || 0}</td>
            <td>
              <span class="badge bg-${effColor}-subtle text-${effColor} fw-bold">
                ${r.effective_percentage}%
              </span>
            </td>
          </tr>
        `;
      }).join('');
    } else {
      // Requests Report
      thead.innerHTML = `
        <tr>
          <th>Request Code</th>
          <th>Reg No & Student</th>
          <th>Class</th>
          <th>Type</th>
          <th>Event / Leave Detail</th>
          <th>Dates</th>
          <th>Status</th>
          <th>Attendance Integrated</th>
        </tr>
      `;

      tbody.innerHTML = data.map(r => {
        let statusBadge = '';
        if (r.status === 'APPROVED') {
          statusBadge = '<span class="badge-status badge-approved">Approved</span>';
        } else if (r.status === 'PENDING_HOD') {
          statusBadge = '<span class="badge-status badge-faculty-approved">Pending HOD</span>';
        } else if (r.status === 'PENDING_FACULTY') {
          statusBadge = '<span class="badge-status badge-pending">Pending Faculty</span>';
        } else {
          statusBadge = '<span class="badge-status badge-rejected">Rejected</span>';
        }

        return `
          <tr>
            <td class="fw-bold font-monospace text-primary">${r.request_code}</td>
            <td>
              <div class="fw-bold">${r.student_name}</div>
              <small class="text-muted font-monospace">${r.register_number}</small>
            </td>
            <td>${r.department} - Y${r.year} (${r.section})</td>
            <td><span class="badge ${r.request_type === 'OD' ? 'badge-od' : 'badge-leave'}">${r.request_type}</span></td>
            <td>
              <div class="fw-semibold">${r.event_name || r.leave_type || '—'}</div>
              <small class="text-muted text-truncate d-block" style="max-width: 180px;">${r.reason}</small>
            </td>
            <td class="small fw-semibold text-nowrap">${r.start_date} to ${r.end_date}</td>
            <td>${statusBadge}</td>
            <td>${r.attendance_updated ? '<span class="badge bg-success-subtle text-success"><i class="fas fa-check-double me-1"></i>Credited</span>' : '<span class="text-muted small">No</span>'}</td>
          </tr>
        `;
      }).join('');
    }
  },

  async exportCSV() {
    const params = this.getParams();
    params.export = 'true';

    try {
      const blob = await API.get('/admin/reports', params);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${params.type}_report_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      App.showToast('CSV report exported successfully!', 'success');
    } catch (err) {
      App.showToast('Failed to export CSV: ' + err.message, 'danger');
    }
  }
};
