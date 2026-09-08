# WeatherWise (Bermuda-Bozok)

[![Python](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13%20|%203.14-blue)](pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**WeatherWise**, ham hava durumu verilerini gündelik hayat için anlamlı, doğrudan uygulanabilir kararlara (kıyafet seçimi, şemsiye ihtiyacı, açık hava aktivite uygunluğu ve en uygun zaman aralığı) dönüştüren yüksek performanslı, yapay zeka destekli bir full-stack hava durumu ve yaşam asistanıdır.

---

## ⚡ Temel Mimari ve Performans Optimizasyonları

- **Paralel Asenkron HTTP/2 Boru Hattı:** Open-Meteo verileri tek bir birleşik çağrı (`current`, `hourly`, `daily`) ve Air Quality API çağrısı ile `asyncio.gather` üzerinden paralel olarak toplanır. Persistent connection pool ve keep-alive ile gecikme **~90ms** seviyesindedir.
- **Alt-Milisaniye (< 0.7ms) ML Çıkarımı:** Pandas ve dinamik DataFrame serileştirme yükü kaldırılarak, önceden dizinlenmiş öznitelik haritası ve doğrudan NumPy vektör / XGBoost inplace çıkarım mimarisine geçilmiştir.
- **Zaman Dilimi Uyumlu Tahmin:** Sunucu saati yerine hedeflenen konumun yerel zaman damgası (`current.time`) referans alınarak 24 saatlik pencere kaymaları önlenir.
- **Hibrit Önbellekleme & Sıkıştırma:** TTLCache ile sık sorgulanan konumlar sıfır ağ maliyetiyle yanıtlanır; GZip middleware ile transfer boyutu %70 sıkıştırılır.
- **LLM Destekli Doğal Dil Tavsiyesi:** Hugging Face Router üzerinden dinamik metin üretimi; ağ gecikmesi durumunda anında deterministik fallback mekanizması.

---

## 📂 Proje Yapısı

```
.
├── src/
│   └── weatherwise/            # Backend uygulama paketi
│       ├── main.py             # FastAPI rotaları, lifespan ve middleware
│       ├── services.py         # Asenkron veri boru hattı, ML çıkarımı ve optimizasyonlar
│       ├── schemas.py          # Pydantic v2 veri modelleri ve doğrulayıcılar
│       ├── config.py           # Ortam değişkenleri ve çalışma zamanı ayarları
│       └── train.py            # XGBoost modelleri eğitim betiği
├── frontend/                   # React 19 + TypeScript + Tailwind CSS v4 arayüzü
│   ├── src/
│   │   ├── components/         # Modüler UI bileşenleri (Hero, Hourly, Daily, Activities, vb.)
│   │   ├── lib/api.ts          # Tip korumalı API istemcisi ve doğrulayıcılar
│   │   └── App.tsx             # Ana dashboard uygulaması
│   └── vite.config.ts          # Vite geliştirme ve reverse proxy yapılandırması
├── models/                     # Eğitilmiş XGBoost model ve encoder artifaktları (.joblib)
├── data/                       # Eğitim veri setleri (.csv)
├── tests/                      # Kapsamlı pytest test süiti
└── postman/                    # API test ve sunum koleksiyonu
```

---

## 🚀 Hızlı Başlangıç

### Gereksinimler
- Python `3.11+`
- Node.js `20+` ve npm

### 1. Monorepo / Backend Kurulumu

```bash
# Sanal ortam oluşturma ve etkinleştirme
python3 -m venv .venv
source .venv/bin/activate

# Bağımlılıkların yüklenmesi
pip install -e ".[dev]"
```

### 2. Frontend Kurulumu

```bash
cd frontend
npm install
cd ..
```

### 3. Servisleri Başlatma

Kök dizindeki geliştirici betikleri ile:

```bash
# Backend'i başlatma (Port 8000)
npm run dev:backend

# Frontend'i başlatma (Port 5173)
npm run dev:frontend
```

Alternatif doğrudan komutlar:
```bash
# Backend
.venv/bin/uvicorn weatherwise.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

---

## ⚙️ Ortam Değişkenleri (.env)

Kök dizinde `.env` dosyası oluşturularak yapılandırılabilir:

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `HF_API_KEY` | `None` | Hugging Face Router API anahtarı (Opsiyonel, LLM tavsiyeleri için) |
| `WEATHERWISE_CACHE_TTL_SECONDS` | `600` | Yanıt önbellek süresi (saniye) |
| `WEATHERWISE_REQUEST_TIMEOUT_SECONDS` | `5` | Dış servis istek zaman aşımı (saniye) |

*Not: Open-Meteo hava durumu sorguları API anahtarı gerektirmez.*

---

## 📡 API Uç Noktaları

### `GET /health`
Servis sağlığını, model durumunu ve dış bağımlılıkları raporlar.

### `GET /cities/search?q={query}`
Şehir adı otomatik tamamlama ve koordinat çözümleme önerileri döner.

### `POST /weather/dashboard`
Ana dashboard yükünü tek seferde toplar (canlı hava, saatlik tahmin, 7 günlük görünüm, ML kararları, aktivite pencereleri ve kıyafet planı).

```json
{
  "city": "Istanbul",
  "activity": "walking",
  "language": "en"
}
```

Veya koordinat bazlı:
```json
{
  "city": "Current Location",
  "latitude": 41.0082,
  "longitude": 28.9784,
  "activity": "walking",
  "language": "en"
}
```

### `POST /weather/recommendation`
Canlı hava durumuna göre hızlı kıyafet ve şemsiye tavsiyesi üretir.

### `POST /planning/day`
Seçilen aktivite (`walking`, `cycling`, `outdoor_dining`) için gün içindeki en uygun saat aralığını ve uygunluk skorunu hesaplar.

### `POST /recommendations/activities`
Tüm desteklenen aktiviteler için eşzamanlı uygunluk durumunu değerlendirir.

---

## 🧪 Test ve Kalite Kontrol

```bash
# Python testlerini çalıştırma (17 Test)
.venv/bin/pytest

# Backend statik kod analizi (Ruff)
.venv/bin/ruff check .

# Frontend tip denetimi ve build testi
cd frontend && npm run lint && npm run build
```

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır.

