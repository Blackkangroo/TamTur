"""
config.py - Tüm ayarlar ve gizli anahtarlar tek yerde (Modül A).

Bu dosya .env dosyasını okur ve ayarları Config sınıfında toplar.
Diğer dosyalar anahtarları doğrudan .env'den değil, buradan alır.
Böylece bir ayarın nerede tanımlandığı sorusunun tek cevabı vardır: config.py.
İşletmeye özel üç şey de (ad, slogan, BUSINESS_CONTEXT) burada tutulur.
"""
import os

from dotenv import load_dotenv

# .env dosyasını okur ve içindekileri ortam değişkeni yapar.
# Bu satır dosyanın BAŞINDA olmalı; aksi hâlde aşağıdaki os.environ.get'ler .env'i görmez.
load_dotenv()

# Projenin kök klasörü (config.py'nin bulunduğu klasör). Göreli yolları buna göre çözeriz.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _veritabani_yolu():
    """DATABASE_URL'i okur; göreli bir yolsa proje köküne göre mutlak yola çevirir."""
    yol = os.environ.get('DATABASE_URL', 'smartlead.db')
    if os.path.isabs(yol):
        return yol
    return os.path.join(BASE_DIR, yol)


def _cors_listesi():
    """CORS_ORIGINS'i ("*" veya virgülle ayrılmış adresler) listeye çevirir."""
    ham = os.environ.get('CORS_ORIGINS', '*')
    # "a, b ,c" -> ["a", "b", "c"]  (boş parçalar atılır)
    return [parca.strip() for parca in ham.split(',') if parca.strip()]


class Config:
    """Her ortamda ortak olan ayarlar.

    Ortam/gizli ayarlar os.environ.get('ANAHTAR', 'varsayilan') ile .env'den okunur;
    işletme metinleri (BUSINESS_*) gizli olmadığı için doğrudan burada yazılır.
    """

    # Flask'ın çerez/oturum imzası için kullandığı anahtar
    SECRET_KEY = os.environ.get('SECRET_KEY', 'gelistirme-icin-gecici-anahtar')

    # SQLite dosyasının tam yolu
    DATABASE_URL = _veritabani_yolu()

    # Yapay zekâ ayarları. Anahtar boşsa servis "demo modu"nda çalışır.
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
    # Sağlayıcı adı: yönerge (Modül A) bu ayarı ister. Şu an tek sağlayıcı Groq olduğu
    # için kodda okunmaz; ileride sağlayıcı değişirse ai_service.py bu değere bakar.
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'groq')
    # Model adı: yönerge llama-3.1-8b-instant diyordu; Groq o modeli Ekim 2026'da kaldırdı
    # (istek 404 model_not_found dönüyordu). Yeni model .env'deki AI_MODEL ile
    # değiştirilebilir; kodun başka yerine dokunmak gerekmez.
    AI_MODEL = os.environ.get('AI_MODEL', 'openai/gpt-oss-120b')

    # Tarayıcıdan API'ye istek atabilecek siteler (liste)
    CORS_ORIGINS = _cors_listesi()

    # ---------------------------------------------------------------
    # İŞLETMEYE ÖZEL AYARLAR - projeyi kendi konunuza uyarlarken
    # değiştireceğiniz ilk üç şey bunlardır. Arayüz metinleri (tanıtım paragrafı,
    # hizmet kartları, renkler) için app/templates/*.html ve wix/*.js içindeki
    # DEĞİŞTİR etiketlerine de bakın.
    # ---------------------------------------------------------------
    BUSINESS_NAME = 'Tam Tur'                         # DEĞİŞTİR: kendi işletmenize göre
    # Çift tırnak: metnin içinde kesme işareti (İstanbul'u) olduğu için
    BUSINESS_SLOGAN = "İstanbul'u lisanslı rehberlerle, az bilinen rotalarından keşfedin."  # DEĞİŞTİR
    # DEĞİŞTİR: kendi işletmenize göre (yapay zekânın kişiliği ve bildiği gerçekler)
    BUSINESS_CONTEXT = """sen detaylı bilgi veren yapay zekasın"""


class DevelopmentConfig(Config):
    """Geliştirme ortamı: hata ayıklama açık, hatalar tarayıcıda ayrıntılı görünür."""
    DEBUG = True


class ProductionConfig(Config):
    """Üretim ortamı (Render): hata ayıklama kapalı."""
    DEBUG = False


# create_app bu sözlükten ortama göre doğru sınıfı seçer: config['development'] gibi.
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}


if __name__ == '__main__':
    # Modül A kontrol noktası: "python config.py" ile ayarların okunduğunu göster.
    # Anahtarın tamamını asla yazdırmayız; sadece ilk 4 karakterini maskeli gösteririz.
    anahtar = Config.GROQ_API_KEY
    maskeli = (anahtar[:4] + '****') if anahtar else '(boş -> demo modu)'
    print('BUSINESS_NAME :', Config.BUSINESS_NAME)
    print('BUSINESS_SLOGAN:', Config.BUSINESS_SLOGAN)
    print('DATABASE_URL  :', Config.DATABASE_URL)
    print('AI_PROVIDER   :', Config.AI_PROVIDER)
    print('AI_MODEL      :', Config.AI_MODEL)
    print('GROQ_API_KEY  :', maskeli)
    print('CORS_ORIGINS  :', Config.CORS_ORIGINS)
    print('DEBUG (dev)   :', DevelopmentConfig.DEBUG, '| DEBUG (prod):', ProductionConfig.DEBUG)
