// wix/dashboard.js - Yönetim panelinin (B2B) Wix Velo sayfa kodu.
//
// Bu dosya Wix editöründe "Panel" sayfasının kod paneline (Page Code) yapıştırılır.
// Sayfa açılınca Render'daki Flask backend'den GET /api/leads ile kayıtları çeker
// ve bir Repeater'a (tekrarlayan satır listesi) bağlar. Her satırın içindeki Text
// elementleri isimText, telefonText, mesajText, tarihText ID'lerini taşır; Repeater'ın
// ID'si leadRepeater'dır. Bu ID'ler Flask şablonu (dashboard.html) ile aynıdır.
// Opsiyonel elementler: toplamText (toplam sayı), durumMesaji (hata/durum), yenileBtn (Yenile).
// Kurulum adımları için: wix/README.md

import { fetch } from 'wix-fetch';

// Backend adresi. Sonunda "/" OLMASIN.
const API_URL = 'https://tamtur.onrender.com'; // DEĞİŞTİR: Render adresiniz (örn. https://smartlead-ai.onrender.com)

// ---------------------------------------------------------------
// Sayfa hazır olunca: önce satır şablonunu tanımla, SONRA veriyi çek
// ---------------------------------------------------------------
$w.onReady(async function () {
  // 1) onItemReady, .data atamasından ÖNCE tanımlanmalı.
  //    Wix, her kayıt için bir satır oluştururken bu fonksiyonu çağırır.
  //    Sonra tanımlanırsa ilk yüklemede satırlar boş kalır.
  //    $item: SADECE bu satırın içindeki elementleri seçer ($w tüm sayfayı seçerdi).
  //    itemData: backend'in gönderdiği bir kayıt {id, _id, isim, telefon, mesaj, tarih}
  $w('#leadRepeater').onItemReady(($item, itemData) => {
    $item('#isimText').text = itemData.isim;
    $item('#telefonText').text = itemData.telefon;
    $item('#mesajText').text = itemData.mesaj || '-';          // mesaj opsiyonel; boşsa tire
    $item('#tarihText').text = tarihiBicimle(itemData.tarih);
  });

  // 2) Opsiyonel "Yenile" butonu. Sayfaya eklemediyseniz bu blok sessizce geçer.
  try {
    $w('#yenileBtn').onClick(leadleriYukle);
  } catch (hata) {
    console.log('yenileBtn sayfada yok, atlandı');
  }

  // 3) Kayıtları çek
  await leadleriYukle();
});

// ---------------------------------------------------------------
// Veri çekme: GET /api/leads -> { basari, leads: [ {id, _id, isim, telefon, mesaj, tarih}, ... ] }
// ---------------------------------------------------------------
async function leadleriYukle() {
  varsaYaz('#durumMesaji', 'Kayıtlar yükleniyor...');

  try {
    const yanit = await fetch(API_URL + '/api/leads', { method: 'get' });
    const veri = await yanit.json();

    if (!veri.basari) {
      varsaYaz('#durumMesaji', veri.hata || 'Kayıtlar okunamadı.');
      return;
    }

    // Repeater kuralı: her kayıtta METİN tipinde ve benzersiz bir "_id" olmalı.
    // Backend bunu zaten ekliyor (database.py: _id = str(id)); burası yalnızca emniyet:
    // _id yoksa id'den üretir, varsa metne çevirir. (dashboard.html'deki forEach ile aynı kalıp)
    veri.leads.forEach(function (lead) {
      lead._id = String(lead._id || lead.id);
    });

    // Veriyi Repeater'a ver: Wix her kayıt için yukarıdaki onItemReady'yi çalıştırır
    $w('#leadRepeater').data = veri.leads;

    varsaYaz('#toplamText', 'Toplam ' + veri.leads.length + ' kayıt');
    varsaYaz('#durumMesaji', veri.leads.length === 0
      ? 'Henüz kayıt yok.'
      : 'Güncellendi (en yeni kayıt ilk sırada)');
  } catch (hata) {
    // Ağ yok, CORS engeli, adres yanlış ya da cevap JSON değil
    console.log('lead listesi hatası:', hata);
    varsaYaz('#durumMesaji', 'Bağlantı hatası: sunucuya ulaşılamadı.');
  }
}

// ---------------------------------------------------------------
// Yardımcılar
// ---------------------------------------------------------------
// Opsiyonel bir Text elementine yazar. Element sayfada yoksa hata vermez, sessizce geçer.
// (toplamText ve durumMesaji eklemek isteğe bağlıdır; eklerseniz çalışır.)
function varsaYaz(secici, metin) {
  try {
    $w(secici).text = metin;
  } catch (hata) {
    console.log(secici + ' sayfada yok, atlandı');
  }
}

// SQLite tarihi "2026-10-10 14:05:33" biçiminde ve UTC saatindedir.
// JS'in anlaması için "2026-10-10T14:05:33Z" yapar, sonra ziyaretçinin yerel saatine
// ve Türkçe biçimine çevirir: "10 Ekim 2026 17:05". (dashboard.html'deki fonksiyonla aynı)
function tarihiBicimle(ham) {
  if (!ham) { return '-'; }
  const tarih = new Date(ham.replace(' ', 'T') + 'Z');
  if (isNaN(tarih.getTime())) { return ham; }   // çevrilemezse olduğu gibi göster
  return tarih.toLocaleString('tr-TR', {
    day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}
