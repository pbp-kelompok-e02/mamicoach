// Handle payment form submission
document.addEventListener('DOMContentLoaded', function() {
    const paymentForm = document.getElementById('payment-form');
    
    if (paymentForm) {
        paymentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const form = e.target;
            const payButton = document.getElementById('pay-button');
            const selectedMethod = form.querySelector('input[name="payment_method"]:checked');
            
            if (!selectedMethod) {
                showToast('Silakan pilih metode pembayaran', 'error');
                return;
            }
            
            // Disable button and show loading
            payButton.disabled = true;
            payButton.textContent = 'Memproses...';
            
            // Submit form via fetch
            const formData = new FormData(form);
            
            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.redirect_url) {
                    // Redirect to Midtrans payment page
                    window.location.href = data.redirect_url;
                } else {
                    showToast('Inisiasi pembayaran gagal: ' + (data.error || 'Kesalahan tidak diketahui'), 'error');
                    payButton.disabled = false;
                    payButton.textContent = 'Lanjut ke Pembayaran';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Terjadi kesalahan. Silakan coba lagi.', 'error');
                payButton.disabled = false;
                payButton.textContent = 'Lanjut ke Pembayaran';
            });
        });
    }
    
    // Add visual feedback for selected payment method
    document.querySelectorAll('.payment-method-card input[type="radio"]').forEach(radio => {
        radio.addEventListener('change', function() {
            document.querySelectorAll('.payment-method-card').forEach(card => {
                card.classList.remove('border-emerald-500', 'bg-green-50');
            });
            if (this.checked) {
                this.closest('.payment-method-card').classList.add('border-emerald-500', 'bg-green-50');
            }
        });
    });
});
