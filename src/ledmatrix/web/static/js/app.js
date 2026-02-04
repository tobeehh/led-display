/**
 * LED Display Web UI - Main JavaScript
 */

// Global state
let currentApp = null;
let currentAppConfig = null;

// ============================================================================
// API Helpers
// ============================================================================

async function apiGet(endpoint) {
    const resp = await fetch(endpoint);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

async function apiPost(endpoint, data = null) {
    const options = { method: 'POST' };
    if (data) {
        options.headers = { 'Content-Type': 'application/json' };
        options.body = JSON.stringify(data);
    }
    const resp = await fetch(endpoint, options);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

async function apiPut(endpoint, data) {
    const resp = await fetch(endpoint, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

// ============================================================================
// Status & Dashboard
// ============================================================================

async function loadStatus() {
    try {
        const data = await apiGet('/api/status');

        // Update status elements if they exist
        const activeApp = document.getElementById('activeApp');
        const brightness = document.getElementById('brightness');
        const networkStatus = document.getElementById('networkStatus');
        const brightnessSlider = document.getElementById('brightnessSlider');
        const brightnessValue = document.getElementById('brightnessValue');

        if (activeApp) {
            activeApp.textContent = formatAppName(data.active_app) || 'None';
        }
        if (brightness) {
            brightness.textContent = data.brightness + '%';
        }
        if (networkStatus) {
            networkStatus.textContent = data.network.connected
                ? data.network.ssid
                : 'Disconnected';
        }
        if (brightnessSlider && !brightnessSlider.matches(':active')) {
            brightnessSlider.value = data.brightness;
        }
        if (brightnessValue) {
            brightnessValue.textContent = data.brightness + '%';
        }
    } catch (e) {
        console.error('Failed to load status:', e);
    }
}

function formatAppName(name) {
    if (!name) return null;
    return name.split(/[-_]/)
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

// ============================================================================
// Apps Management
// ============================================================================

async function loadApps() {
    const grid = document.getElementById('appsGrid');
    if (!grid) return;

    try {
        const data = await apiGet('/api/apps');
        renderAppsGrid(data.apps);
    } catch (e) {
        grid.innerHTML = '<div class="alert alert-error">Failed to load apps</div>';
    }
}

function renderAppsGrid(apps) {
    const grid = document.getElementById('appsGrid');
    if (!grid) return;

    grid.innerHTML = '';

    apps.forEach(app => {
        const card = document.createElement('div');
        card.className = `app-card ${app.active ? 'active' : ''}`;
        card.innerHTML = `
            <div class="app-card-header">
                <div class="app-info">
                    <h3>${app.display_name}</h3>
                    <p>${app.description}</p>
                </div>
                <div class="app-status">
                    <span class="status-badge ${app.active ? 'active' : 'inactive'}">
                        ${app.active ? 'Active' : 'Inactive'}
                    </span>
                </div>
            </div>
            <div class="app-card-footer">
                <button class="btn btn-secondary btn-sm" onclick="openConfigModal('${app.name}')">
                    Settings
                </button>
                ${!app.active ? `
                    <button class="btn btn-primary btn-sm" onclick="activateApp('${app.name}')">
                        Activate
                    </button>
                ` : ''}
            </div>
        `;
        grid.appendChild(card);
    });
}

async function activateApp(name) {
    try {
        await apiPost(`/api/apps/${name}/activate`);
        loadStatus();
        loadApps();
    } catch (e) {
        console.error('Failed to activate app:', e);
        alert('Failed to activate app');
    }
}

async function nextApp() {
    try {
        await apiPost('/api/apps/next');
        loadStatus();
        loadApps();
    } catch (e) {
        console.error('Failed to switch app:', e);
    }
}

async function previousApp() {
    try {
        await apiPost('/api/apps/previous');
        loadStatus();
        loadApps();
    } catch (e) {
        console.error('Failed to switch app:', e);
    }
}

// ============================================================================
// Brightness Control
// ============================================================================

async function setBrightness(value) {
    try {
        await apiPost('/api/display/brightness', { brightness: value });
    } catch (e) {
        console.error('Failed to set brightness:', e);
    }
}

// ============================================================================
// Config Modal
// ============================================================================

async function openConfigModal(appName) {
    try {
        const app = await apiGet(`/api/apps/${appName}`);
        currentApp = appName;
        currentAppConfig = app;

        document.getElementById('modalTitle').textContent = app.display_name + ' Settings';
        document.getElementById('modalBody').innerHTML = renderConfigForm(app.config_schema, app.current_config);
        document.getElementById('configModal').classList.add('active');
    } catch (e) {
        console.error('Failed to load app config:', e);
        alert('Failed to load app settings');
    }
}

function closeModal() {
    document.getElementById('configModal').classList.remove('active');
    currentApp = null;
    currentAppConfig = null;
}

function renderConfigForm(schema, currentConfig) {
    let html = '<form id="configForm">';

    for (const [key, field] of Object.entries(schema)) {
        const value = currentConfig[key] ?? field.default ?? '';
        html += renderFormField(key, field, value);
    }

    html += '</form>';
    return html || '<p class="text-muted">No configurable settings</p>';
}

function renderFormField(key, field, value) {
    const label = field.label || key;
    const description = field.description || '';
    const required = field.required ? '<span class="required">*</span>' : '';

    let input = '';

    switch (field.type) {
        case 'bool':
            input = `
                <div class="toggle-container">
                    <div>
                        <label class="form-label mb-0">${label} ${required}</label>
                        ${description ? `<div class="form-help">${description}</div>` : ''}
                    </div>
                    <label class="toggle">
                        <input type="checkbox" name="${key}" ${value ? 'checked' : ''}>
                        <span class="toggle-slider"></span>
                    </label>
                </div>
            `;
            break;

        case 'select':
            const options = (field.options || []).map(opt =>
                `<option value="${opt.value}" ${value === opt.value ? 'selected' : ''}>${opt.label}</option>`
            ).join('');
            input = `
                <label class="form-label">${label} ${required}</label>
                <select class="form-select" name="${key}">${options}</select>
                ${description ? `<div class="form-help">${description}</div>` : ''}
            `;
            break;

        case 'color':
            input = `
                <label class="form-label">${label} ${required}</label>
                <div class="color-input-wrapper">
                    <input type="color" value="${value || '#FFFFFF'}" onchange="this.nextElementSibling.value = this.value">
                    <input type="text" class="form-input" name="${key}" value="${value || '#FFFFFF'}"
                           pattern="^#[0-9A-Fa-f]{6}$" placeholder="#FFFFFF"
                           onchange="this.previousElementSibling.value = this.value">
                </div>
                ${description ? `<div class="form-help">${description}</div>` : ''}
            `;
            break;

        case 'int':
            const min = field.min_value !== null ? field.min_value : '';
            const max = field.max_value !== null ? field.max_value : '';

            if (min !== '' && max !== '' && (max - min) <= 100) {
                input = `
                    <label class="form-label">${label} ${required}</label>
                    <div class="range-container">
                        <input type="range" class="range-input" name="${key}"
                               min="${min}" max="${max}" value="${value ?? min}"
                               oninput="this.nextElementSibling.textContent = this.value">
                        <span class="range-value">${value ?? min}</span>
                    </div>
                    ${description ? `<div class="form-help">${description}</div>` : ''}
                `;
            } else {
                input = `
                    <label class="form-label">${label} ${required}</label>
                    <input type="number" class="form-input" name="${key}" value="${value || ''}"
                           ${min !== '' ? `min="${min}"` : ''} ${max !== '' ? `max="${max}"` : ''}>
                    ${description ? `<div class="form-help">${description}</div>` : ''}
                `;
            }
            break;

        case 'password':
            input = `
                <label class="form-label">${label} ${required}</label>
                <input type="password" class="form-input" name="${key}" value=""
                       placeholder="Enter to change...">
                ${description ? `<div class="form-help">${description}</div>` : ''}
            `;
            break;

        case 'string':
        default:
            input = `
                <label class="form-label">${label} ${required}</label>
                <input type="text" class="form-input" name="${key}" value="${escapeHtml(value || '')}"
                       placeholder="${escapeHtml(field.default || '')}">
                ${description ? `<div class="form-help">${description}</div>` : ''}
            `;
            break;
    }

    return `<div class="form-group">${input}</div>`;
}

async function saveConfig() {
    if (!currentApp) return;

    const form = document.getElementById('configForm');
    const formData = new FormData(form);
    const settings = {};

    for (const [key, value] of formData.entries()) {
        settings[key] = value;
    }

    // Handle checkboxes
    form.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        settings[cb.name] = cb.checked;
    });

    // Convert numeric fields
    form.querySelectorAll('input[type="number"], input[type="range"]').forEach(input => {
        if (settings[input.name] !== undefined) {
            settings[input.name] = parseInt(settings[input.name]) || 0;
        }
    });

    try {
        await apiPut(`/api/apps/${currentApp}/config`, { enabled: true, settings });
        closeModal();
        loadApps();
    } catch (e) {
        console.error('Failed to save config:', e);
        alert('Failed to save settings');
    }
}

// ============================================================================
// Utilities
// ============================================================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Close modal on overlay click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        closeModal();
    }
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal();
    }
});
