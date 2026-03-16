"""
Password Encryption
===================
Instagram password encryption using AES-GCM-256 + NaCl crypto_box_seal.
Fetches encryption keys from Instagram login page or shared_data API.
"""

import json
import os
import re
import time
import logging
from typing import Dict

from .constants import WEB_USER_AGENT, SHARED_DATA_URL

logger = logging.getLogger("instaharvest_v2")


class EncryptionMixin:
    """Password encryption methods for Instagram login."""

    _encryption_keys = None

    def _get_encryption_keys(self) -> Dict[str, str]:
        """
        Fetch encryption keys from Instagram.

        Priority order (to match real browser behavior):
        1. Cached keys (from _warm_up_session)
        2. Login page HTML inline keys (what real browsers use)
        3. Response headers (ig-set-password-encryption-*)
        4. shared_data API (fallback — may return different key_id!)

        Returns: {key_id, public_key, version}
        """
        if self._encryption_keys:
            return self._encryption_keys

        session = self._client._get_curl_session()

        # Method 1: Parse keys from login page HTML (matches real browser)
        try:
            resp = session.get(
                "https://www.instagram.com/accounts/login/",
                headers={"user-agent": WEB_USER_AGENT},
                timeout=15,
            )
            html = resp.text

            # Try inline JSON: {"key_id":"243","public_key":"9c24..."}
            key_id_match = re.search(r'"key_id"\s*:\s*"?(\d+)"?', html)
            pub_key_match = re.search(r'"public_key"\s*:\s*"([a-f0-9]{64})"', html)

            if key_id_match and pub_key_match:
                self._encryption_keys = {
                    "key_id": key_id_match.group(1),
                    "public_key": pub_key_match.group(1),
                    "version": "10",
                }
                logger.info(
                    f"[Auth] Encryption keys from HTML: key_id={key_id_match.group(1)}, "
                    f"pub_key={pub_key_match.group(1)[:20]}..."
                )
                return self._encryption_keys

            # Try _sharedData embedded in HTML
            match = re.search(r'window\._sharedData\s*=\s*({.+?});', html)
            if match:
                shared_data = json.loads(match.group(1))
                encryption = shared_data.get("encryption", {})
                if encryption.get("public_key"):
                    self._encryption_keys = encryption
                    return encryption

            # Try response headers
            key_id = resp.headers.get("ig-set-password-encryption-key-id")
            pub_key = resp.headers.get("ig-set-password-encryption-pub-key")
            version = resp.headers.get("ig-set-password-encryption-web-key-version")
            if key_id and pub_key:
                self._encryption_keys = {
                    "key_id": key_id,
                    "public_key": pub_key,
                    "version": version or "10",
                }
                return self._encryption_keys

        except Exception as e:
            logger.debug(f"HTML key extraction error: {e}")

        # Method 2: shared_data API (fallback)
        try:
            resp = session.get(
                SHARED_DATA_URL,
                headers={
                    "user-agent": WEB_USER_AGENT,
                    "referer": "https://www.instagram.com/accounts/login/",
                },
                timeout=15,
            )
            data = resp.json()
            encryption = data.get("encryption", {})
            if encryption.get("public_key"):
                self._encryption_keys = encryption
                logger.info(f"[Auth] Encryption keys from API: key_id={encryption.get('key_id')}")
                return encryption
        except Exception as e:
            logger.debug(f"shared_data error: {e}")

        raise Exception("Instagram encryption keys not found!")

    def _encrypt_password(self, password: str) -> str:
        """
        Encrypt password for Instagram login.
        Uses AES-GCM-256 + NaCl crypto_box_seal hybrid encryption.

        Flow:
            1. Generate random 32-byte AES key (IV = 12 zero bytes)
            2. Encrypt password with AES-GCM-256 (AAD = timestamp)
            3. Encrypt AES key with NaCl SealedBox (Instagram's public key)
            4. Combine into Instagram's binary format

        Returns:
            str: "#PWD_BROWSER:10:{timestamp}:{encrypted_b64}"
        """
        try:
            from nacl.public import PublicKey, SealedBox
        except ImportError:
            raise ImportError(
                "pynacl is required! Install it: pip install pynacl"
            )

        import base64
        import struct
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        keys = self._get_encryption_keys()
        key_id = int(keys["key_id"])
        pub_key_hex = keys["public_key"]
        version = keys.get("version", "10")

        timestamp = str(int(time.time()))

        # Convert Instagram's hex public key to NaCl PublicKey
        pub_key_bytes = bytes.fromhex(pub_key_hex)
        nacl_key = PublicKey(pub_key_bytes)
        sealed_box = SealedBox(nacl_key)

        # Step 1: Generate random AES-256 key (32 bytes)
        # IV is fixed to 12 zero bytes (Instagram's #PWD_BROWSER:10 specification)
        aes_key = os.urandom(32)
        iv = bytes(12)  # 12 zero bytes (matches Instagram's EnvelopeEncryption JS)

        # Step 2: Encrypt password with AES-GCM-256
        # AAD (Additional Authenticated Data) = timestamp string
        aes_gcm = AESGCM(aes_key)
        password_bytes = password.encode("utf-8")
        aad = timestamp.encode("utf-8")
        encrypted = aes_gcm.encrypt(iv, password_bytes, aad)

        # AES-GCM output: ciphertext + 16-byte auth tag (Python AESGCM order)
        # Instagram expects: tag FIRST, then ciphertext
        aes_tag = encrypted[-16:]
        aes_ciphertext = encrypted[:-16]

        # Step 3: Encrypt only AES key with NaCl SealedBox
        # (sealed_key = 32 bytes plaintext + 48 bytes NaCl overhead = 80 bytes)
        sealed_key = sealed_box.encrypt(aes_key)

        # Step 4: Build Instagram binary format (verified from JS EnvelopeEncryption source)
        # Format: [1:version][1:key_id][2:sealed_key_size_LE][sealed_key][16:tag][ciphertext]
        # NOTE: tag comes BEFORE ciphertext (opposite of Python AESGCM output order)
        payload = b""
        payload += b"\x01"  # version byte (always 1 in binary)
        payload += struct.pack("<B", key_id)  # key_id (1 byte)
        payload += struct.pack("<H", len(sealed_key))  # sealed key size (2 bytes, little-endian)
        payload += sealed_key  # NaCl sealed AES key (80 bytes)
        payload += aes_tag  # 16-byte GCM auth tag (BEFORE ciphertext!)
        payload += aes_ciphertext  # AES-GCM ciphertext (encrypted password)

        enc_b64 = base64.b64encode(payload).decode("utf-8")

        # Instagram uses version from shared_data (currently 10)
        # CAAWebPasswordEncryption reads version from cr:4552.getVersion()
        enc_version = int(version) if version else 10
        return f"#PWD_BROWSER:{enc_version}:{timestamp}:{enc_b64}"
