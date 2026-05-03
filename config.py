# config.py
# Sistem genel ayarları, varsayılan pazaryerleri ve sabitler

import os

# Proje dizinleri
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
UPLOAD_DIR = os.path.join(EXPORT_DIR, "uploads")
REPORT_DIR = os.path.join(EXPORT_DIR, "reports")

# Veritabanı yolu
DATABASE_PATH = os.path.join(DATA_DIR, "marketplace.db")

# Para birimi
CURRENCY = "TRY"

# Karlılık uyarı eşikleri
LOW_MARGIN_THRESHOLD = 10.0      # %10 altı düşük marj
LOSS_THRESHOLD = 0.0             # 0 altı zarar

# Varsayılan Türkiye pazaryerleri
DEFAULT_MARKETPLACES = [
    {
        "pazaryeri_adi": "Trendyol",
        "komisyon": 21.5,
        "kargo": 45.0,
        "kupon": 0.0,
        "stopaj": 1.0,
        "kdv": 20.0,
        "hizmet_bedeli": 8.5,
        "ekstra_gider": 0.0,
        "varsayilan": 1,
    },
    {
        "pazaryeri_adi": "Hepsiburada",
        "komisyon": 18.0,
        "kargo": 42.0,
        "kupon": 0.0,
        "stopaj": 1.0,
        "kdv": 20.0,
        "hizmet_bedeli": 7.0,
        "ekstra_gider": 0.0,
        "varsayilan": 0,
    },
    {
        "pazaryeri_adi": "N11",
        "komisyon": 17.5,
        "kargo": 40.0,
        "kupon": 0.0,
        "stopaj": 1.0,
        "kdv": 20.0,
        "hizmet_bedeli": 6.5,
        "ekstra_gider": 0.0,
        "varsayilan": 0,
    },
    {
        "pazaryeri_adi": "Amazon TR",
        "komisyon": 15.0,
        "kargo": 48.0,
        "kupon": 0.0,
        "stopaj": 1.0,
        "kdv": 20.0,
        "hizmet_bedeli": 10.0,
        "ekstra_gider": 0.0,
        "varsayilan": 0,
    },
]

# Gerekli klasörleri oluştur
for directory in [DATA_DIR, EXPORT_DIR, UPLOAD_DIR, REPORT_DIR]:
    os.makedirs(directory, exist_ok=True)