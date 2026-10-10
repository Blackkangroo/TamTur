"""
tests/test_api.py - Modül F kanıtı: uç noktalar uçtan uca çalışıyor mu? (pytest)

Her test geçici bir SQLite dosyasıyla (tmp_path) kendi uygulamasını kurar;
gerçek smartlead.db'ye dokunmaz. Yapay zekâ çağrısı yapılmaz: ya demo modu
kullanılır ya da ai_service.yanit_uret sahte (monkeypatch) bir fonksiyonla değiştirilir.
Çalıştır: python -m pytest -q
"""
import pytest

from app import create_app
from app import routes
from app.services.ai_service import AIServiceError


@pytest.fixture
def app(tmp_path):
    """Her test için geçici veritabanlı taze bir uygulama."""
    return create_app('development', {
        'DATABASE_URL': str(tmp_path / 'test.db'),
        'TESTING': True,
    })


@pytest.fixture
def client(app):
    """Flask'ın sahte tarayıcısı: sunucu açmadan istek atar."""
    return app.test_client()


def test_health(client):
    yanit = client.get('/health')
    assert yanit.status_code == 200
    veri = yanit.get_json()
    assert veri['basari'] is True
    assert veri['durum'] == 'aktif'
    assert veri['isletme']   # işletme adı boş değil


def test_sayfalar(client):
    assert client.get('/').status_code == 200
    assert client.get('/dashboard').status_code == 200
    # Sözleşmedeki element ID'leri şablonda var mı?
    govde = client.get('/').get_data(as_text=True)
    for element_id in ('mesajGirisi', 'sorBtn', 'cevapAlani', 'isimGirisi',
                       'telefonGirisi', 'kaydetBtn', 'durumMesaji'):
        assert 'id="%s"' % element_id in govde
    assert 'id="leadRepeater"' in client.get('/dashboard').get_data(as_text=True)


def test_sohbet_eksik_mesaj_400(client):
    # Hiç gövde yok
    yanit = client.post('/api/sohbet', json={})
    assert yanit.status_code == 400
    assert yanit.get_json()['basari'] is False
    assert yanit.get_json()['hata']

    # Sadece boşluktan oluşan mesaj da boş sayılır
    yanit = client.post('/api/sohbet', json={'mesaj': '   '})
    assert yanit.status_code == 400

    # JSON bile değil
    yanit = client.post('/api/sohbet', data='merhaba', content_type='text/plain')
    assert yanit.status_code == 400


def test_sohbet_demo_modu(client, monkeypatch):
    # Anahtar boş -> servis API'ye gitmeden "Demo modu" cevabı döner
    monkeypatch.setattr(routes.ai_service, 'api_key', '')
    yanit = client.post('/api/sohbet', json={'mesaj': 'Kaçta açıksınız?', 'gecmis': []})
    assert yanit.status_code == 200
    veri = yanit.get_json()
    assert veri['basari'] is True
    assert 'Demo' in veri['cevap']
    assert 'Kaçta açıksınız?' in veri['cevap']


def test_sohbet_ai_hatasi_503(client, monkeypatch):
    # Servis hata fırlatırsa rota 503 + kibar JSON dönmeli
    def sahte_yanit_uret(mesaj, gecmis=None):
        raise AIServiceError('Yapay zekâ servisine ulaşılamıyor.')

    monkeypatch.setattr(routes.ai_service, 'yanit_uret', sahte_yanit_uret)
    yanit = client.post('/api/sohbet', json={'mesaj': 'Merhaba'})
    assert yanit.status_code == 503
    veri = yanit.get_json()
    assert veri['basari'] is False
    assert veri['hata'] == 'Yapay zekâ servisine ulaşılamıyor.'


def test_lead_ekle_201_ve_listele(client):
    # İlk kayıt
    yanit = client.post('/api/leads', json={'isim': 'Ayşe', 'telefon': '05001112233', 'mesaj': 'Rezervasyon'})
    assert yanit.status_code == 201
    veri = yanit.get_json()
    assert veri['basari'] is True
    lead = veri['lead']
    assert lead['isim'] == 'Ayşe'
    assert lead['telefon'] == '05001112233'
    assert lead['mesaj'] == 'Rezervasyon'
    assert lead['_id'] == str(lead['id'])
    assert lead['tarih']

    # İkinci kayıt (mesaj opsiyonel; boşluklar kırpılır)
    yanit = client.post('/api/leads', json={'isim': '  Mehmet ', 'telefon': ' 05009998877 '})
    assert yanit.status_code == 201
    assert yanit.get_json()['lead']['isim'] == 'Mehmet'
    assert yanit.get_json()['lead']['mesaj'] is None

    # Listele: en yeni ilk sırada, _id metin tipinde
    yanit = client.get('/api/leads')
    assert yanit.status_code == 200
    veri = yanit.get_json()
    assert veri['basari'] is True
    leads = veri['leads']
    assert len(leads) == 2
    assert leads[0]['isim'] == 'Mehmet'
    assert leads[1]['isim'] == 'Ayşe'
    assert isinstance(leads[0]['_id'], str)
    assert leads[0]['id'] > leads[1]['id']
    for anahtar in ('id', '_id', 'isim', 'telefon', 'mesaj', 'tarih'):
        assert anahtar in leads[0]


def test_lead_eksik_400(client):
    assert client.post('/api/leads', json={}).status_code == 400
    assert client.post('/api/leads', json={'isim': 'Ali'}).status_code == 400
    assert client.post('/api/leads', json={'telefon': '0500'}).status_code == 400
    yanit = client.post('/api/leads', json={'isim': '  ', 'telefon': '0500'})
    assert yanit.status_code == 400
    assert yanit.get_json()['basari'] is False
    assert yanit.get_json()['hata']
    # Çok uzun isim de reddedilir
    assert client.post('/api/leads', json={'isim': 'a' * 101, 'telefon': '0500'}).status_code == 400


def test_sql_injection_zararsiz(client):
    # "?" yer tutucusu sayesinde bu metin SQL olarak DEĞİL, düz veri olarak saklanır
    kotu_isim = "x'); DROP TABLE leads; --"
    yanit = client.post('/api/leads', json={'isim': kotu_isim, 'telefon': '0500'})
    assert yanit.status_code == 201

    # Tablo hâlâ yerinde ve kayıt olduğu gibi duruyor
    yanit = client.get('/api/leads')
    assert yanit.status_code == 200
    leads = yanit.get_json()['leads']
    assert len(leads) == 1
    assert leads[0]['isim'] == kotu_isim
