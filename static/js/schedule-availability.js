/**
 * Availability Modal - JavaScript for Coach Availability Management
 * 
 * Features:
 * - Open/close modal
 * - Add/remove time ranges
 * - Load existing availability for selected date
 * - Save availability (upsert)
 * - Delete all availability for a date
 */

// Get CSRF token for Django
function getCookie(name) {
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

const csrftoken = getCookie('csrftoken');

// Modal control functions
function openAvailabilityModal() {
    const modal = document.getElementById('availabilityModal');
    modal.classList.remove('hidden');
    
    // Set default date to today
    const today = new Date().toISOString().split('T')[0];
    const dateInput = document.getElementById('availabilityDate');
    if (!dateInput.value) {
        dateInput.value = today;
    }
    
    // Load availability for default date
    loadAvailabilityForDate(dateInput.value);
}

function closeAvailabilityModal() {
    const modal = document.getElementById('availabilityModal');
    modal.classList.add('hidden');
    
    // Clear time ranges
    const container = document.getElementById('timeRangesContainer');
    container.innerHTML = '<div class="text-sm text-gray-500 text-center py-4" id="noRangesMessage">Pilih tanggal untuk melihat atau menambah rentang waktu</div>';
    
    // Reset buttons
    document.getElementById('saveBtn').disabled = true;
    document.getElementById('deleteAllBtn').disabled = true;
    
    // Clear messages
    hideModalMessage();
}

// Time range management
function addTimeRange(startTime = '', endTime = '') {
    const template = document.getElementById('timeRangeTemplate');
    const container = document.getElementById('timeRangesContainer');
    
    // Remove "no ranges" message if exists
    const noRangesMsg = document.getElementById('noRangesMessage');
    if (noRangesMsg) {
        noRangesMsg.remove();
    }
    
    // Clone template
    const clone = template.content.cloneNode(true);
    
    // Set values if provided
    if (startTime) {
        clone.querySelector('.range-start').value = startTime;
    }
    if (endTime) {
        clone.querySelector('.range-end').value = endTime;
    }
    
    container.appendChild(clone);
    
    // Enable save button
    document.getElementById('saveBtn').disabled = false;
}

function removeTimeRange(button) {
    const container = document.getElementById('timeRangesContainer');
    const item = button.closest('.time-range-item');
    item.remove();
    
    // If no more ranges, show message and disable save
    if (container.querySelectorAll('.time-range-item').length === 0) {
        container.innerHTML = '<div class="text-sm text-gray-500 text-center py-4" id="noRangesMessage">Pilih tanggal untuk melihat atau menambah rentang waktu</div>';
        document.getElementById('saveBtn').disabled = true;
    }
}

// Load availability for selected date
async function loadAvailabilityForDate(date) {
    if (!date) return;
    
    try {
        const response = await fetch(`/schedule/api/availability/?date=${date}`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': csrftoken,
            },
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to load availability');
        }
        
        // Clear existing ranges
        const container = document.getElementById('timeRangesContainer');
        container.innerHTML = '';
        
        // Add ranges from server
        if (data.ranges && data.ranges.length > 0) {
            data.ranges.forEach(range => {
                addTimeRange(range.start, range.end);
            });
            document.getElementById('deleteAllBtn').disabled = false;
        } else {
            container.innerHTML = '<div class="text-sm text-gray-500 text-center py-4" id="noRangesMessage">Belum ada rentang waktu untuk tanggal ini</div>';
            document.getElementById('deleteAllBtn').disabled = true;
        }
        
    } catch (error) {
        console.error('Error loading availability:', error);
        showModalMessage('Gagal memuat ketersediaan: ' + error.message, 'error');
    }
}

// Save availability (upsert with auto-merge)
async function saveAvailability() {
    const date = document.getElementById('availabilityDate').value;
    
    if (!date) {
        showModalMessage('Pilih tanggal terlebih dahulu', 'error');
        return;
    }
    
    // Collect all time ranges
    const rangeItems = document.querySelectorAll('.time-range-item');
    const ranges = [];
    
    for (let item of rangeItems) {
        const start = item.querySelector('.range-start').value;
        const end = item.querySelector('.range-end').value;
        
        if (!start || !end) {
            showModalMessage('Semua waktu mulai dan selesai harus diisi', 'error');
            return;
        }
        
        if (start >= end) {
            showModalMessage('Waktu selesai harus lebih besar dari waktu mulai', 'error');
            return;
        }
        
        ranges.push({ start, end });
    }
    
    if (ranges.length === 0) {
        showModalMessage('Tambahkan minimal satu rentang waktu', 'error');
        return;
    }
    
    // Disable save button during request
    const saveBtn = document.getElementById('saveBtn');
    const originalText = saveBtn.textContent;
    saveBtn.disabled = true;
    saveBtn.textContent = 'Menyimpan...';
    
    try {
        const response = await fetch('/schedule/api/availability/upsert/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify({ date, ranges }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to save availability');
        }
        
        // Show success message with merge info
        let message = data.message;
        if (data.original_count !== data.merged_count) {
            message += ` (${data.original_count} interval digabung menjadi ${data.merged_count})`;
        }
        showModalMessage(message, 'success');
        
        // Update UI with merged intervals
        if (data.merged_intervals && data.merged_intervals.length > 0) {
            const container = document.getElementById('timeRangesContainer');
            container.innerHTML = '';
            
            data.merged_intervals.forEach(range => {
                addTimeRange(range.start, range.end);
            });
            
            // Show merge notification if intervals were merged
            if (data.original_count !== data.merged_count) {
                setTimeout(() => {
                    showModalMessage(
                        `✨ Interval yang tumpang tindih atau berdekatan telah digabung otomatis!`, 
                        'info'
                    );
                }, 2000);
            }
        }
        
        // Enable delete button
        document.getElementById('deleteAllBtn').disabled = false;
        
        // Optionally close modal after delay
        // setTimeout(() => {
        //     closeAvailabilityModal();
        // }, 3000);
        
    } catch (error) {
        console.error('Error saving availability:', error);
        showModalMessage('Gagal menyimpan: ' + error.message, 'error');
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;
    }
}

// Delete all availability for selected date
async function deleteAllRanges() {
    const date = document.getElementById('availabilityDate').value;
    
    if (!date) {
        showModalMessage('Pilih tanggal terlebih dahulu', 'error');
        return;
    }
    
    if (!confirm(`Hapus semua ketersediaan untuk ${date}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/schedule/api/availability/?date=${date}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrftoken,
            },
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to delete availability');
        }
        
        showModalMessage(data.message, 'success');
        
        // Clear UI
        const container = document.getElementById('timeRangesContainer');
        container.innerHTML = '<div class="text-sm text-gray-500 text-center py-4" id="noRangesMessage">Belum ada rentang waktu untuk tanggal ini</div>';
        
        document.getElementById('saveBtn').disabled = true;
        document.getElementById('deleteAllBtn').disabled = true;
        
    } catch (error) {
        console.error('Error deleting availability:', error);
        showModalMessage('Gagal menghapus: ' + error.message, 'error');
    }
}

// Show message in modal
function showModalMessage(message, type = 'info') {
    const messageEl = document.getElementById('modalMessage');
    messageEl.classList.remove('hidden', 'bg-red-100', 'text-red-700', 'bg-green-100', 'text-green-700', 'bg-blue-100', 'text-blue-700');
    
    if (type === 'error') {
        messageEl.classList.add('bg-red-100', 'text-red-700');
    } else if (type === 'success') {
        messageEl.classList.add('bg-green-100', 'text-green-700');
    } else {
        messageEl.classList.add('bg-blue-100', 'text-blue-700');
    }
    
    messageEl.textContent = message;
    messageEl.classList.add('p-3', 'rounded-md', 'text-sm', 'font-medium');
}

function hideModalMessage() {
    const messageEl = document.getElementById('modalMessage');
    messageEl.classList.add('hidden');
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Listen to date changes
    const dateInput = document.getElementById('availabilityDate');
    if (dateInput) {
        dateInput.addEventListener('change', function() {
            loadAvailabilityForDate(this.value);
        });
    }
    
    // Close modal on background click
    const modal = document.getElementById('availabilityModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeAvailabilityModal();
            }
        });
    }
});
