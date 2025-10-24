import os
import json
import base64
import hashlib
from unittest.mock import patch, MagicMock
from datetime import datetime
import requests

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from booking.models import Booking
from user_profile.models import CoachProfile
from courses_and_coach.models import Course, Category
from .models import Payment
from .midtrans_service import MidtransService


class MidtransServiceUnitTest(TestCase):
    """Test cases for MidtransService"""

    def setUp(self):
        os.environ['MIDTRANS_SERVER_KEY'] = 'server_test_key'
        os.environ['MIDTRANS_CLIENT_KEY'] = 'client_test_key'
        os.environ['MIDTRANS_IS_PRODUCTION'] = 'false'

    def tearDown(self):
        os.environ.pop('MIDTRANS_SERVER_KEY', None)
        os.environ.pop('MIDTRANS_CLIENT_KEY', None)
        os.environ.pop('MIDTRANS_IS_PRODUCTION', None)

    def test_init_sandbox_and_production(self):
        """Test service initializes with correct URLs"""
        svc = MidtransService()
        self.assertIn('sandbox', svc.base_url)
        
        os.environ['MIDTRANS_IS_PRODUCTION'] = 'true'
        svc_prod = MidtransService()
        self.assertNotIn('sandbox', svc_prod.base_url)

    def test_get_auth_header(self):
        """Test auth header generation"""
        svc = MidtransService()
        header = svc._get_auth_header()
        expected = base64.b64encode(b"server_test_key:").decode('utf-8')
        self.assertEqual(header, f"Basic {expected}")

    def test_map_payment_method_known_and_default(self):
        """Test payment method mapping"""
        svc = MidtransService()
        self.assertEqual(svc._map_payment_method_to_midtrans('gopay'), ['gopay'])
        self.assertEqual(svc._map_payment_method_to_midtrans('bca_va'), ['bca_va'])
        self.assertEqual(svc._map_payment_method_to_midtrans('nonexistent'), ['credit_card'])

    @patch('payment.midtrans_service.requests.post')
    def test_create_transaction_success(self, mock_post):
        """Test successful transaction creation"""
        svc = MidtransService()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {'token': 'tok', 'redirect_url': 'https://pay'}
        mock_post.return_value = mock_resp

        out = svc.create_transaction('ORD-1', 1000, {'first_name': 'A'}, [{'id': 1, 'price': 1000, 'quantity': 1, 'name': 'X'}])
        self.assertTrue(out['success'])
        self.assertEqual(out['token'], 'tok')

    @patch('payment.midtrans_service.requests.post')
    def test_create_transaction_failure(self, mock_post):
        """Test transaction creation failure"""
        svc = MidtransService()
        mock_post.side_effect = requests.exceptions.RequestException('boom')
        out = svc.create_transaction('ORD-2', 1000, {}, [])
        self.assertFalse(out['success'])

    @patch('payment.midtrans_service.requests.get')
    def test_get_transaction_status_success(self, mock_get):
        """Test getting transaction status successfully"""
        svc = MidtransService()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {'transaction_status': 'settlement'}
        mock_get.return_value = mock_resp

        res = svc.get_transaction_status('ORD-1')
        self.assertTrue(res['success'])

    @patch('payment.midtrans_service.requests.get')
    def test_get_transaction_status_failure(self, mock_get):
        """Test transaction status failure"""
        svc = MidtransService()
        mock_get.side_effect = requests.exceptions.RequestException('net')
        res = svc.get_transaction_status('ORD-2')
        self.assertFalse(res['success'])

    def test_verify_signature(self):
        """Test signature verification"""
        os.environ['MIDTRANS_SERVER_KEY'] = 'shh'
        svc = MidtransService()
        order = 'O1'
        status_code = '200'
        gross = '100'
        string_to_hash = f"{order}{status_code}{gross}{svc.server_key}"
        expected = hashlib.sha512(string_to_hash.encode('utf-8')).hexdigest()
        self.assertTrue(svc.verify_signature(order, status_code, gross, expected))
        self.assertFalse(svc.verify_signature(order, status_code, gross, 'bad'))


class PaymentModelTest(TestCase):
    """Test cases for Payment model"""

    def setUp(self):
        self.user = User.objects.create_user(username='u1', password='pass')
        self.coach_user = User.objects.create_user(username='coach', password='pass')
        self.coach = CoachProfile.objects.create(user=self.coach_user, bio='bio', expertise=['x'])
        self.cat = Category.objects.create(name='Cat')
        self.course = Course.objects.create(coach=self.coach, category=self.cat, title='C1', description='d', price=50000, duration=60)
        self.booking = Booking.objects.create(user=self.user, coach=self.coach, course=self.course, status='pending')

    def test_payment_creation(self):
        """Test payment can be created"""
        p = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-1')
        self.assertEqual(p.amount, 50000)
        self.assertEqual(p.status, 'pending')

    def test_payment_str(self):
        """Test payment string representation"""
        p = Payment.objects.create(booking=self.booking, user=self.user, amount=1000, method='credit_card', order_id='X-1')
        self.assertIn('Payment', str(p))

    def test_payment_is_successful(self):
        """Test is_successful property"""
        p = Payment.objects.create(booking=self.booking, user=self.user, amount=1000, method='credit_card', order_id='X-1')
        self.assertFalse(p.is_successful)
        p.status = 'settlement'
        self.assertTrue(p.is_successful)

    def test_payment_is_pending(self):
        """Test is_pending property"""
        p = Payment.objects.create(booking=self.booking, user=self.user, amount=1000, method='credit_card', order_id='X-2')
        self.assertTrue(p.is_pending)

    def test_payment_is_failed(self):
        """Test is_failed property"""
        p = Payment.objects.create(booking=self.booking, user=self.user, amount=1000, method='credit_card', order_id='X-3')
        self.assertFalse(p.is_failed)
        p.status = 'deny'
        self.assertTrue(p.is_failed)


class PaymentViewsTest(TestCase):
    """Test cases for payment views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='u1', password='pass', first_name='First', email='test@test.com')
        self.coach_user = User.objects.create_user(username='coach', password='pass')
        self.coach = CoachProfile.objects.create(user=self.coach_user, bio='bio', expertise=['x'], verified=True)
        self.cat = Category.objects.create(name='Cat')
        self.course = Course.objects.create(coach=self.coach, category=self.cat, title='C1', description='d', price=50000, duration=60)
        self.booking = Booking.objects.create(user=self.user, coach=self.coach, course=self.course, status='pending')

    def test_payment_method_selection_view(self):
        """Test payment method selection page"""
        self.client.login(username='u1', password='pass')
        resp = self.client.get(reverse('payment:method_selection', args=[self.booking.id]))
        self.assertEqual(resp.status_code, 200)

    @patch('payment.views.MidtransService.create_transaction')
    def test_process_payment_happy_path(self, mock_create):
        """Test successful payment processing"""
        mock_create.return_value = {'success': True, 'token': 't', 'redirect_url': 'https://pay', 'response': {}}
        self.client.login(username='u1', password='pass')
        resp = self.client.post(reverse('payment:process', args=[self.booking.id]), data={'payment_method': 'credit_card'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['success'])

    def test_process_payment_missing_method(self):
        """Test process payment with missing payment method"""
        self.client.login(username='u1', password='pass')
        resp = self.client.post(reverse('payment:process', args=[self.booking.id]), data={})
        self.assertEqual(resp.status_code, 400)

    def test_process_payment_invalid_method(self):
        """Test process payment with invalid payment method"""
        self.client.login(username='u1', password='pass')
        resp = self.client.post(reverse('payment:process', args=[self.booking.id]), data={'payment_method': 'invalid'})
        self.assertEqual(resp.status_code, 400)

    @patch('payment.views.MidtransService.create_transaction')
    def test_process_payment_midtrans_failure(self, mock_create):
        """Test payment processing when Midtrans fails"""
        mock_create.return_value = {'success': False, 'error': 'err'}
        self.client.login(username='u1', password='pass')
        resp = self.client.post(reverse('payment:process', args=[self.booking.id]), data={'payment_method': 'credit_card'})
        self.assertEqual(resp.status_code, 500)

    @patch('payment.views.MidtransService.verify_signature')
    def test_midtrans_webhook_invalid_signature(self, mock_verify):
        """Test webhook with invalid signature"""
        mock_verify.return_value = False
        payload = {'order_id': 'nope', 'status_code': '200', 'gross_amount': '100', 'signature_key': 'x', 'transaction_id': 'tx1'}
        resp = self.client.post(reverse('payment:midtrans_webhook'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)

    @patch('payment.views.MidtransService.verify_signature')
    def test_midtrans_webhook_payment_not_found(self, mock_verify):
        """Test webhook with payment not found"""
        mock_verify.return_value = True
        payload = {'order_id': 'unknown', 'status_code': '200', 'gross_amount': '100', 'signature_key': 'x', 'transaction_id': 'tx1'}
        resp = self.client.post(reverse('payment:midtrans_webhook'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)

    @patch('payment.views.MidtransService.verify_signature')
    def test_midtrans_webhook_settlement(self, mock_verify):
        """Test webhook processing settlement status"""
        mock_verify.return_value = True
        payment = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-XYZ', status='pending')
        payload = {
            'order_id': 'ORD-XYZ',
            'transaction_status': 'settlement',
            'fraud_status': 'accept',
            'status_code': '200',
            'gross_amount': '50000',
            'signature_key': 'sig',
            'transaction_id': 'tx123',
        }
        resp = self.client.post(reverse('payment:midtrans_webhook'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'settlement')

    @patch('payment.views.MidtransService.get_transaction_status')
    def test_payment_callback_success(self, mock_status):
        """Test payment callback with successful payment"""
        payment = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-ABC', status='pending')
        mock_status.return_value = {'success': True, 'data': {'transaction_status': 'settlement'}}
        resp = self.client.get(reverse('payment:callback') + f"?order_id={payment.order_id}")
        self.assertEqual(resp.status_code, 200)

    @patch('payment.views.MidtransService.get_transaction_status')
    def test_payment_status_view(self, mock_status):
        """Test payment status API endpoint"""
        payment = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-STAT', status='pending')
        mock_status.return_value = {'success': True, 'data': {'transaction_status': 'settlement'}}
        self.client.login(username='u1', password='pass')
        resp = self.client.get(reverse('payment:status', args=[payment.id]) + '?refresh=true')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['success'])

    @patch('payment.views.MidtransService.verify_signature')
    def test_midtrans_webhook_capture_pending(self, mock_verify):
        """Test webhook capture with non-accept fraud status"""
        mock_verify.return_value = True
        payment = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-CAP2', status='pending')
        payload = {
            'order_id': 'ORD-CAP2',
            'transaction_status': 'capture',
            'fraud_status': 'challenge',
            'status_code': '200',
            'gross_amount': '50000',
            'signature_key': 'sig',
            'transaction_id': 'tx999',
        }
        resp = self.client.post(reverse('payment:midtrans_webhook'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'pending')

    @patch('payment.views.MidtransService.verify_signature')
    def test_midtrans_webhook_pending_status(self, mock_verify):
        """Test webhook pending status"""
        mock_verify.return_value = True
        payment = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-PEND', status='pending')
        payload = {
            'order_id': 'ORD-PEND',
            'transaction_status': 'pending',
            'status_code': '201',
            'gross_amount': '50000',
            'signature_key': 'sig',
            'transaction_id': 'tx888',
        }
        resp = self.client.post(reverse('payment:midtrans_webhook'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'pending')

    @patch('payment.views.MidtransService.verify_signature')
    def test_midtrans_webhook_cancel_status(self, mock_verify):
        """Test webhook cancel status"""
        mock_verify.return_value = True
        payment = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-CAN', status='pending')
        payload = {
            'order_id': 'ORD-CAN',
            'transaction_status': 'cancel',
            'status_code': '200',
            'gross_amount': '50000',
            'signature_key': 'sig',
            'transaction_id': 'tx777',
        }
        resp = self.client.post(reverse('payment:midtrans_webhook'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'cancel')

    @patch('payment.views.MidtransService.verify_signature')
    def test_midtrans_webhook_expire_status(self, mock_verify):
        """Test webhook expire status"""
        mock_verify.return_value = True
        payment = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-EXP', status='pending')
        payload = {
            'order_id': 'ORD-EXP',
            'transaction_status': 'expire',
            'status_code': '407',
            'gross_amount': '50000',
            'signature_key': 'sig',
            'transaction_id': 'tx666',
        }
        resp = self.client.post(reverse('payment:midtrans_webhook'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'expire')

    @patch('payment.views.MidtransService.verify_signature')
    def test_midtrans_webhook_failure_status(self, mock_verify):
        """Test webhook failure status"""
        mock_verify.return_value = True
        payment = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-FAIL', status='pending')
        payload = {
            'order_id': 'ORD-FAIL',
            'transaction_status': 'failure',
            'status_code': '500',
            'gross_amount': '50000',
            'signature_key': 'sig',
            'transaction_id': 'tx555',
        }
        resp = self.client.post(reverse('payment:midtrans_webhook'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'failure')

    @patch('payment.views.MidtransService.verify_signature')
    def test_midtrans_webhook_exception_handling(self, mock_verify):
        """Test webhook exception handling"""
        mock_verify.side_effect = Exception('error')
        payload = {'order_id': 'X', 'status_code': '200', 'gross_amount': '100', 'signature_key': 'x', 'transaction_id': 'tx1'}
        resp = self.client.post(reverse('payment:midtrans_webhook'), data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)

    def test_payment_callback_missing_order_id(self):
        """Test callback without order_id"""
        resp = self.client.get(reverse('payment:callback'))
        self.assertEqual(resp.status_code, 302)

    def test_payment_callback_payment_not_found(self):
        """Test callback with non-existent payment"""
        resp = self.client.get(reverse('payment:callback') + '?order_id=NOTFOUND')
        self.assertEqual(resp.status_code, 302)

    @patch('payment.views.MidtransService.get_transaction_status')
    def test_payment_callback_unauthorized_user(self, mock_status):
        """Test callback with different user"""
        other_user = User.objects.create_user(username='other', password='pass')
        payment = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-OTH', status='pending')
        mock_status.return_value = {'success': True, 'data': {'transaction_status': 'settlement'}}
        
        self.client.login(username='other', password='pass')
        resp = self.client.get(reverse('payment:callback') + f'?order_id={payment.order_id}')
        self.assertEqual(resp.status_code, 302)

    @patch('payment.views.MidtransService.get_transaction_status')
    def test_payment_callback_capture_status(self, mock_status):
        """Test callback with capture status"""
        payment = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-CAP3', status='pending')
        mock_status.return_value = {'success': True, 'data': {'transaction_status': 'capture'}}
        resp = self.client.get(reverse('payment:callback') + f'?order_id={payment.order_id}&transaction_status=capture')
        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertIn(payment.status, ['capture', 'settlement'])

    @patch('payment.views.MidtransService.get_transaction_status')
    def test_payment_callback_api_failure(self, mock_status):
        """Test callback when API fails"""
        payment = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-APIF', status='pending')
        mock_status.return_value = {'success': False, 'error': 'API error'}
        resp = self.client.get(reverse('payment:callback') + f'?order_id={payment.order_id}')
        self.assertEqual(resp.status_code, 200)

    @patch('payment.views.MidtransService.get_transaction_status')
    def test_payment_unfinish_missing_order_id(self, mock_status):
        """Test unfinish without order_id"""
        resp = self.client.get(reverse('payment:unfinish'))
        self.assertEqual(resp.status_code, 302)

    @patch('payment.views.MidtransService.get_transaction_status')
    def test_payment_unfinish_not_found(self, mock_status):
        """Test unfinish with non-existent payment"""
        resp = self.client.get(reverse('payment:unfinish') + '?order_id=NOTFOUND')
        self.assertEqual(resp.status_code, 302)

    @patch('payment.views.MidtransService.get_transaction_status')
    def test_payment_error_missing_order_id(self, mock_status):
        """Test error callback without order_id"""
        resp = self.client.get(reverse('payment:error'))
        self.assertEqual(resp.status_code, 302)

    @patch('payment.views.MidtransService.get_transaction_status')
    def test_payment_error_not_found(self, mock_status):
        """Test error callback with non-existent payment"""
        resp = self.client.get(reverse('payment:error') + '?order_id=NOTFOUND')
        self.assertEqual(resp.status_code, 302)

    def test_payment_status_requires_login(self):
        """Test status endpoint requires login"""
        payment = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-AUTH', status='pending')
        resp = self.client.get(reverse('payment:status', args=[payment.id]))
        self.assertEqual(resp.status_code, 302)

    def test_payment_status_without_refresh(self):
        """Test status endpoint without refresh"""
        payment = Payment.objects.create(booking=self.booking, user=self.user, amount=50000, method='credit_card', order_id='ORD-NOREF', status='pending')
        self.client.login(username='u1', password='pass')
        resp = self.client.get(reverse('payment:status', args=[payment.id]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
