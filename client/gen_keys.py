import os, sys
from pathlib import Path

# Allow running from repo root or from the client/ folder
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from shared.crypto_secure import gen_keypair_b64

pk, sk = gen_keypair_b64()
print("SERVER_PUBLIC_KEY_B64=", pk)
print("WORKER_PRIVATE_KEY_B64=", sk)
