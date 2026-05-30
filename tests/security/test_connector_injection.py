"""Connector credential injection security tests."""

import pytest
from fastapi import HTTPException

from services.api_gateway.routers.connectors import _validate_connector_config


def test_rejects_sql_injection_in_config():
    with pytest.raises(HTTPException) as exc:
        _validate_connector_config({"token": "abc'; DROP TABLE users;--"})
    assert exc.value.status_code == 400


def test_accepts_normal_token():
    _validate_connector_config({"token": "splunk-hec-token-abc123"})
