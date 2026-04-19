// files.js — File manager logic

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;');
}

async function loadFiles() {
    const token = AppState.accessToken;
    if (!token) return;

    try {
        const res = await fetch('/files/', {
            headers: {'Authorization': 'Bearer ' + token}
        });
        const files = await res.json();
        renderFiles(files);
    } catch (err) {
        console.error('Could not load files', err);
    }
}

function renderFiles(files) {
    const container = document.getElementById('fileList');
    if (!files.length) {
        container.innerHTML = '<p class="no-files">No files available for your role.</p>';
        return;
    }

    container.innerHTML = files.map(file => `
        <div class="file-item">
            <div class="file-info">
                <span class="file-icon">${getFileIcon(file.file_type)}</span>
                <div class="file-details">
                    <div class="file-name">${escapeHtml(file.original_name)}</div>
                    <div class="file-meta">${formatSize(file.file_size)} • ${escapeHtml(file.file_type)}</div>
                </div>
            </div>
            <div class="file-actions">
                <button class="btn-download" data-id="${file.id}" data-name="${escapeHtml(file.original_name)}">⬇ Download</button>
                <button class="btn-delete" data-id="${file.id}">🗑</button>
            </div>
        </div>
    `).join('');

    container.querySelectorAll('.btn-download').forEach(btn => {
        btn.addEventListener('click', () => downloadFile(parseInt(btn.dataset.id), btn.dataset.name));
    });
    container.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', () => deleteFile(parseInt(btn.dataset.id)));
    });
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

async function uploadFile() {
    const input = document.getElementById('fileInput');
    const file = input.files[0];
    if (!file) {
        showAlert('dashboard', 'Please select a file first', 'error');
        return;
    }

    const allowed = ['.doc', '.xml', '.pdf'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) {
        showAlert('dashboard', 'Only .doc, .xml, and .pdf files are allowed', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    setLoading('uploadBtn', true, '⬆ Upload File');

    try {
        const res = await fetch('/files/upload', {
            method: 'POST',
            headers: {'Authorization': 'Bearer ' + AppState.accessToken},
            body: formData
        });

        const data = await res.json();

        if (!res.ok) {
            showAlert('dashboard', data.detail || 'Upload failed', 'error');
            return;
        }

        showAlert('dashboard', `"${file.name}" uploaded successfully!`, 'success');
        input.value = '';
        await loadFiles();

    } catch (err) {
        showAlert('dashboard', 'Upload failed', 'error');
    } finally {
        setLoading('uploadBtn', false, '⬆ Upload File');
    }
}

async function downloadFile(fileId, filename) {
    try {
        const res = await fetch(`/files/download/${fileId}`, {
            headers: {'Authorization': 'Bearer ' + AppState.accessToken}
        });

        if (!res.ok) {
            showAlert('dashboard', 'You do not have access to this file', 'error');
            return;
        }

        // Create a download link and click it
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);

    } catch (err) {
        showAlert('dashboard', 'Download failed', 'error');
    }
}

async function deleteFile(fileId) {
    if (!confirm('Are you sure you want to delete this file?')) return;

    try {
        const res = await fetch(`/files/${fileId}`, {
            method: 'DELETE',
            headers: {'Authorization': 'Bearer ' + AppState.accessToken}
        });

        if (!res.ok) {
            const data = await res.json();
            showAlert('dashboard', data.detail || 'Delete failed', 'error');
            return;
        }

        showAlert('dashboard', 'File deleted successfully', 'success');
        await loadFiles();

    } catch (err) {
        showAlert('dashboard', 'Delete failed', 'error');
    }
}

async function assignFileAccess(fileId) {
    const roleNames = document.getElementById('assignRoles').value
        .split(',').map(r => r.trim()).filter(r => r);
    const userIds = document.getElementById('assignUsers').value
        .split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));

    try {
        const res = await fetch(`/files/assign/${fileId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + AppState.accessToken
            },
            body: JSON.stringify({role_names: roleNames, user_ids: userIds})
        });

        const data = await res.json();
        if (!res.ok) {
            showAlert('dashboard', data.detail || 'Assignment failed', 'error');
            return;
        }

        showAlert('dashboard', 'Access assigned successfully!', 'success');
        await loadFiles();

    } catch (err) {
        showAlert('dashboard', 'Assignment failed', 'error');
    }
}
