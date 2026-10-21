# Plan: Delivery App - Monitoring Pengiriman Armada Sendiri

Status: rencana berdasarkan diskusi pengguna; implementasi dilakukan pada tahap berikutnya.

## 1. Tujuan

Delivery App menjadi tempat kerja sederhana untuk memproses pengiriman dari Sales Order dengan pilihan Armada Sendiri atau Ekspedisi. Prioritas pengembangan saat ini adalah monitoring armada sendiri; rincian alur ekspedisi masih belum final. ERPNext menjadi sumber dokumen dan validasi transaksi.

Informasi utama yang harus cepat ditemukan: driver, nomor telepon, plat nomor, company, jadwal keberangkatan, keberangkatan aktual, SO/DN yang dibawa, progres kunjungan, dan checkpoint terakhir yang terkonfirmasi.

## 2. Keputusan dari diskusi

| Topik | Keputusan |
| --- | --- |
| Fokus | Prioritas monitoring armada sendiri. Rincian ekspedisi dan resi dibahas pada tahap lanjutan. |
| Metode pengiriman | Pilihan Armada Sendiri dan Ekspedisi tetap tersedia di app. Alur ekspedisi belum final. |
| Sumber pesanan | Sales Order yang sudah diterima/disubmit di ERPNext. |
| Hubungan dokumen | Satu SO menjadi satu DN dengan seluruh barang yang harus dikirim. |
| Pengiriman parsial | Alur app menggunakan pengiriman penuh. Jika barang belum siap, petugas menunggu. |
| Validasi stok | Menggunakan validasi ERPNext saat submit DN. |
| Pembuatan DN | Langsung submit setelah petugas menjalankan aksi pembuatan DN. |
| Trip | Satu Delivery Trip dapat memuat beberapa DN. |
| Titik keberangkatan | Mengikuti Company dari SO, diteruskan ke DN dan trip. |
| Checkpoint | Menggunakan `Delivery Stop.visited`, yang diperbarui aplikasi existing. |
| Lokasi pelanggan | Satu Customer memiliki satu lokasi pengiriman; koordinat disimpan di Customer master. |
| Pengisian lokasi | Petugas mengatur pin dari app saat menyiapkan trip jika Customer belum memiliki koordinat. Lokasi dipakai ulang. |
| Peta | Leaflet dan OpenStreetMap, dengan garis rute mengikuti jalan. |
| Arti peta | Rute rencana dan checkpoint yang terkonfirmasi; pelacakan GPS menjadi pengembangan terpisah. |
| Desain | Minimalis, user-friendly, bahasa Indonesia yang jelas, ikon Lucide, tanpa emoji/emoticon. |

Company untuk satu trip harus sama dengan Company seluruh DN/SO di dalamnya. Pilihan DN pada layar penyusunan trip difilter per company, dengan validasi yang sama di backend.

Delivery Trip armada sendiri hanya menerima DN bermetode Armada Sendiri. DN Ekspedisi tetap tercatat pada daftar pengiriman dengan metode yang jelas dan mengikuti alur ekspedisi yang sudah tersedia sampai rancangan lanjutannya ditetapkan.

## 3. Temuan dari kode existing

### 3.1 Sumber checkpoint sudah tersedia

- `../scanner_app/scanner_app/scanner_app/delivery_note_scan.py::mark_stop_visited`
  mencari trip melalui `Delivery Note.delivery_trip`, menandai stop yang cocok sebagai `visited`, dan menyimpan trip.
- `../scanner_app/scanner_app/scanner_app/scan_history.py::record_history`
  menyimpan `Scanner Scan History` dengan `recorded_at`, `scanned_by`, `company`, referensi DN, referensi trip, serta `details` berisi `already_visited`.
- Scan ulang atas stop yang sudah visited juga dicatat. Scan dengan `already_visited=true` harus dikecualikan dari penentuan waktu kunjungan baru.
- Teks pada halaman scanner menyebut scan ketika tiba di tujuan. Dashboard menggunakan istilah **Dikunjungi/Checkpoint terkonfirmasi**. Bukti penerimaan/POD ditampilkan sebagai informasi tersendiri jika memang tersedia.

### 3.2 Perilaku native ERPNext

- `../erpnext/erpnext/stock/doctype/delivery_stop/delivery_stop.json` menyediakan `visited`, `lat`, `lng`, `estimated_arrival`, `details`, dan relasi DN. Waktu konfirmasi kunjungan bukan field native pada stop ini.
- `../erpnext/erpnext/stock/doctype/delivery_trip/delivery_trip.py::update_status` mengubah trip submitted menjadi `In Transit` ketika sebagian stop visited dan `Completed` ketika semuanya visited. Ketika belum ada stop visited, status native kembali ke `Scheduled`.
- `Sales Order.make_delivery_note` menyediakan pemetaan native item, company, alamat, pajak, warehouse, referensi SO, serta data serial/batch/reservasi sesuai ERPNext.

### 3.3 Bagian Delivery App yang perlu disesuaikan

- `delivery_app/api.py::get_operations_summary` masih membuat marker memakai hash nama DN dan koordinat demo sekitar Jakarta. Prioritas pertama adalah menggantinya dengan koordinat master/stop yang benar-benar tersedia.
- `delivery_app/api.py::start_trip` saat ini hanya mengubah status; belum menyimpan waktu keberangkatan aktual.
- `delivery_app/api.py::complete_trip` saat ini bisa memaksa status selesai. Alur monitoring perlu mengikuti kondisi stop, sehingga penyelesaian trip konsisten dengan `visited`.
- `create_delivery_trip` masih bisa mengambil company dari Global Defaults. Sumber company perlu diturunkan dari DN/SO yang dipilih.
- `frontend/src/components/OperationsMap.vue` sudah memakai OSM dengan atribusi, tetapi masih berupa marker tanpa garis rute.
- Dashboard sekarang berorientasi DN, ekspedisi, dan POD; navigasi belum memiliki antrean Sales Order.

## 4. Usulan default untuk hal yang belum diputuskan pengguna

### 4.1 Keberangkatan aktual

Usulan: admin/petugas pengiriman menekan **Berangkat** pada trip submitted.

- `departure_time` tetap menjadi jadwal keberangkatan.
- Simpan waktu aktual dari server dan pengguna yang mencatatnya.
- Aksi berulang mengembalikan catatan keberangkatan yang sudah ada, sehingga jam pertama tidak bergeser.
- Trip lama yang tidak memiliki waktu aktual menampilkan **Belum tercatat**.
- Waktu scan pertama, waktu membuat dokumen, dan jadwal tidak dijadikan pengganti waktu berangkat aktual.

Gunakan `monitoring_status` pada response app agar trip yang sudah berangkat bisa terlihat **Dalam Perjalanan** sebelum checkpoint pertama. Perhitungannya konsisten untuk tabel, filter, dan KPI:

1. Dokumen cancelled: **Dibatalkan**.
2. Dokumen draft: **Draft**.
3. Trip submitted dengan stop tidak kosong dan semuanya visited: **Selesai Kunjungan**.
4. Trip submitted dengan waktu berangkat aktual atau sebagian stop visited: **Dalam Perjalanan**.
5. Trip submitted lainnya: **Terjadwal**.

Status native tetap tersedia di detail dokumen. Status monitoring dihitung dari sumber di atas agar perubahan status native saat scanner menyimpan trip tetap dapat ditampilkan dengan konsisten.

### 4.2 Kendala pengantaran

Usulan awal: **Catatan kendala opsional** per tujuan menggunakan `Delivery Stop.details` yang sudah tersedia.

- Catatan existing ditampilkan di detail stop; petugas berwenang bisa melengkapinya.
- Stop belum visited ditampilkan **Belum dikunjungi**. Kondisi tersebut saja belum memberikan alasan pengantaran tertunda.
- Penolakan, retur, dan alur tindak lanjut khusus dibahas setelah proses operasionalnya diketahui.

## 5. Data lokasi dan checkpoint

### 5.1 Lokasi master dan snapshot trip

Usulan field:

| Dokumen | Data | Penggunaan |
| --- | --- | --- |
| Customer | `custom_latitude`, `custom_longitude` (Float) | Koordinat Latitude & Longitude pelanggan (alamat/pengiriman). |
| Company | `custom_latitude`, `custom_longitude` (Float) | Koordinat asal keberangkatan armada untuk company tersebut. |
| Delivery Trip | `custom_origin_latitude`, `custom_origin_longitude` (Float) | Snapshot koordinat asal keberangkatan saat trip disusun. |
| Delivery Trip | `custom_actual_departure`, Datetime | Waktu konfirmasi berangkat dari server. |
| Delivery Trip | `custom_departed_by`, Link User | Petugas yang mengonfirmasi keberangkatan. |
| Delivery Stop | `lat`, `lng` native | Snapshot koordinat Customer untuk tujuan tersebut. |

Periksa metadata situs terlebih dahulu dan gunakan field existing yang ekuivalen jika tersedia. Field tambahan dibuat secara idempotent melalui setup app.

- Input Geolocation dibatasi ke satu Point yang valid. Latitude dan longitude diproses sebagai angka, dengan urutan `[longitude, latitude]` untuk GeoJSON/OSRM dan `[latitude, longitude]` untuk Leaflet.
- Validasi angka nol secara eksplisit; koordinat valid di garis ekuator tidak boleh ditolak hanya karena bernilai nol.
- Tombol **Atur Lokasi Customer** muncul ketika menyusun trip dengan lokasi yang belum diatur. Company memiliki pengaturan pin keberangkatan sekali per company.
- Alamat dari SO/DN ditampilkan sebagai panduan ketika menempatkan pin.
- Pengubahan master memengaruhi trip baru. Snapshot perjalanan yang sudah berjalan/diselesaikan tetap mengacu pada lokasi yang dipakai saat disusun.
- Data lama yang koordinatnya kosong tetap dapat dimonitor dalam tabel, dengan keterangan **Koordinat belum diatur** pada peta.
- Menyiapkan rute lengkap memerlukan titik Company dan seluruh stop. Koordinat yang hilang harus terlihat jelas agar petugas dapat melengkapinya.

### 5.2 Pembacaan kunjungan

- Sumber progres: `Delivery Stop.visited` pada trip.
- Sumber waktu: `Scanner Scan History.recorded_at`, untuk DN dan trip yang sama, dengan `operation=Delivery Note` dan `already_visited=false` pada detail scan.
- Gunakan konfirmasi perubahan visited yang valid; abaikan rescan `already_visited=true` agar scan ulang tidak memindahkan checkpoint terakhir.
- Cocokkan log dengan stop yang saat ini visited. Bila ada beberapa konfirmasi akibat kunjungan yang direset dan dikonfirmasi lagi, gunakan konfirmasi valid terbaru.
- Checkpoint terakhir ditentukan berdasarkan waktu konfirmasi, sehingga kunjungan di luar urutan rencana tetap terbaca benar.
- Jika suatu stop visited tanpa log waktu yang cocok, tampilkan **Dikunjungi - waktu belum tersedia**. Jangan memakai `idx`, `modified`, atau waktu refresh sebagai jam kunjungan.
- Jika ada visited tanpa waktu, jelaskan bahwa urutan aktual belum lengkap; marker berwaktu diberi label **Konfirmasi terakhir yang tercatat**.
- Tujuan berikutnya adalah tujuan belum visited menurut urutan rencana, dengan label **Tujuan berikutnya (rencana)**.
- Timestamp ditampilkan mengikuti timezone situs/pengguna dan memiliki label waktu konfirmasi.
- Query riwayat dibatasi ke trip/DN yang dapat dibaca pengguna dan company yang relevan. Hindari mengambil seluruh histori scanner untuk setiap refresh.
- Ketika DocType riwayat scanner belum tersedia, progres tetap dapat dibaca dari visited dan informasi waktu ditampilkan sebagai belum tersedia.

## 6. Alur operasional

### A. Menerima SO dan membuat DN

1. Halaman **Pesanan** menampilkan SO submitted yang memenuhi syarat diproses, dengan pencarian serta filter company dan tanggal.
2. Petugas memilih satu SO; ringkasan pelanggan, alamat, seluruh item, kuantitas, dan warehouse ditampilkan dari data ERPNext, beserta pilihan metode **Armada Sendiri / Ekspedisi**. Metode yang dipilih disimpan pada `Delivery Note.custom_delivery_method`.
3. Aksi **Buat Delivery Note** menjalankan mapper native ERPNext, insert, dan submit dalam satu transaksi.
4. Kuantitas mengikuti seluruh kebutuhan pengiriman SO. Backend memverifikasi hasil mapping; filter tanggal/item atau reservasi parsial tidak boleh menghasilkan DN parsial yang tampil sebagai pengiriman penuh.
5. Field wajib yang belum lengkap, seperti warehouse atau serial/batch sesuai konfigurasi ERPNext, ditampilkan secara kontekstual untuk dilengkapi sebelum submit.
6. Hasil validasi ERPNext ditampilkan dekat aksi/form. Submit yang gagal tidak menghasilkan DN sukses atau draft yatim yang tersembunyi.
7. SO/DN existing ditangani melalui relasi native `against_sales_order`/`so_detail`. Double-click, request ulang, dan proses bersamaan harus mengarah ke satu DN aktif, dengan pemeriksaan ulang dan penguncian transaksi per SO.
8. SO yang sudah memiliki DN aktif atau pemenuhan parsial dari alur lain menampilkan dokumen/progres existing. Alur satu SO satu DN penuh hanya tersedia untuk SO yang memenuhi syarat tersebut.

### B. Menyusun perjalanan

1. Pilih beberapa DN submitted bermetode Armada Sendiri dari satu company yang belum masuk trip aktif lainnya.
2. Isi driver, kendaraan, jadwal berangkat, serta urutan stop secara sederhana.
3. Ambil titik keberangkatan dari company DN/SO. Lengkapi lokasi company/customer bila diperlukan.
4. Tampilkan preview rute dan daftar tujuan bernomor, lalu simpan/submit Delivery Trip menggunakan lifecycle native ERPNext.
5. Setiap DN memiliki stop tersendiri agar tetap cocok dengan pemindaian DN pada scanner. DN berbeda untuk customer yang sama tetap memiliki progres masing-masing walaupun pin lokasinya sama.
6. Pemilihan company yang tidak cocok, DN Ekspedisi, DN ganda, DN draft/cancelled, dan DN yang ditugaskan ulang ke trip aktif lain divalidasi di backend. Metode Ekspedisi pada DN existing harus dihormati ketika menyeleksi dokumen untuk trip.

### C. Monitoring

1. Dashboard menampilkan trip aktif dan progres berdasarkan visited.
2. Pilih trip untuk membuka driver, plat nomor, jadwal/aktual berangkat, peta rute, dan daftar stop.
3. Perubahan scanner muncul melalui pembaruan berkala ringan, misalnya 30 detik saat halaman terlihat, serta tombol **Perbarui**.
4. Pisahkan **Data diperbarui pukul ...** dari **Checkpoint dikonfirmasi pukul ...**.
5. Semua stop visited menghasilkan tampilan **Selesai Kunjungan**. Bukti penerimaan ditampilkan sesuai data POD yang tersedia.

## 7. Rancangan tampilan minimalis

### Navigasi

- **Dashboard**: pusat monitoring.
- **Pesanan**: tab Sales Order dan Delivery Note, dengan pilihan/filter metode Armada Sendiri atau Ekspedisi. DN armada sendiri yang memenuhi syarat dapat dilanjutkan ke penjadwalan trip.
- **Perjalanan**: trip aktif, terjadwal, dan riwayat dengan satu pola tabel/filter.
- **Pengaturan**: lokasi keberangkatan per company, pengaturan rute, serta akses data armada/driver.

Nama aplikasi tetap **Delivery App**. Pilihan Ekspedisi tetap mudah diakses dari Pesanan dan detail DN; informasi serta aksi ekspedisi ditampilkan secara kontekstual mengikuti fitur existing. Rincian layanan, resi, integrasi, dan monitoring ekspedisi belum ditetapkan sebagai rancangan final. Detail dokumen existing tetap menjadi sumber riwayat yang sudah tercatat.

### Dashboard

- Ringkasan pendek: **Menunggu Penjadwalan**, **Terjadwal**, **Dalam Perjalanan**, **Selesai Kunjungan Hari Ini**.
- Menunggu penjadwalan dihitung dari DN submitted armada sendiri yang belum terikat trip aktif; SO yang belum memiliki DN memiliki ringkasan tersendiri pada Pesanan.
- Selesai hari ini memakai waktu konfirmasi stop terakhir yang lengkap. Trip tanpa bukti waktu penyelesaian ditampilkan tanpa tanggal penyelesaian yang ditebak.
- Tabel utama: Trip, Company, Driver, Plat Nomor, Jadwal, Berangkat Aktual, Progres, Checkpoint Terakhir, Status.
- Filter company, tanggal, status, pencarian driver/plat/trip, dan tombol Perbarui.
- Klik baris membuka panel detail. Satu trip terpilih ditampilkan di peta agar garis rute mudah dibaca.

### Detail perjalanan

- Ringkasan driver/telepon, kendaraan/plat, company, dan jadwal/aktual.
- Peta rute rencana dengan titik asal dan nomor stop.
- Daftar stop: customer, SO/DN, alamat, status visited, waktu konfirmasi, dan catatan.
- Aksi utama yang relevan: **Berangkat** dan **Lihat Dokumen**; pengisian checkpoint tetap berasal dari integrasi scanner.
- Label lokasi peta: **Checkpoint terkonfirmasi**, sesuai bukti waktu yang tersedia.

### Pedoman visual

- Latar putih/slate, border tipis, ruang antar elemen yang cukup, ikon Lucide konsisten.
- Teks isi sekitar 13-14 px dan kontras yang jelas; minimalis tetap mudah dibaca.
- Warna seperlunya untuk status, disertai teks agar makna tidak bergantung pada warna.
- Form menampilkan field yang diperlukan pada langkah tersebut; data SO/Customer diisi otomatis.
- State loading, kosong, data belum lengkap, dan gagal memuat terlihat jelas. Retry menggunakan aksi singkat di area terkait.
- Layout responsif: tabel/panel berdampingan pada desktop dan detail bertumpuk pada layar kecil.

## 8. Peta dan routing

- Gunakan Leaflet dan tile OSM yang sudah terpasang, dengan atribusi terlihat dan pemuatan tile normal sesuai viewport.
- Gunakan OSRM Route API untuk garis jalan mengikuti urutan stop. Pengurutan stop mengikuti rencana petugas.
- Sediakan konfigurasi base URL OSRM pada server dan panduan deployment self-hosted dengan data OSM wilayah operasional. Lisensi software terbuka; kapasitas server dan wilayah extract ditentukan saat deployment.
- Routing dipanggil dari backend dan di-cache berdasarkan profil, titik asal, urutan koordinat stop, serta konfigurasi layanan. Refresh visited cukup memperbarui marker/progres tanpa menghitung ulang jalur yang sama.
- Ketika layanan routing belum tersedia/gagal, peta tetap menampilkan titik valid dan pesan **Rute jalan belum tersedia**. Tampilkan tombol coba lagi.
- Garis diberi label **Rute rencana**. Warna kunjungan diterapkan pada marker, sehingga kunjungan di luar urutan tidak dianggap sebagai bukti kendaraan melewati suatu ruas jalan.
- Batasi timeout/jumlah titik sesuai layanan. Handle koordinat tidak lengkap dan dua stop dengan lokasi sama tanpa kehilangan relasi DN.
- Viewport awal mengikuti company atau titik trip, kemudian fit bounds. Titik origin/checkpoint selalu berasal dari lokasi yang sudah diatur.

## 9. Tahapan implementasi

### Tahap 1 - Fondasi data monitoring

- [x] Verifikasi metadata situs untuk field lokasi dan keberangkatan yang ekuivalen.
- [x] Tambahkan field Customer, Company, dan snapshot/aktual trip melalui setup idempotent.
- [x] Bangun pembaca visited dan waktu konfirmasi dari Scanner Scan History.
- [x] Ganti koordinat demo pada API peta dengan sumber lokasi nyata dan state data belum lengkap.
- [x] Terapkan company berasal dari SO/DN serta validasi kesesuaian company pada trip.

### Tahap 2 - Pemrosesan SO menjadi DN

- [x] Tambahkan daftar/ringkasan SO untuk proses pengiriman penuh.
- [x] Gunakan mapper native dan submit atomik dengan proteksi duplikasi/retry.
- [x] Tampilkan validasi ERPNext dan kebutuhan field wajib pada form yang ringkas.

### Tahap 3 - Trip dan peta

- [x] Lengkapi penyusunan trip, pin Customer/Company, serta snapshot koordinat.
- [x] Terapkan usulan Berangkat dengan waktu aktual dan status monitoring yang konsisten.
- [x] Tambahkan konfigurasi/deployment OSRM, cache rute, dan polyline jalan.
- [x] Tampilkan checkpoint, waktu konfirmasi, serta catatan existing per stop.

### Tahap 4 - Penyederhanaan UI

- [ ] Susun navigasi Dashboard, Pesanan, Perjalanan, dan Pengaturan.
- [ ] Pertahankan pilihan/filter Armada Sendiri dan Ekspedisi pada Pesanan serta metode yang tersimpan pada DN existing.
- [ ] Jadikan tabel trip sebagai pusat monitoring dengan panel detail dan peta rute terpilih.
- [ ] Tambahkan pembaruan berkala, filter company/status, dan state kosong/error.
- [ ] Rapikan label, ukuran teks, dan layout responsif sesuai pedoman minimalis.

### Tahap 5 - Verifikasi dan rilis

- [ ] Uji SO penuh menjadi satu DN submitted; error stok/batch dari ERPNext membatalkan transaksi secara benar.
- [ ] Uji request ganda/bersamaan, SO yang sudah diproses, dan DN yang sudah terikat trip.
- [ ] Verifikasi kedua pilihan metode tetap tersedia, pilihan tersimpan pada DN, dan DN Ekspedisi ditolak dari trip armada sendiri tanpa mengubah metodenya.
- [ ] Uji data company terpisah serta hak baca/tulis/submit sesuai ERPNext pada semua endpoint baru atau diubah.
- [ ] Uji start sebelum checkpoint pertama, klik Berangkat ulang, serta trip cancelled/completed.
- [ ] Uji scan berurutan, di luar urutan, scan ulang, visited tanpa riwayat, dan waktu konfirmasi yang tidak lengkap.
- [ ] Uji pin tersimpan/pakai ulang, perubahan master setelah trip dibuat, koordinat kosong, dan koordinat nol yang valid.
- [ ] Uji peta saat OSRM tersedia/tidak tersedia, dua stop satu lokasi, dan snapshot asal dari company yang benar.
- [ ] Uji filter/status/KPI konsisten, panel detail, pembaruan data, dan layout desktop/mobile.
- [ ] Build produksi frontend, verifikasi endpoint/halaman pada site, lalu commit perubahan yang sudah layak tanpa push.

Pengujian otomatis diprioritaskan untuk transaksi DN, validasi company/penugasan trip, dan derivasi checkpoint. Perubahan tampilan sederhana diverifikasi melalui build dan pemeriksaan antarmuka.

## 10. Hal yang dilengkapi saat implementasi

1. Pin keberangkatan setiap Company serta pin Customer yang belum terisi.
2. Ketersediaan Scanner Scan History pada site dan kecukupan log untuk trip historis.
3. Resource server, wilayah data OSM, dan endpoint OSRM untuk deployment.
4. Usulan Berangkat oleh admin dan catatan kendala pada bagian 4 tetap merupakan default rancangan sampai ada informasi operasional tambahan.
5. Finalisasi alur ekspedisi, termasuk layanan, input resi, integrasi, dan tampilan monitoringnya, dibahas terpisah setelah kebutuhan operasionalnya jelas.

Plan ini menjadi arah pengembangan lanjutan dari `plan.md`, dengan prioritas monitoring armada sendiri sesuai diskusi terbaru.
