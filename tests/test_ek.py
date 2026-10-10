"""
tests/test_ek.py - Ek (sertleştirme) testleri: sınır durumları ve bozuk girdiler.

test_api.py "mutlu yol"u ve temel hataları kapsar; bu dosya kenar durumlarına bakar:
gövdesiz istek, yalnızca boşluk, uzunluk sınırları, yanlış tipte "gecmis",
Groq'a giden isteğin biçimi (model, system mesajı, timeout) ve HTTP hata cevapları.
Hiçbir test internete çıkmaz: requests.post monkeypatch ile sahte bir fonksiyona çevrilir.
Çalıştır: python -m pytest -q
"""
import sqlite3

import pytest
import requests

from app import create_app
from app import routes
from app.routes import GECMIS_MAX, ISIM_MAX, MESAJ_MAX, TELEFON_MAX
from app.services import ai_service as servis_modulu
from app.services.ai_service import AIService, AIServiceError
from config import Config


# ---------------------------------------------------------------
# Ortak hazırlık (fixture'lar) - test_api.py ile aynı mantık
# ---------------------------------------------------------------
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


@pytest.fixture
def agsiz(monkeypatch):
    """Emniyet kemeri: bu fixture'ı isteyen test içinde requests.post ÇAĞRILAMAZ.
    Yanlışlıkla ağa çıkan bir test hemen kırmızı olur."""
    def yasak_post(*args, **kwargs):
        raise AssertionError('Bu testte requests.post çağrılmamalıydı (ağ erişimi yok).')

    monkeypatch.setattr(servis_modulu.requests, 'post', yasak_post)


@pytest.fixture
def demo_modu(monkeypatch, agsiz):
    """Servisin anahtarını boşaltır -> demo modu. Ağ kapalı (agsiz) olduğu için
    demo modunun gerçekten API'ye gitmediği de dolaylı olarak doğrulanır."""
    monkeypatch.setattr(routes.ai_service, 'api_key', '')


class SahteCevap:
    """requests.post'un döndürdüğü nesnenin sadece kullandığımız kısmı.
    durum_kodu 400 ve üstüyse raise_for_status, gerçek requests gibi HTTPError fırlatır."""

    def __init__(self, veri, durum_kodu=200):
        self._veri = veri
        self.status_code = durum_kodu

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError('HTTP %d hatası' % self.status_code)

    def json(self):
        return self._veri


def sahte_post_kur(monkeypatch, cevap):
    """requests.post'u, gönderilenleri bir sözlüğe kaydedip 'cevap'ı dönen sahte
    fonksiyonla değiştirir. Kaydedilen sözlük döner; test onu inceler."""
    gonderilen = {}

    def sahte_post(url, **kwargs):
        gonderilen['url'] = url
        gonderilen.update(kwargs)     # headers, json, timeout ... hepsi kaydedilir
        return cevap

    monkeypatch.setattr(servis_modulu.requests, 'post', sahte_post)
    return gonderilen


def basarili_cevap(metin):
    """Groq'un başarılı cevabının en küçük hâli."""
    return SahteCevap({'choices': [{'message': {'content': metin}}]})


# ---------------------------------------------------------------
# /api/sohbet - girdi kontrolleri (400) ve çökmeme (500 DEĞİL)
# ---------------------------------------------------------------
def test_sohbet_govdesiz_istek_400(client, demo_modu):
    # Hiç gövde yok (ne JSON ne metin) -> 400 + sözleşmedeki hata biçimi
    yanit = client.post('/api/sohbet')
    assert yanit.status_code == 400
    veri = yanit.get_json()
    assert veri['basari'] is False
    assert veri['hata']

    # JSON "null" gövdesi de boş sayılır
    yanit = client.post('/api/sohbet', data='null', content_type='application/json')
    assert yanit.status_code == 400


def test_sohbet_sadece_bosluk_400(client, demo_modu):
    # Boşluk, sekme ve satır sonu karışımı da "boş mesaj"dır
    for bos in ('', ' ', '   ', '\t', '\n', ' \t\n '):
        yanit = client.post('/api/sohbet', json={'mesaj': bos})
        assert yanit.status_code == 400, repr(bos)
    # mesaj null gönderilirse de 400
    assert client.post('/api/sohbet', json={'mesaj': None}).status_code == 400


def test_sohbet_mesaj_uzunluk_siniri(client, demo_modu):
    # Tam sınırda kabul (demo modu -> 200), bir fazlası 400
    assert client.post('/api/sohbet', json={'mesaj': 'a' * MESAJ_MAX}).status_code == 200
    yanit = client.post('/api/sohbet', json={'mesaj': 'a' * (MESAJ_MAX + 1)})
    assert yanit.status_code == 400
    assert str(MESAJ_MAX) in yanit.get_json()['hata']   # hata mesajı sınırı söyler
    # Baştaki/sondaki boşluklar sınıra sayılmaz (önce kırpılır, sonra ölçülür)
    uzun_ama_bosluklu = '   ' + 'a' * MESAJ_MAX + '   '
    assert client.post('/api/sohbet', json={'mesaj': uzun_ama_bosluklu}).status_code == 200


def test_sohbet_gecmis_gecersiz_tipte_cokmez(client, demo_modu):
    # gecmis liste olmalı; başka tip gelirse rota yok sayar. 500 ASLA dönmez.
    bozuk_gecmisler = ('bozuk metin', 42, {'role': 'user'}, None, True, [1, 'x', None, {}])
    for bozuk in bozuk_gecmisler:
        yanit = client.post('/api/sohbet', json={'mesaj': 'Merhaba', 'gecmis': bozuk})
        assert yanit.status_code in (200, 400), repr(bozuk)
        assert 'basari' in yanit.get_json()


def test_sohbet_gecmis_bozuk_oldugunda_apiye_temiz_gider(client, monkeypatch):
    # Gerçek yol (anahtar var, ağ sahte): gecmis bozuksa Groq'a sadece system + user gider
    monkeypatch.setattr(routes.ai_service, 'api_key', 'test')
    gonderilen = sahte_post_kur(monkeypatch, basarili_cevap('Tamam'))

    yanit = client.post('/api/sohbet', json={'mesaj': 'Merhaba', 'gecmis': 'bozuk'})
    assert yanit.status_code == 200
    assert yanit.get_json()['cevap'] == 'Tamam'
    assert [m['role'] for m in gonderilen['json']['messages']] == ['system', 'user']


def test_sohbet_gecmis_sunucuda_kirpilir(client, monkeypatch):
    # Tarayıcıdaki GECMIS_SINIRI sunucuyu korumaz; curl ile 50 kayıt gelse de Groq'a
    # yalnızca son GECMIS_MAX kayıt + system + yeni mesaj gider (kota korunur)
    monkeypatch.setattr(routes.ai_service, 'api_key', 'test')
    gonderilen = sahte_post_kur(monkeypatch, basarili_cevap('Tamam'))

    gecmis = [{'role': 'user', 'content': 'soru %d' % i} for i in range(50)]
    yanit = client.post('/api/sohbet', json={'mesaj': 'Merhaba', 'gecmis': gecmis})
    assert yanit.status_code == 200
    mesajlar = gonderilen['json']['messages']
    assert len(mesajlar) == GECMIS_MAX + 2                          # system + 10 geçmiş + yeni mesaj
    assert mesajlar[1]['content'] == 'soru %d' % (50 - GECMIS_MAX)  # en eskiler atıldı, en yeniler kaldı
    assert mesajlar[-2]['content'] == 'soru 49'


def test_sohbet_503_sebebi_loga_yazilir(client, monkeypatch, caplog):
    # Kullanıcı yalnızca kibar mesajı görür; asıl sebep (örn. 401) sunucu loguna düşer
    monkeypatch.setattr(routes.ai_service, 'api_key', 'test')
    sahte_post_kur(monkeypatch, SahteCevap({'error': 'x'}, durum_kodu=401))

    with caplog.at_level('WARNING'):
        yanit = client.post('/api/sohbet', json={'mesaj': 'Merhaba'})
    assert yanit.status_code == 503
    assert '401' in caplog.text                        # geliştirici terminalde görür
    assert '401' not in yanit.get_json()['hata']       # kullanıcıya sızmaz


def test_sohbet_sayisal_mesaj_cokmez(client, demo_modu):
    # Metin yerine sayı/bool/liste gelirse 500 olmamalı (200 ya da 400 kabul)
    for deger in (123, 4.5, True, ['liste'], {'a': 1}):
        yanit = client.post('/api/sohbet', json={'mesaj': deger})
        assert yanit.status_code in (200, 400), repr(deger)


def test_json_nesne_degilse_400(client, demo_modu):
    # Geçerli JSON ama sözlük değil (liste, metin, sayı, bool): 500 değil 400 dönmeli
    for govde in ('[1, 2]', '"merhaba"', '7', 'true'):
        for yol in ('/api/sohbet', '/api/leads'):
            yanit = client.post(yol, data=govde, content_type='application/json')
            assert yanit.status_code == 400, (yol, govde)
            assert 'JSON' in yanit.get_json()['hata']   # mesaj sebebi söyler, "mesaj yazın" demez


# ---------------------------------------------------------------
# /api/leads - girdi kontrolleri
# ---------------------------------------------------------------
def test_lead_govdesiz_istek_400(client):
    yanit = client.post('/api/leads')
    assert yanit.status_code == 400
    veri = yanit.get_json()
    assert veri['basari'] is False
    assert veri['hata']
    # JSON olmayan gövde (form verisi gibi) de 400
    assert client.post('/api/leads', data='isim=Ali', content_type='text/plain').status_code == 400


def test_lead_isim_telefon_sadece_bosluk_400(client):
    denemeler = [
        {'isim': '   ', 'telefon': '0500'},
        {'isim': 'Ali', 'telefon': ' \t '},
        {'isim': '\n', 'telefon': '\n'},
        {'isim': None, 'telefon': '0500'},
        {'isim': 'Ali', 'telefon': None},
    ]
    for govde in denemeler:
        yanit = client.post('/api/leads', json=govde)
        assert yanit.status_code == 400, govde
        assert yanit.get_json()['basari'] is False
    # Hiçbiri veritabanına girmemiş olmalı
    assert client.get('/api/leads').get_json()['leads'] == []


def test_lead_uzunluk_sinirlari(client):
    # Sınırda kabul, bir fazlası ret: isim, telefon ve mesaj için ayrı ayrı
    assert client.post('/api/leads', json={'isim': 'a' * ISIM_MAX, 'telefon': '0500'}).status_code == 201
    assert client.post('/api/leads', json={'isim': 'a' * (ISIM_MAX + 1), 'telefon': '0500'}).status_code == 400

    assert client.post('/api/leads', json={'isim': 'Ali', 'telefon': '5' * TELEFON_MAX}).status_code == 201
    assert client.post('/api/leads', json={'isim': 'Ali', 'telefon': '5' * (TELEFON_MAX + 1)}).status_code == 400

    gecerli = {'isim': 'Ali', 'telefon': '0500', 'mesaj': 'm' * MESAJ_MAX}
    assert client.post('/api/leads', json=gecerli).status_code == 201
    cok_uzun = {'isim': 'Ali', 'telefon': '0500', 'mesaj': 'm' * (MESAJ_MAX + 1)}
    assert client.post('/api/leads', json=cok_uzun).status_code == 400

    # Reddedilenler veritabanına girmedi: sadece 3 geçerli kayıt var
    assert len(client.get('/api/leads').get_json()['leads']) == 3


def test_lead_bos_mesaj_null_kaydedilir(client):
    # mesaj opsiyonel: sadece boşluk gelirse "   " değil, null (None) saklanır
    yanit = client.post('/api/leads', json={'isim': 'Ali', 'telefon': '0500', 'mesaj': '   '})
    assert yanit.status_code == 201
    assert yanit.get_json()['lead']['mesaj'] is None

    yanit = client.post('/api/leads', json={'isim': 'Veli', 'telefon': '0501', 'mesaj': None})
    assert yanit.status_code == 201
    assert yanit.get_json()['lead']['mesaj'] is None


def test_lead_sayisal_degerler_cokmez(client):
    # Wix/tarayıcıdan sayı gelirse 500 olmamalı (metne çevrilip kabul ya da 400)
    yanit = client.post('/api/leads', json={'isim': 123, 'telefon': 5551234})
    assert yanit.status_code in (201, 400)


# ---------------------------------------------------------------
# /api/leads - liste sözleşmesi (Wix Repeater bunu okur)
# ---------------------------------------------------------------
def test_leads_bos_liste(client):
    # Hiç kayıt yokken bile basari true ve boş liste (Repeater boş kalır, hata vermez)
    assert client.get('/api/leads').get_json() == {'basari': True, 'leads': []}


def test_leads_her_kayitta_sozlesme_anahtarlari(client):
    client.post('/api/leads', json={'isim': 'Ayşe', 'telefon': '0500', 'mesaj': 'Soru'})
    client.post('/api/leads', json={'isim': 'Mehmet', 'telefon': '0501'})   # mesaj yok

    leads = client.get('/api/leads').get_json()['leads']
    assert len(leads) == 2
    for lead in leads:
        # Bölüm 8 sözleşmesi: en az bu altı anahtar; bir harf farkı Wix bağlantısını koparır
        for anahtar in ('id', '_id', 'isim', 'telefon', 'mesaj', 'tarih'):
            assert anahtar in lead, anahtar
        assert isinstance(lead['id'], int)
        assert isinstance(lead['_id'], str)
        assert lead['_id'] == str(lead['id'])      # Wix Repeater'ın istediği metin kimlik
        assert isinstance(lead['tarih'], str) and lead['tarih']
        assert lead['isim'] and lead['telefon']


def test_leads_siralama_en_yeni_ilk(client):
    # Üç kayıt ekle; listede ilk gelen EN SON eklenen olmalı (ORDER BY id DESC)
    for isim in ('Birinci', 'İkinci', 'Üçüncü'):
        assert client.post('/api/leads', json={'isim': isim, 'telefon': '0500'}).status_code == 201

    leads = client.get('/api/leads').get_json()['leads']
    assert [lead['isim'] for lead in leads] == ['Üçüncü', 'İkinci', 'Birinci']
    idler = [lead['id'] for lead in leads]
    assert idler == sorted(idler, reverse=True)   # id'ler büyükten küçüğe
    assert len(set(idler)) == 3                    # hepsi farklı


def test_lead_veritabani_hatasi_loga_yazilir(client, monkeypatch, caplog):
    # Veritabanı bozuk/tablo yok gibi bir hatada kullanıcı kibar 500 JSON görür,
    # asıl sebep ("no such table: leads") sunucu loguna düşer (AI yolundaki 503 ile aynı desen)
    def bozuk_lead_ekle(isim, telefon, mesaj=None):
        raise sqlite3.OperationalError('no such table: leads')

    monkeypatch.setattr(routes, 'lead_ekle', bozuk_lead_ekle)
    with caplog.at_level('ERROR'):
        yanit = client.post('/api/leads', json={'isim': 'Ayşe', 'telefon': '0500'})
    assert yanit.status_code == 500
    assert yanit.get_json()['basari'] is False
    assert 'Veritabanı hatası' in caplog.text and 'no such table' in caplog.text   # geliştirici görür
    assert 'no such table' not in yanit.get_json()['hata']                          # kullanıcıya sızmaz


# ---------------------------------------------------------------
# /api/sohbet - gerçek servis yolu, sahte ağ (uçtan uca)
# ---------------------------------------------------------------
def test_sohbet_basarili_uctan_uca(client, monkeypatch):
    monkeypatch.setattr(routes.ai_service, 'api_key', 'test')
    gonderilen = sahte_post_kur(monkeypatch, basarili_cevap(' Saat 08:00 '))

    yanit = client.post('/api/sohbet', json={
        'mesaj': '  Kaçta açıksınız?  ',
        'gecmis': [{'role': 'user', 'content': 'Selam'},
                   {'role': 'assistant', 'content': 'Merhaba!'}],
    })
    assert yanit.status_code == 200
    assert yanit.get_json() == {'basari': True, 'cevap': 'Saat 08:00'}   # strip uygulanmış

    mesajlar = gonderilen['json']['messages']
    assert [m['role'] for m in mesajlar] == ['system', 'user', 'assistant', 'user']
    assert mesajlar[-1]['content'] == 'Kaçta açıksınız?'                   # rota kırpmış


def test_sohbet_ag_hatasi_uctan_uca_503(client, monkeypatch):
    # requests.post bağlantı hatası fırlatır -> servis AIServiceError -> rota 503 + kibar JSON
    monkeypatch.setattr(routes.ai_service, 'api_key', 'test')

    def kopuk_post(*args, **kwargs):
        raise requests.ConnectionError('ağ yok')

    monkeypatch.setattr(servis_modulu.requests, 'post', kopuk_post)
    yanit = client.post('/api/sohbet', json={'mesaj': 'Merhaba'})
    assert yanit.status_code == 503
    veri = yanit.get_json()
    assert veri['basari'] is False
    assert veri['hata']
    # İç hata ayrıntısı kullanıcıya sızmaz
    assert 'Traceback' not in veri['hata'] and 'ağ yok' not in veri['hata']


# ---------------------------------------------------------------
# AIService - Groq'a giden isteğin biçimi
# ---------------------------------------------------------------
def test_istek_bicimi_model_system_timeout(monkeypatch):
    gonderilen = sahte_post_kur(monkeypatch, basarili_cevap('Tamam'))
    servis = AIService(api_key='gsk_test', model='test-model', business_context='SİSTEM TALİMATI')
    servis.yanit_uret('Selam')

    assert gonderilen['url'] == servis_modulu.GROQ_URL
    assert gonderilen['headers']['Authorization'] == 'Bearer gsk_test'
    assert gonderilen['headers']['Content-Type'] == 'application/json'

    govde = gonderilen['json']
    assert govde['model'] == 'test-model'                   # model adı gövdede
    assert govde['messages'][0] == {'role': 'system', 'content': 'SİSTEM TALİMATI'}   # ilk mesaj system
    assert govde['messages'][-1] == {'role': 'user', 'content': 'Selam'}

    # timeout gönderilmeli: aksi hâlde Groq cevap vermezse istek sonsuza dek bekler
    assert 'timeout' in gonderilen
    assert gonderilen['timeout'] > 0


def test_varsayilan_model_ve_talimat_configten(monkeypatch):
    # Parametre verilmezse model ve sistem talimatı config.py'den gelir (yönergedeki model)
    gonderilen = sahte_post_kur(monkeypatch, basarili_cevap('Tamam'))
    AIService(api_key='gsk_test').yanit_uret('Selam')

    assert gonderilen['json']['model'] == Config.AI_MODEL
    assert gonderilen['json']['messages'][0]['content'] == Config.BUSINESS_CONTEXT


def test_mesajlari_hazirla_yabanci_roller_atlanir():
    servis = AIService(api_key='test', business_context='BİZİM TALİMAT')
    gecmis = [
        {'role': 'system', 'content': 'SIZDIRILMIŞ TALİMAT'},   # ziyaretçi sistem talimatı sokamaz
        {'role': 'tool', 'content': 'araç çıktısı'},
        {'role': 'developer', 'content': 'x'},
        {'role': 'USER', 'content': 'büyük harf rol'},           # tam eşleşme gerekir
        {'role': None, 'content': 'rol yok'},
        {'content': 'rol alanı hiç yok'},
    ]
    mesajlar = servis._mesajlari_hazirla('soru', gecmis)

    assert [m['role'] for m in mesajlar] == ['system', 'user']
    assert mesajlar[0]['content'] == 'BİZİM TALİMAT'
    assert sum(1 for m in mesajlar if m['role'] == 'system') == 1   # tek system mesajı: bizimki
    assert all('SIZDIRILMIŞ' not in m['content'] for m in mesajlar)


def test_mesajlari_hazirla_icerik_tipi_kontrolu():
    servis = AIService(api_key='test', business_context='X')
    gecmis = [
        {'role': 'user', 'content': 123},            # metin değil -> atlanır
        {'role': 'user', 'content': None},
        {'role': 'user', 'content': ['liste']},
        {'role': 'user', 'content': '   '},          # boş -> atlanır
        {'role': 'assistant', 'content': 'geçerli cevap'},
    ]
    mesajlar = servis._mesajlari_hazirla('soru', gecmis)
    assert [m['role'] for m in mesajlar] == ['system', 'assistant', 'user']
    assert mesajlar[1]['content'] == 'geçerli cevap'


def test_mesajlari_hazirla_asiri_uzun_icerik_atlanir():
    # Geçmişteki tek bir kayıt ICERIK_MAX'ı aşarsa API'ye gitmez; tam sınırdaki kalır
    servis = AIService(api_key='test', business_context='X')
    gecmis = [
        {'role': 'user', 'content': 'a' * servis_modulu.ICERIK_MAX},         # tam sınır: kalır
        {'role': 'user', 'content': 'a' * (servis_modulu.ICERIK_MAX + 1)},   # bir fazla: atlanır
    ]
    mesajlar = servis._mesajlari_hazirla('soru', gecmis)
    assert [m['role'] for m in mesajlar] == ['system', 'user', 'user']
    assert len(mesajlar[1]['content']) == servis_modulu.ICERIK_MAX


def test_mesajlari_hazirla_gecmis_metin_cokmez():
    # Rota zaten listeye zorlar; yine de servis bir metinle çağrılırsa çökmemeli
    servis = AIService(api_key='test', business_context='X')
    assert [m['role'] for m in servis._mesajlari_hazirla('soru', 'bozuk')] == ['system', 'user']


def test_demo_modu_gecmis_ne_olursa_olsun(agsiz):
    # Anahtar yokken gecmis'in tipi ne olursa olsun demo cevabı döner, ağa çıkılmaz
    servis = AIService(api_key='')
    for gecmis in (None, [], 'bozuk', 42):
        assert 'Demo' in servis.yanit_uret('Selam', gecmis)


# ---------------------------------------------------------------
# AIService - hata durumları hep AIServiceError'a çevrilmeli
# ---------------------------------------------------------------
def test_http_hata_kodlari_aiserviceerror(monkeypatch):
    # 401 (yanlış anahtar), 429 (kota doldu), 500/503 (Groq'ta sorun):
    # raise_for_status -> HTTPError -> AIServiceError
    for kod in (401, 429, 500, 503):
        sahte_post_kur(monkeypatch, SahteCevap({'error': 'x'}, durum_kodu=kod))
        servis = AIService(api_key='gsk_gizli_anahtar')
        with pytest.raises(AIServiceError) as bilgi:
            servis.yanit_uret('Selam')
        # Kullanıcıya giden mesaj anahtarı sızdırmaz
        assert 'gsk_gizli_anahtar' not in str(bilgi.value)
        # "raise ... from hata" sayesinde asıl sebep zincirde durur (geliştirici log'da görür)
        assert isinstance(bilgi.value.__cause__, requests.HTTPError)


def test_zaman_asimi_aiserviceerror(monkeypatch):
    def yavas_post(*args, **kwargs):
        raise requests.Timeout('20 saniye geçti')

    monkeypatch.setattr(servis_modulu.requests, 'post', yavas_post)
    with pytest.raises(AIServiceError):
        AIService(api_key='test').yanit_uret('Selam')


def test_json_cozulemeyen_cevap_aiserviceerror(monkeypatch):
    class BozukJson(SahteCevap):
        def json(self):
            raise ValueError('JSON değil')   # requests'in JSONDecodeError'u da bir ValueError'dur

    sahte_post_kur(monkeypatch, BozukJson({}))
    with pytest.raises(AIServiceError):
        AIService(api_key='test').yanit_uret('Selam')


def test_eksik_anahtarli_cevap_aiserviceerror(monkeypatch):
    # Beklenen anahtarlar yoksa KeyError -> AIServiceError
    for veri in ({}, {'choices': [{}]}, {'choices': [{'message': {}}]}):
        sahte_post_kur(monkeypatch, SahteCevap(veri))
        with pytest.raises(AIServiceError):
            AIService(api_key='test').yanit_uret('Selam')


def test_yanlis_tipte_cevap_aiserviceerror(monkeypatch):
    # Cevap geldi ama yanlış TİPTE (content null, choices null, message metin, gövde metin):
    # TypeError/AttributeError da AIServiceError'a çevrilmeli -> rota 503 döner, 500 değil
    for veri in ({'choices': [{'message': {'content': None}}]},
                 {'choices': None},
                 {'choices': [{'message': 'metin'}]},
                 'sözlük değil metin'):
        sahte_post_kur(monkeypatch, SahteCevap(veri))
        with pytest.raises(AIServiceError):
            AIService(api_key='test').yanit_uret('Selam')


def test_bos_metinli_cevap_aiserviceerror(monkeypatch):
    # Servis 200 dedi ama metin boş ('' ya da sadece boşluk): kullanıcıya boş baloncuk
    # gitmesin diye AIServiceError -> rota 503 döner. Dolu metin ise olduğu gibi döner.
    for metin in ('', '   ', '\n\t'):
        sahte_post_kur(monkeypatch, basarili_cevap(metin))
        with pytest.raises(AIServiceError):
            AIService(api_key='test').yanit_uret('Selam')
    sahte_post_kur(monkeypatch, basarili_cevap('  Merhaba!  '))
    assert AIService(api_key='test').yanit_uret('Selam') == 'Merhaba!'
