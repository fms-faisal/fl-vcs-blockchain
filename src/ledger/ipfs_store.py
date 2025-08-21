import hashlib
from pathlib import Path

class LocalIPFS:
    def __init__(self, root: str | Path = "./.ipfs_local"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def add_bytes(self, data: bytes) -> tuple[str, str]:
        h = hashlib.sha256(data).hexdigest()
        p = self.root / h
        if not p.exists():
            p.write_bytes(data)
        return h, f"ipfs://{h}"

    def get(self, cid: str) -> bytes:
        cid = cid.replace("ipfs://", "")
        p = self.root / cid
        return p.read_bytes()