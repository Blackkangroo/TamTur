"""
tests/test_ai_service.py - AIService'in Groq'a gitmeden test edilmesi.

Gerçek ağ çağrısı yapılmaz: requests.post sahte bir fonksiyonla değiştirilir
(monkeypatch). Böylece başarılı cevap, bağlantı hatası ve bozuk cevap
durumlarının hepsi internet olmadan kontrol edilir.
"""
import pytest
import requests

from app.services import ai_service as servis_modulu
from app.services.ai_service import AIService, AIServiceError


class SahteCevap:
    """requests.post'un döndürdüğü nesnenin sadece kullandığımız kısmı."""

    def __init__(self, veri):
        self._veri = veri

    def raise_for_status(self):
        pass   # 200 gibi davran

    def json(self):
        return self._veri


def test_basarili_cevap(monkeypatch):
    gonderilen = {}

    def sahte_post(url, headers=None, json=None, timeout=None):
        gonderilen['url'] = url
        gonderilen['headers'] = headers
        gonderilen['json'] = json
        return SahteCevap({'choices': [{'message': {'content': '  Merhaba, hoş geldiniz!  '}}]})

    monkeypatch.setattr(servis_modulu.requests, 'post', sahte_post)

    servis = AIService(api_key='test', model='test-model', business_context='Sen test asistanısın.')
    cevap = servis.yanit_uret('Selam', [])

    assert cevap == 'Merhaba, hoş geldiniz!'          # strip() uygulanmış
    assert gonderilen['url'].startswith('https://api.groq.com/')
    assert gonderilen['headers']['Authorization'] == 'Bearer test'
    assert gonderilen['json']['model'] == 'test-model'
    assert gonderilen['json']['messages'][-1] == {'role': 'user', 'content': 'Selam'}


def test_baglanti_hatasi_aiserviceerror(monkeypatch):
    def sahte_post(*args, **kwargs):
        raise requests.RequestException('ağ yok')

    monkeypatch.setattr(servis_modulu.requests, 'post', sahte_post)

    servis = AIService(api_key='test')
    with pytest.raises(AIServiceError):
        servis.yanit_uret('Selam')


def test_bozuk_cevap_aiserviceerror(monkeypatch):
    # choices listesi boş -> IndexError -> AIServiceError'a çevrilmeli
    monkeypatch.setattr(servis_modulu.requests, 'post',
                        lambda *a, **k: SahteCevap({'choices': []}))
    servis = AIService(api_key='test')
    with pytest.raises(AIServiceError):
        servis.yanit_uret('Selam')


def test_demo_modu_apiye_gitmez(monkeypatch):
    def sahte_post(*args, **kwargs):
        raise AssertionError('Demo modunda requests.post çağrılmamalı')

    monkeypatch.setattr(servis_modulu.requests, 'post', sahte_post)

    servis = AIService(api_key='')
    cevap = servis.yanit_uret('Kaçta açıksınız?')
    assert 'Demo' in cevap
    assert 'Kaçta açıksınız?' in cevap


def test_mesajlari_hazirla_sirasi():
    servis = AIService(api_key='test', business_context='SİSTEM TALİMATI')
    gecmis = [
        {'role': 'user', 'content': 'önceki soru'},
        {'role': 'assistant', 'content': 'önceki cevap'},
        {'role': 'system', 'content': 'bu süzülmeli'},      # geçersiz rol -> atlanır
        {'role': 'user', 'content': '', 'ekstra': 'alan'},  # boş içerik -> atlanır
        'bozuk kayıt',                                       # sözlük değil -> atlanır
    ]
    mesajlar = servis._mesajlari_hazirla('yeni soru', gecmis)

    assert [m['role'] for m in mesajlar] == ['system', 'user', 'assistant', 'user']
    assert mesajlar[0]['content'] == 'SİSTEM TALİMATI'
    assert mesajlar[1]['content'] == 'önceki soru'
    assert mesajlar[2]['content'] == 'önceki cevap'
    assert mesajlar[-1]['content'] == 'yeni soru'
    # Geçmişten sadece role/content alanları taşınır
    assert all(set(m.keys()) == {'role', 'content'} for m in mesajlar)


def test_gecmis_none_olabilir():
    servis = AIService(api_key='test', business_context='X')
    mesajlar = servis._mesajlari_hazirla('soru', None)
    assert [m['role'] for m in mesajlar] == ['system', 'user']
