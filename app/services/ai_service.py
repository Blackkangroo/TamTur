"""
app/services/ai_service.py - Yapay zekâ çağrıları SADECE burada (Modül C).

Kullanıcı mesajını alır, Groq API'sine gönderir ve cevabı metin olarak döner.
Bu dosya Flask'ı, HTTP sunucusunu ve veritabanını BİLMEZ; sadece yapay zekâ ile konuşur.
Anahtar yoksa çökmek yerine "demo modu" cevabı verir. İstek hatalarında
AIServiceError fırlatır; rotalar bu hatayı yakalayıp kibar bir JSON döner.
"""
import requests

from config import Config

# Groq, OpenAI ile aynı istek biçimini kullanır; adres sabittir.
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'

# Geçmişteki tek bir mesajın en çok kaç karakteri API'ye gider (rotadaki MESAJ_MAX ile
# aynı). Tarayıcı KULLANICI mesajını 2000 ile sınırlar (maxlength); asistan cevapları ise
# max_tokens=512 ile zaten kısa kalır. Bu sınır, curl ile gelen aşırı uzun kayıtlara karşı
# sunucunun kendi korumasıdır.
ICERIK_MAX = 2000


class AIServiceError(Exception):
    """Yapay zekâ servisine özel hata. Mesajı kullanıcıya gösterilebilecek kadar kibardır."""
    pass


class AIService:
    """Yapay zekâ ile konuşan sınıf. Tek bir örneği (ai_service) dosya sonunda oluşturulur."""

    def __init__(self, api_key=None, model=None, business_context=None):
        # Parametre verilmezse ayarlar config.py'den okunur (testlerde elle verilir)
        self.api_key = api_key if api_key is not None else Config.GROQ_API_KEY
        self.model = model if model is not None else Config.AI_MODEL
        self.business_context = (
            business_context if business_context is not None else Config.BUSINESS_CONTEXT
        )

    def _sistem_talimati(self):
        """Yapay zekânın kişiliğini tanımlayan metni (BUSINESS_CONTEXT) döner."""
        return self.business_context

    def _mesajlari_hazirla(self, mesaj, gecmis):
        """Groq'a gidecek "messages" listesini sırayla kurar:
        1) sistem talimatı  2) geçmiş mesajlar  3) yeni kullanıcı mesajı.
        """
        mesajlar = [{'role': 'system', 'content': self._sistem_talimati()}]

        # Geçmişten sadece role/content alanlarını ve geçerli rolleri alırız;
        # tarayıcıdan ne gelirse gelsin bozuk kayıtlar API'ye gitmez.
        for kayit in gecmis or []:
            if not isinstance(kayit, dict):
                continue
            rol = kayit.get('role')
            icerik = kayit.get('content')
            # Aşırı uzun içerik API'ye gitmez (kota ve bağlam penceresi korunur)
            if isinstance(icerik, str) and len(icerik) > ICERIK_MAX:
                continue
            if rol in ('user', 'assistant') and isinstance(icerik, str) and icerik.strip():
                mesajlar.append({'role': rol, 'content': icerik})

        mesajlar.append({'role': 'user', 'content': mesaj})
        return mesajlar

    def yanit_uret(self, mesaj, gecmis=None):
        """Mesaja yapay zekâ cevabı üretir. Anahtar yoksa demo cevabı döner."""
        # Demo modu: anahtar tanımlı değilse API'ye hiç gitmeden kibar bir cevap döneriz
        if not self.api_key:
            return (
                '(Demo modu) Merhaba! Şu an yapay zekâ anahtarı tanımlı değil, '
                'bu yüzden gerçek bir cevap üretemiyorum. '
                'Mesajınız: "' + mesaj + '"'
            )

        headers = {
            'Authorization': 'Bearer ' + self.api_key,
            'Content-Type': 'application/json',
        }
        govde = {
            'model': self.model,
            'messages': self._mesajlari_hazirla(mesaj, gecmis),
            'temperature': 0.7,   # 0 = hep aynı cevap, 1 = çok yaratıcı; 0.7 dengeli
            'max_tokens': 512,    # cevabın üst uzunluğu
        }

        # Dış servis çağrısı try-except ile sarılır: ağ yoksa, anahtar yanlışsa,
        # cevap beklenmedik biçimdeyse kullanıcıya kibar bir hata gider.
        try:
            cevap = requests.post(GROQ_URL, headers=headers, json=govde, timeout=20)
            cevap.raise_for_status()           # 4xx/5xx ise hata fırlatır
            veri = cevap.json()
            cevap_metni = veri['choices'][0]['message']['content'].strip()
            if not cevap_metni:   # servis 200 dedi ama hiç metin yok -> kullanıcıya boş baloncuk gitmesin
                raise AIServiceError('Yapay zekâ boş bir cevap döndü. Lütfen tekrar deneyin.')
            return cevap_metni
        except requests.RequestException as hata:
            raise AIServiceError(
                'Yapay zekâ servisine şu an ulaşılamıyor. Lütfen biraz sonra tekrar deneyin.'
            ) from hata
        # alan yoksa KeyError, liste boşsa IndexError, JSON değilse ValueError,
        # tip yanlışsa (content null, choices null, gövde liste...) TypeError/AttributeError
        except (KeyError, IndexError, ValueError, TypeError, AttributeError) as hata:
            raise AIServiceError(
                'Yapay zekâ servisinden beklenmedik bir cevap geldi. Lütfen tekrar deneyin.'
            ) from hata


# Uygulamanın her yerinde kullanılacak TEK örnek
ai_service = AIService()
