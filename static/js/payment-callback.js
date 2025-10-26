// Get CSRF token from cookie
function getCSRFToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Check payment status
function checkPaymentStatus(paymentStatusUrl) {
    fetch(paymentStatusUrl + '?refresh=true', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.payment.status === 'paid') {
                location.reload();
            }
        }
    })
    .catch(error => console.error('Error:', error));
}

// Show cancel confirmation modal
function showCancelConfirmation() {
    const modal = document.getElementById('cancel-confirmation-modal');
    if (modal) {
        modal.classList.remove('hidden');
    }
}

// Close cancel modal
function closeCancelModal() {
    const modal = document.getElementById('cancel-confirmation-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

// Confirm and cancel booking
function confirmCancelBooking(bookingId, dashboardUrl) {
    fetch(`/booking/api/booking/${bookingId}/cancel/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Booking berhasil dibatalkan!', 'success');
            setTimeout(() => {
                window.location.href = dashboardUrl;
            }, 1500);
        } else {
            showToast('Gagal membatalkan booking: ' + (data.message || 'Unknown error'), 'error');
            closeCancelModal();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Terjadi kesalahan saat membatalkan booking', 'error');
        closeCancelModal();
    });
}

// Initialize modal event listeners
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('cancel-confirmation-modal');
    if (modal) {
        document.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeCancelModal();
            }
        });
    }
});
