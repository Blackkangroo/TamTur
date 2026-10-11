# Tam Tur — SmartLead AI

İstanbul özelinde kurumları ve şahısları **lisanslı rehberlerle** buluşturan Tam Tur için yapay zekâ destekli sohbet ve iletişim bilgisi (lead) toplama uygulaması. Ziyaretçi karşılama sayfasında asistana soru sorar, ilgilenirse isim ve telefon bırakır; işletme sahibi kayıtları yönetim panelinde görür.

Bu proje "SmartLead AI Öğrenci Proje Yönergesi"ne göre, Separation of Concerns ilkesiyle geliştirilmiştir. Hazırlayan: Alp Batu Geçer.

## Canlı adresler

| Ne | Adres |
|---|---|
| Backend (Render) | https://tamtur.onrender.com |
| Sağlık kontrolü | https://tamtur.onrender.com/health |
| Karşılama sayfası | https://tamtur.onrender.com/ |
| Yönetim paneli | https://tamtur.onrender.com/dashboard |
| Kaynak kod (GitHub) | https://github.com/Blackkangroo/TamTur |
| Wix (iki arayüz) | Karşılama: https://alpgecer.wixstudio.com/tamtur · Yönetim paneli: https://alpgecer.wixstudio.com/tamtur/blank |

Render ücretsiz planı boşta kalınca uyur; ilk istek 30-60 saniye sürebilir. Önce `/health` adresini açıp uyandırın.

## Ne yapar?

- **Sohbet:** Ziyaretçinin sorusu Groq API üzerinden yapay zekâya gider. Asistanın kişiliği `config.py` içindeki `BUSINESS_CONTEXT` metnidir: Tam Tur'un hizmetleri, az bilinen tarihi rotalar (Fener-Balat, Kariye, Yedikule, Kuzguncuk, Eyüp, Süleymaniye-Vefa), fiyat için rakam vermeme ve forma yönlendirme kuralı.
- **Lead toplama:** İsim ve telefon SQLite veritabanına kaydedilir, panelde en yeni kayıt üstte listelenir.
- **Hata yönetimi:** Dış servis hataları kullanıcıya kibar bir JSON olarak döner: eksik veri 400, yapay zekâ hatası 503, yeni kayıt 201.

## Mimari

```
TamTur/
├── run.py                  ← Giriş noktası (gunicorn run:app)
├── config.py               ← Modül A: tüm ayarlar, .env okur, BUSINESS_* sabitleri
├── requirements.txt
├── .env.example            ← .env şablonu (.env Git'e girmez)
├── render.yaml             ← Modül H: Render yapılandırması
├── app/
│   ├── __init__.py         ← Modül E: create_app() fabrikası, CORS, /health
│   ├── database.py         ← Modül B: SQLite; SQL YALNIZCA burada
│   ├── routes.py           ← Modül D: iki Blueprint, beş uç nokta; SQL/AI kodu yok
│   ├── services/
│   │   └── ai_service.py   ← Modül C: Groq çağrısı YALNIZCA burada
│   └── templates/          ← Karşılama (Z-Pattern) ve panel (F-Pattern) sayfaları
├── tests/                  ← Modül F kanıtı: 47 pytest testi
└── wix/                    ← Modül G: Wix Velo sayfa kodları ve kurulum rehberi
```

Mimari sözleşme: `database.py` dışında SQL yok, `ai_service.py` dışında yapay zekâ çağrısı yok, `routes.py` yalnızca bu iki katmanın fonksiyonlarını çağırır.

## Kurulum ve çalıştırma

```powershell
git clone https://github.com/Blackkangroo/TamTur.git
cd TamTur
python -m venv venv
.\venv\Scripts\Activate.ps1          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env               # macOS/Linux: cp .env.example .env
# .env içine GROQ_API_KEY=gsk_... yazın (yoksa uygulama "demo modu"nda çalışır)
python config.py                     # Modül A kontrol noktası: ayarlar yazdırılır
python run.py                        # http://localhost:5000
```

## API

| Metod + Yol | Görevi | Başarı | Hata |
|---|---|---|---|
| `GET /health` | Sunucu canlılık kontrolü | 200 `{"basari": true, "durum": "aktif", "isletme": "Tam Tur"}` | — |
| `GET /` | Karşılama sayfası | 200 HTML | — |
| `GET /dashboard` | Yönetim paneli | 200 HTML | — |
| `POST /api/sohbet` | `{"mesaj": "...", "gecmis": [...]}` → yapay zekâ cevabı | 200 `{"basari": true, "cevap": "..."}` | 400 boş mesaj, 503 AI hatası |
| `POST /api/leads` | `{"isim": "...", "telefon": "...", "mesaj": "..."}` → kayıt | 201 `{"basari": true, "lead": {...}}` | 400 eksik veri |
| `GET /api/leads` | Tüm kayıtlar, en yeni ilk | 200 `{"basari": true, "leads": [...]}` | — |

Anahtar adları (`mesaj`, `cevap`, `isim`, `telefon`, `lead`, `leads`, `hata`, `_id`) Wix koduyla birebir aynıdır.

## Test

```powershell
python -m pytest -q        # 47 passed
```

Testler Groq'a gerçek istek atmaz; `requests.post` sahte fonksiyonla değiştirilir.

## Güvenlik

- Groq anahtarı yalnızca `.env` dosyasında ve Render ortam değişkenlerinde; `.env` `.gitignore` ile depo dışında.
- SQL sorgularında yalnızca `?` yer tutucusu; kullanıcı verisi SQL metnine eklenmez.
- Üretimde `DEBUG=False` (`FLASK_ENV=production`).

## Not: yapay zekâ modeli

Yönergedeki `llama-3.1-8b-instant` modeli Ekim 2026'da Groq tarafından kaldırıldı (istek `404 model_not_found` dönüyordu). Önce `qwen/qwen3.8-27b` denendi; konuşma geçmişi gönderildiğinde boş cevap döndürdüğü için `openai/gpt-oss-120b` seçildi. Model adı `.env` içindeki `AI_MODEL` ile değiştirilebilir, kodun başka yeri değişmez.
