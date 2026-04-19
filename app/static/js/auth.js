let tempEmail = null;
let tempPassword = null;

async function handleLogin() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    if (!email || !password) {
        showAlert('login', 'Please enter your email and password', 'error');
        return;
    }

    setLoading('loginBtn', true, 'Sign In');

    try {
        const {status, data} = await API.login(email, password);

        if (data.token_type === 'mfa_required') {
            tempEmail = email;
            tempPassword = password;
            showScreen('mfaScreen');
            return;
        }

        if (status !== 200) {
            showAlert('login', data.detail || 'Login failed', 'error');
            return;
        }

        AppState.accessToken = data.access_token;
        AppState.refreshToken = data.refresh_token;
        scheduleTokenRefresh(data.access_token);
        await loadDashboard();

    } catch (err) {
        showAlert('login', 'Connection error. Is the server running?', 'error');
    } finally {
        setLoading('loginBtn', false, 'Sign In');
    }
}

async function handleMFALogin() {
    const code = document.getElementById('mfaCode').value;

    if (!code || code.length !== 6) {
        showAlert('mfa', 'Please enter a 6-digit code', 'error');
        return;
    }

    setLoading('mfaBtn', true, 'Verify Code');

    try {
        const {status, data} = await API.loginMFA(tempEmail, tempPassword, code);

        if (status !== 200) {
            showAlert('mfa', data.detail || 'Invalid MFA code', 'error');
            return;
        }

        AppState.accessToken = data.access_token;
        AppState.refreshToken = data.refresh_token;
        scheduleTokenRefresh(data.access_token);
        tempEmail = null;
        tempPassword = null;
        await loadDashboard();

    } catch (err) {
        showAlert('mfa', 'Connection error', 'error');
    } finally {
        setLoading('mfaBtn', false, 'Verify Code');
    }
}

async function handleLogout() {
    clearTimeout(AppState.refreshTimer);
    AppState.refreshTimer = null;
    sessionStorage.removeItem('adminToken');
    try {
        await API.logout(AppState.refreshToken);
    } catch (err) {}

    AppState.accessToken = null;
    AppState.refreshToken = null;
    document.getElementById('loginEmail').value = '';
    document.getElementById('loginPassword').value = '';
    document.getElementById('mfaCode').value = '';
    showScreen('loginScreen');
}

async function handleRefreshToken() {
    try {
        const {status, data} = await API.refresh(AppState.refreshToken);

        if (status !== 200) {
            showAlert('dashboard', 'Session expired. Please login again.', 'error');
            setTimeout(() => showScreen('loginScreen'), 2000);
            return;
        }

        AppState.accessToken = data.access_token;
        AppState.refreshToken = data.refresh_token;
        sessionStorage.setItem('adminToken', data.access_token);
        scheduleTokenRefresh(data.access_token);
        showAlert('dashboard', 'Token refreshed successfully!', 'success');

    } catch (err) {
        showAlert('dashboard', 'Connection error', 'error');
    }
}

async function handleForgotPassword() {
    const email = document.getElementById('resetEmail').value;
    if (!email) {
        showAlert('reset', 'Please enter your email', 'error');
        return;
    }

    try {
        const {data} = await API.forgotPassword(email);
        if (data.reset_token) {
            document.getElementById('resetToken').value = data.reset_token;
            document.getElementById('resetTokenSection').style.display = 'block';
            showAlert('reset', 'Reset token generated! Enter it below.', 'success');
        }
    } catch (err) {
        showAlert('reset', 'Connection error', 'error');
    }
}

async function handleResetPassword() {
    const token = document.getElementById('resetToken').value;
    const newPassword = document.getElementById('newPassword').value;

    if (!token || !newPassword) {
        showAlert('reset', 'Please fill in all fields', 'error');
        return;
    }

    try {
        const {status, data} = await API.resetPassword(token, newPassword);

        if (status !== 200) {
            showAlert('reset', data.detail || 'Reset failed', 'error');
            return;
        }

        showAlert('reset', 'Password reset! Please login with your new password.', 'success');
        setTimeout(() => showScreen('loginScreen'), 2000);

    } catch (err) {
        showAlert('reset', 'Connection error', 'error');
    }
}
