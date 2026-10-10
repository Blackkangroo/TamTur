"""
run.py - Sunucuyu başlatan giriş noktası (Modül E).

Bu dosya tek bir iş yapar: fabrikadan (create_app) uygulamayı alır ve çalıştırır.
"app" değişkeni modül düzeyinde olmalı; çünkü Render'daki başlatma komutu
"gunicorn run:app" bu değişkeni dışarıdan arar.
"""
import os

from app import create_app

# Uygulama burada, dosya içe aktarılır aktarılmaz oluşturulur (gunicorn için şart).
app = create_app()

if __name__ == '__main__':
    # Sadece "python run.py" ile çalıştırıldığında burası devreye girer.
    # host 127.0.0.1: yalnızca bu bilgisayardan erişim; geliştirme sunucusu ve hata
    # ayıklayıcı ağdaki başka cihazlara açılmaz. Render bu bloğu hiç çalıştırmaz
    # (gunicorn run:app kendi bağlanır). Telefondan denemek isterseniz geçici
    # olarak '0.0.0.0' yazabilirsiniz.
    # PORT burada okunur (config.py'de değil): bu bir uygulama ayarı değil, yalnızca
    # geliştirme sunucusunun hangi kapıyı dinleyeceğidir; Render'da gunicorn bunu kendi alır.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='127.0.0.1', port=port, debug=app.config['DEBUG'])
