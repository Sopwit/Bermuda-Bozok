# WeatherWise API Referansı

WeatherWise API, OpenAPI 3.1 standardında tip korumalı uç noktalar sunar.

- **Etkileşimli Swagger UI:** `http://localhost:8000/docs`
- **ReDoc Dokümantasyonu:** `http://localhost:8000/redoc`

---

## 📡 Uç Noktalar

### 1. Sistem Sağlık Denetimi
`GET /health`

Servis durumunu, model yüklenme durumunu ve dış bağımlılıkları döner.

#### Yanıt (200 OK):
```json
{
  "status": "ok",
  "service": "weatherwise-api",
  "version": "1.1.0",
  "model_assets_loaded": true,
  "dependencies": {
    "open_meteo": "configured (no key required)",
    "huggingface": "configured"
  }
}
```

---

### 2. Şehir Arama ve Otomatik Tamamlama
`GET /cities/search?q={query}`

Kullanıcı arama sorgusuna göre eşleşen şehirleri ve koordinatlarını listeler.

#### Yanıt (200 OK):
```json
{
  "status": "success",
  "query": "Istanbul",
  "results": [
    {
      "name": "Istanbul",
      "country": "Turkey",
      "admin1": "Istanbul",
      "latitude": 41.01384,
      "longitude": 28.94966,
      "display_name": "Istanbul, Turkey"
    }
  ]
}
```

---

### 3. Ana Hava Durumu ve Dashboard Yükü
`POST /weather/dashboard`

Tüm hava durumu bileşenlerini (canlı veriler, ML kararları, 24 saatlik tahmin, 7 günlük tahmin, aktivite pencereleri ve kıyafet önerisi) tek bir çağrıda döner.

#### İstek Gövdesi:
```json
{
  "city": "Istanbul",
  "activity": "walking",
  "language": "en"
}
```
*Koordinat bazlı sorgulama için `latitude` ve `longitude` değerleri de verilebilir.*

#### Yanıt (200 OK):
```json
{
  "status": "success",
  "location": "Istanbul",
  "headline": "Pleasant morning. light layers recommended.",
  "reason": "Light wind and mild temperatures make outdoor stay comfortable.",
  "confidence": "high",
  "live_data": {
    "temperature_c": 19.8,
    "feels_like_c": 19.5,
    "precipitation_mm": 0.0,
    "wind_speed_kmh": 9.6,
    "humidity_pct": 67,
    "weather_condition": "clouds",
    "season": "autumn"
  },
  "ml_decision": {
    "umbrella_needed": false,
    "clothing_category": "long_sleeves_light_layer"
  },
  "outfit_plan": {
    "summary": "Light layers suitable for 19°C.",
    "items": ["long_sleeves", "light_jacket"],
    "umbrella_required": false
  },
  "activity_advice": {
    "activity": "walking",
    "recommendation": "recommended",
    "reason": "dry weather and comfortable wind make walking suitable"
  },
  "ai_advice": "Conditions are ideal for walking. Carry light layers for breezy hours.",
  "activities": [
    { "name": "walking", "recommendation": "recommended", "reason": "..." },
    { "name": "cycling", "recommendation": "recommended", "reason": "..." },
    { "name": "outdoor_dining", "recommendation": "acceptable", "reason": "..." }
  ],
  "activity_windows": [],
  "hourly_forecast": [],
  "daily_forecast": []
}
```

---

### 4. Hızlı Tavsiye ve Kıyafet Kararı
`POST /weather/recommendation`

Canlı hava durumuna göre hızlı kıyafet ve şemsiye kararını döner.

#### İstek Gövdesi:
```json
{
  "city": "Ankara",
  "activity": "walking",
  "language": "tr"
}
```

---

### 5. Günlük Aktivite Planlama
`POST /planning/day`

Seçilen aktivite için gün içindeki en uygun saat aralığını hesaplar.

#### İstek Gövdesi:
```json
{
  "city": "Izmir",
  "activity": "cycling"
}
```

#### Yanıt (200 OK):
```json
{
  "status": "success",
  "location": "Izmir",
  "activity": "cycling",
  "best_time_window": "14:00 - 18:00",
  "summary": "Best cycling conditions in the afternoon.",
  "reason": "Low wind and pleasant temperature window.",
  "confidence": "high"
}
```

---

### 6. Çoklu Aktivite Değerlendirmesi
`POST /recommendations/activities`

Desteklenen tüm açık hava aktivitelerini (`walking`, `cycling`, `outdoor_dining`) mevcut hava koşullarına göre karşılaştırmalı olarak değerlendirir.
