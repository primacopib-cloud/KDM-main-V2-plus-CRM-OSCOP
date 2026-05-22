from dataclasses import dataclass
from typing import Dict, Any
import uuid

@dataclass
class CheckoutSessionRequest:
    amount: float
    currency: str
    success_url: str
    cancel_url: str
    metadata: Dict[str, Any]

@dataclass
class CheckoutSessionResponse:
    session_id: str
    url: str

@dataclass
class CheckoutStatusResponse:
    status: str
    payment_status: str

class StripeCheckout:
    def __init__(self, api_key: str, webhook_url: str):
        self.api_key = api_key
        self.webhook_url = webhook_url
    async def create_checkout_session(self, request: CheckoutSessionRequest):
        sid = 'cs_test_' + uuid.uuid4().hex[:24]
        return CheckoutSessionResponse(session_id=sid, url=f'https://checkout.stripe.test/{sid}')
    async def get_checkout_status(self, session_id: str):
        return CheckoutStatusResponse(status='complete', payment_status='paid')
