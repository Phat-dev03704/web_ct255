# 🚀 QUICK START - Hướng Dẫn Nhanh

Cài đặt và chạy dự án trong **5 phút**!

---

## ⚡ BƯỚC 1: Cài Python Packages (2 phút)

```bash
cd flask_app
pip install Flask==3.0.0 Flask-SQLAlchemy PyMySQL cryptography bcrypt python-dotenv ortools
```

---

## ⚡ BƯỚC 2: Setup Database (2 phút)

```bash
# Tạo database và import dữ liệu
mysql -u root < schema.sql
mysql -u root vrp_system < seed_data.sql

# Fix encoding tiếng Việt
mysql -u root -e "ALTER DATABASE vrp_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

**Nếu dùng XAMPP:**
```powershell
D:\AppForLearn\xamppInstall\mysql\bin\mysql.exe -u root < schema.sql
Get-Content seed_data.sql | D:\AppForLearn\xamppInstall\mysql\bin\mysql.exe -u root vrp_system
```

---

## ⚡ BƯỚC 3: Chạy App (30 giây)

```bash
python app.py
```

Truy cập: **http://localhost:5000**

---

## 🔑 Đăng Nhập

**Admin:**
- Email: `admin@vrp.com`
- Pass: `admin123`

**Tài xế:**
- User: `TX001`
- Pass: `123456`

**Khách hàng:**
- Email: `khach1@example.com`
- Pass: `123456`

---

## 🆘 Lỗi Thường Gặp

**Lỗi import package:**
```bash
pip install <package-name>
```

**Lỗi database:**
```bash
# Import lại
mysql -u root < schema.sql
```

**Port 5000 bị chiếm:**
```bash
# Tìm và kill process
netstat -ano | findstr :5000
taskkill /PID <pid> /F
```

---

✅ **Xong! Bắt đầu sử dụng hệ thống VRP!**
