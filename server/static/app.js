// server/static/app.js
let token = localStorage.getItem('jwt_token') || "";
let currentUser = "";
let allFiles = [];
let isLoginMode = true;
let selectedFileObject = null;

//AUTH
function toggleAuthMode() {
    isLoginMode = !isLoginMode;
    document.getElementById('auth-title').innerText = isLoginMode ? "Login" : "Register";
    document.getElementById('btn-login').style.display = isLoginMode ? 'block' : 'none';
    document.getElementById('btn-reg').style.display = isLoginMode ? 'none' : 'block';
}

async function register() {
    const u = document.getElementById('u').value;
    const p = document.getElementById('p').value;
    const fd = new FormData(); fd.append("username", u); fd.append("password", p);

    const res = await fetch('/register', {method: 'POST', body: fd});
    if (res.ok) { alert("Registered! Please login."); toggleAuthMode(); }
    else alert("Registration failed (User exists?)");
}

async function login() {
    const u = document.getElementById('u').value;
    const p = document.getElementById('p').value;
    const fd = new FormData(); fd.append("username", u); fd.append("password", p);

    const res = await fetch('/token', {method: 'POST', body: fd});
    if (res.ok) {
        const data = await res.json();
        token = data.access_token;
        currentUser = u;
        localStorage.setItem('jwt_token', token);
        showApp();
    } else alert("Invalid credentials");
}

function logout() {
    token = "";
    localStorage.removeItem('jwt_token');
    location.reload();
}

function showApp() {
    document.getElementById('auth-box').style.display = 'none';
    document.getElementById('app-box').style.display = 'flex';
    document.getElementById('username-display').innerText = currentUser;
    loadFiles();
}

//DATA & UI
async function loadFiles() {
    if (!token) return;
    const res = await fetch('/files', {headers: {'Authorization': `Bearer ${token}`}});
    if (res.status === 401) { logout(); return; }
    allFiles = await res.json();
    applyFilters();
}

function applyFilters() {
    let data = [...allFiles];
    if (document.getElementById('filter-check').checked) {
        data = data.filter(f => ['.py', '.jpg'].includes(f.extension));
    }
    const sort = document.getElementById('sort-select').value;
    if (sort === 'asc') data.sort((a,b) => a.uploader.localeCompare(b.uploader));
    if (sort === 'desc') data.sort((a,b) => b.uploader.localeCompare(a.uploader));
    renderTable(data);
}

function renderTable(data) {
    const tbody = document.getElementById('file-list');
    tbody.innerHTML = "";

    // Скидання стану
    selectedFileObject = null;
    document.querySelectorAll('.action-btn').forEach(b => b.style.display = 'none');
    document.getElementById('preview-content').innerHTML = "Select a file...";

    // Приховуємо кнопку Save при зміні вибору
    const btnSave = document.getElementById('btn-save');
    if(btnSave) btnSave.style.display = 'none';

    data.forEach(f => {
        const tr = document.createElement('tr');
        if (f.access_type !== 'owner') tr.classList.add('shared');

        tr.innerHTML = `
            <td>${f.filename} ${f.access_type !== 'owner' ? '🔗' : ''}</td>
            <td>${f.extension}</td>
            <td class="opt-col">${f.created_at}</td>
            <td class="opt-col">${f.updated_at}</td>
            <td class="opt-col">${f.uploader}</td>
            <td class="opt-col">${f.editor}</td>
        `;

        tr.onclick = () => {
            document.querySelectorAll('tr').forEach(r => r.classList.remove('selected'));
            tr.classList.add('selected');
            selectedFileObject = f;

            document.getElementById('btn-dl').style.display = 'inline-block';
            document.getElementById('btn-del').style.display = 'inline-block';

            if (f.access_type === 'owner') {
                document.getElementById('btn-share').style.display = 'inline-block';
                document.getElementById('btn-del').innerText = "🗑 Delete File";
            } else {
                document.getElementById('btn-share').style.display = 'none';
                document.getElementById('btn-del').innerText = "🚫 Remove Access";
            }

            previewFile(f);
        };
        tbody.appendChild(tr);
    });
    toggleCols();
}

function toggleCols() {
    const hide = document.getElementById('cols-check').checked;
    const cols = document.querySelectorAll('.opt-col');
    cols.forEach(c => c.style.display = hide ? 'none' : 'table-cell');
}

//PREVIEW & EDITING
async function previewFile(file) {
    const container = document.getElementById('preview-content');
    const btnSave = document.getElementById('btn-save');

    container.innerHTML = "Loading...";
    if(btnSave) btnSave.style.display = 'none';

    const fileUrl = `/raw/${file.storage_name}`;
    // Генеруємо мітку часу для обходу кешу
    const timestamp = new Date().getTime();

    if (file.extension === '.png') {
        // Додаємо timestamp до картинки
        container.innerHTML = `<img src="${fileUrl}?t=${timestamp}" style="max-width: 100%; border: 1px solid #555;">`;

    } else if (file.extension === '.js') {
        try {
            // Додаємо timestamp до fetch запиту
            const res = await fetch(`${fileUrl}?t=${timestamp}`);
            let text = await res.text();

            const canEdit = (file.access_type === 'owner' || file.access_type === 'write');

            if (canEdit) {
                container.innerHTML = `<textarea id="editor-area" style="width:100%; height:400px; background:#1e1e1e; color:#a9b7c6; border:1px solid #555; padding:10px; font-family:monospace; resize: vertical;">${text}</textarea>`;

                const area = document.getElementById('editor-area');
                area.addEventListener('input', () => {
                    if(btnSave) btnSave.style.display = 'block';
                });

            } else {
                text = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
                container.innerHTML = `<pre>${text}</pre>`;
            }

        } catch(e) { container.innerHTML = "Error loading text"; }

    } else {
        container.innerHTML = '<div style="padding: 20px; color: #888;">No preview available for this type.</div>';
    }
}

// ACTIONS

async function saveContent() {
    if (!selectedFileObject) return;
    const textArea = document.getElementById('editor-area');
    if (!textArea) return;

    const newText = textArea.value;

    const res = await fetch('/update_content', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            storage_name: selectedFileObject.storage_name,
            content: newText
        })
    });

    if (res.ok) {
        alert("Saved!");
        document.getElementById('btn-save').style.display = 'none'; // Ховаємо кнопку після успішного збереження
        loadFiles();
    } else {
        alert("Error saving content");
    }
}

async function upload(file) {
    if(!file) return;

    const fd = new FormData();
    fd.append("file", file);

    try {
        const res = await fetch('/upload', {
            method: 'POST',
            body: fd,
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (res.ok) {
            loadFiles();
        } else {
            const err = await res.json();
            alert("Upload failed: " + (err.detail || res.statusText));
        }
    } catch (e) {
        alert("Network error");
        console.error(e);
    }
}

async function downloadFile() {
    if (!selectedFileObject) return;
    const url = `/raw/${selectedFileObject.storage_name}`;

    const a = document.createElement('a');
    a.href = url;
    a.download = selectedFileObject.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

async function deleteFile() {
    if (!selectedFileObject) return;
    const msg = selectedFileObject.access_type === 'owner' ?
        `Delete ${selectedFileObject.filename} permanently?` :
        `Remove access to ${selectedFileObject.filename}?`;

    if (!confirm(msg)) return;

    const res = await fetch(`/delete/${selectedFileObject.storage_name}`, {
        method: 'DELETE',
        headers: {'Authorization': `Bearer ${token}`}
    });

    if (res.ok) {
        alert("Done");
        loadFiles();
    } else {
        alert("Error deleting");
    }
}

async function shareFile() {
    if (!selectedFileObject) return alert("Select a file first");

    const user = prompt("Target user:");
    if(user) {
        const level = prompt("Level (read/write):", "read");
        await fetch('/share', {
            method: 'POST',
            headers: {'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json'},
            body: JSON.stringify({filename: selectedFileObject.filename, target_user: user, level})
        });
        alert("Shared!");
    }
}

// --- DRAG N DROP ---
const dropZone = document.getElementById('drop-zone');

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.add('drop-active'); }, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => { e.preventDefault(); e.stopPropagation(); dropZone.classList.remove('drop-active'); }, false);
});

dropZone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if(files.length > 0) upload(files[0]);
});

// Auto login check
if(token) showApp();