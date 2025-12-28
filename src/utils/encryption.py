"""Secure credential encryption utilities for JIRA API tokens."""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CredentialEncryption:
    """Secure encryption/decryption for JIRA credentials."""

    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize encryption with key from environment or provided key."""
        if encryption_key:
            self._key = encryption_key.encode()
        else:
            self._key = self._get_or_generate_key()

        self._fernet = Fernet(self._key)

    def _get_or_generate_key(self) -> bytes:
        """Get encryption key from environment or generate new one."""
        env_key = os.getenv('ENCRYPTION_KEY')

        if env_key:
            try:
                # Validate key format
                key_bytes = env_key.encode()
                Fernet(key_bytes)  # This will raise an exception if invalid
                return key_bytes
            except Exception:
                raise ValueError(
                    "Invalid ENCRYPTION_KEY in environment. "
                    "Generate a new key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
        else:
            raise ValueError(
                "ENCRYPTION_KEY not found in environment. "
                "Please set ENCRYPTION_KEY environment variable. "
                "Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

    def encrypt_token(self, token: str) -> bytes:
        """Encrypt a JIRA API token."""
        if not token:
            raise ValueError("Token cannot be empty")

        if len(token.strip()) < 10:
            raise ValueError("Token appears to be too short")

        return self._fernet.encrypt(token.encode())

    def decrypt_token(self, encrypted_token: bytes) -> str:
        """Decrypt a JIRA API token."""
        if not encrypted_token:
            raise ValueError("Encrypted token cannot be empty")

        try:
            return self._fernet.decrypt(encrypted_token).decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt token: {str(e)}")

    def encrypt_credential_dict(self, credentials: dict) -> bytes:
        """Encrypt a dictionary of credentials."""
        import json
        credentials_json = json.dumps(credentials)
        return self._fernet.encrypt(credentials_json.encode())

    def decrypt_credential_dict(self, encrypted_credentials: bytes) -> dict:
        """Decrypt a dictionary of credentials."""
        import json
        try:
            credentials_json = self._fernet.decrypt(encrypted_credentials).decode()
            return json.loads(credentials_json)
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials: {str(e)}")

    def validate_token_format(self, token: str) -> bool:
        """Validate JIRA API token format."""
        if not token or len(token.strip()) < 10:
            return False

        # Basic format validation for Atlassian API tokens
        # They are typically alphanumeric with some special characters
        import re
        pattern = r'^[A-Za-z0-9+/=_-]{20,}$'
        return bool(re.match(pattern, token.strip()))

    @staticmethod
    def generate_key() -> str:
        """Generate a new encryption key."""
        return Fernet.generate_key().decode()

    @staticmethod
    def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> bytes:
        """Derive encryption key from password (alternative to random key)."""
        if salt is None:
            salt = b"ai_transcript_to_jira_salt_2024"  # Use consistent salt

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key


class SecureCredentialManager:
    """High-level credential management with validation."""

    def __init__(self, encryption: Optional[CredentialEncryption] = None):
        """Initialize with encryption instance."""
        self.encryption = encryption or CredentialEncryption()

    def store_jira_credentials(self, username: str, api_token: str, base_url: str) -> bytes:
        """Store JIRA credentials securely."""
        # Validation
        if not username or '@' not in username:
            raise ValueError("Username must be a valid email address")

        if not self.encryption.validate_token_format(api_token):
            raise ValueError("Invalid API token format")

        if not base_url.startswith('https://'):
            raise ValueError("Base URL must use HTTPS")

        # Create credentials dictionary
        credentials = {
            'username': username.strip(),
            'api_token': api_token.strip(),
            'base_url': base_url.strip().rstrip('/'),
            'created_at': 'datetime.now().isoformat()'
        }

        return self.encryption.encrypt_credential_dict(credentials)

    def retrieve_jira_credentials(self, encrypted_credentials: bytes) -> dict:
        """Retrieve JIRA credentials securely."""
        try:
            credentials = self.encryption.decrypt_credential_dict(encrypted_credentials)

            # Validate retrieved credentials
            required_fields = ['username', 'api_token', 'base_url']
            for field in required_fields:
                if field not in credentials:
                    raise ValueError(f"Missing required field: {field}")

            return credentials

        except Exception as e:
            raise ValueError(f"Failed to retrieve credentials: {str(e)}")

    def update_api_token(self, encrypted_credentials: bytes, new_token: str) -> bytes:
        """Update API token in existing credentials."""
        credentials = self.retrieve_jira_credentials(encrypted_credentials)

        if not self.encryption.validate_token_format(new_token):
            raise ValueError("Invalid new API token format")

        credentials['api_token'] = new_token.strip()
        credentials['updated_at'] = 'datetime.now().isoformat()'

        return self.encryption.encrypt_credential_dict(credentials)

    def test_credential_decryption(self, encrypted_credentials: bytes) -> bool:
        """Test if credentials can be decrypted without exposing them."""
        try:
            credentials = self.retrieve_jira_credentials(encrypted_credentials)
            # Verify all required fields exist and have reasonable values
            return (
                bool(credentials.get('username')) and
                bool(credentials.get('api_token')) and
                bool(credentials.get('base_url'))
            )
        except Exception:
            return False

    def get_credential_summary(self, encrypted_credentials: bytes) -> dict:
        """Get non-sensitive summary of credentials."""
        try:
            credentials = self.retrieve_jira_credentials(encrypted_credentials)
            return {
                'username': credentials.get('username', '').replace(
                    credentials.get('username', '').split('@')[0][1:], '*' * 3
                ) if '@' in credentials.get('username', '') else 'Unknown',
                'base_url': credentials.get('base_url', 'Unknown'),
                'token_length': len(credentials.get('api_token', '')),
                'created_at': credentials.get('created_at', 'Unknown'),
                'updated_at': credentials.get('updated_at', 'Never')
            }
        except Exception:
            return {'error': 'Unable to decrypt credentials'}


# Utility functions for CLI usage
def generate_encryption_key() -> str:
    """Generate and return a new encryption key."""
    return CredentialEncryption.generate_key()


def encrypt_jira_token_cli(token: str, key: Optional[str] = None) -> str:
    """CLI utility to encrypt a JIRA token."""
    encryption = CredentialEncryption(key)
    encrypted_token = encryption.encrypt_token(token)
    return base64.b64encode(encrypted_token).decode()


def decrypt_jira_token_cli(encrypted_token_b64: str, key: Optional[str] = None) -> str:
    """CLI utility to decrypt a JIRA token."""
    encryption = CredentialEncryption(key)
    encrypted_token = base64.b64decode(encrypted_token_b64.encode())
    return encryption.decrypt_token(encrypted_token)


if __name__ == "__main__":
    # CLI usage examples
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python encryption.py generate_key")
        print("  python encryption.py encrypt <token>")
        print("  python encryption.py decrypt <encrypted_token_b64>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "generate_key":
        print(f"Generated encryption key: {generate_encryption_key()}")

    elif command == "encrypt" and len(sys.argv) > 2:
        token = sys.argv[2]
        encrypted = encrypt_jira_token_cli(token)
        print(f"Encrypted token: {encrypted}")

    elif command == "decrypt" and len(sys.argv) > 2:
        encrypted_token = sys.argv[2]
        try:
            decrypted = decrypt_jira_token_cli(encrypted_token)
            print(f"Decrypted token: {decrypted}")
        except Exception as e:
            print(f"Decryption failed: {e}")

    else:
        print("Invalid command or missing arguments")