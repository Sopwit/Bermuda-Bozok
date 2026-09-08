# WeatherWise Geliştirici Kılavuzu

Bu belge, WeatherWise projesinde yerel geliştirme ortamının kurulumunu, test süreçlerini ve kod standartlarını açıklar.

---

## 💻 Geliştirme Ortamı Kurulumu

### 1. Python Sanal Ortamı ve Bağımlılıklar

```bash
# Sanal ortam oluşturma
python3 -m venv .venv
source .venv/bin/activate

# Paketleri ve geliştirme araçlarını yükleme
pip install -e ".[dev]"
```

### 2. Frontend Kurulumu

```bash
cd frontend
npm install
cd ..
```

---

## 🏃 Servisleri Çalıştırma

Monorepo kök dizininde tanımlı `package.json` betikleri:

| Komut | Açıklama |
|---|---|
| `npm run dev` | Frontend geliştirme sunucusunu başlatır (`localhost:5173`) |
| `npm run dev:backend` | FastAPI backend sunucusunu başlatır (`localhost:8000`) |
| `npm run build` | Frontend TypeScript derlemesini ve prodüksiyon bundle'ını üretir |
| `npm run lint:backend` | Ruff ile backend kod stilini ve kalitesini denetler |
| `npm run lint:frontend` | ESLint ile frontend kod kalitesini denetler |
| `npm test` | Pytest ile tüm backend ve CLI test süitini çalıştırır |

---

## 🧪 Test Süiti

Proje, 24 adet kapsamlı birim, entegrasyon ve CLI testini içerir:

```bash
# Sanal ortamla doğrudan çalıştırma
.venv/bin/pytest -v

# Sadece belirli bir test modülünü çalıştırma
.venv/bin/pytest tests/test_cli.py
```

---

## 🧠 Model Eğitimi

Modelleri yeniden eğitmek için:

```bash
# CLI ile
weatherwise train

# veya doğrudan Python ile
python3 -m weatherwise.train
```
