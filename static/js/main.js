// Placeholder for custom JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('SOLAPP JS Loaded');

    // Example: Activate Bootstrap tooltips if used
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Handle client profile tab persistence using localStorage or URL hash
    const tabElList = document.querySelectorAll('#clientDataTab button[data-bs-toggle="tab"]');
    tabElList.forEach(tabEl => {
        tabEl.addEventListener('shown.bs.tab', event => {
            const hash = event.target.getAttribute('data-bs-target');
            localStorage.setItem('activeClientTab', hash);
        });
    });

    // Activate the stored tab on page load
    const activeTabHash = localStorage.getItem('activeClientTab');
    if (activeTabHash) {
        const triggerEl = document.querySelector(`#clientDataTab button[data-bs-target="${activeTabHash}"]`);
        if (triggerEl) {
            try {
                const tab = new bootstrap.Tab(triggerEl);
                tab.show();
            } catch (e) {
                console.error(`Error showing saved tab ${activeTabHash}:`, e);
                localStorage.removeItem('activeClientTab'); // Clear invalid hash
            }
        } else {
            localStorage.removeItem('activeClientTab'); // Clear hash if element not found
        }
    }
});

/**
 * Shows a Bootstrap Toast message.
 * @param {string} message The message to display.
 * @param {string} category 'success', 'warning', 'danger', 'info' (maps to bg-*) Defaults to 'info'.
 * @param {number} delay How long the toast should stay visible (ms). Defaults to 5000.
 */
function showToast(message, category = 'info', delay = 5000) {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        console.error('Toast container not found!');
        return;
    }

    const toastId = 'toast-' + Date.now(); // Unique ID for the toast element
    const toastBgColor = category === 'error' ? 'danger' : category; // map error to danger

    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white bg-${toastBgColor} border-0" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="${delay}">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHTML);

    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);

    // Optional: Remove the toast element from DOM after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function () {
        toastElement.remove();
    });

    toast.show();
}

// Example Usage (can be called from other JS functions):
// showToast('Operation successful!', 'success');
// showToast('Warning: Check inputs.', 'warning');
// showToast('An error occurred.', 'danger'); 