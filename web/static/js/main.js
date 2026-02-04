// LED Display Control Panel JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize any interactive elements
    initForms();
});

function initForms() {
    // Add AJAX form submission where appropriate
    const ajaxForms = document.querySelectorAll('form[data-ajax]');
    ajaxForms.forEach(form => {
        form.addEventListener('submit', handleAjaxSubmit);
    });
}

async function handleAjaxSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    try {
        const response = await fetch(form.action, {
            method: form.method || 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: new URLSearchParams(formData)
        });

        const data = await response.json();

        if (data.success) {
            showNotification('Settings saved successfully', 'success');
        } else {
            showNotification(data.error || 'An error occurred', 'error');
        }
    } catch (error) {
        showNotification('Network error. Please try again.', 'error');
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Style the notification
    Object.assign(notification.style, {
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        padding: '15px 25px',
        borderRadius: '8px',
        color: 'white',
        fontWeight: '500',
        zIndex: '1000',
        animation: 'slideIn 0.3s ease-out',
        backgroundColor: type === 'success' ? '#4CAF50' :
                         type === 'error' ? '#f44336' : '#2196F3'
    });

    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// API utilities
const api = {
    async get(url) {
        const response = await fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        return response.json();
    },

    async post(url, data = {}) {
        const formData = new URLSearchParams(data);
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        });
        return response.json();
    }
};

// Status polling
function startStatusPolling(interval = 5000) {
    setInterval(async () => {
        try {
            const status = await api.get('/api/status');
            updateStatusDisplay(status);
        } catch (error) {
            console.error('Status polling error:', error);
        }
    }, interval);
}

function updateStatusDisplay(status) {
    // Update network status if elements exist
    const networkStatus = document.querySelector('.network-status');
    if (networkStatus && status.network) {
        const connected = status.network.connected;
        networkStatus.className = `value ${connected ? 'connected' : 'disconnected'}`;
        networkStatus.textContent = connected ? 'Connected' : 'Disconnected';
    }

    // Update active app if element exists
    const activeApp = document.querySelector('.active-app-name');
    if (activeApp) {
        activeApp.textContent = status.active_app || 'None';
    }
}

// Brightness control
function setBrightness(value) {
    api.post('/system/brightness', { brightness: value })
        .then(data => {
            if (!data.success) {
                showNotification('Failed to set brightness', 'error');
            }
        })
        .catch(() => {
            showNotification('Network error', 'error');
        });
}

// App control
function activateApp(appName) {
    api.post(`/app/${appName}/activate`)
        .then(data => {
            if (data.success) {
                showNotification(`Activated ${appName}`, 'success');
                // Refresh page to update UI
                setTimeout(() => location.reload(), 500);
            } else {
                showNotification('Failed to activate app', 'error');
            }
        })
        .catch(() => {
            showNotification('Network error', 'error');
        });
}

function nextApp() {
    api.post('/app/next')
        .then(data => {
            if (data.success) {
                showNotification(`Switched to ${data.active_app}`, 'success');
                setTimeout(() => location.reload(), 500);
            }
        })
        .catch(() => {
            showNotification('Network error', 'error');
        });
}

// WiFi control
function connectWifi(ssid, password) {
    return api.post('/wifi/connect', { ssid, password });
}

function disconnectWifi() {
    return api.post('/wifi/disconnect');
}

function scanWifi() {
    return api.get('/wifi/scan');
}

// Export for use in HTML
window.showNotification = showNotification;
window.api = api;
window.setBrightness = setBrightness;
window.activateApp = activateApp;
window.nextApp = nextApp;
window.connectWifi = connectWifi;
window.disconnectWifi = disconnectWifi;
window.scanWifi = scanWifi;
