"""
app/database.py - Veritabanı işlemleri; SQL SADECE burada yazılır (Modül B).

SQLite dosyasına bağlanır, "leads" tablosunu oluşturur, kayıt ekler ve listeler.
Diğer dosyalar (routes.py gibi) SQL yazmaz; buradaki fonksiyonları çağırır.
Kullanıcıdan gelen değerler SQL metnine eklenmez; her zaman "?" yer tutucusu ile
ayrı parametre olarak verilir. Bu, SQL Injection'a karşı zorunlu korumadır.
"""
import sqlite3

from flask import current_app, g


def get_db():
    """Veritabanına bağlanır; aynı istek içinde tekrar çağrılırsa aynı bağlantıyı döner.

    "g" Flask'ın istek başına tuttuğu küçük bir depodur. Bağlantıyı oraya koyarız ki
    bir istek içinde birden fazla sorgu aynı bağlantıyı kullansın.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE_URL'])
        # Satırlara sütun adıyla erişim: satir['isim'] gibi
        g.db.row_factory = sqlite3.Row
    return g.db


def kapat_db(hata=None):
    """İstek bitince bağlantıyı kapatır. Flask bunu otomatik çağırır (teardown).

    hata: istek sırasında bir istisna olduysa Flask onu buraya verir; biz kullanmıyoruz
    ama Flask bu imzayı (tek parametre) bekler. Parametre silinirse her istek sonunda
    TypeError olur.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    """leads tablosunu oluşturur (yoksa) ve bağlantı kapatmayı Flask'a kaydeder.

    create_app içinde "with app.app_context():" bloğunda çağrılır.
    """
    # Her istek sonunda kapat_db çalışsın
    app.teardown_appcontext(kapat_db)

    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            isim    TEXT NOT NULL,
            telefon TEXT NOT NULL,
            mesaj   TEXT,
            tarih   DATETIME DEFAULT CURRENT_TIMESTAMP   -- UTC saatidir; arayüz yerel saate çevirir (dashboard.html / wix/dashboard.js tarihiBicimle)
        )
    """)
    db.commit()


def _satiri_sozluge_cevir(satir):
    """Bir sqlite3.Row satırını JSON'a uygun sözlüğe çevirir.

    Wix Repeater her kayıtta metin tipinde bir "_id" ister; bu yüzden id'nin
    string hâlini "_id" adıyla ekliyoruz.
    """
    veri = dict(satir)
    veri['_id'] = str(veri['id'])
    return veri


def lead_ekle(isim, telefon, mesaj=None):
    """Yeni bir lead kaydeder ve eklenen kaydı sözlük olarak döner."""
    db = get_db()
    # Değerler SQL metnine EKLENMEZ: "?" yer tutucuları + ayrı demet (tuple)
    imlec = db.execute(
        'INSERT INTO leads (isim, telefon, mesaj) VALUES (?, ?, ?)',
        (isim, telefon, mesaj),
    )
    db.commit()

    # Az önce eklenen kaydı (otomatik id ve tarih dâhil) geri okuyup döneriz
    satir = db.execute('SELECT * FROM leads WHERE id = ?', (imlec.lastrowid,)).fetchone()
    return _satiri_sozluge_cevir(satir)


def tum_leadler():
    """Tüm kayıtları en yeniden eskiye doğru liste olarak döner."""
    db = get_db()
    satirlar = db.execute('SELECT * FROM leads ORDER BY id DESC').fetchall()
    return [_satiri_sozluge_cevir(satir) for satir in satirlar]
