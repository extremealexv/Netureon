function deleteDevice(mac) {
    if (!confirm('Are you sure you want to delete this device?')) {
        return;
    }

    fetch('/unknown/delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mac: mac })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Remove the device row from the table
            const row = document.querySelector(`tr[data-mac="${mac}"]`);
            if (row) {
                row.remove();
            }
            // Show success message
            showNotification('success', data.message);
        } else {
            // Show error message
            showNotification('error', data.error || 'Failed to delete device');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('error', 'Failed to delete device: ' + error.message);
    });
}

function showNotification(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    document.querySelector('.notifications').appendChild(alertDiv);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}