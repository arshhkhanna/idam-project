const AppState = {
    accessToken: null,
    refreshToken: null,
    refreshTimer: null
};

function scheduleTokenRefresh(accessToken) {
    clearTimeout(AppState.refreshTimer);
    try {
        const payload = JSON.parse(atob(accessToken.split('.')[1]));
        const delay = payload.exp * 1000 - Date.now() - 60000; // 60s before expiry
        if (delay > 0) {
            AppState.refreshTimer = setTimeout(handleRefreshToken, delay);
        }
    } catch (e) {}
}

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

function showAlert(screenPrefix, message, type) {
    const alert = document.getElementById(screenPrefix + 'Alert');
    if (!alert) return;
    alert.textContent = message;
    alert.className = 'alert ' + type;
    alert.style.display = 'block';
    setTimeout(() => alert.style.display = 'none', 4000);
}

function setLoading(btnId, loading, originalText) {
    const btn = document.getElementById(btnId);
    if (loading) {
        btn.innerHTML = '<span class="spinner"></span>Please wait...';
        btn.disabled = true;
    } else {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function updateFileName() {
    const input = document.getElementById('fileInput');
    const label = document.getElementById('selectedFileName');
    if (input.files[0]) {
        label.textContent = `Selected: ${input.files[0].name}`;
    }
}

function openAdminPanel() {
    sessionStorage.setItem('adminToken', AppState.accessToken);
    window.open('/admin-panel', '_blank');
}

async function loadDashboard() {
    try {
        const {status, data} = await API.getProfile(AppState.accessToken);
        if (status !== 200) {
            showAlert('dashboard', 'Could not load profile', 'error');
            return;
        }

        document.getElementById('userEmail').textContent = data.email;
        document.getElementById('tokenInfo').textContent =
            'Access token active • Refresh token valid for 7 days';

        if (data.roles && data.roles.length > 0) {
            document.getElementById('userRoles').textContent =
                'Roles: ' + data.roles.join(', ');
        }

        const adminRoles = ['super_admin', 'admin', 'security_analyst', 'monitor_audit'];
        const hasAdminAccess = data.roles && data.roles.some(r => adminRoles.includes(r));
        const adminBtn = document.getElementById('adminPanelBtn');
        if (adminBtn) {
            adminBtn.style.display = hasAdminAccess ? 'block' : 'none';
        }

        showScreen('dashboardScreen');
        await loadFiles();

    } catch (err) {
        showAlert('dashboard', 'Connection error', 'error');
    }
}

async function getProfile() {
    try {
        const {status, data} = await API.getProfile(AppState.accessToken);
        if (status !== 200) {
            showAlert('dashboard', 'Session expired. Please login again.', 'error');
            setTimeout(() => showScreen('loginScreen'), 2000);
            return;
        }
        document.getElementById('userEmail').textContent = data.email;

        if (data.roles && data.roles.length > 0) {
            document.getElementById('userRoles').textContent =
                'Roles: ' + data.roles.join(', ');
        }

        showAlert('dashboard', 'Profile refreshed!', 'success');
        await loadFiles();
    } catch (err) {
        showAlert('dashboard', 'Could not load profile', 'error');
    }
}

document.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    const active = document.querySelector('.screen.active').id;
    if (active === 'loginScreen') handleLogin();
    if (active === 'mfaScreen') handleMFALogin();
});
