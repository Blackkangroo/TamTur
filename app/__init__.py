"""
app/__init__.py - Uygulama fabrikası: create_app (Modül E).

Parçaları (ayarlar, CORS, veritabanı, rotalar) tek bir Flask uygulamasında birleştirir.
"Fabrika" deseni sayesinde testler kendi ayarlarıyla (örneğin geçici bir veritabanı ile)
ayrı bir uygulama oluşturabilir; run.py ise gerçek ayarlarla oluşturur.
Sıra yönergedeki gibidir: ayarlar -> CORS -> init_db -> blueprint'ler -> /health.
"""
import os

from flask import Flask, jsonify
from flask_cors import CORS

from app.database import init_db
from app.routes import api_bp, pages_bp
from config import config


def create_app(config_name=None, ayarlar=None):
    """Flask uygulamasını kurar ve döner.

    config_name: 'development' / 'production'; verilmezse FLASK_ENV'den okunur.
    ayarlar: testlerin ayar değiştirmek için verdiği sözlük (örn. DATABASE_URL).
    """
    app = Flask(__name__)

    # 1) Ayarları yükle: config sözlüğünden ortama uygun sınıfı seç.
    #    FLASK_ENV bir uygulama ayarı değil, HANGİ ayar sınıfının seçileceğini söyler;
    #    bu yüzden config.py'de değil burada okunur.
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(config.get(config_name, config['default']))
    if ayarlar:
        app.config.update(ayarlar)   # testler için ek/özel ayarlar
    # JSON cevaplarda Türkçe karakterler \u015e gibi değil, olduğu gibi görünsün
    app.json.ensure_ascii = False

    # 2) CORS aç: Wix sitesi (farklı adres) tarayıcıdan API'ye istek atabilsin
    CORS(app, origins=app.config['CORS_ORIGINS'])

    # 3) Veritabanı tablosunu hazırla (get_db current_app'e ihtiyaç duyar -> app context)
    with app.app_context():
        init_db(app)

    # 4) Rotaları kaydet: sayfalar kökte, API uçları /api önekiyle
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # 5) Canlılık kontrolü: Render ve siz, sunucunun ayakta olduğunu buradan görürsünüz
    @app.route('/health')
    def health():
        return jsonify({
            'basari': True,
            'durum': 'aktif',
            'isletme': app.config['BUSINESS_NAME'],
        })

    return app
