"""Efek samping aktivasi: papan klip dan pengumuman suara kode aktivasi.

Suara pengumuman memakai rekaman di ``assets/sounds/<locale>/``
(``activation.wav`` + ``0.wav``..``9.wav``). Aplikasi ini berbahasa Indonesia,
jadi locale diambil dari :class:`SystemConstants` (``id-ID``) - bukan lagi
``zh-CN``.
"""

from __future__ import annotations

from typing import Optional

from src.logging import get_logger

logger = get_logger()


def _locale_aktif() -> str:
    """Lokal audio pengumuman (default Indonesia)."""
    try:
        from src.constants.system import SystemConstants

        return getattr(SystemConstants, "DEFAULT_LOCALE", "id-ID")
    except Exception:
        return "id-ID"


def apply_code_side_effects(code: str, message: Optional[str] = None) -> None:
    """Catat + salin ke papan klip + bacakan; bukan urusan teks CLI/GUI."""
    if not code:
        return
    msg = message or "Silakan masukkan kode aktivasi di panel kontrol"
    logger.info(f"Pemberitahuan aktivasi: {msg}")
    logger.info(f"Kode aktivasi: {code}")

    text = (
        "Silakan masuk ke panel kontrol untuk menambahkan perangkat, "
        f"lalu masukkan kode aktivasi: {' '.join(code)}"
    )
    try:
        from src.utils.common_utils import handle_verification_code

        handle_verification_code(text)
    except Exception as e:
        logger.debug(f"Gagal menyalin kode aktivasi: {e}")

    try:
        from src.utils.activation_announcer import announce_activation_code

        announce_activation_code(code, locale=_locale_aktif())
    except Exception as e:
        logger.debug(f"Gagal mengumumkan kode aktivasi: {e}")


def announce_code(code: str) -> None:
    """Hanya membacakan (dipakai saat percobaan ulang berkala)."""
    if not code:
        return
    from src.utils.activation_announcer import announce_activation_code

    announce_activation_code(code, locale=_locale_aktif())
