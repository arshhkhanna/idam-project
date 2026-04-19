function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;');
}

let token = null;
let allUsers = [];
let allFiles = [];
let allAuditLogs = [];
let selectedFileId = null;
let selectedUserId = null;

// Populated on load from the logged-in user's roles
const adminPerms = {
    canReadUsers: false,
    canWriteUsers: false,
    canWriteRoles: false,
    canReadAudit: false,
    canReadRoles: false,
    canManageFiles: false
};

window.onload = async () => {
    token = sessionStorage.getItem('adminToken');
    sessionStorage.removeItem('adminToken'); // one-time use — prevents stale token reuse
    if (!token) {
        window.location.href = '/';
        return;
    }

    // Verify token works
    const res = await fetch('/users/me', {
        headers: {'Authorization': 'Bearer ' + token}
    });

    if (!res.ok) {
        sessionStorage.removeItem('adminToken');
        alert('Session expired. Please login again.');
        window.location.href = '/';
        return;
    }

    const user = await res.json();
    document.getElementById('adminEmail').textContent = user.email;

    const adminPanelRoles = ['super_admin', 'admin', 'security_analyst', 'monitor_audit'];
    if (!user.roles || !user.roles.some(r => adminPanelRoles.includes(r))) {
        alert('You do not have admin access.');
        window.location.href = '/';
        return;
    }

    // Derive permissions from roles (mirrors the backend permission diagram)
    const roles = new Set(user.roles);
    adminPerms.canReadUsers   = ['super_admin', 'admin', 'security_analyst'].some(r => roles.has(r));
    adminPerms.canWriteUsers  = ['super_admin', 'admin'].some(r => roles.has(r));
    adminPerms.canWriteRoles  = ['super_admin', 'admin'].some(r => roles.has(r));
    adminPerms.canReadAudit   = ['super_admin', 'security_analyst', 'monitor_audit'].some(r => roles.has(r));
    adminPerms.canReadRoles   = ['super_admin', 'admin'].some(r => roles.has(r));
    adminPerms.canManageFiles = roles.has('super_admin');

    // Show only tabs the user has access to; activate the first visible one
    const tabAccess = {
        users: adminPerms.canReadUsers,
        files: adminPerms.canManageFiles,
        roles: adminPerms.canReadRoles,
        audit: adminPerms.canReadAudit
    };
    let firstTab = null;
    document.querySelectorAll('.nav-item[data-tab]').forEach(btn => {
        const tab = btn.dataset.tab;
        if (tabAccess[tab]) {
            btn.style.display = '';
            if (!firstTab) firstTab = tab;
        } else {
            btn.style.display = 'none';
        }
    });
    if (firstTab) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        document.getElementById(firstTab + 'Tab').classList.add('active');
        document.querySelector(`.nav-item[data-tab="${firstTab}"]`).classList.add('active');
        const titles = { users: 'Users', files: 'Files', roles: 'Roles & Permissions', audit: 'Audit Logs' };
        document.getElementById('tabTitle').textContent = titles[firstTab];
    }

    // Load only data the user can access
    if (adminPerms.canReadUsers)   await loadUsers();
    if (adminPerms.canManageFiles) await loadFiles();
    if (adminPerms.canReadRoles)   await loadRoles();
    if (adminPerms.canReadAudit)   await loadAuditLogs();
};

function showTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById(tab + 'Tab').classList.add('active');
    event.target.classList.add('active');
    const titles = {
        users: 'Users',
        files: 'Files',
        roles: 'Roles & Permissions',
        audit: 'Audit Logs'
    };
    document.getElementById('tabTitle').textContent = titles[tab];
}

function showAdminAlert(message, type) {
    const alert = document.getElementById('adminAlert');
    alert.textContent = message;
    alert.className = 'alert ' + type;
    alert.style.display = 'block';
    setTimeout(() => alert.style.display = 'none', 4000);
}

async function loadUsers() {
    const res = await fetch('/admin/users/detailed', {
        headers: {'Authorization': 'Bearer ' + token}
    });
    if (!res.ok) return;
    allUsers = await res.json();
    renderUsers(allUsers);
}

function renderUsers(users) {
    const tbody = document.getElementById('usersTable');
    tbody.innerHTML = users.map(u => `
        <tr>
            <td>${u.id}</td>
            <td>${escapeHtml(u.email)}</td>
            <td><span class="tag ${u.is_active ? 'tag-active' : 'tag-inactive'}">
                ${u.is_active ? '● Active' : '● Inactive'}</span></td>
            <td><span class="tag ${u.mfa_enabled ? 'tag-mfa' : 'tag-no-mfa'}">
                ${u.mfa_enabled ? '🔐 On' : '○ Off'}</span></td>
            <td>${u.roles.map(r => `<span class="tag tag-role">${escapeHtml(r)}</span>`).join('') || '<span style="color:#64748b">None</span>'}</td>
            <td>
                ${adminPerms.canWriteRoles ? `<button class="btn-action btn-assign" data-uid="${u.id}" data-email="${escapeHtml(u.email)}">+ Role</button>` : ''}
                ${adminPerms.canWriteUsers ? `<button class="btn-action ${u.is_active ? 'btn-disable' : 'btn-enable'}" data-uid="${u.id}" data-action="${u.is_active ? 'disable' : 'enable'}">${u.is_active ? 'Disable' : 'Enable'}</button>` : ''}
            </td>
        </tr>
    `).join('');

    if (adminPerms.canWriteRoles) {
        tbody.querySelectorAll('.btn-assign').forEach(btn => {
            btn.addEventListener('click', () => openRoleModal(parseInt(btn.dataset.uid), btn.dataset.email));
        });
    }
    if (adminPerms.canWriteUsers) {
        tbody.querySelectorAll('[data-action="disable"]').forEach(btn => {
            btn.addEventListener('click', () => disableUser(parseInt(btn.dataset.uid)));
        });
        tbody.querySelectorAll('[data-action="enable"]').forEach(btn => {
            btn.addEventListener('click', () => enableUser(parseInt(btn.dataset.uid)));
        });
    }
}

function filterUsers() {
    const q = document.getElementById('userSearch').value.toLowerCase();
    renderUsers(allUsers.filter(u =>
        u.email.toLowerCase().includes(q) ||
        u.roles.some(r => r.includes(q))
    ));
}

async function disableUser(userId) {
    if (!confirm('Disable this user?')) return;
    const res = await fetch(`/admin/users/${userId}/disable`, {
        method: 'PATCH',
        headers: {'Authorization': 'Bearer ' + token}
    });
    if (res.ok) {
        showAdminAlert('User disabled', 'success');
        await loadUsers();
    }
}

async function enableUser(userId) {
    if (!confirm('Approve and enable this user?')) return;
    const res = await fetch(`/admin/users/${userId}/enable`, {
        method: 'PATCH',
        headers: {'Authorization': 'Bearer ' + token}
    });
    if (res.ok) {
        showAdminAlert('User approved and enabled', 'success');
        await loadUsers();
    } else {
        showAdminAlert('Failed to enable user', 'error');
    }
}

async function loadFiles() {
    const res = await fetch('/admin/files', {
        headers: {'Authorization': 'Bearer ' + token}
    });
    if (!res.ok) return;
    allFiles = await res.json();
    renderFiles(allFiles);
}

function renderFiles(files) {
    const tbody = document.getElementById('filesTable');
    if (!files.length) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#64748b; padding:32px;">No files uploaded yet</td></tr>';
        return;
    }
    tbody.innerHTML = files.map(f => `
        <tr>
            <td>${f.id}</td>
            <td>${getFileIcon(f.file_type)} ${escapeHtml(f.original_name)}</td>
            <td><span style="color:#64748b">${escapeHtml(f.file_type)}</span></td>
            <td>${formatSize(f.file_size)}</td>
            <td>${f.allowed_roles.map(r => `<span class="tag tag-role">${escapeHtml(r)}</span>`).join('') || '<span style="color:#64748b">None assigned</span>'}</td>
            <td>
                <button class="btn-action btn-assign" data-fid="${f.id}" data-name="${escapeHtml(f.original_name)}">🔒 Access</button>
                <button class="btn-action btn-delete-file" data-fid="${f.id}">🗑</button>
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('.btn-assign').forEach(btn => {
        btn.addEventListener('click', () => openAssignModal(parseInt(btn.dataset.fid), btn.dataset.name));
    });
    tbody.querySelectorAll('.btn-delete-file').forEach(btn => {
        btn.addEventListener('click', () => deleteFileAdmin(parseInt(btn.dataset.fid)));
    });
}

function filterFiles() {
    const q = document.getElementById('fileSearch').value.toLowerCase();
    renderFiles(allFiles.filter(f => f.original_name.toLowerCase().includes(q)));
}

async function deleteFileAdmin(fileId) {
    if (!confirm('Delete this file permanently?')) return;
    const res = await fetch(`/files/${fileId}`, {
        method: 'DELETE',
        headers: {'Authorization': 'Bearer ' + token}
    });
    if (res.ok) {
        showAdminAlert('File deleted', 'success');
        await loadFiles();
    }
}

function getFileIcon(type) {
    if (type.includes('pdf')) return '📄';
    if (type.includes('image')) return '🖼️';
    if (type.includes('word') || type.includes('document')) return '📝';
    if (type.includes('sheet') || type.includes('excel')) return '📊';
    return '📎';
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

async function loadRoles() {
    const res = await fetch('/roles/', {
        headers: {'Authorization': 'Bearer ' + token}
    });
    if (!res.ok) return;
    const roles = await res.json();
    renderRoles(roles);
}

function renderRoles(roles) {
    const grid = document.getElementById('rolesGrid');
    grid.innerHTML = roles.map(r => `
        <div class="role-card">
            <h3>${escapeHtml(r.name)}</h3>
            <p>${escapeHtml(r.description)}</p>
            <div class="permission-list">
                ${r.permissions.map(p =>
                    `<span class="permission-tag">${escapeHtml(p.resource)}:${escapeHtml(p.action)}</span>`
                ).join('')}
            </div>
        </div>
    `).join('');
}

async function loadAuditLogs() {
    const res = await fetch('/admin/audit-logs', {
        headers: {'Authorization': 'Bearer ' + token}
    });
    if (!res.ok) return;
    allAuditLogs = await res.json();
    renderAuditLogs(allAuditLogs);
}

function renderAuditLogs(logs) {
    const tbody = document.getElementById('auditTable');
    tbody.innerHTML = logs.map(l => `
        <tr>
            <td>${l.id}</td>
            <td>${escapeHtml(l.email || '—')}</td>
            <td><code style="color:#a5b4fc">${escapeHtml(l.action)}</code></td>
            <td><span class="tag ${l.status === 'success' ? 'tag-success' : 'tag-failed'}">
                ${escapeHtml(l.status)}</span></td>
            <td>${escapeHtml(l.ip_address || '—')}</td>
            <td style="color:#64748b">${escapeHtml(l.details || '—')}</td>
        </tr>
    `).join('');
}

function filterAudit() {
    const q = document.getElementById('auditSearch').value.toLowerCase();
    renderAuditLogs(allAuditLogs.filter(l =>
        (l.email || '').toLowerCase().includes(q) ||
        l.action.toLowerCase().includes(q) ||
        l.status.toLowerCase().includes(q)
    ));
}

function openAssignModal(fileId, fileName) {
    selectedFileId = fileId;
    document.getElementById('modalFileName').textContent = `File: ${fileName}`;
    const file = allFiles.find(f => f.id === fileId);
    if (file) {
        document.getElementById('modalRoles').value = file.allowed_roles.join(', ');
        document.getElementById('modalUsers').value = file.allowed_users.join(', ');
    }
    document.getElementById('assignModal').classList.add('open');
}

function closeModal() {
    document.getElementById('assignModal').classList.remove('open');
    selectedFileId = null;
}

async function submitAssignment() {
    const roleNames = document.getElementById('modalRoles').value
        .split(',').map(r => r.trim()).filter(r => r);
    const userIds = document.getElementById('modalUsers').value
        .split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));

    const res = await fetch(`/files/assign/${selectedFileId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({role_names: roleNames, user_ids: userIds})
    });

    if (res.ok) {
        showAdminAlert('Access assigned successfully!', 'success');
        closeModal();
        await loadFiles();
    } else {
        showAdminAlert('Failed to assign access', 'error');
    }
}

function openRoleModal(userId, email) {
    selectedUserId = userId;
    document.getElementById('roleModalUser').textContent = `User: ${email}`;
    document.getElementById('roleModal').classList.add('open');
}

function closeRoleModal() {
    document.getElementById('roleModal').classList.remove('open');
    selectedUserId = null;
}

async function submitRoleAssignment() {
    const roleName = document.getElementById('roleSelect').value;
    const res = await fetch(`/roles/assign/${selectedUserId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({role_name: roleName})
    });
    const data = await res.json();
    if (res.ok) {
        showAdminAlert(`Role "${roleName}" assigned!`, 'success');
        closeRoleModal();
        await loadUsers();
    } else {
        showAdminAlert(data.detail || 'Failed to assign role', 'error');
    }
}

function signOut() {
    sessionStorage.removeItem('adminToken');
    window.location.href = '/';
}

document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        closeModal();
        closeRoleModal();
    }
});
