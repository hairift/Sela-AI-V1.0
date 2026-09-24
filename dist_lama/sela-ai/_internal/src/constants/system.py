# 系统常量定义
from enum import Enum


class InitializationStage(Enum):
    """
    Tahapan inisialisasi.
    """

    DEVICE_FINGERPRINT = "Tahap 1: Menyiapkan identitas perangkat"
    CONFIG_MANAGEMENT = "Tahap 2: Memuat konfigurasi"
    OTA_CONFIG = "Tahap 3: Mengambil konfigurasi OTA"
    ACTIVATION = "Tahap 4: Proses aktivasi"


class SystemConstants:
    """
    Konstanta sistem.
    """

    # Informasi aplikasi
    APP_NAME = "sela-ai"  # 程序标识名（ASCII，用于目录、配置、bundle_id）
    APP_DISPLAY_NAME = "SELA AI"  # 显示名称（用于窗口标题、Launchpad、安装器 UI）
    APP_VERSION = "1.0.0"
    BOARD_TYPE = "bread-compact-wifi"

    # Bahasa antarmuka bawaan (hanya Bahasa Indonesia)
    DEFAULT_LANGUAGE = "id"
    # Lokal audio pengumuman kode aktivasi. Rekaman tersedia di
    # assets/sounds/<locale>/ (activation.wav + 0..9.wav).
    DEFAULT_LOCALE = "id-ID"

    # Pengaturan timeout bawaan
    DEFAULT_TIMEOUT = 10
    ACTIVATION_MAX_RETRIES = 60
    ACTIVATION_RETRY_INTERVAL = 5

    # Nama berkas
    CONFIG_FILE = "config.json"
    EFUSE_FILE = "efuse.json"
