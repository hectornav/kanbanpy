"""
gen_vapid.py - Generate a VAPID keypair for Web Push.

Usage:
    cd server && python gen_vapid.py >> ../.env
Then restart the app. Keep the private key secret.
"""
import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def main() -> None:
    priv = ec.generate_private_key(ec.SECP256R1())
    public_point = priv.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    private_value = priv.private_numbers().private_value.to_bytes(32, "big")
    print(f"KANBAN_VAPID_PUBLIC_KEY={_b64(public_point)}")
    print(f"KANBAN_VAPID_PRIVATE_KEY={_b64(private_value)}")


if __name__ == "__main__":
    main()
