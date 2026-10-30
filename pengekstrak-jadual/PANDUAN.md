# JadualPDF — pengekstrak jadual guru

Web app setempat menggunakan **Python + Streamlit** untuk membaca jadual PDF teks, menyemak hasil dan menghasilkan Excel/CSV/JSON yang serasi dengan **Import jadual** dalam Sistem Relief 1.1.

## Mula di Windows

1. Nyahzip keseluruhan pakej ke satu folder, contohnya `Documents\JadualPDF`. Jangan menjalankan MULA.bat terus dari dalam ZIP.
2. Pastikan **Python 3.11 hingga 3.14** dipasang. Python **3.12** ialah versi yang digunakan untuk pengujian. Jika tiada, muat turun daripada [python.org](https://www.python.org/downloads/windows/), jalankan pemasang dan aktifkan pilihan menambah Python ke PATH jika pilihan itu ditawarkan.
3. Klik dua kali **MULA.bat**.
4. Kali pertama, pelancar mencipta persekitaran `.venv` dalam folder projek dan memasang kebergantungan. Internet diperlukan untuk pemasangan tersebut.
5. Selepas siap, app dibuka dalam pelayar pada alamat setempat, biasanya `http://127.0.0.1:8501`. Jika port itu digunakan, pelancar memilih port seterusnya.
6. Biarkan tetingkap konsol terbuka semasa menggunakan app. Untuk berhenti, tekan **Ctrl+C** dalam tetingkap itu.

Kali berikutnya, klik MULA.bat semula. Selepas kebergantungan siap dipasang, pemprosesan PDF dan penjanaan fail tidak memerlukan API AI atau Internet. Memulakan app tidak menerbitkannya ke Internet; versi ini mendengar pada `127.0.0.1` sahaja.

## Cara menggunakan

1. Upload PDF asal jadual guru dan klik **Ekstrak jadual**.
2. Tunggu semua halaman dibaca. Semak bilangan halaman, guru, waktu dan perkara yang memerlukan perhatian.
3. Dalam **Semak & betulkan**, pilih halaman/guru. Imej sumber berada di kiri dan jadual data di kanan.
4. Gunakan **Sorot petak sumber** untuk melihat petak tertentu dalam warna jingga dan paparan yang dibesarkan.
5. Jika perlu, betulkan nama guru atau data sedia ada: hari, nombor waktu, masa, subjek, kelas dan bilik. Klik **Simpan pembetulan** sebelum bertukar halaman. Hari ialah 1=Isnin hingga 5=Jumaat; masa menggunakan HH:mm seperti 09:30.
6. Buka **Laporan semakan** untuk melihat jumlah mengikut guru dan subjek, pertindihan serta sebarang halaman yang gagal dibaca.
7. Dalam **Muat turun**, sahkan semakan dan klik **Sediakan fail eksport**. Pilih Excel, CSV, JSON atau ZIP yang mengandungi semua fail dan laporan.
8. Buka sistem relief, klik **Import jadual**, pilih fail yang baru dimuat turun dan ikut aliran padanan guru serta pengesahan overwrite.

Upload fail lain mengosongkan hasil sebelumnya. Selepas pembetulan, pengesahan dan fail muat turun lama dibatalkan; cikgu perlu menyemak dan menjana semula eksport. Sesi ini disimpan dalam memori app. Memuat semula pelayar atau menghentikan server boleh menghilangkan pembetulan yang belum dimuat turun.

## Format PDF yang disokong

Versi pertama khusus kepada profil jadual **aSc** yang serupa dengan PDF rujukan sekolah:

- Tajuk `Jadual Waktu: NAMA GURU`.
- Satu halaman bagi seorang guru.
- Lima baris hari Isnin hingga Jumaat, dengan nama hari yang boleh diputar.
- Petak bergaris dan header nombor waktu serta masa mula/tamat.
- Ringkasan Subjek/Jumlah dan jumlah Pelajaran/Minggu di sebelah kanan.
- PDF mempunyai teks asli, bukan sekadar gambar imbasan.

Penghurai mengesan kedudukan hari, header, petak serta ringkasan daripada geometri; masa tidak dihardcode. Saiz halaman vektor yang diskalakan turut diuji. Pengasingan subjek, kelas dan bilik masih menggunakan corak fon/label profil ini. Susun atur yang berbeza boleh memerlukan penambahan profil penghurai.

**PDF imbasan/OCR, jadual kelas yang bukan jadual individu guru, beberapa guru pada satu halaman, jadual hujung minggu dan susun atur bebas belum disokong.** Halaman yang tidak dikenali dilaporkan dan eksport relief disekat supaya data tidak lengkap tidak diterima secara senyap.

Had versi ini: **20 MB**, **150 halaman**, maksimum **20,000 waktu** eksport. Maksimum nombor waktu ialah 30. Format kelas asal seperti 3KAA, 4B, 5D dan kumpulan berpisah slash dipelihara. Kod bilik tidak dikembangkan kepada nama bilik secara andaian.

## Ketepatan dan semakan

App menjalankan semakan berikut:

1. Setiap petak berteks dipadankan kepada satu hari dan satu atau beberapa waktu.
2. Teks setiap petak dibandingkan menggunakan **pdfplumber** dan **PDFium**, berdasarkan pusat koordinat aksara. Ruang kosong tidak diambil kira dalam perbandingan aksara ini.
3. Bilangan waktu setiap guru dibandingkan dengan jumlah tercetak dan jumlah ringkasan subjek.
4. Jumlah waktu mengikut subjek/guru dibandingkan dengan ringkasan PDF. Pemetaan kod subjek sekolah dimasukkan dalam `core.py` dan boleh ditambah jika kod baharu diperkenalkan.
5. Guru-hari-waktu berganda, masa tidak sah, kelas/subjek kosong dan masa pengajaran bertindih dikesan.
6. Nombor waktu yang sama mesti mempunyai masa yang konsisten, supaya hasil serasi dengan importer relief.

**HALANG** bermaksud eksport relief tidak dibenarkan: contohnya halaman gagal dibaca atau data mempunyai pertindihan. Laporan diagnostik masih boleh dimuat turun.

**SEMAK** bermaksud terdapat perbezaan jumlah, kod subjek yang belum dipadankan atau perbandingan teks yang memerlukan pemeriksaan visual. Eksport hanya dibenarkan selepas pengguna menulis sebab pengesahan sekurang-kurangnya 10 aksara dan mengesahkan semakan. Fail mencatat status pengesahan pengguna; ia tidak dilabel seolah-olah semua semakan automatik lulus.

Semakan jumlah dan aksara petak asal bukan jaminan semua makna jadual telah difahami. Label subjek/kelas gabungan dikekalkan sebagai kumpulan; app tidak meneka subjek atau kumpulan murid khusus bagi setiap guru. Jadual sekolah yang masih berkuat kuasa perlu disahkan oleh penyelaras.

## Pembetulan

### Menyemak ralat bertindih

Dalam versi 1.0.1, laporan menyatakan nombor baris global, waktu, masa, kelas, subjek dan julat pertindihan. Contohnya 09:00-09:30 bertindih dengan 09:20-10:00 selama 09:20-09:30. Dua slot yang bersambung tepat (09:00-09:30 dan 09:30-10:00) tidak dianggap bertindih.

Buka **Semak & betulkan**, pilih halaman yang dilaporkan, kemudian cari nombor dalam lajur **Baris data**. Nombor itu bukan nombor baris fizikal dalam petak PDF. Bandingkan hari, nombor waktu dan masa kedua-dua baris dengan sumber di kiri. Jika hasil bacaan tersalah, betulkan mengikut PDF. Jika jadual asal juga bertindih, dapatkan pengesahan penyelaras jadual; jangan ubah masa secara andaian untuk melepasi semakan. Waktu 6 dan 7 dalam contoh sekolah mempunyai masa yang saling bertindih, tetapi nombor waktu lain juga boleh bertindih jika data atau jadual berbeza.

Butang **Muat turun laporan diagnostik** menghasilkan laporan_semakan.json. Fail itu boleh digunakan bersama PDF yang diproses untuk menyiasat ralat tertentu.

Versi ini membenarkan pembetulan **baris yang berjaya diekstrak**, bukan menambah/membuang petak sumber atau membina semula halaman yang tidak dikenali. Pembetulan yang menghasilkan ID berganda, julat masa tidak sah atau pertindihan ditolak. Bilangan waktu dan ringkasan dikira semula setiap kali perubahan disimpan.

Nama guru dan label hari dalam data dikemas kini secara konsisten. Petak serta teks sumber tidak diubah. Excel/ZIP/JSON merekod perubahan, dan label status membezakan data dengan pembetulan pengguna daripada ekstrak tanpa pembetulan.

## Fail eksport

| Fail/tab | Kegunaan |
|---|---|
| Jadual | Satu baris setiap waktu pengajaran; digunakan importer relief. |
| Guru | Nama, ID sumber dan ringkasan semakan guru. |
| Waktu | Label/mula/tamat daripada header PDF, termasuk rehat. |
| BlokAsal | Petak, koordinat dan teks asal sebelum pembetulan. |
| SemakanGuru | Jumlah PDF berbanding jumlah data setiap guru. |
| SemakanSubjek | Jumlah PDF berbanding jumlah data mengikut subjek/guru. |
| Catatan | Sumber, SHA256, profil, pengesahan dan batas semakan. |
| Pembetulan | Ditambah jika ada perubahan yang disimpan. |

Excel mengandungi nilai siap baca, bukan formula. Masa Excel bertipe masa dan dipaparkan sebagai HH:mm. CSV menggunakan UTF-8 dengan BOM. Teks yang kelihatan seperti formula ditulis secara literal dalam Excel dan dilindungi untuk import CSV.

ID guru seperti G001 ialah **ID sumber dalam fail itu**, berdasarkan halaman, bukan identiti kekal antara edisi. Sistem relief memadankan nama kepada ID kekalnya ketika import. Nama dan susunan halaman yang berubah mesti disemak semasa padanan.

## Privasi dan penyimpanan

Kod app tidak memanggil API AI, Google Drive atau perkhidmatan penukaran PDF pihak ketiga. Fail upload, imej pratonton dan hasil berada dalam memori proses/sesi setempat; app tidak menyimpan PDF asal secara automatik ke folder projek. Fail muat turun disimpan oleh pelayar mengikut pilihan pengguna. Telemetri Streamlit dinyahaktifkan dalam konfigurasi projek.

Versi ini belum dipasang pada hosting awam dan tidak mempunyai sistem akaun pengguna. Jika kemudian mahu hosting atau penggunaan ramai guru, tambah kawalan akses, had sumber serta strategi penyimpanan yang sesuai terlebih dahulu.

## Jika ada masalah

| Keadaan | Tindakan |
|---|---|
| MULA.bat memaparkan Python tidak ditemui | Pasang Python 3.12, kemudian cuba semula. Semak `py --version` atau `python --version` dalam Terminal. |
| Pemasangan kebergantungan gagal | Semak Internet dan jalankan MULA.bat sekali lagi; marker siap hanya ditulis selepas pemasangan berjaya. |
| Persekitaran .venv rosak / Python telah ditukar | Tutup app, namakan semula folder `.venv` kepada `.venv-lama`, kemudian jalankan MULA.bat untuk mencipta persekitaran baharu. |
| Pelayar tidak dibuka automatik | Salin URL 127.0.0.1 yang dipaparkan dalam konsol ke Chrome/Edge. |
| Halaman dilaporkan tidak disokong | Pastikan PDF teks asal dan susun atur sama dengan profil. Muat turun laporan diagnostik; profil baharu mungkin diperlukan. |
| Ringkasan subjek tidak sepadan | Semak label asal dan kod subjek; tambah pemetaan yang betul dalam SUBJECTS di core.py jika kod sekolah baharu. Jangan sekadar mengabaikan perbezaan. |
| Data hilang selepas refresh | Mulakan ekstraksi semula. Sesi memori tidak menggantikan fail yang dimuat turun. |

## Arahan manual / pembangunan

Dalam folder projek:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Untuk ujian:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:JADUAL_TEST_PDF = 'C:\lokasi\JADUAL WAKTU GURU JILID 5.pdf'
.\.venv\Scripts\python.exe -m pytest tests -q
```

PDF rujukan tidak dibundel dalam pakej. Untuk ujian perbandingan ekstrak terdahulu, tetapkan `JADUAL_TEST_REFERENCE` kepada `tables.json` rujukan yang mempunyai matriks tab Jadual. Jika PDF rujukan tiada, ujian integrasi berkenaan akan ditandakan skip, bukannya dianggap lulus.

## Pengesahan versi ini

Fail rujukan 75 halaman telah menghasilkan **75 guru, 1,214 petak dan 2,031 waktu**, sama dengan ekstrak terdahulu. Semua **174** ringkasan subjek/guru dan **1,214** perbandingan teks petak asal sepadan. Setiap medan bagi 2,031 rekod dibandingkan dengan data rujukan terdahulu.

Ujian turut merangkumi input rosak/berkunci, PDF imej, halaman guru berganda, PDF vektor diskalakan, pembetulan, data bertindih, pengesahan eksport, nilai Excel bertipe masa dan literal, serta CSV/JSON/ZIP. Aliran upload, ekstraksi, muat turun dan pembetulan diuji dalam Chrome setempat. Ini bukti bagi profil dan fail rujukan tersebut; fail edisi baharu tetap perlu disemak.

Rujukan teknologi: [Streamlit](https://docs.streamlit.io/), [pdfplumber](https://github.com/jsvine/pdfplumber), [pypdfium2](https://pypdfium2.readthedocs.io/), [XlsxWriter](https://xlsxwriter.readthedocs.io/).
