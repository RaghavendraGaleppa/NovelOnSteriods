import os
import hashlib
import pathlib
from typing import Optional

def get_file_hash(filepath: pathlib.Path) -> Optional[str]:
    """
    Calculates the SHA256 hash of a file's content.
    Returns the hex digest of the hash, or None if the file doesn't exist.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File {filepath} does not exist")
    
    # Use a buffer to handle large files efficiently without loading all into memory.
    with open(filepath, "rb") as f:
        sha256_hash = hashlib.sha256()
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()