# WeatherWise CLI Kılavuzu

WeatherWise, terminal üzerinden hızlı sorgulama, sunucu yönetimi, model eğitimi ve sağlık denetimi yapabileceğiniz güçlü ve bağımsız bir CLI arayüzü sunar.

---

## 🚀 Kullanım Yolları

Sanal ortam aktifken veya monorepo betiğiyle doğrudan çalıştırabilirsiniz:

```bash
# 1. Doğrudan komut (Editable modda kurulduğunda)
weatherwise [KOMUT] [SEÇENEKLER]

# 2. Python modülü olarak
python3 -m weatherwise [KOMUT] [SEÇENEKLER]

# 3. npm monorepo kökünden
npm run cli -- [KOMUT] [SEÇENEKLER]
```

---

## 🛠️ Alt Komutlar

### 1. `query` (veya doğrudan şehir adı)
Belirtilen şehir veya koordinatlar için anlık hava durumu ve ML kıyafet/şemsiye tavsiyesi üretir.

```bash
# Hızlı sorgulama
weatherwise Istanbul
weatherwise "New York"

# Aktivite ve dil seçimi ile
weatherwise query Ankara --activity cycling --lang tr

# Koordinat ile sorgulama
weatherwise query --lat 41.0082 --lon 28.9784

# Ham JSON çıktısı alma (betik ve otomasyonlar için)
weatherwise Istanbul --json
```

---

### 2. `serve`
FastAPI backend API sunucusunu başlatır.

```bash
# Standart başlatma (127.0.0.1:8000)
weatherwise serve

# Geliştirme modunda (otomatik yeniden yükleme)
weatherwise serve --reload --port 8000 --host 0.0.0.0
```

---

### 3. `train`
`data/hourly_observations.csv` veri setini okuyarak XGBoost şemsiye ve kıyafet modellerini eğitir ve `models/` dizinine kaydeder.

```bash
weatherwise train
```

---

### 4. `health`
Sistem durumunu, XGBoost modellerinin hazır olup olmadığını ve dış API servislerinin erişilebilirliğini denetler.

```bash
# Konsol çıktısı
weatherwise health

# JSON formatında çıktı
weatherwise health --json
```
