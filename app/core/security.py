"""
Security utilities for SINPE Bridge API.

Provides:
- HMAC SHA-256 signature validation
- Request signing for Android clients
- Replay protection
- Content hash verification
"""

import hashlib
import hmac
import json
from typing import Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SignatureValidator:
    """Validates HMAC SHA-256 signatures from mobile clients."""
    
    MAX_TIMESTAMP_DIFF = 300  # 5 minutes
    
    @staticmethod
    def compute_signature(body: str, api_key: str) -> str:
        """
        Compute HMAC SHA-256 signature for request body.
        
        Args:
            body: Request body as JSON string
            api_key: Secret API key for signing
            
        Returns:
            Hex-encoded signature
        """
        if isinstance(body, (dict, list)):
            body = json.dumps(body, separators=(",", ":"), sort_keys=True)
        
        signature = hmac.new(
            api_key.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    @staticmethod
    def verify_signature(
        body: str,
        provided_signature: str,
        api_key: str
    ) -> bool:
        """
        Verify HMAC SHA-256 signature.
        
        Args:
            body: Request body as JSON string
            provided_signature: Signature from request header
            api_key: Secret API key for verification
            
        Returns:
            True if signature is valid
        """
        try:
            expected_signature = SignatureValidator.compute_signature(body, api_key)
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(expected_signature, provided_signature)
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    @staticmethod
    def verify_timestamp(timestamp: int) -> bool:
        """
        Verify request timestamp to prevent replay attacks.
        
        Args:
            timestamp: Unix timestamp from request envelope
            
        Returns:
            True if timestamp is within acceptable range
        """
        try:
            request_time = datetime.fromtimestamp(timestamp)
            current_time = datetime.utcnow()
            diff = abs((current_time - request_time).total_seconds())
            
            if diff > SignatureValidator.MAX_TIMESTAMP_DIFF:
                logger.warning(
                    f"Timestamp replay detected: diff={diff}s, "
                    f"request_time={request_time}, current_time={current_time}"
                )
                return False
            
            return True
        except Exception as e:
            logger.error(f"Timestamp verification error: {e}")
            return False


class ContentHashValidator:
    """Validates content hashes (SHA-256) from mobile clients."""
    
    @staticmethod
    def compute_hash(content: str) -> str:
        """
        Compute SHA-256 hash for content.
        
        Args:
            content: Content to hash
            
        Returns:
            Hex-encoded hash
        """
        if isinstance(content, (dict, list)):
            content = json.dumps(content, separators=(",", ":"), sort_keys=True)
        
        return hashlib.sha256(content.encode()).hexdigest()
    
    @staticmethod
    def verify_hash(content: str, provided_hash: str) -> bool:
        """
        Verify SHA-256 content hash.
        
        Args:
            content: Content to verify
            provided_hash: Hash from request envelope
            
        Returns:
            True if hash matches
        """
        try:
            expected_hash = ContentHashValidator.compute_hash(content)
            return hmac.compare_digest(expected_hash, provided_hash)
        except Exception as e:
            logger.error(f"Hash verification error: {e}")
            return False


class DeviceIdentifier:
    """Device identity and anonymization utilities."""
    
    @staticmethod
    def anonymize_device_id(device_id: str) -> str:
        """
        Create anonymized hash of device ID for logging/tracing.
        
        Args:
            device_id: Full device identifier
            
        Returns:
            SHA-256 hash of device ID (short prefix usable for tracing)
        """
        return hashlib.sha256(device_id.encode()).hexdigest()[:16]
    
    @staticmethod
    def create_device_fingerprint(
        device_id: str,
        sim_slot: Optional[int] = None,
        sim_iccid: Optional[str] = None
    ) -> str:
        """
        Create device fingerprint for deduplication and fraud detection.
        
        Args:
            device_id: Device identifier
            sim_slot: SIM slot number
            sim_iccid: SIM ICCID (partially anonymized)
            
        Returns:
            Device fingerprint hash
        """
        fingerprint_data = f"{device_id}:{sim_slot}:{sim_iccid}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()
