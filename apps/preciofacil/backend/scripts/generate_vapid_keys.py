"""Genera un par de claves VAPID para las notificaciones push de PrecioFácil.

Uso:
    python -m scripts.generate_vapid_keys

Imprime las dos variables de entorno a añadir a la configuración del
backend (VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY). Son un par de claves nuevo
por despliegue: no las compartas ni las subas al repositorio.
"""
from __future__ import annotations

from py_vapid import Vapid, b64urlencode
from cryptography.hazmat.primitives import serialization


def main() -> None:
    vapid = Vapid()
    vapid.generate_keys()

    public_raw = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    private_raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")

    print("Añade esto a tu entorno del backend (.env o docker-compose):\n")
    print(f"VAPID_PUBLIC_KEY={b64urlencode(public_raw)}")
    print(f"VAPID_PRIVATE_KEY={b64urlencode(private_raw)}")
    print("VAPID_CLAIMS_EMAIL=mailto:tu-email@ejemplo.com")


if __name__ == "__main__":
    main()
