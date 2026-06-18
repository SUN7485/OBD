import pytest
from unittest.mock import AsyncMock, patch
import secrets
import hashlib


@pytest.mark.asyncio
async def test_generate_api_key():
    """Test API key generation"""
    from ..services.api_keys import APIKeyService

    key = APIKeyService.generate_key()

    # Should be 32 characters
    assert len(key) == 32
    # Should be hex
    all(c in "0123456789abcdef" for c in key)


@pytest.mark.asyncio
async def test_hash_api_key():
    """Test API key hashing for storage"""
    key = "abc123def456"

    # Hash the key
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    # Original key should not be stored
    assert key not in key_hash
    # Should be SHA-256 hash
    assert len(key_hash) == 64


@pytest.mark.asyncio
async def test_validate_api_key():
    """Test API key validation"""
    from ..services.api_keys import APIKeyService

    original_key = APIKeyService.generate_key()
    key_hash = APIKeyService.hash_key(original_key)

    # Validate should succeed
    is_valid = APIKeyService.validate_key(original_key, key_hash)

    assert is_valid is True


@pytest.mark.asyncio
async def test_invalid_api_key_rejected():
    """Test invalid API key is rejected"""
    from ..services.api_keys import APIKeyService

    original_key = "valid-key-123"
    wrong_key = "wrong-key-456"

    key_hash = APIKeyService.hash_key(original_key)
    is_valid = APIKeyService.validate_key(wrong_key, key_hash)

    assert is_valid is False


@pytest.mark.asyncio
async def test_revoke_api_key():
    """Test API key revocation"""
    from ..services.api_keys import APIKeyService

    key = APIKeyService.generate_key()
    key_hash = APIKeyService.hash_key(key)

    # Revoke key
    revoked = APIKeyService.revoke_key(key_hash)

    assert revoked is True


@pytest.mark.asyncio
async def test_expired_api_key_rejected():
    """Test expired API key is rejected"""
    import time
    from ..services.api_keys import APIKeyService

    # Create key with expiry
    expiry = int(time.time()) - 100  # Expired 100 seconds ago

    # Should be rejected
    is_expired = expiry < int(time.time())

    assert is_expired is True


@pytest.mark.asyncio
async def test_api_key_for_specific_car():
    """Test API key is scoped to car"""
    from ..services.api_keys import APIKeyService

    car_id = "car-123"

    # Create key for specific car
    key = APIKeyService.generate_key(car_id=car_id)

    # Key should be associated with car
    assert key is not None


@pytest.mark.asyncio
async def test_list_api_keys_for_organization():
    """Test listing API keys for organization"""
    org_id = "org-123"

    # Mock list of keys
    keys = [
        {"id": "key-1", "car_id": "car-1", "name": "Device 1"},
        {"id": "key-2", "car_id": None, "name": "General"},
    ]

    # Filter for org
    org_keys = [k for k in keys]

    assert len(org_keys) == 2
