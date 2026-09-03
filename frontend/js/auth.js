/**
 * Authentication and Session Management
 */

const Auth = {
  init() {
    this.bindEvents();
    this.checkSession();
  },

  bindEvents() {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
      loginForm.addEventListener('submit', (e) => this.handleLogin(e));
    }

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => this.handleLogout());
    }

    const forgotPasswordForm = document.getElementById('forgot-password-form');
    if (forgotPasswordForm) {
      forgotPasswordForm.addEventListener('submit', (e) => this.handleForgotPassword(e));
    }

    const changePasswordForm = document.getElementById('change-password-form');
    if (changePasswordForm) {
      changePasswordForm.addEventListener('submit', (e) => this.handleChangePassword(e));
    }
  },

  async handleLogin(e) {
    if (e) e.preventDefault();
    const usernameInput = document.getElementById('login-username');
    const passwordInput = document.getElementById('login-password');
    const submitBtn = document.getElementById('login-submit-btn');

    const username = usernameInput ? usernameInput.value.trim() : '';
    const password = passwordInput ? passwordInput.value.trim() : '';
    if (!username || !password) {
      App.showToast('Please enter both username/email and password.', 'warning');
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Authenticating...';
    }

    try {
      const response = await API.post('/auth/login', { username, password });
      API.setToken(response.token);
      API.setCurrentUser(response.user);

      if (response.user.must_change_password) {
        App.showToast('Temporary password detected. Please change it to continue.', 'warning');
        this.showChangePasswordModal();
      } else {
        App.showToast(`Welcome back, ${response.user.full_name}!`, 'success');
        this.routeUser(response.user);
      }
    } catch (err) {
      App.showToast(err.message || 'Login failed. Please check your credentials.', 'danger');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-sign-in-alt me-2"></i>Sign In to Portal';
      }
    }
  },




  showChangePasswordModal() {
    const modalEl = document.getElementById('modal-change-password');
    if (modalEl) {
      const modal = bootstrap.Modal.getOrCreateInstance(modalEl, { backdrop: 'static', keyboard: false });
      modal.show();
    }
  },

  async handleChangePassword(e) {
    e.preventDefault();
    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    const submitBtn = document.getElementById('change-password-submit');

    if (newPassword.length < 8) {
      App.showToast('New password must be at least 8 characters long.', 'warning');
      return;
    }
    if (newPassword !== confirmPassword) {
      App.showToast('New passwords do not match.', 'warning');
      return;
    }

    if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Updating...'; }
    try {
      const response = await API.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword
      });
      const user = API.getCurrentUser();
      if (user) {
        user.must_change_password = false;
        API.setCurrentUser(user);
      }
      bootstrap.Modal.getInstance(document.getElementById('modal-change-password')).hide();
      document.getElementById('change-password-form').reset();
      App.showToast(response.message, 'success');
      this.routeUser(user);
    } catch (err) {
      App.showToast(err.message || 'Unable to change password.', 'danger');
    } finally {
      if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Change Password'; }
    }
  },

  async handleForgotPassword(e) {
    e.preventDefault();
    const emailInput = document.getElementById('forgot-email');
    const email = emailInput ? emailInput.value.trim() : '';

    if (!email) {
      App.showToast('Please enter your registered email address.', 'warning');
      return;
    }

    try {
      const response = await API.post('/auth/forgot-password', { email });
      App.showToast(response.message, 'info');
      bootstrap.Modal.getInstance(document.getElementById('modal-forgot-password')).hide();
    } catch (err) {
      App.showToast(err.message, 'danger');
    }
  },

  handleLogout() {
    API.logout();
  },

  checkSession() {
    const user = API.getCurrentUser();
    const token = API.getToken();

    if (user && token) {
      if (user.must_change_password) {
        this.showChangePasswordModal();
      } else {
        this.routeUser(user);
      }
    } else {
      this.showLoginView();
    }
  },

  showLoginView() {
    document.getElementById('login-view').classList.remove('d-none');
    document.getElementById('app-shell').classList.add('d-none');
  },

  routeUser(user) {
    document.getElementById('login-view').classList.add('d-none');
    document.getElementById('app-shell').classList.remove('d-none');

    // Update Topbar and Sidebar User Info
    const userNameEl = document.getElementById('sidebar-user-name');
    const userRoleEl = document.getElementById('sidebar-user-role');
    const userAvatarEl = document.getElementById('sidebar-user-avatar');

    if (userNameEl) userNameEl.textContent = user.full_name;
    if (userRoleEl) userRoleEl.textContent = user.role.replace('_', ' ');
    if (userAvatarEl) {
      const initials = user.full_name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase();
      userAvatarEl.textContent = initials || 'U';
    }

    // Toggle Role-specific Nav Items
    document.querySelectorAll('.nav-role-student').forEach(el => el.classList.toggle('d-none', user.role !== 'STUDENT'));
    document.querySelectorAll('.nav-role-faculty').forEach(el => el.classList.toggle('d-none', user.role !== 'FACULTY'));
    document.querySelectorAll('.nav-role-admin').forEach(el => el.classList.toggle('d-none', user.role !== 'HOD_ADMIN'));

    // Switch view
    if (user.role === 'STUDENT') {
      App.switchView('student-dashboard');
      StudentModule.loadDashboard();
    } else if (user.role === 'FACULTY') {
      App.switchView('faculty-dashboard');
      FacultyModule.loadDashboard();
    } else if (user.role === 'HOD_ADMIN') {
      App.switchView('admin-dashboard');
      AdminModule.loadDashboard();
    }

    // Start background notification poll
    NotificationsModule.startPolling();
  }
};
