# MamiCoach
> [!Note]
> **Anggota Kelompok PBP E02**:
> - Galih Nur Rizqy (2406343224)
> - Kevin Cornellius Widjaja (2406428781)
> - Natan Harum Panogu Silalahi (2406496170)
> - Vincent Valentino Oei (2406353225)
> - Vincentius Filbert Amadeo (2406351711)


### Table of Contents
- [MamiCoach](#mamicoach)
    - [Table of Contents](#table-of-contents)
  - [Deskripsi Aplikasi](#deskripsi-aplikasi)
  - [Penggunaan](#penggunaan)
  - [Daftar Modul](#daftar-modul)
  - [ERD](#erd)
  - [Sumber Data](#sumber-data)
  - [Peran Pengguna](#peran-pengguna)
    - [1. Pengguna (User)](#1-pengguna-user)
    - [2. Pelatih (Coach)](#2-pelatih-coach)
    - [3. Admin](#3-admin)
  - [Link Deployment \& Design](#link-deployment--design)


## Deskripsi Aplikasi
$${\color{green}\textbf{Mami}}\textbf{Coach}$$ adalah platform yang menghubungkan pelatih profesional dengan pengguna yang ingin belajar langsung dari ahlinya. Kami memfasilitasi jual beli kelas online dengan sistem rating, review, dan verifikasi pelatih untuk memastikan kredibilitas. 

Pengguna dapat menemukan pelatih berkualitas, membeli kelas, dan berinteraksi langsung, sementara pelatih dapat membangun reputasi, mengelola murid, dan mengembangkan bisnisnya. MamiCoach menciptakan ekosistem belajar yang transparan, terpercaya, dan berorientasi pada hasil nyata.


---

## Penggunaan

### 1. Setup Awal

#### Prerequisites:
- Python 3.8+ sudah terinstall
- pip (Python package manager)
- Git

#### Langkah-langkah Setup:

**Step 1: Clone Repository**
```bash
git clone https://github.com/pbp-kelompok-e02/mamicoach.git
cd mamicoach
```

**Step 2: Buat Virtual Environment**
```bash
# Windows
python -m venv env
env\Scripts\activate

# macOS / Linux
python3 -m venv env
source env/bin/activate
```


**Step 3: Install Dependencies**
```bash
pip install -r requirements.txt
```

**Step 4: Jalankan Migrasi Database**
```bash
python manage.py makemigrations
python manage.py migrate
```

**Step 5: Load Sample Data**
```bash
python manage.py populate_all
```

**Step 6: Buat Superuser (Admin)**
```bash
python manage.py createsuperuser
```

**Otomatis Setup (Quick Start):**

Jika OS anda adalah Windows, jalankan:
```ps
.\setup.bat
```

Jika OS anda UNIX based (macOS/Linux), jalankan:
```bash
chmod +x setup.sh
./setup.sh
```

Script ini akan otomatis melakukan semua langkah di atas.

### 2. Menjalankan Aplikasi
```bash
python manage.py runserver
```

Aplikasi akan tersedia di `http://localhost:8000/`

### 3. Login & Registrasi
- **Register User Baru:** Akses halaman registrasi untuk membuat akun sebagai User atau Coach
- **Login:** Gunakan username dan password untuk login ke aplikasi
- **Verifikasi Coach:** Jika register sebagai coach, tunggu verifikasi dari admin

### 4. Navigasi Aplikasi

#### Sebagai User (Pengguna):
1. **Dashboard Home** - Lihat daftar semua kelas yang tersedia
2. **Cari & Filter Kelas** - Gunakan filter untuk mencari kelas berdasarkan kategori, harga, atau rating
3. **Detail Kelas** - Klik kelas untuk melihat detail, deskripsi, jadwal, dan review dari coach
4. **Book Kelas** - Pilih tanggal dan waktu yang tersedia untuk membooking kelas
5. **Pembayaran** - Lakukan pembayaran melalui gateway yang tersedia
6. **Chat dengan Coach** - Setelah booking, bisa berkomunikasi dengan coach melalui fitur chat
7. **Beri Review** - Setelah kelas selesai, berikan rating dan review untuk coach

#### Sebagai Coach (Pelatih):
1. **Dashboard Coach** - Lihat overview murid, kelas, dan earnings
2. **Kelola Kelas** - Buat kelas baru, edit, atau hapus kelas
3. **Jadwal Ketersediaan** - Atur jadwal ketersediaan untuk sesi coaching
4. **Kelola Booking** - Lihat daftar booking dari murid, ubah status (Confirmed/Done/Canceled)
5. **Chat dengan Murid** - Berkomunikasi dengan murid sebelum dan sesudah kelas
6. **Lihat Review** - Monitoring rating dan review dari murid

#### Sebagai Admin:
1. **Admin Dashboard** - Lihat overview aplikasi
2. **Verifikasi Coach** - Review dan verifikasi akun coach baru
3. **Kelola Pengguna** - Lihat dan manage daftar semua pengguna
4. **Monitor Pembayaran** - Pantau transaksi dan status pembayaran

### 5. Fitur Utama

**Booking & Schedule:**
- Pilih kelas dan tanggal yang sesuai
- Lihat ketersediaan real-time dari coach
- Konfirmasi booking dan lanjut ke pembayaran

**Payment:**
- Proses pembayaran melalui Midtrans/gateway
- Lihat riwayat transaksi
- Invoice otomatis dikirim setelah pembayaran

**Chat & Komunikasi:**
- Real-time chat dengan coach/murid
- Chat hanya bisa diakses setelah booking
- History chat tersimpan

**Review & Rating:**
- Beri rating 1-5 bintang
- Tulis review/feedback
- Lihat review dari pengguna lain


### 6. Panduan Singkat Simulasi Pembayaran dengan Midtrans
Lakukan penjadwalan course pada aplikasi mamicoach, setelah anda mengkonfirmasi booking maka anda akan diarahkan ke laman pemilihan metode pembayaran, disini anda dapat memilih metode pembayaran yang anda inginkan dan melanjutkan pembayaran. 
Setelah sampai pada laman pembayaran milik midtrans, copy nomor virtual account atau identifier pembayaran lainnya yang tersedia pada laman tersebut. 
Selanjutnya anda dapat membuka website [simulator.sandbox.midtrans.com](https://simulator.sandbox.midtrans.com/) dan anda dapat memilih metode pembayaran yang sesuai seperti yang dipilih sebelumnya dan mensimulasikan payment. Setelah itu, anda dapat menekan `Refresh Status` pada laman payment milik midtrans dimana pembayaran anda akan terselesaikan dan anda akan diarahkan kembali ke mamicoach.

## Daftar Modul
| **Module Name** | **Description of Features** | **Delegated Unit** |
| -- | -- | -- |
| Authentication & User Management | Semua hal terkait akun, login, role, dan akses.<br><br>**Fitur:**<br>- Registrasi User & Coach<br>- Login / Logout (menggunakan Django Auth)<br>- Role-based access control (User, Coach, Admin)<br>- Verifikasi akun Coach oleh Admin<br>- Profile page (edit data pribadi, hanya terlihat oleh user login)<br>- Template: `register.html`, `login.html`, `profile.html`<br>- AJAX untuk validasi username/email<br>- Model:<br>  - `CoachProfile` <br>  - `UserProfile` <br>  - `AdminVerification` | Natan Harum Panogu Silalahi [2406496170] |
| Class & Coach Management | Manajemen kelas dan profil coach.<br><br>**Fitur:**<br>- Coach membuat, mengedit, dan menghapus kelas.<br>- Tampilkan daftar semua kelas + filter (olahraga, harga, level).<br>- Detail halaman kelas (coach, deskripsi, harga, rating).<br>- Upload sertifikasi (untuk verifikasi coach).<br>- Admin memverifikasi sertifikat → beri badge *Verified Coach*.<br>- Template: `class_list.html`, `class_detail.html`, `coach_list.html`<br>- AJAX filter kelas per kategori olahraga.<br>- Model:<br>  - `Course`<br>  - `Category`<br> | Kevin Cornellius Widjaja [2406428781] |
| Booking & Schedule | Proses booking kelas, pemilihan jadwal, dan status.<br><br>**Fitur:**<br>- Form booking (pilih kelas, tanggal, jam).<br>- Filter kelas berdasarkan hari & coach.<br>- Dashboard user: daftar booking (Pending, Confirmed, Done).<br>- Dashboard coach: daftar sesi masuk.<br>- AJAX update status (coach → Confirmed/Done/Canceled).<br>- Model:<br>  - `Booking` (`user`, `coach`, `class`, `date`, `status`)<br>  - `ScheduleSlot` (slot waktu yang ditawarkan coach) | Galih Nur Rizqy [2406343224] |
| Payment System | Simulasi atau integrasi gateway (Xendit sandbox).<br><br>**Fitur:**<br>- Generate invoice (via Xendit API atau dummy page).<br>- Status pembayaran (`Pending`, `Paid`).<br>- Webhook handler (jika pakai sandbox).<br>- Tampilan riwayat transaksi user.<br>- Template: `payment_page.html`, `payment_success.html`<br>- AJAX update status payment otomatis setelah webhook.<br>- Model:<br>  - `Payment` (booking_id, amount, status, method, timestamp)<br>- Admin page untuk konfirmasi pembayaran ke coach dan refund ke user | Vincentius Filbert Amadeo [2406351711] |
| Chat & Review | Interaksi & feedback user terhadap coach.<br><br>**Fitur:**<br>- Real-time chat sederhana (AJAX polling).<br>- Chat hanya terbuka jika user sudah booking kelas.<br>- Setelah kelas selesai → form review (rating + komentar).<br>- Tampilkan review di halaman kelas dan profil coach.<br>- Template: `chat.html`, `review_form.html`, `reviews_section.html`<br>- Model:<br>  - `ChatMessage`<br> - `ChatSession`<br>  - `Review` (rating, komentar, user, class, coach) | Vincent Valentino Oei [2406353225] |



## ERD
[ERD Link](https://dbdiagram.io/d/68e6390fd2b621e422d55017)
> [!Note]
> Subject to Change

## Sumber Data
[Superprof.id](https://www.superprof.co.id/)

Data yang telah discrape:
- [Coaches](./dataset/main_coach.csv)
- [Courses](./dataset/main_course.csv)

> [!Note]
> Semua sumber data dikurasi, diperoleh, dan dimodifikasi secara manual untuk menyesuaikan kebutuhan data dalam proyek ini.


## Peran Pengguna

### 1. Pengguna (User)
Peran ini ditujukan untuk individu yang ingin belajar dan mengembangkan keterampilan baru. Mereka adalah konsumen utama di platform Mamicoach.

**Deskripsi & Hak Akses:**
- **Mencari & Menemukan:** Dapat menjelajahi semua kategori, mencari pelatih, dan memfilter kelas berdasarkan subjek, rating, atau harga.
- **Membeli Kelas:** Dapat melakukan transaksi pembelian kelas yang diminati.
- **Mengikuti Kelas:** Memiliki akses ke materi kelas yang sudah dibeli dan dapat berinteraksi dengan pelatih.
- **Memberi Rating & Review:** Setelah menyelesaikan kelas, mereka dapat memberikan penilaian dan ulasan yang akan terlihat oleh publik untuk membantu pengguna lain.

---

### 2. Pelatih (Coach)
Peran ini untuk para profesional atau ahli di bidangnya yang ingin membagikan ilmunya dan membangun bisnis pelatihan secara online.

**Deskripsi & Hak Akses:**
- **Profil Terverifikasi:** Memiliki halaman profil publik yang menampilkan keahlian, pengalaman, dan portofolio setelah melewati proses verifikasi oleh Mamicoach.
- **Membuat & Mengelola Kelas:** Dapat membuat, mengedit, dan mempublikasikan kelas online, termasuk menentukan kurikulum, harga, dan jadwal.
- **Mengelola Murid:** Dapat melihat daftar murid yang terdaftar di kelasnya, berinteraksi, dan memantau kemajuan mereka.
- **Membangun Reputasi:** Menerima rating dan review dari murid, yang akan membangun kredibilitas dan reputasi mereka di platform.


### 3. Admin
Peran ini untuk pengelola platform yang bertanggung jawab menjaga kualitas, keamanan, dan operasional MamiCoach. Berdasarkan pembagian modul, Admin memiliki akses dan tugas spesifik untuk memastikan platform berjalan lancar.

**Deskripsi & Hak Akses:**
- **Verifikasi Pelatih:** Meninjau pendaftaran pelatih baru, memverifikasi sertifikat yang diunggah, dan memberikan status "Verified Coach" untuk menjaga kredibilitas platform.
- **Manajemen Pembayaran:** Mengelola alur keuangan, termasuk mengonfirmasi pembayaran dari pengguna dan meneruskan pembayaran (*payout*) kepada pelatih.
- **Manajemen Pengembalian Dana (Refund):** Memproses dan menyetujui permintaan pengembalian dana dari pengguna sesuai dengan kebijakan yang berlaku.


## Link Deployment & Design
- [Link Deployment](https://kevin-cornellius-mamicoach.pbp.cs.ui.ac.id/)
- [Link Figma](https://www.figma.com/design/Ysa8K8heNxQcG8eyjdRAXD/TK-PBP-E02?node-id=0-1&t=q5cEKERHtkHz8QlB-1)
