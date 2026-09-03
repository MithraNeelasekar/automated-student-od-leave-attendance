/**
 * Notification Center Module
 */

const NotificationsModule = {
  pollInterval: null,

  init() {
    this.bindEvents();
  },

  bindEvents() {
    const notifBtn = document.getElementById('topbar-notif-btn');
    if (notifBtn) {
      notifBtn.addEventListener('click', () => this.openNotificationsModal());
    }

    const markAllReadBtn = document.getElementById('notif-mark-all-read-btn');
    if (markAllReadBtn) {
      markAllReadBtn.addEventListener('click', () => this.markAllRead());
    }
  },

  startPolling() {
    this.fetchUnreadCount();
    if (this.pollInterval) clearInterval(this.pollInterval);
    this.pollInterval = setInterval(() => this.fetchUnreadCount(), 15000); // 15s poll
  },

  stopPolling() {
    if (this.pollInterval) clearInterval(this.pollInterval);
  },

  async fetchUnreadCount() {
    if (!API.getToken()) return;
    try {
      const data = await API.get('/notifications/unread-count');
      const badge = document.getElementById('topbar-notif-badge');
      if (badge) {
        const count = data.unread_count || 0;
        badge.textContent = count;
        badge.classList.toggle('d-none', count === 0);
      }
    } catch {
      // Ignore background poll errors
    }
  },

  async openNotificationsModal() {
    try {
      const data = await API.get('/notifications?limit=30');
      this.renderNotificationList(data.notifications || []);
      const modal = new bootstrap.Modal(document.getElementById('modal-notifications'));
      modal.show();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  },

  renderNotificationList(notifications) {
    const listEl = document.getElementById('notifications-list-container');
    if (!listEl) return;

    if (notifications.length === 0) {
      listEl.innerHTML = `<div class="text-center py-5 text-muted"><i class="fas fa-bell-slash fs-2 mb-2 d-block"></i>No notifications yet.</div>`;
      return;
    }

    listEl.innerHTML = notifications.map(n => `
      <div class="p-3 border-bottom d-flex align-items-start gap-3 ${n.is_read ? 'bg-white' : 'bg-primary-subtle bg-opacity-25'}" id="notif-item-${n.id}">
        <div class="mt-1">
          <div class="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center" style="width: 32px; height: 32px; font-size: 0.85rem;">
            <i class="fas fa-bell"></i>
          </div>
        </div>
        <div class="flex-grow-1">
          <div class="d-flex justify-content-between align-items-center">
            <div class="fw-bold fs-6">${n.title}</div>
            <span class="small text-muted" style="font-size: 0.75rem;">${n.created_at}</span>
          </div>
          <div class="small text-muted mt-1">${n.message}</div>
          ${n.link ? `<div class="mt-1"><span class="badge bg-secondary font-monospace">${n.link}</span></div>` : ''}
        </div>
        <div>
          ${!n.is_read ? `
            <button class="btn btn-sm btn-link text-decoration-none p-0" onclick="NotificationsModule.markRead(${n.id})" title="Mark as Read">
              <i class="fas fa-check-circle text-primary"></i>
            </button>
          ` : ''}
        </div>
      </div>
    `).join('');
  },

  async markRead(notificationId) {
    try {
      await API.put(`/notifications/${notificationId}/read`);
      const item = document.getElementById(`notif-item-${notificationId}`);
      if (item) {
        item.classList.remove('bg-primary-subtle', 'bg-opacity-25');
        item.classList.add('bg-white');
      }
      this.fetchUnreadCount();
    } catch (err) {
      console.error(err);
    }
  },

  async markAllRead() {
    try {
      await API.put('/notifications/read-all');
      this.fetchUnreadCount();
      const modal = bootstrap.Modal.getInstance(document.getElementById('modal-notifications'));
      if (modal) modal.hide();
      App.showToast('All notifications marked as read.', 'success');
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  }
};
