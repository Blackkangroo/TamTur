# Wix Velo Bağlantısı — Adım Adım (Modül G)

Bu klasördeki dosyalar, Wix sitenizdeki sayfaların **kod**udur:

| Dosya | Wix sayfası | Ne yapar |
|---|---|---|
| `karsilama.js` | Karşılama (B2C) | Ziyaretçi soru sorar (`POST /api/sohbet`), isim/telefon bırakır (`POST /api/leads`); hero ve hizmet kartı metinlerini yazar |
| `dashboard.js` | Panel (B2B) | Kayıtları çeker (`GET /api/leads`) ve Repeater'da listeler |
| `masterPage.js` | Tüm sayfalar (header/footer) | Header'daki işletme adını ve footer telif satırını yazar; sayfa kodu buraya yapıştırılmaz |

Flask projesindeki `app/templates/index.html` ve `dashboard.html` aynı işi yapan
**yedek/demo arayüz**dür. Wix'teki element ID'leri ve JSON anahtarları onlarla birebir
aynıdır; bu yüzden Flask sayfasında çalışan bir şey, aynı ID'lerle Wix'te de çalışır.

> Önce backend Render'da yayında olmalı (Modül H). Tarayıcıda
> `https://ADRESINIZ.onrender.com/health` açıp `{"basari": true, "durum": "aktif", ...}`
> gördüyseniz devam edin.

---

> [!note] Tam Tur sitesi Wix Studio ile kuruldu (11 Eki 2026)
> Yayın adresi: https://alpgecer.wixstudio.com/tamtur (Karşılama) ve https://alpgecer.wixstudio.com/tamtur/blank (Panel).
> Hesabın yeni "Harmony" editöründe Velo kod paneli yoktu; site Wix Studio çalışma alanına taşındı,
> kod Studio'nun `{ }` Code panelinden girildi. Bu klasördeki `karsilama.js` ve `dashboard.js`
> Studio'daki sayfa kodlarının birebir kopyasıdır. Editörde Türkçe karakter girişi sorunlu olduğu
> için sabit metinler (`markaMetinleri`) ve hizmet kartları (`repeater1`) kodla yazılır.
> Tasarım (11 Eki akşam): başlık fontu Ogg (serif), hero solda başlık + paragraf + "Hemen Rezervasyon Yap"
> butonu, sağda Fener sokağı fotoğrafı; sohbet bölümünde Galata panoraması üstünde cam görünümlü (glassmorphism)
> iki kutu: sohbet sağda, isim/telefon formu altta (yönergedeki Z-Pattern).

## 0. Önemli: Wix'ten `localhost`'a ulaşılamaz

Wix sayfa kodu **ziyaretçinin tarayıcısında** çalışır ve Wix sitesi `https://` ile
yayınlanır. Bu iki sebeple `API_URL = 'http://localhost:5000'` Wix içinde **çalışmaz**
(tarayıcı "mixed content" diye engeller; ayrıca ziyaretçinin bilgisayarında sizin
sunucunuz yok). `localhost` değeri sadece yer tutucudur. Wix'te test etmek için
mutlaka Render adresini (`https://...onrender.com`) yazın.

Yerelde test etmek istiyorsanız Flask şablonlarını kullanın: `python run.py` →
`http://localhost:5000` (karşılama) ve `http://localhost:5000/dashboard` (panel).

---

## 1. Dev Mode (Velo) açma

1. Wix'te sitenizi **Editor** ile açın (Wix Editor veya Wix Studio).
2. Üst menüden **Dev Mode → Turn on Dev Mode** (Wix Studio'da sol kenarda **Code** `{}`
   simgesi). Menü adları Wix sürümüne göre biraz değişebilir; aradığınız şey
   "Velo / Code / Dev Mode" kelimeleridir.
3. Açıldığında ekranın altında bir **kod paneli** (Page Code) ve sağ altta
   **Properties & Events** paneli görünür. ID'leri bu panelden vereceğiz.

## 2. İki sayfa oluşturma

**Pages** menüsünden iki sayfa ekleyin:

- `Karşılama` (ana sayfa olabilir)
- `Panel` (isterseniz **Pages → Settings → Permissions**'tan "Password protected" yapın;
  burada müşteri telefonları görünür)

Her sayfanın **kendi** kod paneli vardır. Karşılama sayfasına `karsilama.js`,
Panel sayfasına `dashboard.js` yapıştırılacak. Karıştırmayın.

## 3. Bir elemente ID verme (her element için aynı yol)

1. Elementi seçin.
2. Sağ alttaki **Properties & Events** panelinde en üstte **ID** alanı vardır
   (örn. `text12`). Silip bizim ID'yi yazın: `mesajGirisi`.
3. Enter'a basın. Büyük/küçük harf **önemlidir**: `MesajGirisi` ≠ `mesajGirisi`.

## 4. Karşılama sayfası — elementler

Yönergedeki **Z-Pattern** düzenine göre yerleştirin: sol üst logo/işletme adı + slogan,
sağ üst "Panel" bağlantısı (isteğe bağlı), ortada sağda sohbet kutusu, en altta
isim/telefon formu.

| Sıra | Element türü (Add menüsü) | ID | Ne işe yarar |
|---|---|---|---|
| 1 | **Input → Text Input** (tek satır) | `mesajGirisi` | Ziyaretçinin sorusu. Placeholder: "Örn: Kaçta açıksınız?" |
| 2 | **Button** | `sorBtn` | Yazısı: "Sor" |
| 3 | **Text** (paragraf) | `cevapAlani` | Sohbet buraya yazılır. Başlangıç yazısı: "Merhaba! Size nasıl yardımcı olabilirim?" Yüksekliği bol bırakın. |
| 4 | **Input → Text Input** | `isimGirisi` | Placeholder: "Adınız Soyadınız" |
| 5 | **Input → Text Input** (tip: Phone olabilir) | `telefonGirisi` | Placeholder: "05xx xxx xx xx" |
| 6 | **Button** | `kaydetBtn` | Yazısı: "Kaydet" |
| 7 | **Text** (küçük) | `durumMesaji` | Hata/başarı mesajları. Başlangıç yazısı bir boşluk olabilir; **görünür** bırakın (hidden yapmayın). |

**Glassmorphism (cam görünümü)** için sohbet elementlerini bir **Container Box** içine
alın ve kutunun tasarımından: dolgu rengi beyaz, saydamlık %40–60; kenarlık 1 px beyaz
%60; köşe yuvarlaklığı 16–20 px; hafif gölge. Wix Studio'da "Backdrop blur / Blur"
efekti varsa açın; yoksa yarı saydamlık yeterlidir. Arka plana koyu–açık bir degrade
koyun ki cam etkisi görünsün.

**Marka öğeleri:** logo, işletme adı, slogan ve 3 "hizmet" kartı Wix'te normal
Text/Image elementleridir, kodla ilgisi yoktur. Flask tarafındaki karşılıkları
`config.py` → `BUSINESS_NAME`, `BUSINESS_SLOGAN` ve `index.html`'deki `DEĞİŞTİR`
etiketli bölümlerdir. Wix'te ve Flask'ta aynı metni kullanın.

## 5. Panel sayfası — elementler

Yönergedeki **F-Pattern**: en üstte başlık + toplam sayı şeridi, altında soldan sağa
satırlar. En önemli bilgi olan **İsim** en solda ve en kalın yazıyla.

| Sıra | Element türü | ID | Not |
|---|---|---|---|
| 1 | **List & Grid → Repeater** | `leadRepeater` | Hazır tasarımlardan sade bir tanesini seçin. İçindeki örnek resim/buton gibi fazlalıkları silin. **Dataset'e bağlamayın**; veriyi kod verecek. |
| 2 | Repeater'ın **içine** Text | `isimText` | Kalın, en solda |
| 3 | Repeater'ın **içine** Text | `telefonText` | |
| 4 | Repeater'ın **içine** Text | `mesajText` | Uzun olabilir; genişliği bol verin |
| 5 | Repeater'ın **içine** Text | `tarihText` | Küçük/gri |
| 6 | Text (opsiyonel) | `toplamText` | Üst şerit: "Toplam 12 kayıt" |
| 7 | Text (opsiyonel) | `durumMesaji` | Hata/durum mesajı |
| 8 | Button (opsiyonel) | `yenileBtn` | "Yenile" |

Repeater'da elementleri **tek bir satıra** (ilk item'a) koyarsınız; Wix bunu her kayıt
için kopyalar. Repeater içindeki ID'ler sayfanın geri kalanında **tekrar kullanılmaz**.

## 6. Kodu yapıştırma ve API_URL'yi değiştirme

1. Karşılama sayfasında alt kod panelini açın; içindeki hazır satırları **silin**.
2. `wix/karsilama.js` dosyasının **tamamını** yapıştırın.
3. En üstteki satırı Render adresinizle değiştirin:
   ```js
   const API_URL = 'https://smartlead-ai-xxxx.onrender.com'; // sonunda / yok
   ```
4. Panel sayfası için aynı işlemi `wix/dashboard.js` ile yapın (API_URL yine değişecek).
5. **Preview** ile deneyin, sonra **Publish**.

## 7. CORS — backend'e "bu site bana istek atabilir" demek

Wix sayfası (`https://...wixsite.com`) ile backend (`https://...onrender.com`) farklı
adreslerdir. Tarayıcı, backend izin vermedikçe bu isteği engeller (CORS). İzin,
backend'deki `CORS_ORIGINS` ayarıdır (`config.py` okur, `create_app` uygular).

- Başlangıçta `CORS_ORIGINS=*` (herkese açık) ile çalışır; en kolay test yolu budur.
- Yayına alırken Render → **Environment** sekmesinde daraltın. Virgülle ayrılır ve
  **yalnızca şema + alan adı** yazılır, sayfa yolu YAZILMAZ:
  ```
  CORS_ORIGINS=https://kullaniciadi.wixsite.com,https://www.sitenizin-adi.com
  ```
  (`https://kullaniciadi.wixsite.com/sitem` gibi `/sitem` eklenmiş adres **eşleşmez**;
  tarayıcı Origin başlığında yol göndermez.)
- Wix **Preview** modunda site farklı bir adresten çalışabilir; Preview'da CORS hatası
  alırsanız geçici olarak `*` yapın, yayınladıktan sonra daraltın.
- Render'da ortam değişkenini değiştirince servis yeniden başlar; 1–2 dakika bekleyin.

## 8. Repeater `_id` kuralı

Wix Repeater'a verilen dizideki **her nesnede** `_id` adında, **metin (string)** tipinde
ve **benzersiz** bir alan olmalıdır; yoksa Repeater hiçbir şey göstermez. Backend bunu
zaten ekler (`database.py` → `_id = str(id)`); `dashboard.js` yine de emniyet için kısa bir
`forEach` döngüsünde her kayda `lead._id = String(lead._id || lead.id)` yapar (`_id` yoksa
`id`'den üretir, varsa metne çevirir). Ayrıca `onItemReady`, `.data` atamasından **önce**
yazılmalıdır (kodda sırası böyledir; yerini değiştirmeyin).

## 9. "Aynı kelimeler" kuralı

Frontend'in gönderdiği ve okuduğu alan adları backend ile **birebir** aynı olmalıdır.
Tek harf farkı bağlantıyı koparır. Bu projede tek doğru liste (`docs/YONERGE_OZETI.md` §8):

| Nerede | Gönderilen / okunan anahtarlar |
|---|---|
| `POST /api/sohbet` isteği | `mesaj`, `gecmis` (`[{role, content}]`) |
| `POST /api/sohbet` cevabı | `basari`, `cevap` — hata: `basari: false`, `hata` |
| `POST /api/leads` isteği | `isim`, `telefon`, `mesaj` (opsiyonel) |
| `POST /api/leads` cevabı | `201` + `basari`, `lead` |
| `GET /api/leads` cevabı | `basari`, `leads: [{id, _id, isim, telefon, mesaj, tarih}]` |

Bir anahtarı değiştirmek gerekirse backend + Flask şablonları + bu klasördeki iki
`.js` + bu README birlikte değişir.

## 10. Sık yapılan hatalar

| Belirti | Sebep | Çözüm |
|---|---|---|
| Butona basınca hiçbir şey olmuyor | ID yazım farkı (`sorbtn`, `SorBtn`, `sor_btn`) veya kod yanlış sayfaya yapıştırıldı | Properties panelinden ID'yi kontrol et; kodun o sayfanın panelinde olduğundan emin ol |
| Konsolda `Mixed Content` / `blocked` | `API_URL` `http://` ile başlıyor ya da hâlâ `localhost` | `https://...onrender.com` yaz |
| Konsolda `CORS policy` hatası | Backend `CORS_ORIGINS` Wix adresini içermiyor veya adrese yol eklenmiş | Bölüm 7 |
| İlk istek 30–60 saniye sürüyor / zaman aşımı | Render ücretsiz planı boşta kalınca uyur; ilk istek onu uyandırır | Normaldir. Sunumdan 1–2 dk önce `/health` adresini tarayıcıda açıp uyandır |
| `404 Not Found` | `API_URL` sonunda `/` var (`...com//api/sohbet`) veya yol yanlış | `API_URL` sonundaki `/`'ı sil |
| Cevap geliyor ama ekranda görünmüyor | `cevapAlani` bir Text değil (Text Box/Input) ya da `.text` yerine `.value` gerekir | Text elementi kullan; Input ise `.value` yaz |
| Repeater boş | `_id` eksik/metin değil, `onItemReady` `.data`'dan sonra yazılmış, Repeater içi ID'ler farklı | Bölüm 8 ve 5 |
| `durumMesaji`'nda "Lütfen bir mesaj yazın" ama yazdım | `mesajGirisi` ID'si başka bir elementte | ID'yi doğru Text Input'a ver |
| Türkçe karakterler `\u015e` gibi kaçış kodu olarak görünüyor | Eski backend sürümü | `app/__init__.py`'de `app.json.ensure_ascii = False` var mı kontrol et |
| Demo modu cevabı geliyor | Render'da `GROQ_API_KEY` tanımlı değil | Render → Environment → `GROQ_API_KEY` ekle, servisi yeniden başlat |
| Header'da hâlâ "Business Name" yazıyor | `masterPage.js` içinde header satırı yok (11 Eki'de yanlışlıkla sayfa kodunun kopyası duruyordu) | `wix/masterPage.js` içeriğini Studio'daki `masterPage.js`'e yapıştır; sayfa kodu oraya girmez |

**Hata ayıklama:** Preview'da **F12 → Console** sekmesi; Velo kodundaki `console.log`
satırları ve tarayıcının ağ hataları (CORS, 404, mixed content) burada görünür.

## 11. Teslim kontrol listesi

- [ ] `https://ADRES.onrender.com/health` → `"durum": "aktif"`
- [ ] Karşılama sayfasında soru sor → cevap `cevapAlani`'nda
- [ ] İsim/telefon kaydet → "Teşekkürler ..." mesajı
- [ ] Panel sayfasında kayıt listede, en yeni en üstte, isim kalın ve solda
- [ ] Render'da `CORS_ORIGINS` yalnızca Wix adresini içeriyor
- [ ] `.env` GitHub'da görünmüyor
