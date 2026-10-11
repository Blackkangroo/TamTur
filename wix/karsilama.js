// wix/karsilama.js - Karşılama sayfasının (B2C) Wix Velo sayfa kodu (Wix Studio).
//
// Bu dosyanın birebir kopyası Wix Studio'da "Home" sayfasının kod panelindedir.
// Ziyaretçi soru yazar -> Render'daki Flask backend'e POST /api/sohbet -> cevap ekrana yazılır.
// İsim/telefon bırakır -> POST /api/leads. Element ID'leri Flask şablonu (index.html) ile AYNIDIR:
// mesajGirisi, sorBtn, cevapAlani, isimGirisi, telefonGirisi, kaydetBtn, durumMesaji.
// markaMetinleri(): sayfadaki sabit Türkçe metinleri, hero görselini ve hizmet kartlarını (repeater1) kod yazar;
// Wix editöründe Türkçe karakter girişi sorunluydu, metinler tek yerden yönetiliyor.
// Hero (section7): solda başlık (text15) + paragraf (text14) + buton (button1), sağda fotoğraf (imageX2).
import { fetch } from 'wix-fetch';

const API_URL = 'https://tamtur.onrender.com';

let gecmis = [];
let sohbetMetni = '';
let sonKullaniciMesaji = '';
const GECMIS_SINIRI = 10;

$w.onReady(function () {
  markaMetinleri();
  $w('#sorBtn').onClick(sor);
  $w('#kaydetBtn').onClick(kaydet);
  $w('#button1').onClick(() => { $w('#section4').scrollTo(); }); // "Hemen Rezervasyon Yap" -> sohbet bölümüne kaydır
  $w('#mesajGirisi').onKeyPress((olay) => {
    if (olay.key === 'Enter') { sor(); }
  });
});

function markaMetinleri() {
  // Görseller Wikimedia Commons'tan (CC lisanslı): hero fotoğrafı (Fener sokağı, arkada Fener Rum Lisesi) ve üç hizmet kartı
  $w('#text15').text = "İstanbul'u Lisanslı Rehberlerle Keşfedin";
  $w('#text14').text = "Az bilinen rotalarıyla İstanbul'u keşfedin. Bireyleri ve kurumları Bakanlık kokartlı rehberlerle buluşturur, size özel rota planlar, Fener-Balat'tan Yedikule'ye tarihi gezi organizasyonları düzenleriz.";
  $w('#button1').label = 'Hemen Rezervasyon Yap';
  $w('#imageX2').src = 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/Fener_street.jpg/1280px-Fener_street.jpg';
  $w('#imageX2').alt = 'Fener sokağı, arkada Fener Rum Lisesi';
  $w('#section4').background.src = 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Istanbul_panorama_from_Galata_tower_-_1.jpg/1920px-Istanbul_panorama_from_Galata_tower_-_1.jpg'; // sohbet bölümü arka planı (Galata panoraması); cam efekti bunun üstünde görünür
  $w('#text10').text = 'Asistana sorun';
  $w('#cevapAlani').text = 'Merhaba! Size nasıl yardımcı olabilirim?';
  $w('#mesajGirisi').placeholder = 'Örn: Fener-Balat turu kaç saat sürer?';
  $w('#sorBtn').label = 'Sor';
  $w('#text13').text = 'Size ulaşalım';
  $w('#isimGirisi').placeholder = 'Adınız Soyadınız';
  $w('#telefonGirisi').placeholder = '05xx xxx xx xx';
  $w('#kaydetBtn').label = 'Kaydet';
  $w('#durumMesaji').text = 'Sorunuzu bekliyoruz.';
  $w('#repeater1').onItemReady(($item, veri) => {
    $item('#text7').text = veri.numara + '\n' + veri.baslik; // numara üstte, başlık altta
    $item('#text8').text = veri.aciklama;
    $item('#imageX1').src = veri.gorsel;
    $item('#imageX1').alt = veri.baslik;
  });
  $w('#repeater1').data = [
    { _id: '1', numara: '01', baslik: 'Lisanslı Rehberler', aciklama: 'Bakanlık kokartlı, deneyimli rehberlerle bireysel ve kurumsal turlar.', gorsel: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Christ_Pantocrator_the_Land_of_the_Living_Mosaic_Inner_Narthex_Chora_Church_Istanbul.jpg/1280px-Christ_Pantocrator_the_Land_of_the_Living_Mosaic_Inner_Narthex_Chora_Church_Istanbul.jpg' },
    { _id: '2', numara: '02', baslik: 'Özel Rota Planlama', aciklama: 'İlgi alanınıza ve zamanınıza göre size özel bir İstanbul rotası.', gorsel: 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Istanbul_Yedikule_Theodosian_Walls_southern_end_in_2006_3426b.jpg/1280px-Istanbul_Yedikule_Theodosian_Walls_southern_end_in_2006_3426b.jpg' },
    { _id: '3', numara: '03', baslik: 'Az Bilinen Tarihi Rotalar', aciklama: "Fener-Balat'tan Yedikule'ye, kalabalıktan uzak tarihi geziler.", gorsel: 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Balat_houses.jpg/1280px-Balat_houses.jpg' }
  ];
}

async function sor() {
  if (!$w('#sorBtn').enabled) { return; }
  const mesaj = $w('#mesajGirisi').value.trim();
  if (!mesaj) {
    $w('#durumMesaji').text = 'Lütfen önce bir mesaj yazın.';
    return;
  }
  $w('#sorBtn').disable();
  $w('#durumMesaji').text = 'Asistan düşünüyor...';
  try {
    const yanit = await fetch(API_URL + '/api/sohbet', {
      method: 'post',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mesaj: mesaj, gecmis: gecmis })
    });
    const veri = await yanit.json();
    if (veri.basari) {
      sohbetMetni += 'Siz: ' + mesaj + '\n' + 'Asistan: ' + veri.cevap + '\n\n';
      $w('#cevapAlani').text = sohbetMetni;
      gecmis.push({ role: 'user', content: mesaj });
      gecmis.push({ role: 'assistant', content: veri.cevap });
      gecmis = gecmis.slice(-GECMIS_SINIRI);
      sonKullaniciMesaji = mesaj;
      $w('#mesajGirisi').value = '';
      $w('#durumMesaji').text = 'Cevap geldi.';
    } else {
      $w('#durumMesaji').text = veri.hata || 'Bağlantı hatası';
    }
  } catch (hata) {
    console.log('sohbet hatası:', hata);
    $w('#durumMesaji').text = 'Bağlantı hatası: sunucuya ulaşılamadı.';
  } finally {
    $w('#sorBtn').enable();
  }
}

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
      body: JSON.stringify({ isim: isim, telefon: telefon, mesaj: sonKullaniciMesaji })
    });
    const veri = await yanit.json();
    if (yanit.status === 201 && veri.basari) {
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
