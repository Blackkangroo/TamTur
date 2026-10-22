
"""
app/database.py - Veritabanı işlemleri
"""
import sqlite3

from flask import current_app, g


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE_URL'])
        g.db.row_factory = sqlite3.Row
    return g.db


def kapat_db(hata=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    app.teardown_appcontext(kapat_db)

    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isim TEXT NOT NULL,
            telefon TEXT NOT NULL,
            mesaj TEXT,
            tarih DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Mevcut tabloya email sütununu, yalnızca eksikse ekle.
    sutunlar = {
        satir['name']
        for satir in db.execute("PRAGMA table_info(leads)").fetchall()
    }

    if 'email' not in sutunlar:
        db.execute("ALTER TABLE leads ADD COLUMN email TEXT")

    db.commit()


def _satiri_sozluge_cevir(satir):
    veri = dict(satir)
    veri['_id'] = str(veri['id'])
    return veri


def lead_ekle(isim, telefon, mesaj=None, email=None):
    db = get_db()

    imlec = db.execute(
        """
        INSERT INTO leads (isim, telefon, mesaj, email)
        VALUES (?, ?, ?, ?)
        """,
        (isim, telefon, mesaj, email),
    )

    db.commit()

    satir = db.execute(
        'SELECT * FROM leads WHERE id = ?',
        (imlec.lastrowid,),
    ).fetchone()

    return _satiri_sozluge_cevir(satir)


def tum_leadler():
    db = get_db()

    satirlar = db.execute(
        'SELECT * FROM leads ORDER BY id DESC'
    ).fetchall()

    return [_satiri_sozluge_cevir(satir) for satir in satirlar]

