# 📦 HƯỚNG DẪN CÀI ĐẶT DỰ ÁN VRP SYSTEM

## 🔧 Yêu Cầu Hệ Thống

- **Python**: 3.8 trở lên
- **MySQL/MariaDB**: 5.7 trở lên (hoặc XAMPP)
- **Trình duyệt**: Chrome, Firefox, Edge (phiên bản mới)

---

## 📥 BƯỚC 1: Clone Dự Án

```bash
git clone <repository-url>
cd "Business Intelligence\code"
```

---

## 🐍 BƯỚC 2: Cài Đặt Python Dependencies

### Cài đặt cho Flask App (Web Interface):

```bash
cd flask_app
pip install -r requirements.txt
```

### Cài đặt cho Thuật toán VRP (nếu cần chạy riêng):

```bash
cd ..
pip install -r requirements.txt
```

**Các package chính:**
- Flask 3.0.0 (Web framework)
- Flask-SQLAlchemy (ORM)
- PyMySQL (MySQL connector)
- OR-Tools (VRP solver)
- bcrypt (Mã hóa mật khẩu)

---

## 🗄️ BƯỚC 3: Thiết Lập Database

### 3.1 Khởi động MySQL

**Nếu dùng XAMPP:**
```bash
# Khởi động MySQL từ XAMPP Control Panel
# hoặc
D:\AppForLearn\xamppInstall\mysql\bin\mysqld.exe
```

### 3.2 Tạo Database và Import Schema

```bash
cd flask_app

# Tạo database và bảng
mysql -u root < schema.sql

# Import dữ liệu mẫu
mysql -u root vrp_system < seed_data.sql
```

**Hoặc dùng MySQL CLI:**
```bash
D:\AppForLearn\xamppInstall\mysql\bin\mysql.exe -u root < schema.sql
Get-Content seed_data.sql | D:\AppForLearn\xamppInstall\mysql\bin\mysql.exe -u root vrp_system
```

### 3.3 Cấu Hình UTF-8 (quan trọng cho tiếng Việt)

```bash
mysql -u root -e "ALTER DATABASE vrp_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

---

## ⚙️ BƯỚC 4: Cấu Hình Môi Trường

### 4.1 Tạo file `.env` trong thư mục `flask_app`:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=vrp_system

# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Optional: OSRM Server (cho routing)
OSRM_SERVER=http://router.project-osrm.org
```

### 4.2 Kiểm tra kết nối database:

```bash
mysql -u root vrp_system -e "SELECT COUNT(*) FROM NGUOI_DUNG;"
```

---

## 🚀 BƯỚC 5: Chạy Ứng Dụng

### 5.1 Khởi động Flask Server:

```bash
cd flask_app
python app.py
```

### 5.2 Truy cập Web:

Mở trình duyệt và truy cập:
- **URL**: http://localhost:5000
- **Đăng nhập Admin**: 
  - Email: `admin@vrp.com`
  - Password: `admin123`

---

## 👥 TÀI KHOẢN MẪU

### Admin:
- Email: `admin@vrp.com`
- Password: `admin123`

### Tài xế:
- Username: `TX001`, `TX002`, `TX003`
- Password: `123456`

### Khách hàng:
- Email: `khach1@example.com`, `khach2@example.com`
- Password: `123456`

---

## 📂 CẤU TRÚC DỰ ÁN

```
code/
├── flask_app/              # Web application
│   ├── app.py             # Entry point
│   ├── models.py          # Database models
│   ├── routes.py          # API routes
│   ├── templates/         # HTML templates
│   ├── static/            # CSS, JS, images
│   ├── schema.sql         # Database schema
│   ├── seed_data.sql      # Sample data
│   └── requirements.txt   # Python packages
│
├── algorithm/             # VRP algorithms
│   ├── OR-Tools/          # OR-Tools solver
│   ├── GA/                # Genetic Algorithm
│   ├── Tabu/              # Tabu Search
│   └── ...
│
└── docs/                  # Documentation
    └── HUONG_DAN_CAI_DAT.md
```

---

## 🔍 KIỂM TRA CÀI ĐẶT

### 1. Kiểm tra Python packages:
```bash
pip list | findstr "Flask SQLAlchemy PyMySQL ortools bcrypt"
```

### 2. Kiểm tra database:
```bash
mysql -u root vrp_system -e "SHOW TABLES;"
```

### 3. Kiểm tra dữ liệu:
```bash
mysql -u root vrp_system -e "SELECT COUNT(*) FROM DON_HANG;"
mysql -u root vrp_system -e "SELECT COUNT(*) FROM TAI_XE;"
mysql -u root vrp_system -e "SELECT COUNT(*) FROM XE;"
```

### 4. Test Flask app:
```bash
curl http://localhost:5000
```

---

## ❌ XỬ LÝ LỖI THƯỜNG GẶP

### Lỗi: `ModuleNotFoundError: No module named 'xxx'`
**Giải pháp:**
```bash
pip install <tên-package>
```

### Lỗi: `Access denied for user 'root'@'localhost'`
**Giải pháp:**
- Kiểm tra MySQL đã chạy chưa
- Đặt lại mật khẩu root nếu cần
- Cập nhật file `.env` với thông tin đúng

### Lỗi: `Table 'vrp_system.xxx' doesn't exist`
**Giải pháp:**
```bash
# Import lại schema
mysql -u root < flask_app/schema.sql
mysql -u root vrp_system < flask_app/seed_data.sql
```

### Lỗi: Hiển thị tiếng Việt bị lỗi (??????)
**Giải pháp:**
```bash
# Đổi encoding database
mysql -u root -e "ALTER DATABASE vrp_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### Lỗi: Port 5000 đã được sử dụng
**Giải pháp:**
```bash
# Tìm và dừng tiến trình đang dùng port 5000
netstat -ano | findstr :5000
taskkill /PID <process-id> /F
```

---

## 🛠️ CÔNG CỤ HỮU ÍCH

### MySQL Command Line:
```bash
# Đăng nhập MySQL
mysql -u root -p

# Xem databases
SHOW DATABASES;

# Chọn database
USE vrp_system;

# Xem bảng
SHOW TABLES;

# Xem cấu trúc bảng
DESCRIBE DON_HANG;
```

### Flask Debug Mode:
Trong `app.py`, đặt:
```python
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

---

## 📞 HỖ TRỢ

- **Email**: support@vrp.com
- **Documentation**: `/docs`
- **GitHub Issues**: <repository-url>/issues

---

## 📝 GHI CHÚ

- **Backup database** thường xuyên trước khi thay đổi
- Đọc `README.md` để hiểu thêm về dự án
- Xem folder `algorithm/` để biết các thuật toán VRP khả dụng
- File `command_line/CLI_GUIDE.txt` có hướng dẫn sử dụng CLI

---

**Chúc bạn cài đặt thành công! 🎉**
