# WeatherWise

[![Python](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13%20|%203.14-blue)](pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**WeatherWise**, canlı meteoroloji verilerini yapay zeka ve makine öğrenimi modelleriyle analiz ederek doğrudan uygulanabilir kararlara (kıyafet seçimi, şemsiye ihtiyacı, aktivite uygunluğu ve gün içi en iyi zaman aralığı) dönüştüren full-stack bir yaşam asistanıdır.

---

## 🚀 Hızlı Başlangıç

### 1. Kurulum

```bash
# Python sanal ortamı ve backend bağımlılıkları
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend bağımlılıkları
cd frontend && npm install && cd ..
```

### 2. Başlatma

```bash
# Backend (Port 8000)
npm run dev:backend

# Frontend (Port 5173)
npm run dev:frontend
```

### 3. Terminalden Hızlı Sorgulama (CLI)

```bash
# Şehir sorgulama
weatherwise Istanbul

# JSON çıktısı ile
weatherwise Ankara --json
```

---

## 📚 Dokümantasyon

Detaylı teknik dokümanlar `docs/` dizininde kategorize edilmiştir:

| Doküman | İçerik |
|---|---|
| 🏛️ [**Mimari Dokümantasyonu**](docs/ARCHITECTURE.md) | Asenkron HTTP/2 boru hattı, alt-milisaniye ML çıkarımı, zaman dilimi sabitleme ve LLM fallback mekanizması |
| 📡 [**API Referansı**](docs/API.md) | REST API rotaları (`/health`, `/weather/dashboard`, `/planning/day` vb.), istek/yanıt JSON şemaları |
| 💻 [**CLI Kılavuzu**](docs/CLI.md) | `weatherwise` komut satırı aracı, alt komutlar (`query`, `serve`, `train`, `health`) ve kullanım örnekleri |
| 🛠️ [**Geliştirici Kılavuzu**](docs/DEVELOPMENT.md) | Ortam kurulumu, 24 testlik Pytest süiti, model eğitimi ve kod kalitesi araçları |

---

## ⚡ Monorepo Geliştirici Komutları

```bash
npm run dev           # Frontend geliştirme sunucusu
npm run dev:backend   # FastAPI backend sunucusu (Port 8000)
npm test              # Pytest backend ve CLI test süiti (24 test)
npm run lint:backend  # Ruff statik kod analizi
npm run lint:frontend # ESLint arayüz denetimi
npm run build         # Frontend prodüksiyon derlemesi
```

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) altında korunmaktadır.
