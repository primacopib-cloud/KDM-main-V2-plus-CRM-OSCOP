"""Smoke tests for brevo_service: phone normalisation + skip-when-unconfigured."""
import asyncio
import os
from unittest.mock import patch

import pytest

from brevo_service import _normalize_phone, send_email, send_sms, is_brevo_configured


def test_normalize_phone_fr_with_country_code():
    assert _normalize_phone("+33 6 12 34 56 78") == "+33612345678"


def test_normalize_phone_fr_local():
    assert _normalize_phone("06 12 34 56 78") == "+33612345678"


def test_normalize_phone_dom():
    assert _normalize_phone("+590 690 11 11 11") == "+590690111111"


def test_normalize_phone_empty_returns_none():
    assert _normalize_phone("") is None
    assert _normalize_phone(None) is None


def test_normalize_phone_garbage_returns_none():
    assert _normalize_phone("abc") is None


def test_is_brevo_configured_reflects_env():
    with patch.dict(os.environ, {"BREVO_API_KEY": ""}, clear=False):
        assert is_brevo_configured() is False
    with patch.dict(os.environ, {"BREVO_API_KEY": "xkeysib-fake"}, clear=False):
        assert is_brevo_configured() is True


@pytest.mark.asyncio
async def test_send_email_skipped_when_no_key():
    with patch.dict(os.environ, {"BREVO_API_KEY": ""}, clear=False):
        res = await send_email("u@example.com", "U", "subj", "<p>x</p>")
    assert res is None


@pytest.mark.asyncio
async def test_send_sms_skipped_for_invalid_phone():
    res = await send_sms("not-a-phone", "hello")
    assert res is None
