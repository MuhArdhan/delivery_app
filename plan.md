# 🚚 Blueprint & Plan: Reverse-Engineering Fleetbase ke Frappe ERPNext (`delivery_app`)

Dokumen ini membedah (*reverse-engineer*) konsep, arsitektur data, dan workflow dari sistem operasi logistik **[Fleetbase](https://github.com/fleetbase/fleetbase)** (khususnya modul **Fleet-Ops**) untuk di-porting menjadi aplikasi native Frappe **`delivery_app`** yang terintegrasi erat dengan dokumen standar ERPNext: **`Delivery Note`** dan **`Delivery Trip`**.

---

## 1. Matriks Reverse-Engineering (Fleetbase ➔ ERPNext / `delivery_app`)

Tabel pemetaan arsitektur dari modul **Fleet-Ops (Fleetbase)** ke ekosistem **Frappe / ERPNext**:

| Entitas Fleetbase (`fleetops`) | Padanan di ERPNext / `delivery_app` | Peran & Tanggung Jawab |
| :--- | :--- | :--- |
| **`Order` & `Payload`** | **`Delivery Note`** (ERPNext) + Custom Fields | Dokumen induk muatan: daftar barang pesanan, alamat tujuan, pelanggan, dan metode kirim. |
| **`Waypoint`** | **`Delivery Stop`** (Child Table di `Delivery Trip`) | Titik singgah pengiriman dalam suatu rute (*multi-drop*): alamat, urutan stop, estimasi kedatangan. |
| **`Proof`** | **`Proof of Delivery (POD)`** (`delivery_app`) | Bukti digital serah terima barang: foto di lokasi, tanda tangan digital penerima, dan koordinat GPS. |
| **`IntegratedVendor`** | **`Delivery Gateway Settings`** (`delivery_app`) | Konfigurasi kurir pihak ketiga / 3PL (Biteship API / Ekspedisi) untuk cek status resi eksternal. |
| **`TrackingNumber` & `TrackingStatus`** | Field `waybill_no`, `tracking_status`, & Timeline HTML di DN | Mesin pelacakan status dan riwayat tahapan pengiriman paket. |
| **`Driver` & `Vehicle`** | **`Driver` & `Vehicle`** (ERPNext) | Manajemen armada internal dan penugasan pengemudi. |
| **`Route` & OSRM Engine** | Rute optimasi bawaan `Delivery Trip` / OSRM | Pengurutan titik antar (*waypoint re-ordering*) dan estimasi jarak/waktu tempuh. |
| **`Navigator App`** (Driver UI) | **Driver Mobile Portal (`/driver`)** (`delivery_app`) | Antarmuka mobile pengemudi: melihat trip hari ini, navigasi maps, dan submit bukti serah terima (POD). |

---

## 2. Arsitektur Dua Alur Pengiriman (Dual-Flow)

```text
                           [Sales Order / Sales Invoice]
                                         │
                                         ▼
                            [Delivery Note] (ERPNext)
                      [Pilih Delivery Method di Header DN]
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
      [Alur A: Ekspedisi (3PL)]                   [Alur B: Armada Sendiri]
   (Reverse: IntegratedVendor & Waybill)      (Reverse: Waypoint, Dispatch & Proof)
                   │                                           │
         Input Ekspedisi & No. Resi                  Digabung ke [Delivery Trip]
         (JNE, J&T, SiCepat, dll.)                   (Rute Multi-Drop & Penugasan Supir)
                   │                                           │
         Sinkronisasi API Lacak                      Supir Buka [Driver Mobile Portal: /driver]
         (Biteship Public Tracking)                  (Lihat Daftar Antar & Navigasi)
                   │                                           │
         Timeline Update Otomatis                    Sampai di Tujuan: Ambil Bukti
         (Draft ➔ In Transit ➔ Delivered)            (Foto Barang + TTD + Tag GPS)
                   │                                           │
                   ▼                                           ▼
         [Delivery Note Selesai]                     [Submit Proof of Delivery (POD)]
                                                               │
                                                               ▼
                                                     Delivery Stop ditandai 'Visited = 1'
                                                     Delivery Note ditandai 'Delivered'
                                                     Delivery Trip otomatis 'Completed'
```

---

## 3. Spesifikasi Rancang Bangun Teknis

### A. Alur Ekspedisi (3PL Courier Integration)
*Diadopsi dari konsep `IntegratedVendor` dan `TrackingNumber` di Fleetbase.*

1. **DocType `Delivery Gateway Settings` (Single):**
   * Menyimpan API Key (Biteship), mode Sandbox/Live, status aktif.
   * Auto-polling scheduler toggle & frekuensi pengecekan resi.
   * Whitelisted test connection endpoint: `delivery_app.services.biteship.test_connection`.
2. **Custom Fields di `Delivery Note`:**
   * `custom_delivery_method`: Select (`Armada Sendiri`, `Ekspedisi`) — *default: Armada Sendiri*.
   * `custom_courier_code`: Select (JNE, J&T, SiCepat, Anteraja, Ninja, Pos Indonesia, Sentral Cargo, dll.).
   * `custom_waybill_no`: Data (Nomor Resi / AWB).
   * `custom_tracking_status`: Read Only (`Pending`, `In Transit`, `Delivered`, `Returned`, `Failed`).
   * `custom_last_tracking_update`: Datetime.
   * `custom_tracking_history_html`: HTML (Timeline perjalanan paket seperti di Fleetbase).
3. **Client Script (`delivery_note.js`):**
   * Tombol **"Lacak Resi"** untuk memicu fetch live status ke Biteship dan menampilkan popup modal riwayat perjalanan.
4. **Background Task Scheduler (`hooks.py`):**
   * Cron job otomatis untuk memperbarui resi yang masih aktif (`In Transit`).

---

### B. Alur Armada Sendiri & Proof of Delivery (POD)
*Diadopsi dari konsep `Payload`, `Waypoint`, `Proof`, dan `Navigator App` di Fleetbase.*

1. **DocType `Proof of Delivery` (POD):**
   * `delivery_note`: Link `Delivery Note`.
   * `delivery_trip`: Link `Delivery Trip`.
   * `delivery_stop`: Data / Baris Stop.
   * `recipient_name`: Data (Nama yang menerima barang).
   * `recipient_relationship`: Select (Yang Bersangkutan, Keluarga, Satpam/Resepsionis, Rekan Kerja, Lainnya).
   * `proof_photo`: Attach Image (Foto barang diserahkan di lokasi).
   * `signature`: Signature (Kanvas tanda tangan digital penerima).
   * `latitude` & `longitude`: Float (Geotag otomatis dari GPS perangkat saat serah terima).
   * `submitted_at`: Datetime.
   * `notes`: Small Text.
2. **Koneksi ke `Delivery Trip` & `Delivery Stop` (ERPNext):**
   * Begitu POD disubmit:
     * Baris stop di `Delivery Trip` di-update: `visited = 1`.
     * `Delivery Note` terkait di-update: status POD menjadi `Delivered` dan tautan dokumen POD disimpan.
     * Evaluasi otomatis: Jika semua stop sudah `visited = 1`, maka `Delivery Trip` otomatis ditandai `Completed`.
3. **Driver Mobile Portal (`/driver`):**
   * Rute: `/driver` (Akses responsif smartphone untuk pengemudi).
   * Fitur:
     * Menampilkan Trip aktif hari ini untuk supir yang login.
     * Kartu per tujuan pengantaran (Nama Customer, Alamat, No. Telp / Tombol WhatsApp, Link Google Maps).
     * Tombol *\"Selesaikan Pengantaran\"* ➔ Membuka form modal kamera + tanda tangan + auto-capture GPS.

---

## 4. Status Eksekusi (Implementation Checklist)

### 📌 Milestone 1: Fondasi Skema & Custom Fields
- [x] Buat DocType **`Delivery Gateway Settings`** (Single DocType untuk API Key Biteship).
- [x] Buat DocType **`Proof of Delivery`** (Penyimpanan foto, tanda tangan, koordinat GPS, penerima).
- [x] Daftarkan **Custom Fields** pada `Delivery Note` dan `Delivery Stop` via `delivery_app/setup.py` (idempoten via `create_custom_fields`).
- [x] Atur visibility field di `delivery_note.js` (Form dinamis: tombol "Lacak Resi", "Input POD", dan "Lihat POD").

### 📌 Milestone 2: Modul Ekspedisi & Pelacakan Resi (Biteship)
- [x] Buat API client helper `delivery_app/services/biteship.py` (`fetch_biteship_tracking(waybill, courier)`).
- [x] Buat Whitelisted Method Frappe di Python untuk live tracking: `delivery_app.services.biteship.track_delivery_note`.
- [x] Buat render HTML timeline vertikal responsive terinspirasi antarmuka Fleetbase.
- [x] Tambahkan background task di `delivery_app.services.biteship.sync_active_shipments` & daftarkan di `hooks.py` scheduler.
- [x] Siapkan webhook receiver: `delivery_app.services.biteship.handle_webhook`.

### 📌 Milestone 3: Integrasi Armada Sendiri & Delivery Trip
- [x] Buat API method di backend untuk submit POD dari lapangan (`delivery_app.api.submit_pod`).
- [x] Integrasikan perubahan status otomatis ke `Delivery Stop.visited` dan `Delivery Trip.status = Completed`.
- [x] Validasi bisnis: Cegah `Delivery Note` bermetode `Ekspedisi` dimasukkan ke dalam `Delivery Trip` armada sendiri (`delivery_app.overrides.delivery_trip.validate_delivery_trip`).

### 📌 Milestone 4: Driver Mobile Portal (PWA / Web View)
- [x] Siapkan controller dan template halaman web supir `/driver` (`delivery_app/www/driver.py` & `driver.html`).
- [x] Terapkan komponen kanvas tanda tangan (*Signature Pad*) dan akses kamera dengan kompresi gambar otomatis di browser.
- [x] Terapkan Geolocation API HTML5 untuk membaca titik koordinat saat supir menyelesaikan antar.
- [x] Sediakan integrasi satu-klik navigasi Google Maps dan tombol WhatsApp langsung ke kontak pelanggan.

### 📌 Milestone 5: Pengujian & Validasi
- [x] Verifikasi schema database DocType dan Custom Fields pada site `development.localhost`.
- [x] Verifikasi compile asset bundle dan clear-cache.
- [x] Verifikasi response rendering template `/driver`.

### 📌 Milestone 6: Fleetbase Logistics Operations Console (Vue 3 + Vite SPA)
- [x] Inisialisasi frontend SPA `delivery_app/frontend` menggunakan Vue 3, Vite, Tailwind CSS, Leaflet.js, dan Lucide Icons.
- [x] Implementasi Command Center Dashboard (`DashboardView.vue`): KPI Cards, Live Operations Map (Leaflet) sebaran pengiriman & status armada, feed aktivitas terkini.
- [x] Implementasi Orders Dispatch Center (`DeliveryNotesView.vue`): filter status (Siap Kirim, In Transit, Terkirim, Semua), pencarian multi-parameter, multi-select batch dispatch.
- [x] Implementasi Modal Ekspedisi 3PL (`DispatchEkspedisiModal.vue`): pilihan 13 kurir Indonesia, hitung estimasi ongkir, input / generate otomatis nomor resi AWB, dispatch ke Biteship.
- [x] Implementasi Modal Rute Armada (`CreateTripModal.vue`): pilih Driver, Kendaraan, waktu berangkat, urutkan titik singgah (stops reordering) dengan tombol ▲ ▼.
- [x] Implementasi Modal Lacak Resi (`TrackingTimelineModal.vue`): timeline vertikal real-time dengan status checkpoint.
- [x] Implementasi Modal Bukti POD (`PodDetailModal.vue`): foto di lokasi, tanda tangan digital, tautan koordinat Google Maps.
- [x] Implementasi Slide-over Drawer (`DeliveryNoteDrawer.vue`): detail produk, pelanggan, kontak WhatsApp, riwayat logistik.
- [x] Implementasi Rute Pengiriman (`DeliveryTripsView.vue`): daftar trip, progress bar persentase selesai, aksi mulai trip, selesai trip, dan shortcut navigator supir.
- [x] Implementasi POD Hub (`PodGalleryView.vue`): galeri visual arsip tanda tangan & foto bukti serah terima.
- [x] Implementasi Fleet Resources (`FleetResourcesView.vue`): ringkasan pengemudi dan kendaraan aktif.
- [x] Implementasi Pengaturan Ekspedisi (`SettingsView.vue`): konfigurasi API Key Biteship, environment sandbox/live, background sync interval, uji koneksi API.
- [x] Routing Frappe www template `/delivery` (`delivery.py` & `delivery.html`) dengan CSRF token injection dan session protection.
- [x] Build produksi ke `delivery_app/public/console/` terverifikasi sukses (HTTP 200).

### 📌 Milestone 7: Minimalist UI Refactoring & Zero-Emoticon Standard
- [x] Audit komprehensif seluruh file frontend SPA, modal, drawer, leaflet map, driver portal, dan backend response untuk eliminasi 100% emoticon/emoji.
- [x] Penggantian seluruh ikon emoji menjadi Lucide SVG Icons (`lucide-vue-next`): `Truck`, `Package`, `Route`, `ShieldCheck`, `Users`, `Settings`, `Smartphone`, `Building2`, `ExternalLink`, `LogOut`, `MapPin`, `Activity`, `RefreshCw`, `Search`, `Calendar`, `Check`, `CheckCircle2`, `Send`, `Save`, `Zap`, `Plus`, `Play`, `ChevronUp`, `ChevronDown`, `ChevronLeft`, `ChevronRight`.
- [x] Overhaul desain antarmuka menjadi minimalis profesional: palet netral (slate/white), border tipis 1px presisi, tipografi restrained, penghilangan gradient berlebihan, serta Leaflet map marker pin minimalis bulat elegan.
- [x] Rebuild produksi Vite bundle dan verifikasi live loading di `/delivery` dan `/driver`.
