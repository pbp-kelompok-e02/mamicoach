# Booking & Payment Integration Guide

## Status Flow

```
pending → paid → confirmed → done
   ↓         ↓        ↓
canceled  canceled  canceled
```

### Status Descriptions:
1. **`pending`** - User membuat booking, belum bayar (slot sudah di-reserve)
2. **`paid`** - User sudah menyelesaikan pembayaran, menunggu konfirmasi coach
3. **`confirmed`** - Coach menerima booking
4. **`done`** - Sesi selesai
5. **`canceled`** - Booking dibatalkan (bisa dari status manapun)

---

## API Endpoints untuk Payment Module

### 1. Create Booking (User)
**Endpoint:** `POST /booking/api/course/<course_id>/create/`

**Request Body:**
```json
{
    "date": "2025-10-25",
    "start_time": "09:00"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Booking created successfully",
    "booking_id": 123,
    "start_datetime": "2025-10-25T09:00:00",
    "end_datetime": "2025-10-25T10:00:00"
}
```

**Initial Status:** `pending`

---

### 2. Mark Booking as Paid (Payment Module) ⭐
**Endpoint:** `POST /booking/api/booking/<booking_id>/mark-paid/`

**Headers:**
```
Authorization: Required (user must own the booking)
Content-Type: application/json
```

**Request Body (Optional):**
```json
{
    "payment_id": "PAY-12345",
    "payment_method": "credit_card"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Booking marked as paid successfully",
    "booking_id": 123,
    "status": "paid",
    "payment_id": "PAY-12345",
    "payment_method": "credit_card"
}
```

**Validation:**
- User harus pemilik booking
- Status booking harus `pending`
- Jika status bukan `pending`, akan return error 400

---

### 3. Get Booking Details
**Endpoint:** `GET /booking/api/bookings/?role=user`

**Query Parameters:**
- `role`: `user` atau `coach`
- `status`: filter by status (optional)

**Response:**
```json
{
    "bookings": [
        {
            "id": 123,
            "user_name": "John Doe",
            "coach_name": "Coach Smith",
            "course_title": "Yoga Pemula",
            "start_datetime": "2025-10-25T09:00:00",
            "end_datetime": "2025-10-25T10:00:00",
            "date": "2025-10-25",
            "start_time": "09:00",
            "end_time": "10:00",
            "status": "paid",
            "created_at": "2025-10-23T10:00:00"
        }
    ],
    "count": 1
}
```

---

## Payment Flow Integration

### Recommended Flow:

```
1. User pilih course dan time slot
   ↓
2. POST /booking/api/course/<course_id>/create/
   Status: pending
   ↓
3. Redirect ke payment page
   Display: Confirmation page dengan booking details
   ↓
4. User complete payment
   ↓
5. POST /booking/api/booking/<booking_id>/mark-paid/
   Status: paid
   ↓
6. Show success page
   "Booking berhasil! Menunggu konfirmasi coach"
```

---

## Example Payment Integration Code

### Frontend (JavaScript):

```javascript
// Step 1: Create booking
async function createBooking(courseId, date, startTime) {
    const response = await fetch(`/booking/api/course/${courseId}/create/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ date, start_time: startTime })
    });
    
    const data = await response.json();
    
    if (data.success) {
        // Redirect to payment confirmation
        window.location.href = `/payment/confirm/${data.booking_id}/`;
    }
}

// Step 2: Mark as paid (after payment success)
async function markBookingAsPaid(bookingId, paymentData) {
    const response = await fetch(`/booking/api/booking/${bookingId}/mark-paid/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            payment_id: paymentData.paymentId,
            payment_method: paymentData.method
        })
    });
    
    const data = await response.json();
    
    if (data.success) {
        // Show success message
        alert('Payment successful! Waiting for coach confirmation.');
        window.location.href = '/booking/history/';
    }
}
```

### Backend (Python View):

```python
from django.shortcuts import render, get_object_or_404
from booking.models import Booking

def payment_confirmation(request, booking_id):
    """
    Show payment confirmation page before processing payment
    """
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.status != 'pending':
        messages.error(request, 'This booking has already been processed')
        return redirect('booking:history')
    
    context = {
        'booking': booking,
        'course': booking.course,
        'coach': booking.coach,
        'start_datetime': booking.start_datetime,
        'end_datetime': booking.end_datetime,
        'price': booking.course.price,
    }
    
    return render(request, 'payment/confirmation.html', context)


def payment_success(request, booking_id):
    """
    Handle successful payment callback
    """
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Call mark-paid API internally or update directly
    if booking.status == 'pending':
        booking.status = 'paid'
        booking.save()
        
        messages.success(request, 'Payment successful! Waiting for coach confirmation.')
    
    return render(request, 'payment/success.html', {'booking': booking})
```

---

## Database Model Reference

### Booking Model Fields:
```python
- id: int (Primary Key)
- user: ForeignKey(User)
- coach: ForeignKey(CoachProfile)
- course: ForeignKey(Course)
- start_datetime: DateTimeField
- end_datetime: DateTimeField
- status: CharField (choices: pending, paid, confirmed, done, canceled)
- created_at: DateTimeField (auto)
- updated_at: DateTimeField (auto)
```

---

## Error Handling

### Common Errors:

**400 Bad Request:**
```json
{
    "error": "Only pending bookings can be marked as paid. Current status: paid"
}
```

**403 Forbidden:**
```json
{
    "error": "You are not authorized to update this booking"
}
```

**404 Not Found:**
```json
{
    "error": "Booking not found"
}
```

**409 Conflict (Overlap):**
```json
{
    "error": "This time slot conflicts with an existing booking"
}
```

---

## Testing

### Test Cases for Payment Integration:

1. **Create booking → Status should be `pending`**
2. **Mark as paid with valid payment_id → Status should be `paid`**
3. **Try to mark already paid booking → Should return error 400**
4. **Try to mark booking owned by other user → Should return error 403**
5. **Cancel paid booking → Status should be `canceled`**

---

## Contact

Jika ada pertanyaan atau butuh bantuan integrasi, hubungi:
- Backend Team: [Your Name]
- Booking System: [Teammate Name]

