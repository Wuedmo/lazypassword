"""
SSH key management for lazypassword.
Handles secure storage and operations on SSH keys.
"""

import os
import re
import uuid
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass, field, asdict

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.backends import default_backend


@dataclass
class SSHKey:
    """Represents an SSH key pair stored in the vault."""
    
    id: str
    name: str
    private_key: str
    public_key: str
    passphrase: str = ""
    key_type: str = "ed25519"  # ed25519 or rsa
    comment: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> dict:
        """Convert SSHKey to dictionary for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "SSHKey":
        """Create SSHKey from dictionary."""
        return cls(**data)
    
    @staticmethod
    def generate_keypair(key_type: str = "ed25519", comment: str = "") -> Tuple[str, str]:
        """
        Generate a new SSH key pair.
        
        Args:
            key_type: Type of key to generate ('ed25519' or 'rsa')
            comment: Comment to add to the public key
            
        Returns:
            Tuple of (private_key_pem, public_key_openssh)
        """
        if key_type == "ed25519":
            private_key = ed25519.Ed25519PrivateKey.generate()
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.OpenSSH,
                encryption_algorithm=serialization.NoEncryption()
            )
            public_bytes = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH
            )
        elif key_type == "rsa":
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
            public_bytes = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH
            )
        else:
            raise ValueError(f"Unsupported key type: {key_type}. Use 'ed25519' or 'rsa'.")
        
        private_key_str = private_bytes.decode('utf-8')
        public_key_str = public_bytes.decode('utf-8')
        
        if comment:
            public_key_str = f"{public_key_str} {comment}"
        
        return private_key_str, public_key_str


class SSHManager:
    """Manages SSH keys stored in the vault."""
    
    def __init__(self, vault):
        """
        Initialize SSH manager with a vault instance.
        
        Args:
            vault: Vault instance for storage
        """
        self.vault = vault
    
    def generate_keypair(self, name: str, key_type: str = "ed25519", comment: str = "") -> SSHKey:
        """
        Generate a new SSH key pair and store it in the vault.
        
        Args:
            name: Human-readable name for the key
            key_type: Type of key ('ed25519' or 'rsa')
            comment: Optional comment for the public key
            
        Returns:
            SSHKey: The generated and stored key
        """
        private_key_str, public_key_str = SSHKey.generate_keypair(key_type, comment)
        
        ssh_key = SSHKey(
            id=str(uuid.uuid4()),
            name=name,
            private_key=private_key_str,
            public_key=public_key_str,
            key_type=key_type,
            comment=comment,
        )
        
        self.add_key(ssh_key)
        return ssh_key
    
    def add_key(self, ssh_key: SSHKey) -> None:
        """
        Add an existing SSH key to the vault.
        
        Args:
            ssh_key: SSHKey instance to store
        """
        self.vault.add_ssh_key(ssh_key.to_dict())
    
    def add_existing_key(self, name: str, private_key: str, public_key: str,
                         passphrase: str = "", key_type: str = "ed25519",
                         comment: str = "") -> SSHKey:
        """
        Add an existing SSH key to the vault.
        
        Args:
            name: Human-readable name for the key
            private_key: The private key content (PEM format)
            public_key: The public key content (OpenSSH format)
            passphrase: Optional passphrase for the private key
            key_type: Type of key ('ed25519', 'rsa', etc.)
            comment: Optional comment
            
        Returns:
            SSHKey: The added key
        """
        ssh_key = SSHKey(
            id=str(uuid.uuid4()),
            name=name,
            private_key=private_key,
            public_key=public_key,
            passphrase=passphrase,
            key_type=key_type,
            comment=comment,
        )
        self.add_key(ssh_key)
        return ssh_key
    
    def get_key(self, key_id: str) -> Optional[SSHKey]:
        """
        Get an SSH key by ID.
        
        Args:
            key_id: The key's unique ID
            
        Returns:
            SSHKey if found, None otherwise
        """
        keys = self.vault.get_ssh_keys()
        for key_data in keys:
            if key_data.get("id") == key_id:
                return SSHKey.from_dict(key_data)
        return None
    
    def list_keys(self) -> list:
        """
        List all SSH keys in the vault.
        
        Returns:
            List of SSHKey objects
        """
        keys = self.vault.get_ssh_keys()
        return [SSHKey.from_dict(k) for k in keys]
    
    def delete_key(self, key_id: str) -> bool:
        """
        Delete an SSH key from the vault.
        
        Args:
            key_id: The key's unique ID
            
        Returns:
            True if deleted, False if not found
        """
        return self.vault.delete_ssh_key(key_id)
    
    def export_private_key(self, key_id: str, filepath: str) -> bool:
        """
        Export a private key to a file with proper permissions (600).
        
        Args:
            key_id: The key's unique ID
            filepath: Path to save the private key
            
        Returns:
            True if successful
        """
        ssh_key = self.get_key(key_id)
        if not ssh_key:
            raise ValueError(f"Key with ID '{key_id}' not found")
        
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the key with restrictive permissions
        # Use os.open with O_CREAT | O_WRONLY | O_TRUNC and mode 600
        flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
        fd = os.open(path, flags, 0o600)
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(ssh_key.private_key)
        except:
            os.close(fd)
            raise
        
        return True
    
    def export_public_key(self, key_id: str, filepath: str) -> bool:
        """
        Export a public key to a file with proper permissions (644).
        
        Args:
            key_id: The key's unique ID
            filepath: Path to save the public key
            
        Returns:
            True if successful
        """
        ssh_key = self.get_key(key_id)
        if not ssh_key:
            raise ValueError(f"Key with ID '{key_id}' not found")
        
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write with standard public key permissions
        flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
        fd = os.open(path, flags, 0o644)
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(ssh_key.public_key)
        except:
            os.close(fd)
            raise
        
        return True
    
    def add_to_ssh_agent(self, key_id: str) -> bool:
        """
        Add a private key to the running ssh-agent.
        
        Args:
            key_id: The key's unique ID
            
        Returns:
            True if successful
        """
        ssh_key = self.get_key(key_id)
        if not ssh_key:
            raise ValueError(f"Key with ID '{key_id}' not found")
        
        # Check if ssh-agent is running
        result = subprocess.run(
            ["ssh-add", "-l"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 2:
            # No ssh-agent running
            raise RuntimeError("ssh-agent is not running. Start it with: eval $(ssh-agent -s)")
        
        # Write key to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='_key', delete=False) as f:
            f.write(ssh_key.private_key)
            temp_path = f.name
        
        try:
            # Add to ssh-agent
            result = subprocess.run(
                ["ssh-add", temp_path],
                capture_output=True,
                text=True,
                input=ssh_key.passphrase + "\n" if ssh_key.passphrase else None
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Failed to add key to ssh-agent: {result.stderr}")
            
            return True
        finally:
            # Securely delete the temp file
            try:
                # Overwrite with zeros before deletion
                with open(temp_path, 'wb') as f:
                    f.write(b'\x00' * len(ssh_key.private_key.encode()))
                os.unlink(temp_path)
            except:
                pass
    
    def get_key_fingerprint(self, key_id: str, hash_type: str = "sha256") -> str:
        """
        Get the fingerprint of an SSH key.
        
        Args:
            key_id: The key's unique ID
            hash_type: 'sha256' or 'md5'
            
        Returns:
            The fingerprint string
        """
        ssh_key = self.get_key(key_id)
        if not ssh_key:
            raise ValueError(f"Key with ID '{key_id}' not found")
        
        # Use ssh-keygen to get the fingerprint
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='_key', delete=False) as f:
            f.write(ssh_key.public_key)
            temp_path = f.name
        
        try:
            fingerprint_args = ["ssh-keygen", "-lf", temp_path]
            if hash_type == "md5":
                fingerprint_args.append("-E")
                fingerprint_args.append("md5")
            
            result = subprocess.run(
                fingerprint_args,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Failed to get fingerprint: {result.stderr}")
            
            # Parse output: "2048 MD5:xx:xx:xx... comment (RSA)"
            output = result.stdout.strip()
            match = re.search(r'(?:MD5|SHA256):([\w\+\/]+)', output)
            if match:
                return f"{hash_type.upper()}:{match.group(1)}"
            return output
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def get_key_info(self, key_id: str) -> dict:
        """
        Get comprehensive information about a key.
        
        Args:
            key_id: The key's unique ID
            
        Returns:
            Dictionary with key information
        """
        ssh_key = self.get_key(key_id)
        if not ssh_key:
            raise ValueError(f"Key with ID '{key_id}' not found")
        
        try:
            sha256_fp = self.get_key_fingerprint(key_id, "sha256")
        except:
            sha256_fp = "N/A"
        
        try:
            md5_fp = self.get_key_fingerprint(key_id, "md5")
        except:
            md5_fp = "N/A"
        
        # Mask the private key - only show first and last few chars
        private_masked = "***[HIDDEN]***"
        if len(ssh_key.private_key) > 60:
            private_masked = f"{ssh_key.private_key[:30]}...{ssh_key.private_key[-30:]}"
        
        return {
            "id": ssh_key.id,
            "name": ssh_key.name,
            "key_type": ssh_key.key_type,
            "comment": ssh_key.comment,
            "has_passphrase": bool(ssh_key.passphrase),
            "public_key": ssh_key.public_key,
            "private_key_masked": private_masked,
            "sha256_fingerprint": sha256_fp,
            "md5_fingerprint": md5_fp,
            "created_at": ssh_key.created_at,
            "updated_at": ssh_key.updated_at,
        }
