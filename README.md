# MamiCoach
> [!Note]
> **Anggota Kelompok PBP E02**:
> - Galih Nur Rizqy (2406343224)
> - Kevin Cornellius Widjaja (2406428781)
> - Natan Harum Panogu Silalahi (2406496170)
> - Vincent Valentino Oei (2406353225)
> - Vincentius Filbert Amadeo (2406351711)


### Table of Contents
* [Anggota Kelompok](#MamiCoach)
* [Deskripsi Aplikasi](#Deskripsi-Aplikasi)
* [Penggunaan](#Penggunaan)
* [Daftar Modul](#Daftar-Modul)
* [ERD](#ERD)
* [Sumber Data](#Sumber-Data)
* [Peran Pengguna](#Peran-Pengguna)
* [Link Deployment dan Design](#Link-Deployment--Design)


## Deskripsi Aplikasi
$${\color{green}\textbf{Mami}}\textbf{Coach}$$ adalah platform yang menghubungkan pelatih profesional dengan pengguna yang ingin belajar langsung dari ahlinya. Kami memfasilitasi jual beli kelas online dengan sistem rating, review, dan verifikasi pelatih untuk memastikan kredibilitas. 

Pengguna dapat menemukan pelatih berkualitas, membeli kelas, dan berinteraksi langsung, sementara pelatih dapat membangun reputasi, mengelola murid, dan mengembangkan bisnisnya. MamiCoach menciptakan ekosistem belajar yang transparan, terpercaya, dan berorientasi pada hasil nyata.


---

## Penggunaan
Pastikan terlebih dahulu bahwa anda telah melakukan instalasi python pada device anda. Pastikan juga anda telah menduplikat file `.env.example` ke `.env`, serta mengisi file tersebut dengan environment variables yang sesuai dengan keperluan anda.

Kemudian jika OS anda adalah windows, jalankan:
```ps
.\setup.bat
```

Jika OS anda UNIX based, seperti linux, jalankan:
```
./setup.sh
```


## Daftar Modul
| **Module Name** | **Description of Features** | **Delegated Unit** |
| -- | -- | -- |
| Authentication & User Management | Semua hal terkait akun, login, role, dan akses.<br><br>**Fitur:**<br>- Registrasi User & Coach<br>- Login / Logout (menggunakan Django Auth)<br>- Role-based access control (User, Coach, Admin)<br>- Verifikasi akun Coach oleh Admin<br>- Profile page (edit data pribadi, hanya terlihat oleh user login)<br>- Template: `register.html`, `login.html`, `profile.html`<br>- AJAX untuk validasi username/email<br>- Model:<br>  - `User` (extend `AbstractUser`)<br>  - `CoachProfile` (OneToOne → User)<br>  - `AdminVerification` | Anggota 1 |
| Class & Coach Management | Manajemen kelas dan profil coach.<br><br>**Fitur:**<br>- Coach membuat, mengedit, dan menghapus kelas.<br>- Tampilkan daftar semua kelas + filter (olahraga, harga, level).<br>- Detail halaman kelas (coach, deskripsi, harga, rating).<br>- Upload sertifikasi (untuk verifikasi coach).<br>- Admin memverifikasi sertifikat → beri badge *Verified Coach*.<br>- Template: `class_list.html`, `class_detail.html`, `coach_list.html`<br>- AJAX filter kelas per kategori olahraga.<br>- Model:<br>  - `SportClass`<br>  - `Certification`<br>  - `VerifiedCoachBadge` | Kevin Cornellius Widjaja [2406428781] |
| Booking & Schedule | Proses booking kelas, pemilihan jadwal, dan status.<br><br>**Fitur:**<br>- Form booking (pilih kelas, tanggal, jam).<br>- Filter kelas berdasarkan hari & coach.<br>- Dashboard user: daftar booking (Pending, Confirmed, Done).<br>- Dashboard coach: daftar sesi masuk.<br>- AJAX update status (coach → Confirmed/Done/Canceled).<br>- Model:<br>  - `Booking` (`user`, `coach`, `class`, `date`, `status`)<br>  - `ScheduleSlot` (slot waktu yang ditawarkan coach) | Anggota 3 |
| Payment System | Simulasi atau integrasi gateway (Xendit sandbox).<br><br>**Fitur:**<br>- Generate invoice (via Xendit API atau dummy page).<br>- Status pembayaran (`Pending`, `Paid`).<br>- Webhook handler (jika pakai sandbox).<br>- Tampilan riwayat transaksi user.<br>- Template: `payment_page.html`, `payment_success.html`<br>- AJAX update status payment otomatis setelah webhook.<br>- Model:<br>  - `Payment` (booking_id, amount, status, method, timestamp) | Vincentius Filbert Amadeo [2406351711] |
| Chat & Review | Interaksi & feedback user terhadap coach.<br><br>**Fitur:**<br>- Real-time chat sederhana (AJAX polling).<br>- Chat hanya terbuka jika user sudah booking kelas.<br>- Setelah kelas selesai → form review (rating + komentar).<br>- Tampilkan review di halaman kelas dan profil coach.<br>- Template: `chat.html`, `review_form.html`, `reviews_section.html`<br>- Model:<br>  - `ChatMessage`<br>  - `Review` (rating, komentar, user, class, coach) | Vincent Valentino Oei [2406353225] |



## ERD
![ERD](./assets/erd.svg)
[ERD Link](https://dbdiagram.io/d/68e6390fd2b621e422d55017)


## Sumber Data
[Superprof.id](https://www.superprof.co.id/)
All data source are curated, obtained, and modified manually to fit data needs for this project. 


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


## Link Deployment & Design
- [Link Deployment](https://kevin-cornellius-mamicoach.pbp.cs.ui.ac.id/)
- [Link Figma](https://www.figma.com/design/Ysa8K8heNxQcG8eyjdRAXD/TK-PBP-E02?node-id=0-1&t=q5cEKERHtkHz8QlB-1)
