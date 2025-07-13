# 🪙 Octra Faucet Auto-Claimer

Skrip Python untuk mengklaim faucet dari **Octra Network** secara massal menggunakan banyak wallet secara otomatis. Mendukung input interaktif, retry otomatis, laporan hasil yang rapi, dan bisa mengulang hanya wallet yang gagal.

---

## 🔧 Fitur Utama

- ✅ Automasi klaim faucet dengan reCAPTCHA solver
- 🗂️ Multi-wallet (dari file teks di folder `wallets/`)
- 🔁 Retry otomatis untuk koneksi atau CAPTCHA gagal
- 📊 Laporan hasil sukses/gagal
- 🔄 Fitur ulangi hanya wallet yang gagal
- 🧹 Auto bersihkan `__pycache__`

---

## 📁 Struktur Folder

```
octra_faucet_claimer/
├── claim_faucet.py
├── wallets/
│   ├── wallet1NamaBebas.txt
│   ├── wallet2NamaBebas.txt
│   └── ...
```

**Contoh isi wallet file:**
```
Address: 0x1234567890abcdef1234567890abcdef12345678
```

---

## 🧠 Prasyarat

- Python 3.8+
- API key dari layanan solver captcha ([SolveCaptcha](https://solvecaptcha.com?from=480476))

---

## 🧪 Instalasi

1. **Clone repositori**

```bash
git clone https://github.com/username/octra-faucet-claimer.git
cd octra-faucet-claimer
```

2. **Buat environment (opsional tapi disarankan)**

```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependensi**

```bash
pip install -r requirements.txt
```

4. **Isi API Key di skrip**
> Buka `claim_faucet.py` dan ubah baris berikut:

```python
SOLVER_API_KEY: str = "ISI_API_KEY_ANDA_DI_SINI"
```

---

## 🚀 Cara Menjalankan

1. Masukkan file wallet `.txt` ke dalam folder `wallets/`
2. Jalankan skrip:

```bash
python claim_faucet.py
```

3. Pilih wallet yang ingin diproses dengan input seperti:
   - `1,2,5-7` → Untuk pilih wallet nomor 1,2,5,6,7
   - `semua` → Untuk proses semua wallet

---

## ⚠️ Catatan Penting

- Script ini **tidak menyimpan private key**.
- Setiap wallet akan diproses dengan delay ±1 menit untuk menghindari rate limit.
- Layanan CAPTCHA solver dapat memiliki biaya tambahan.

---

## 📄 Lisensi

Skrip ini dirilis dengan lisensi **MIT**.

---

## 🙏 Kontribusi

Pull request dan issue sangat diterima! Silakan fork dan kembangkan lebih lanjut.
