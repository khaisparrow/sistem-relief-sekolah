# Sistem Relief Sekolah & JadualPDF

Panduan untuk guru dan penyelaras sekolah menyediakan jadual guru ganti daripada jadual waktu PDF.

Projek ini mengandungi **dua aplikasi yang digunakan bersama**:

| Aplikasi | Kegunaan | Tempat digunakan |
|---|---|---|
| **JadualPDF** | Membaca jadual PDF, menyemak data dan menghasilkan Excel/CSV/JSON. | Komputer sendiri, melalui pelayar. Menggunakan Python + Streamlit. |
| **Sistem Relief Sekolah** | Merekod guru tidak hadir, menetapkan guru ganti secara manual dan mencetak jadual relief. | Pelayar dengan Internet. Menggunakan Google Apps Script dan Google Sheets. |

**Aliran kerja:** PDF jadual guru → JadualPDF → fail Excel → Google Sheets → Sistem Relief.

Panduan pemasangan mudah ini ditulis untuk **Windows**. Tiada kunci API AI diperlukan. Versi GAS ini digunakan oleh **penyelaras yang memasang sistem**, menggunakan akaun Google yang sama. Ia belum menyediakan portal log masuk berasingan untuk semua guru.

## Kandungan

- [Format PDF yang disokong](#format-pdf-yang-disokong)
- [Persediaan sebelum bermula](#persediaan-sebelum-bermula)
- [Pasang dan gunakan JadualPDF](#pasang-dan-gunakan-jadualpdf)
- [Pasang Sistem Relief GAS](#pasang-sistem-relief-gas)
- [Urus relief harian](#urus-relief-harian)
- [Mengemas kini jadual sekolah](#mengemas-kini-jadual-sekolah)
- [Masalah lazim dan cara menyemak](#masalah-lazim-dan-cara-menyemak)
- [Berkongsi kod melalui GitHub](#berkongsi-kod-melalui-github)
- [Arahan tambahan untuk pengguna mahir](#arahan-tambahan-untuk-pengguna-mahir)

## Format PDF yang disokong

> **PENTING: Baca bahagian ini sebelum memasang app.**
>
> Versi pertama JadualPDF dibina dan diuji untuk **PDF jadual individu guru berformat aSc yang serupa dengan profil di bawah**. Keserasian bergantung pada susun atur, bukan sekadar fail berakhir dengan `.pdf`.
>
> PDF imbasan, gambar jadual dan susun atur yang berlainan belum disokong secara umum.

### Ciri PDF yang diperlukan

1. PDF mempunyai **teks asli yang boleh dipilih/disalin**. Gunakan PDF asal yang dieksport daripada perisian jadual jika tersedia.
2. **Seorang guru pada satu halaman**, dengan tajuk seperti `Jadual Waktu: NAMA GURU`.
3. Hari persekolahan ialah **Isnin hingga Jumaat**.
4. Ada **garisan petak jadual**, nombor waktu serta masa mula dan tamat pada header jadual.
5. Ada **ringkasan Subjek/Jumlah dan jumlah Pelajaran/Minggu** di sebelah kanan halaman.
6. Label subjek, kelas dan bilik menggunakan corak fon/susunan yang serasi dengan profil penghurai.

**Cara semak ringkas:** buka PDF dan cuba pilih beberapa perkataan pada jadual. Jika seluruh halaman hanya boleh dipilih sebagai satu gambar, fail itu mungkin PDF imbasan. Ujian ini membantu mengenal pasti teks asli, tetapi tidak menjamin susun aturnya disokong.

### Contoh keserasian

| Keadaan fail | Sokongan versi sekarang |
|---|---|
| Format aSc serupa, tetapi bilangan guru atau kelas berbeza | Boleh dicuba; semak semua laporan sebelum eksport. |
| Masa pengajaran berbeza tetapi struktur masih serasi | Masa dibaca daripada header PDF. Hasil tetap perlu disemak. |
| Nama hari diputar pada sisi jadual | Disokong dalam profil yang diuji. |
| Subjek/kelas gabungan seperti `PI/PM` atau `3A/3B` | Label kumpulan dikekalkan; pembahagian guru kepada kumpulan tidak diteka. |
| PDF hasil imbasan atau gambar | Belum disokong; memerlukan OCR, iaitu teknologi membaca teks daripada gambar. |
| Beberapa guru dalam satu halaman | Belum disokong. |
| Hari persekolahan selain Isnin–Jumaat | Belum disokong oleh profil ini. |
| PDF jadual kelas, bukannya jadual individu guru | Belum disokong oleh profil ini. |
| Susun atur/perisian jadual yang berbeza | Perlu diuji dan mungkin memerlukan profil penghurai baharu. |

**75 guru dan 2,031 waktu ialah angka daripada fail ujian, bukan bilangan wajib.** Had versi JadualPDF sekarang ialah:

| Perkara | Had |
|---|---|
| Saiz PDF | 20 MB |
| Bilangan halaman | 150 |
| Nombor waktu | 1 hingga 30 |
| Jumlah rekod pengajaran untuk eksport | 20,000 |

Jika halaman tidak dapat dibaca dengan pasti, app melaporkannya dan menyekat eksport relief. **Jangan membuang halaman guru semata-mata untuk melepasi ralat bagi jadual operasi sebenar.** Guru yang tiada dalam fail import boleh dianggap tidak aktif dalam jadual baharu.

## Persediaan sebelum bermula

Sediakan:

- Komputer Windows dan pelayar seperti Chrome atau Edge.
- PDF jadual guru yang memenuhi ciri di atas.
- Akaun Google sendiri untuk menyimpan Google Sheet dan memasang GAS.
- Internet untuk memuat turun projek, memasang kebergantungan Python kali pertama dan menggunakan sistem GAS.
- **Python 3.11 hingga 3.14**. Pakej ini diuji menggunakan Python 3.12. Pelancar semasa belum menerima Python 3.15.

Versi dalam pakej dokumentasi ini: **JadualPDF 1.0.1** dan **Sistem Relief 1.1.1**.

### Fail projek

```text
README.md
sistem-relief/
    Code.gs
    Import.gs
    Index.html
    ImportPanel.html
    appsscript.json
pengekstrak-jadual/
    MULA.bat
    mula.ps1
    app.py
    core.py
    exports.py
    requirements.txt
    PANDUAN.md
    .streamlit/
        config.toml
```

Jangan mencampurkan Code.gs atau Import.gs daripada versi lama dengan versi baharu. Kekalkan semua fail Python dalam folder yang sama seperti struktur di atas, termasuk folder `.streamlit`.

## Pasang dan gunakan JadualPDF

### A. Muat turun projek daripada GitHub

1. Pada halaman repositori ini, klik butang hijau **Code**.
2. Pilih **Download ZIP**.
3. Buka folder Downloads dan cari fail ZIP yang dimuat turun.
4. Klik kanan → **Extract All / Ekstrak Semua**.
5. Pilih folder yang mudah dicari, contohnya Documents.
6. Buka folder hasil ekstrak, kemudian buka **pengekstrak-jadual**.

**Jangan menjalankan MULA.bat terus dari dalam ZIP.** Semua fail perlu diekstrak dahulu.

### B. Pasang Python jika belum ada

1. Buka [laman rasmi Python untuk Windows](https://www.python.org/downloads/windows/).
2. Pilih pemasangan Windows daripada cabang **3.11, 3.12, 3.13 atau 3.14**. Python 3.12 ialah versi ujian projek ini; jangan memilih 3.15 untuk pelancar semasa.
3. Gunakan **Windows installer**, bukan pakej *embeddable*. Bagi kebanyakan komputer sekolah moden, pilih installer **64-bit**.
4. Jika pemasang menawarkan **Add Python to PATH**, tandakan pilihan itu.
5. Lengkapkan pemasangan.

Jika komputer sudah mempunyai versi Python yang disokong, pemasangan semula tidak diperlukan. Jika tidak pasti atau tidak mempunyai kebenaran memasang perisian, minta bantuan penyelaras ICT sekolah.

### C. Buka app

1. Dalam folder **pengekstrak-jadual**, klik dua kali **MULA.bat**.
2. Kali pertama, tetingkap konsol akan memasang kebergantungan. Biarkan proses selesai; Internet diperlukan pada peringkat ini.
3. App akan dibuka dalam pelayar. Alamatnya biasanya `http://127.0.0.1:8501`.
4. Jika pelayar tidak dibuka sendiri, salin alamat yang dipaparkan dalam konsol ke pelayar.
5. Biarkan tetingkap konsol terbuka semasa menggunakan app.

Alamat `127.0.0.1` bermaksud app berjalan di **komputer sendiri**. Ia bukan pautan yang boleh dikongsi untuk dibuka pada komputer guru lain. Jika port 8501 sedang digunakan, pelancar memilih port seterusnya.

Untuk penggunaan seterusnya, klik MULA.bat semula. Setelah kebergantungan siap dipasang, pemprosesan PDF ini boleh dilakukan tanpa Internet. Sistem GAS tetap memerlukan Internet.

Untuk menghentikan app, pergi ke tetingkap konsol dan tekan **Ctrl+C**.

### D. Tukarkan PDF kepada Excel/CSV

1. Klik **Pilih PDF jadual waktu guru** dan pilih fail PDF asal.
2. Klik **Ekstrak jadual**.
3. Tunggu sehingga semua halaman selesai diproses.
4. Semak bilangan halaman, guru, waktu dan perkara yang memerlukan perhatian.
5. Buka tab **Semak & betulkan**. Pilih guru/halaman dan bandingkan data dengan PDF di sebelah kiri.
6. Gunakan **Sorot petak sumber** untuk membesarkan petak tertentu.
7. Jika perlu, betulkan nama, hari, waktu, masa, kelas, subjek atau bilik. Klik **Simpan pembetulan** sebelum bertukar halaman.
8. Buka **Laporan semakan** dan periksa jumlah guru/subjek serta sebarang ralat.
9. Buka **Muat turun**, tandakan pengesahan semakan dan klik **Sediakan fail eksport**.
10. Untuk pemasangan GAS kali pertama, pilih **Excel (.xlsx)**. Untuk mengemas kini sistem GAS yang sudah dipasang, Excel, CSV atau JSON boleh digunakan.

Fail yang dimuat turun biasanya berada dalam folder Downloads. Nama fail eksport ialah `jadual.xlsx`, `Jadual.csv` atau `data_relief.json`.

> **Simpan kerja sebelum menutup app.** Pembetulan berada dalam sesi memori. Refresh pelayar atau menghentikan server boleh menghilangkan kerja yang belum dimuat turun. Selepas mengubah data, pengesahan dan eksport lama dibatalkan; semak dan jana semula fail terkini.

### E. Fahami status semakan

| Status | Maksud dan tindakan |
|---|---|
| Semua semakan sepadan | Jumlah/struktur yang diperiksa sepadan. Tetap semak pratonton dan pastikan edisi jadual yang betul. |
| **SEMAK** | Ada perbezaan yang perlu diperiksa, contohnya ringkasan subjek. Jika mengesahkan hasil secara manual, catat sebabnya sebelum eksport. Fail mengekalkan status pengesahan pengguna. |
| **HALANG** | Ada masalah seperti halaman tidak dikenali, data tidak sah atau masa bertindih. Eksport relief disekat sehingga masalah diselesaikan. |

**Jumlah waktu yang sepadan tidak menjamin tiada pertindihan masa.** App memeriksa kedua-duanya secara berasingan.

Versi ini membenarkan pembetulan baris sedia ada. Ia belum menyediakan pembinaan semula halaman yang tidak dikenali atau penambahan/pembuangan petak sumber melalui editor.

## Pasang Sistem Relief GAS

**Buat bahagian ini selepas mendapat fail Excel daripada JadualPDF.** Tidak perlu menggunakan Terminal untuk memasang GAS.

### A. Masukkan data awal ke Google Sheets

1. Log masuk ke [Google Sheets](https://sheets.google.com/) dengan akaun yang akan mengurus sistem.
2. Buka satu spreadsheet kosong.
3. Pilih **File / Fail → Import → Upload / Muat naik**.
4. Pilih fail **jadual.xlsx** yang telah disemak.
5. Pilih **Create new spreadsheet / Cipta hamparan baharu** dan lengkapkan import.
6. Buka spreadsheet baharu itu. Namakan, contohnya **Sistem Relief — Nama Sekolah**.
7. Pastikan tab **Jadual**, **Guru** dan **Waktu** wujud serta mempunyai data. Tab semakan dan sumber tambahan juga boleh ada.

Gunakan Excel untuk langkah pertama ini supaya semua tab diimport sekali gus. Satu CSV sahaja tidak menyediakan semua tab yang diperlukan untuk pemasangan awal. Jangan menukar nama tab atau nama header lajurnya.

### B. Cipta projek Apps Script

1. Dalam spreadsheet baharu tadi, pilih **Extensions / Sambungan → Apps Script**.
2. Namakan projek **Sistem Relief Sekolah**.
3. Buka fail **Code.gs** yang disediakan oleh editor. Padam kod contoh dan tampal **seluruh kandungan Code.gs** daripada folder `sistem-relief` projek ini.
4. Klik **+ → Script**. Taip nama **Import** sahaja. Tampal kandungan **Import.gs**.
5. Klik **+ → HTML**. Taip nama **Index** sahaja. Tampal kandungan **Index.html**.
6. Klik **+ → HTML** sekali lagi. Taip nama **ImportPanel** sahaja. Tampal kandungan **ImportPanel.html**.
7. Klik **Project Settings** (ikon gear) dan aktifkan **Show "appsscript.json" manifest file in editor**.
8. Kembali ke **Editor**, buka **appsscript.json** dan gantikan kandungannya dengan fail manifest projek ini.
9. Simpan semua fail.

**Cara menyalin fail kod:** klik fail berkenaan di GitHub dan buka paparan Raw jika perlu, kemudian salin keseluruhan kandungannya. Untuk fail yang dimuat turun, klik kanan → **Open with → Notepad**. Jangan salin sekali tanda pagar tiga backtick daripada contoh Markdown.

Semak lima fail ini dalam editor:

| Nama dalam editor | Jenis |
|---|---|
| Code.gs | Script |
| Import.gs | Script |
| Index.html | HTML |
| ImportPanel.html | HTML |
| appsscript.json | Manifest, dipaparkan melalui Project Settings |

**Huruf besar/kecil pada Index dan ImportPanel mesti tepat.** Editor menambah sambungan `.gs` atau `.html` secara automatik apabila mencipta fail. Jangan mencipta fail seperti `Index.html.html`, Code kedua atau Import kedua.

### C. Jalankan pemasangan sekali

1. Dalam senarai fungsi bersebelahan butang **Run**, pilih **setupSistem**.
2. Klik **Run**. Jangan pilih doGet untuk langkah pemasangan.
3. Jika diminta, klik **Review permissions**, pilih akaun Google yang sama dan semak kebenaran spreadsheet serta alamat e-mel.
4. Teruskan kebenaran hanya apabila telah memastikan projek dan kod itu ialah salinan sendiri yang ingin digunakan. Jika tidak pasti tentang amaran yang dipaparkan, berhenti dan minta bantuan penyelaras ICT.
5. Tunggu **Execution log** memaparkan **Pemasangan berjaya**.
6. Kembali ke Google Sheet. Tab **Tetapan**, **Ketidakhadiran** dan **Relief** akan ditambah.
7. Dalam tab **Tetapan**, tukar nilai **NAMA_SEKOLAH** kepada sekolah sendiri dan **JADUAL_SUMBER** kepada edisi jadual sebenar. Jangan ubah nama kunci dalam lajur pertama.

Alamat e-mel pentadbir dan ID spreadsheet disimpan secara automatik semasa pemasangan. Tidak perlu menaip ID spreadsheet ke dalam kod. Zon masa ditetapkan kepada **Asia/Kuala_Lumpur**.

### D. Terbitkan web app

1. Klik **Deploy → New deployment**.
2. Klik ikon gear dan pilih **Web app**.
3. Isi keterangan ringkas, contohnya `Sistem Relief Sekolah`.
4. Pada **Execute as**, pilih **Me**.
5. Pada **Who has access**, pilih **Only myself**.
6. Klik **Deploy** dan lengkapkan kebenaran jika diminta.
7. Salin **Web app URL** yang berakhir dengan `/exec`.
8. Buka pautan itu menggunakan akaun Google yang memasang sistem. Simpan sebagai bookmark.

Tetapan **Only myself** ialah konfigurasi bagi versi penyelaras ini. Berkongsi kod di GitHub tidak bermaksud web app setiap sekolah perlu dibuka kepada semua orang. Setiap sekolah boleh memasang salinan dengan akaun dan spreadsheet sendiri.

Rujukan rasmi: [panduan web app Google Apps Script](https://developers.google.com/apps-script/guides/web).

### E. Buat ujian ringkas

1. Pilih tarikh hari persekolahan yang sesuai untuk ujian.
2. Tambah seorang guru sebagai tidak hadir dan pilih tempoh.
3. Pastikan kelas/waktu guru pada hari itu muncul.
4. Klik **Pilih guru**, pilih calon yang sesuai dan simpan.
5. Muat semula halaman dan pastikan penetapan masih ada.
6. Cuba **Cetak jadual**. Dialog pelayar boleh mencetak atau memilih **Save as PDF**.
7. Selepas ujian, **batalkan rekod ketidakhadiran contoh** supaya tidak bercampur dengan rekod operasi sebenar. Penetapan berkaitan turut dibatalkan.

## Urus relief harian

1. Buka bookmark web app dan pilih tarikh.
2. Masukkan guru tidak hadir, sama ada sepanjang hari atau sebahagian hari.
3. Tetapkan guru ganti secara manual bagi waktu yang memerlukan relief.
4. Semak baki **Belum ditetapkan** dan rekod **SEMAK**.
5. Cetak jadual harian untuk diedarkan melalui kaedah sekolah.

App menyemak kelas asal, ketidakhadiran dan relief lain berdasarkan **masa sebenar**. Calon yang tiada pertindihan masih perlu disemak oleh penyelaras untuk tugas lain seperti mesyuarat atau urusan pentadbiran.

Guru asal tidak boleh menggantikan kelas sendiri. Satu rekod ketidakhadiran aktif bagi setiap guru/tarikh disokong dalam versi ini. Jika hendak menukar tempoh, batalkan rekod lama dan masukkan rekod baharu; semak semula relief yang terlibat.

## Mengemas kini jadual sekolah

Gunakan aliran ini apabila sekolah mengeluarkan edisi baharu:

1. Dapatkan PDF asal edisi baharu dan semak formatnya.
2. Proses dengan JadualPDF, semak semua ralat dan muat turun Excel/CSV/JSON.
3. Buka web app relief dan klik **Import jadual**.
4. Pilih fail baharu. Had fail import GAS ialah **5 MB**, dengan maksimum **500 guru** dan **20,000 waktu**.
5. Isi nama edisi dan tarikh mula digunakan. Tarikh mesti hari ini atau selepasnya dan tidak mendahului tarikh kuat kuasa import berjaya terakhir.
6. Semak padanan guru. Nama yang sama boleh dipadankan secara automatik. Bagi nama berbeza, pilih guru sedia ada atau **Guru baharu** dengan teliti.
7. Klik **Semak import**. Lihat jumlah data, guru yang tidak aktif dan relief yang akan dibatalkan.
8. Selepas menyemak, tandakan pengesahan dan klik **Overwrite jadual semasa**.
9. Tunggu mesej berjaya, kembali ke app dan muat semula paparan.
10. Tetapkan semula relief yang terjejas.

> **Import menggantikan keseluruhan jadual, bukan menambah beberapa baris sahaja.** Jika hanya beberapa waktu berubah, edit salinan jadual penuh dan import fail penuh tersebut. Semak jumlah guru dan waktu sebelum mengesahkan.

ID sumber berdasarkan halaman PDF boleh berubah apabila halaman disusun atau dibuang. **Padankan berdasarkan nama/identiti guru, bukan nombor halaman semata-mata.**

Sebelum overwrite, app membuat sandaran enam tab operasi. Jadual sebelum tarikh kuat kuasa kekal boleh dirujuk melalui sandaran. Relief yang masih sesuai dikekalkan; penetapan yang terjejas dibatalkan untuk disemak dan ditetapkan semula.

**Jangan padam LogImport atau tab tersembunyi B_…** Rekod lama dan pemulihan bergantung padanya. Jika terdapat butang **Pulihkan import**, selesaikan pemulihan sebelum mencuba import lain. Jangan mengedit spreadsheet secara terus ketika import sedang berjalan.

## Masalah lazim dan cara menyemak

### JadualPDF / Python

| Mesej atau keadaan | Cara menyemak |
|---|---|
| Python tidak ditemui | Pasang versi 3.11–3.14, kemudian jalankan MULA.bat semula. Minta bantuan ICT jika perlu. |
| Versi Python belum disokong | Pelancar mungkin memilih versi di luar julat, contohnya 3.15. Gunakan Python yang disokong; langkah manual Python 3.12 disediakan di bawah. |
| Pemasangan kebergantungan gagal | Semak Internet dan jalankan MULA.bat semula. Jangan tutup tetingkap ketika pemasangan berjalan. |
| Pelayar tidak terbuka | Salin alamat 127.0.0.1 daripada konsol. Pastikan konsol masih berjalan. |
| Halaman tidak disokong / memerlukan OCR | Semak sama ada PDF ialah teks asli dan menggunakan susun atur yang diterangkan. Menyimpan gambar sebagai PDF tidak menjadikannya PDF teks. |
| Jumlah guru/subjek tidak sepadan | Buka halaman yang dilaporkan dan bandingkan petak sumber. Kod subjek baharu mungkin memerlukan pemetaan dalam penghurai. |
| Pembetulan hilang | Pastikan klik Simpan pembetulan dan muat turun hasil sebelum refresh/menutup app. |

### Jika dilaporkan masa bertindih

1. Dalam **Laporan semakan**, catat halaman, nama guru dan dua nombor baris yang terlibat.
2. Buka **Semak & betulkan** dan pilih halaman itu.
3. Cari nombor yang sama dalam lajur **Baris data**. Nombor ini merujuk keseluruhan data ekstrak, bukan baris fizikal dalam PDF.
4. Bandingkan hari, masa mula/tamat, subjek dan kelas dengan PDF.
5. Betulkan hanya jika hasil bacaan tersalah. Jika PDF asal juga bertindih, dapatkan pengesahan penyelaras jadual.

Contoh: `10:00–10:30` bertindih dengan `10:20–10:50` selama 10 minit. Nombor waktu yang berbeza tidak semestinya bermaksud masa berbeza, terutama apabila rehat tingkatan berbeza. Dua slot yang bersambung tepat, seperti `09:00–09:30` dan `09:30–10:00`, tidak dianggap bertindih.

**Jangan mematikan semakan atau menukar masa secara andaian untuk melepasi ralat.** Butang **Muat turun laporan diagnostik** masih boleh digunakan walaupun eksport relief disekat.

### Sistem Relief / GAS

| Mesej atau keadaan | Cara menyemak |
|---|---|
| Sistem belum dipasang | Dalam editor projek yang sama, pilih dan Run **setupSistem**. Tunggu mesej berjaya sebelum membuka web app. |
| No HTML file named Index was found | Semak bahawa **Index.html** wujud dengan huruf I besar. Simpan dan terbitkan **New version**. |
| ImportPanel tidak ditemui | Semak fail HTML **ImportPanel.html**, ejaan serta versi deployment. |
| Tab/lajur tidak ditemui | Pastikan Excel awal diimport dengan tab Jadual, Guru dan Waktu; jangan tukar header. |
| Akses terhad | Gunakan akaun Google yang memasang sistem. Semak Me/Only myself. Jika banyak akaun dibuka, gunakan profil pelayar bagi akaun yang betul. |
| Data telah berubah | Muat semula halaman, jalankan semakan/pratonton baharu dan cuba simpan semula. |
| Please make a selection within a single column… | Pastikan **Code.gs dan Import.gs versi 1.1.1** digunakan, kemudian kemas kini deployment. Versi ini membaiki pemformatan berbilang lajur. |
| Semua data telah dipulihkan daripada sandaran | Import gagal dan laluan pemulihan telah dijalankan. Muat semula app, semak data lama, baca mesej tab/lajur/langkah dan selesaikan punca sebelum mencuba lagi. |
| Tiada calon sesuai | Semak guru yang mempunyai halangan dan sebabnya. Penyelaras perlu menyelesaikan pertindihan atau urusan berkaitan. |

### Mengemas kini kod GAS yang sudah dipasang

1. Gantikan kandungan fail sedia ada yang dikemas kini. Jangan tambah Code/Import kedua.
2. Simpan.
3. Pilih **Deploy → Manage deployments → Edit** (ikon pensel).
4. Pilih **New version → Deploy**.
5. Refresh pautan `/exec` yang sama.

Menyimpan kod sahaja tidak semestinya mengemas kini app yang telah diterbitkan. Jangan menjalankan setupSistem semula atau mencipta spreadsheet baharu semata-mata untuk pembaikan kod biasa.

## Berkongsi kod melalui GitHub

Kongsi folder kod projek dan README ini supaya sekolah lain boleh membuat pemasangan sendiri. Fail README.md dipaparkan secara automatik pada halaman utama repositori GitHub. Fail `.md` juga boleh dibaca menggunakan Notepad; untuk panduan berformat, baca terus di GitHub.

**Tidak perlu memasukkan fail berikut dalam repositori awam:**

- PDF jadual sebenar, CSV/Excel/JSON operasi atau laporan diagnostik yang mengandungi nama guru.
- Data ketidakhadiran, sebab cuti dan penetapan relief sekolah.
- Folder `.venv`, `__pycache__` atau fail sementara.
- Kata laluan, token, fail `.env` dan rahsia konfigurasi.

Jika mahu menyediakan contoh, gunakan nama dan data rekaan. Kod sahaja mencukupi untuk diedarkan; setiap sekolah menyediakan PDF serta Google Sheet sendiri.

Untuk mendapatkan bantuan melalui tab **Issues**, nyatakan aplikasi, versi, mesej ralat penuh, langkah yang dibuat dan nombor halaman berkaitan. Semak kandungan laporan/tangkap layar sebelum menyiarkannya secara terbuka. PDF contoh dengan format sama dan data rekaan membantu pengujian tanpa mendedahkan jadual sebenar.

## Arahan tambahan untuk pengguna mahir

Bahagian ini pilihan. Pengguna biasa boleh menggunakan MULA.bat.

### Jalankan Python secara manual

Buka PowerShell dalam folder **pengekstrak-jadual**:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Jika `.venv` sudah dicipta menggunakan Python yang salah, tutup app dan namakan folder itu semula kepada `.venv-lama` sebelum mencipta persekitaran baharu.

### Jalankan ujian penghurai

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:JADUAL_TEST_PDF = 'C:\lokasi\PDF-rujukan.pdf'
.\.venv\Scripts\python.exe -m pytest tests -q
```

Ujian integrasi mengharapkan PDF rujukan projek asal, bukan sebarang PDF sekolah. PDF rujukan tidak dibundel. Jika pemboleh ubah fail rujukan tidak diberikan, ujian berkaitan ditandakan skip; ia tidak boleh dianggap sebagai bukti lulus bagi fail baharu.

### Rujukan rasmi

- [Python untuk Windows](https://www.python.org/downloads/windows/)
- [Pemasangan Streamlit](https://docs.streamlit.io/get-started/installation/command-line)
- [Google Apps Script: projek terikat kepada spreadsheet](https://developers.google.com/apps-script/guides/bound)
- [Google Apps Script: web app dan deployment](https://developers.google.com/apps-script/guides/web)
- [pdfplumber](https://github.com/jsvine/pdfplumber)

---

**Mulakan dengan PDF yang serasi, semak hasilnya, kemudian gunakan data yang telah disahkan untuk operasi relief sekolah.**
