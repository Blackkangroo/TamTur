// wix/karsilama.js - Karşılama sayfasının (B2C) Wix Velo sayfa kodu.
//
// Bu dosya Wix editöründe "Karşılama" sayfasının kod paneline (Page Code) yapıştırılır.
// Ziyaretçi soru yazar -> Render'daki Flask backend'e POST /api/sohbet ->
// yapay zekâ cevabı ekrana yazılır. Ziyaretçi isim/telefon bırakır -> POST /api/leads.
// Element ID'leri Flask şablonu (index.html) ile AYNIDIR: mesajGirisi, sorBtn, cevapAlani,
// isimGirisi, telefonGirisi, kaydetBtn, durumMesaji. JSON anahtarları da backend ile aynı kelimelerdir.
// Kurulum adımları için: wix/README.md

import { fetch } from 'wix-fetch';   // Wix'in kendi fetch'i; tarayıcıdaki fetch ile aynı şekilde kullanılır

// Backend adresi. Sonunda "/" OLMASIN; yollar aşağıda "/api/..." olarak ekleniyor.
const API_URL = 'http://localhost:5000'; // DEĞİŞTİR: Render adresiniz (örn. https://smartlead-ai.onrender.com)

// ---------------------------------------------------------------
// Sohbet geçmişi
// Backend geçmişi SAKLAMAZ; sayfa tutar ve her soruda geri gönderir.
// Biçim Groq'un beklediği biçimdir: [{role: 'user'|'assistant', content: '...'}]
// ---------------------------------------------------------------
let gecmis = [];
let sohbetMetni = '';           // cevapAlani'na yazılan tüm konuşma (Siz: ... / Asistan: ...)
let sonKullaniciMesaji = '';    // Kaydet'te "mesaj" alanı olarak gider
const GECMIS_SINIRI = 10;       // son 10 mesaj yeter; istek şişmesin

// ---------------------------------------------------------------
// Sayfa hazır olunca olayları bağla
// $w.onReady: elementlere ancak sayfa yüklendikten sonra erişilebilir
// ---------------------------------------------------------------
$w.onReady(function () {
  $w('#sorBtn').onClick(sor);
  $w('#kaydetBtn').onClick(kaydet);

  // Enter ile gönderme (mesajGirisi tek satırlık Text Input ise)
  $w('#mesajGirisi').onKeyPress((olay) => {
    if (olay.key === 'Enter') {
      sor();
    }
  });
});

// ---------------------------------------------------------------
// "Sor": POST /api/sohbet  { mesaj, gecmis }  ->  { basari, cevap } | { basari, hata }
// async: içinde "await" kullanacağız (isteğin bitmesini bekle, sonra devam et)
// ---------------------------------------------------------------
async function sor() {
  if (!$w('#sorBtn').enabled) { return; }   // buton kilitliyse istek zaten sürüyor; Enter ile ikinci istek gitmesin
  const mesaj = $w('#mesajGirisi').value.trim();
  if (!mesaj) {
    $w('#durumMesaji').text = 'Lütfen önce bir mesaj yazın.';
    return;
  }

  // İstek sürerken butonu kilitle (çift tıklama olmasın) ve bekleme yazısı göster
  $w('#sorBtn').disable();
  $w('#durumMesaji').text = 'Asistan düşünüyor...';

  try {
    const yanit = await fetch(API_URL + '/api/sohbet', {
      method: 'post',
      headers: { 'Content-Type': 'application/json' },
      // Anahtarlar backend ile AYNI kelimeler: mesaj, gecmis
      body: JSON.stringify({ mesaj: mesaj, gecmis: gecmis }),
    });
    const veri = await yanit.json();

    if (veri.basari) {
      // Konuşmayı ekrana ekle (Text elementi .text ile yazılır; \n yeni satır açar)
      sohbetMetni += 'Siz: ' + mesaj + '\n' + 'Asistan: ' + veri.cevap + '\n\n';
      $w('#cevapAlani').text = sohbetMetni;

      // Hatırlaması için geçmişe ekle, sonra kırp
      gecmis.push({ role: 'user', content: mesaj });
      gecmis.push({ role: 'assistant', content: veri.cevap });
      gecmis = gecmis.slice(-GECMIS_SINIRI);

      sonKullaniciMesaji = mesaj;
      $w('#mesajGirisi').value = '';
      $w('#durumMesaji').text = '';
    } else {
      // Backend 400/503 döndü: kibar hata mesajı backend'den gelir
      $w('#durumMesaji').text = veri.hata || 'Bağlantı hatası';
    }
  } catch (hata) {
    // Ağ yok, CORS engeli, adres yanlış ya da cevap JSON değil
    console.log('sohbet hatası:', hata);
    $w('#durumMesaji').text = 'Bağlantı hatası: sunucuya ulaşılamadı.';
  } finally {
    $w('#sorBtn').enable();   // ne olursa olsun butonu geri aç
  }
}

// ---------------------------------------------------------------
// "Kaydet": POST /api/leads  { isim, telefon, mesaj }  ->  201 { basari, lead }
// ---------------------------------------------------------------
async function kaydet() {
  const isim = $w('#isimGirisi').value.trim();
  const telefon = $w('#telefonGirisi').value.trim();
  if (!isim || !telefon) {
    $w('#durumMesaji').text = 'İsim ve telefon alanları zorunludur.';
    return;
  }

  $w('#kaydetBtn').disable();
  $w('#durumMesaji').text = 'Kaydediliyor...';

  try {
    const yanit = await fetch(API_URL + '/api/leads', {
      method: 'post',
      headers: { 'Content-Type': 'application/json' },
      // Anahtarlar backend ile AYNI kelimeler: isim, telefon, mesaj
      body: JSON.stringify({ isim: isim, telefon: telefon, mesaj: sonKullaniciMesaji }),
    });
    const veri = await yanit.json();

    if (yanit.status === 201 && veri.basari) {   // 201 = yeni kayıt oluşturuldu
      $w('#durumMesaji').text = 'Teşekkürler ' + veri.lead.isim + '! En kısa sürede size ulaşacağız.';
      $w('#isimGirisi').value = '';
      $w('#telefonGirisi').value = '';
    } else {
      $w('#durumMesaji').text = veri.hata || 'Bağlantı hatası';
    }
  } catch (hata) {
    console.log('kayıt hatası:', hata);
    $w('#durumMesaji').text = 'Bağlantı hatası: sunucuya ulaşılamadı.';
  } finally {
    $w('#kaydetBtn').enable();
  }
}
