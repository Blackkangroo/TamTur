// wix/masterPage.js - Tüm sayfalarda ortak çalışan kod (header ve footer metinleri).
// Bu dosyanın birebir kopyası Wix Studio'da masterPage.js dosyasındadır.
// Sayfa kodları (Home -> wix/karsilama.js, Panel -> wix/dashboard.js) buraya YAZILMAZ.
$w.onReady(function () {
  $w('#text3').text = 'Tam Tur'; // header'daki işletme adı (şablonda "Business Name")
  $w('#text2').text = '© 2026 Tam Tur'; // footer telif satırı
});
