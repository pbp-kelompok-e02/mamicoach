"""
Midtrans API integration service
"""
import base64
import hashlib
import hmac
import json
import os
from typing import Dict, Optional
import requests
from django.conf import settings


class MidtransService:
    """
    Service class to interact with Midtrans Snap API
    """
    
    def __init__(self):
        self.server_key = os.getenv('MIDTRANS_SERVER_KEY', '')
        self.client_key = os.getenv('MIDTRANS_CLIENT_KEY', '')
        self.is_production = os.getenv('MIDTRANS_IS_PRODUCTION', 'false').lower() == 'true'
        
        if self.is_production:
            self.base_url = 'https://app.midtrans.com/snap/v1'
            self.api_url = 'https://api.midtrans.com/v2'
        else:
            self.base_url = 'https://app.sandbox.midtrans.com/snap/v1'
            self.api_url = 'https://api.sandbox.midtrans.com/v2'
    
    def _get_auth_header(self) -> str:
        """Generate Basic Auth header"""
        auth_string = f"{self.server_key}:"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        return f"Basic {auth_b64}"
    
    def _map_payment_method_to_midtrans(self, method: str) -> Dict:
        """
        Map our payment method codes to Midtrans enabled_payments
        """
        mapping = {
            'credit_card': ['credit_card'],
            'bca_va': ['bca_va'],
            'mandiri_va': ['echannel'],  # Mandiri Bill Payment
            'bni_va': ['bni_va'],
            'bri_va': ['bri_va'],
            'permata_va': ['permata_va'],
            'cimb_va': ['cimb_va'],
            'other_va': ['other_va'],
            'indomaret': ['cstore'],
            'alfamart': ['cstore'],
            'gopay': ['gopay'],
            'akulaku': ['akulaku'],
            'shopeepay': ['shopeepay'],
            'kredivo': ['kredivo'],
            'qris': ['qris'],
            'dana': ['dana'],
            'danamon_va': ['danamon_va'],
            'bsi_va': ['bsi_va'],
            'seabank_va': ['seabank_va'],
        }
        return mapping.get(method, ['credit_card'])
    
    def create_transaction(
        self,
        order_id: str,
        amount: int,
        customer_details: Dict,
        item_details: list,
        payment_method: Optional[str] = None
    ) -> Dict:
        """
        Create Midtrans Snap transaction
        
        Args:
            order_id: Unique order ID
            amount: Total amount in IDR
            customer_details: Customer information (first_name, last_name, email, phone)
            item_details: List of items [{id, price, quantity, name}]
            payment_method: Optional specific payment method to enable
        
        Returns:
            Dict with 'token', 'redirect_url', and raw 'response'
        """
        url = f"{self.base_url}/transactions"
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': self._get_auth_header()
        }
        
        # Get base URL from settings
        base_url = getattr(settings, 'BASE_URL', 'https://kevin-cornellius-mamicoach.pbp.cs.ui.ac.id')
        
        payload = {
            'transaction_details': {
                'order_id': order_id,
                'gross_amount': amount
            },
            'customer_details': customer_details,
            'item_details': item_details,
            'callbacks': {
                'finish': f"{base_url}/payment/callback/",
                'unfinish': f"{base_url}/payment/unfinish/",
                'error': f"{base_url}/payment/error/",
            }
        }
        
        # If specific payment method is chosen, enable only that
        if payment_method:
            enabled_payments = self._map_payment_method_to_midtrans(payment_method)
            payload['enabled_payments'] = enabled_payments
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'token': data.get('token'),
                'redirect_url': data.get('redirect_url'),
                'response': data
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'response': getattr(e.response, 'text', None) if hasattr(e, 'response') else None
            }
    
    def get_transaction_status(self, order_id: str) -> Dict:
        """
        Get transaction status from Midtrans
        
        Args:
            order_id: Order ID to check
            
        Returns:
            Dict with transaction status
        """
        url = f"{self.api_url}/{order_id}/status"
        
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': self._get_auth_header()
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return {
                'success': True,
                'data': response.json()
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_signature(self, order_id: str, status_code: str, gross_amount: str, signature_key: str) -> bool:
        """
        Verify Midtrans notification signature
        
        Args:
            order_id: Order ID
            status_code: Status code from notification
            gross_amount: Gross amount from notification
            signature_key: Signature key from notification
            
        Returns:
            Boolean indicating if signature is valid
        """
        string_to_hash = f"{order_id}{status_code}{gross_amount}{self.server_key}"
        
        hash_result = hashlib.sha512(string_to_hash.encode('utf-8')).hexdigest()
        
        return hash_result == signature_key
