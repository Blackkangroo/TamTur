"""
app/routes.py - HTTP rotaları; sadece yönlendirme yapar (Modül D).

Gelen isteği alır, girdiyi kontrol eder, doğru katmanı çağırır ve JSON/şablon döner.
Burada SQL ya da yapay zekâ kodu YOKTUR: veritabanı için database.py'deki,
yapay zekâ için ai_service.py'deki fonksiyonlar çağrılır.
İki Blueprint vardır: pages_bp (HTML sayfalar) ve api_bp (/api ile başlayan JSON uçları).
"""
import sqlite3  # yalnızca hata sınıfı (sqlite3.Error) için; burada SQL yazılmaz

from flask import Blueprint, current_app, jsonify, render_template, request

from app.database import lead_ekle, tum_leadler
from app.services.ai_service import AIServiceError, ai_service

# Basit uzunluk sınırları: çok uzun girdileri kibarca reddederiz
MESAJ_MAX = 2000
ISIM_MAX = 100
TELEFON_MAX = 100
# Geçmişten en fazla bu kadar kayıt yapay zekâya gider (arayüzdeki GECMIS_SINIRI ile aynı)
GECMIS_MAX = 10

pages_bp = Blueprint('pages', __name__)
api_bp = Blueprint('api', __name__)


# ---------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------
def _json_hata(mesaj, kod):
    """Her hata için aynı biçim: {"basari": false, "hata": "..."} + HTTP durum kodu."""
    return jsonify({'basari': False, 'hata': mesaj}), kod


def _metin_al(veri, anahtar):
    """JSON sözlüğünden bir metin alanı okur, baştaki/sondaki boşlukları kırpar.

    Alan yoksa veya None ise boş metin döner; böylece kontroller tek tip olur.
    """
    deger = veri.get(anahtar)
    if deger is None:
        return ''
    return str(deger).strip()


# ---------------------------------------------------------------
# Sayfalar (HTML)
# ---------------------------------------------------------------
# Not: İşletme adı ve slogan şablona render_template parametresi olarak geçirilir.
# Alternatif olan context_processor (create_app'te) daha "sihirli"dir;
# parametre yöntemi ise şablondaki {{ isletme_adi }}'nın nereden geldiğini
# tek bakışta gösterir. Bu yüzden sade olanı seçtik.
@pages_bp.route('/')
def index():
    """Karşılama sayfası (ziyaretçi sohbet eder, isim/telefon bırakır)."""
    return render_template(
        'index.html',
        isletme_adi=current_app.config['BUSINESS_NAME'],
        slogan=current_app.config['BUSINESS_SLOGAN'],
    )


@pages_bp.route('/dashboard')
def dashboard():
    """Yönetim paneli (işletme sahibi kayıtları görür)."""
    return render_template(
        'dashboard.html',
        isletme_adi=current_app.config['BUSINESS_NAME'],
        slogan=current_app.config['BUSINESS_SLOGAN'],
    )


# ---------------------------------------------------------------
# API (JSON) - create_app bu blueprint'i '/api' önekiyle kaydeder
# ---------------------------------------------------------------
@api_bp.route('/sohbet', methods=['POST'])
def sohbet():
    """POST /api/sohbet  ->  {"basari": true, "cevap": "..."}"""
    # silent=True: gövde JSON değilse hata fırlatma, None dön.
    # Gövde yoksa, JSON değilse (örn. Content-Type başlığı unutulmuş) ya da JSON ama
    # sözlük değilse (liste, metin, sayı): hemen 400 ve sebebi söyleyen mesaj
    veri = request.get_json(silent=True)
    if not isinstance(veri, dict):
        return _json_hata('İstek gövdesi JSON nesnesi olmalı (Content-Type: application/json).', 400)

    mesaj = _metin_al(veri, 'mesaj')
    if not mesaj:
        return _json_hata('Lütfen bir mesaj yazın.', 400)
    if len(mesaj) > MESAJ_MAX:
        return _json_hata('Mesaj çok uzun (en fazla %d karakter).' % MESAJ_MAX, 400)

    # gecmis opsiyoneldir; liste değilse yok sayarız (servis zaten içini süzer)
    gecmis = veri.get('gecmis')
    if not isinstance(gecmis, list):
        gecmis = []
    # Tarayıcıdaki sınır (GECMIS_SINIRI = 10) sunucuyu korumaz; curl ile gelen istek
    # sınırsız olabilir. Yalnızca son GECMIS_MAX kayıt kalır, fazlası API'ye gitmez.
    gecmis = gecmis[-GECMIS_MAX:]

    # Yapay zekâ çağrısı try-except ile sarılı: hata olursa 503 + kibar mesaj
    try:
        cevap = ai_service.yanit_uret(mesaj, gecmis)
    except AIServiceError as hata:
        # Asıl sebep (401 anahtar yanlış, 429 kota doldu, zaman aşımı...) terminale /
        # Render loguna yazılır; kullanıcı yalnızca kibar mesajı görür.
        current_app.logger.warning('Yapay zekâ hatası: %s', hata.__cause__ or hata)
        return _json_hata(str(hata), 503)

    return jsonify({'basari': True, 'cevap': cevap}), 200


@api_bp.route('/leads', methods=['POST'])
def lead_kaydet():
    """POST /api/leads  ->  201 {"basari": true, "lead": {...}}"""
    veri = request.get_json(silent=True)
    if not isinstance(veri, dict):   # gövde JSON sözlüğü değilse hemen 400 (sohbet ile aynı)
        return _json_hata('İstek gövdesi JSON nesnesi olmalı (Content-Type: application/json).', 400)

    isim = _metin_al(veri, 'isim')
    telefon = _metin_al(veri, 'telefon')
    mesaj = _metin_al(veri, 'mesaj')   # opsiyonel

    # Eksik veri -> 400
    if not isim or not telefon:
        return _json_hata('İsim ve telefon alanları zorunludur.', 400)
    if len(isim) > ISIM_MAX:
        return _json_hata('İsim çok uzun (en fazla %d karakter).' % ISIM_MAX, 400)
    if len(telefon) > TELEFON_MAX:
        return _json_hata('Telefon çok uzun (en fazla %d karakter).' % TELEFON_MAX, 400)
    if len(mesaj) > MESAJ_MAX:
        return _json_hata('Mesaj çok uzun (en fazla %d karakter).' % MESAJ_MAX, 400)

    # Veritabanı çağrısı try-except ile sarılı: dosya kilitli/bozuk ise 500 + kibar mesaj
    try:
        lead = lead_ekle(isim, telefon, mesaj or None)
    except sqlite3.Error as hata:
        # Asıl sebep (dosya bozuk, tablo yok, disk salt okunur...) terminale/Render loguna
        # yazılır; kullanıcı yalnızca kibar mesajı görür (AI yolundaki logger ile aynı desen)
        current_app.logger.error('Veritabanı hatası: %s', hata)
        return _json_hata('Kayıt şu an yapılamadı. Lütfen tekrar deneyin.', 500)

    return jsonify({'basari': True, 'lead': lead}), 201


@api_bp.route('/leads', methods=['GET'])
def lead_listele():
    """GET /api/leads  ->  200 {"basari": true, "leads": [...]}  (en yeni ilk)"""
    try:
        leads = tum_leadler()
    except sqlite3.Error as hata:
        current_app.logger.error('Veritabanı hatası: %s', hata)   # asıl sebep loga
        return _json_hata('Kayıtlar şu an okunamıyor. Lütfen tekrar deneyin.', 500)

    return jsonify({'basari': True, 'leads': leads}), 200