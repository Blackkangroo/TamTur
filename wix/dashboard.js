// wix/dashboard.js - Yönetim panelinin (B2B) Wix Velo sayfa kodu (Wix Studio).
//
// Bu dosyanın birebir kopyası Wix Studio'da "Panel" sayfasının kod panelindedir.
// Sayfa açılınca GET /api/leads ile kayıtları çeker ve leadRepeater'a bağlar.
// Her satırda tek bir Text (satirText) vardır; isim | telefon | mesaj | tarih yan yana yazılır.
// Opsiyonel: toplamText (toplam sayı), durumMesaji (durum), yenileBtn (Yenile).
import { fetch } from 'wix-fetch';

const API_URL = 'https://tamtur.onrender.com';

$w.onReady(async function () {
  $w('#text5').text = 'Tam Tur Yönetim Paneli';
  $w('#yenileBtn').label = 'Yenile';
  // onItemReady, .data atamasından ÖNCE tanımlanmalı
  $w('#leadRepeater').onItemReady(($item, itemData) => {
    $item('#satirText').text = itemData.isim + '   |   ' + itemData.telefon + '   |   ' + (itemData.mesaj || '-') + '   |   ' + tarihiBicimle(itemData.tarih);
  });
  $w('#yenileBtn').onClick(leadleriYukle);
  await leadleriYukle();
});

async function leadleriYukle() {
  $w('#durumMesaji').text = 'Kayıtlar yükleniyor...';
  try {
    const yanit = await fetch(API_URL + '/api/leads', { method: 'get' });
    const veri = await yanit.json();
    if (!veri.basari) {
      $w('#durumMesaji').text = veri.hata || 'Kayıtlar okunamadı.';
      return;
    }
    // Repeater kuralı: her kayıtta METİN tipinde benzersiz "_id" (backend ekliyor, burası emniyet)
    veri.leads.forEach(function (lead) {
      lead._id = String(lead._id || lead.id);
    });
    $w('#leadRepeater').data = veri.leads;
    $w('#toplamText').text = 'Toplam ' + veri.leads.length + ' kayıt';
    $w('#durumMesaji').text = veri.leads.length === 0 ? 'Henüz kayıt yok.' : 'Güncellendi (en yeni kayıt ilk sırada)';
  } catch (hata) {
    console.log('lead listesi hatası:', hata);
    $w('#durumMesaji').text = 'Bağlantı hatası: sunucuya ulaşılamadı.';
  }
}

// SQLite tarihi UTC "2026-10-11 09:05:33" -> yerel saat, Türkçe biçim
function tarihiBicimle(ham) {
  if (!ham) { return '-'; }
  const tarih = new Date(ham.replace(' ', 'T') + 'Z');
  if (isNaN(tarih.getTime())) { return ham; }
  return tarih.toLocaleString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}
