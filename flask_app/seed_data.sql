-- ================================================
-- SEED DATA FOR VRP SYSTEM
-- ================================================

USE `vrp_system`;

-- ================================================
-- 1. USER ACCOUNTS
-- ================================================

-- Mat khau mac dinh: "password123" (da hash voi bcrypt)
-- Trong production, nen hash mat khau bang bcrypt
INSERT INTO `USER` (`username`, `password`, `role`) VALUES
('admin', '$2b$12$.3kmlHLupvVysjttLybf.u1Y1ty4Mmdidz8yXvJIY/YUxca5ZpKoW', 'admin'),
('driver1', '$2b$12$.3kmlHLupvVysjttLybf.u1Y1ty4Mmdidz8yXvJIY/YUxca5ZpKoW', 'driver'),
('driver2', '$2b$12$.3kmlHLupvVysjttLybf.u1Y1ty4Mmdidz8yXvJIY/YUxca5ZpKoW', 'driver'),
('driver3', '$2b$12$.3kmlHLupvVysjttLybf.u1Y1ty4Mmdidz8yXvJIY/YUxca5ZpKoW', 'driver'),
('customer1', '$2b$12$.3kmlHLupvVysjttLybf.u1Y1ty4Mmdidz8yXvJIY/YUxca5ZpKoW', 'customer'),
('customer2', '$2b$12$.3kmlHLupvVysjttLybf.u1Y1ty4Mmdidz8yXvJIY/YUxca5ZpKoW', 'customer');

-- ================================================
-- 2. DRIVERS (TÀI XẾ)
-- ================================================

INSERT INTO `TAI_XE` (`MaTX`, `TenTX`, `DiaChi`, `SDT`, `BienSoXe`, `SucChua`, `username`, `TrangThai`) VALUES
('TX001', 'Nguyen Van An', 'Quan Ninh Kieu, Can Tho', '0901234567', '92A-12345', 100, 'driver1', 'available'),
('TX002', 'Tran Thi Binh', 'Quan Ninh Kieu, Can Tho', '0901234568', '92A-12346', 120, 'driver2', 'available'),
('TX003', 'Le Van Cuong', 'Quan Ninh Kieu, Can Tho', '0901234569', '92A-12347', 100, 'driver3', 'available');

-- ================================================
-- 3. PRODUCTS (SẢN PHẨM)
-- ================================================

INSERT INTO `SAN_PHAM` (`MaSP`, `TenSP`, `MoTa`, `TonKho`, `DonGia`, `DonVi`, `HinhAnh`, `TrangThai`) VALUES
('SP001', 'Apple', 'Fresh imported apple from USA, rich in vitamins', 500, 45000, 'kg', 'apple.png', 'active'),
('SP002', 'Mango', 'Hoa Loc mango specialty from Tien Giang, sweet and fragrant', 300, 60000, 'kg', 'mango.png', 'active'),
('SP003', 'Orange', 'Sanh orange from Ha Giang, sweet and juicy', 400, 35000, 'kg', 'orange.png', 'active'),
('SP004', 'Grape', 'Seedless green grape imported from Australia', 200, 120000, 'kg', 'grape.png', 'active'),
('SP005', 'Watermelon', 'Seedless watermelon from Long An, sweet and refreshing', 600, 15000, 'kg', 'watermelon.png', 'active'),
('SP006', 'Durian', 'Ri6 durian from Dak Lak, golden flesh, creamy', 150, 180000, 'kg', 'durian.png', 'active'),
('SP007', 'Mangosteen', 'Fresh mangosteen from Can Tho', 250, 50000, 'kg', 'mangosteen.png', 'active'),
('SP008', 'Rambutan', 'Sweet rambutan from Ben Tre', 300, 25000, 'kg', 'rambutan.png', 'active'),
('SP009', 'Dragon Fruit', 'Organic red dragon fruit from Long An', 400, 20000, 'kg', 'dragonfruit.png', 'active'),
('SP010', 'Pomelo', 'Green skin pomelo from Ben Tre, sweet with few seeds', 350, 30000, 'kg', 'pomelo.png', 'active');

-- ================================================
-- 4. CUSTOMERS (KHÁCH HÀNG) - Từ dữ liệu CSV
-- ================================================

-- DEPOT (Kho chính - DHCT)
INSERT INTO `NGUOI_DUNG` (`MaND`, `TenND`, `DiaChi`, `Lat`, `Lon`, `SDT`, `username`) VALUES
('DEPOT', 'Kho Trung Tâm - DHCT', 'Đại học Cần Thơ, Khu II, Ninh Kiều, Cần Thơ', 10.030874, 105.768299, '0292123456', NULL);

-- Khach hang tu file CSV (khong dau)
INSERT INTO `NGUOI_DUNG` (`MaND`, `TenND`, `DiaChi`, `Lat`, `Lon`, `SDT`, `username`) VALUES
('KH_1', 'Nguyen Van Anh', 'Duong 30/4, Ninh Kieu, Can Tho', 10.027113327, 105.766936541, '0901111001', NULL),
('KH_2', 'Tran Thi Bich', 'Duong Tran Hung Dao, Ninh Kieu, Can Tho', 10.026141870, 105.765166283, '0901111002', NULL),
('KH_3', 'Le Van Cuong', 'Duong Nguyen Van Cu, Ninh Kieu, Can Tho', 10.024419171, 105.765820742, '0901111003', NULL),
('KH_4', 'Pham Thi Dung', 'Duong Mau Than, Ninh Kieu, Can Tho', 10.021641388, 105.762612820, '0901111004', NULL),
('KH_5', 'Hoang Van Em', 'Duong Hoa Binh, Ninh Kieu, Can Tho', 10.022200710, 105.766839981, '0901111005', NULL),
('KH_6', 'Dang Thi Phuong', 'Duong Nguyen Thi Minh Khai, Ninh Kieu, Can Tho', 10.025400826, 105.771389008, '0901111006', NULL),
('KH_7', 'Vo Van Giang', 'Duong Tran Phu, Ninh Kieu, Can Tho', 10.027102121, 105.773341656, '0901111007', NULL),
('KH_8', 'Bui Thi Hong', 'Duong Ly Tu Trong, Ninh Kieu, Can Tho', 10.030640705, 105.775068998, '0901111008', NULL),
('KH_9', 'Dinh Van Ich', 'Duong Phan Dinh Phung, Ninh Kieu, Can Tho', 10.035427075, 105.770680904, '0901111009', NULL),
('KH_10', 'Truong Thi Kieu', 'Duong Cao Thang, Ninh Kieu, Can Tho', 10.037518762, 105.771796703, '0901111010', NULL),
('KH_11', 'Ngo Van Lam', 'Duong Le Loi, Ninh Kieu, Can Tho', 10.036600194, 105.773663521, '0901111011', NULL),
('KH_12', 'Huynh Thi Mai', 'Duong Nguyen Trai, Ninh Kieu, Can Tho', 10.033621974, 105.776259899, '0901111012', NULL),
('KH_13', 'Chau Van Nam', 'Duong Tran Quang Khai, Ninh Kieu, Can Tho', 10.032733086, 105.777890682, '0901111013', NULL),
('KH_14', 'Luong Thi Oanh', 'Duong Chau Van Liem, Ninh Kieu, Can Tho', 10.024799730, 105.776463747, '0901111014', NULL),
('KH_15', 'Mai Van Phong', 'Duong Hung Vuong, Ninh Kieu, Can Tho', 10.022802899, 105.773985386, '0901111015', NULL),
('KH_16', 'Do Thi Quynh', 'Duong Dien Bien Phu, Ninh Kieu, Can Tho', 10.022929062, 105.769350529, '0901111016', 'customer1'),
('KH_17', 'Phan Van Roi', 'Duong Nguyen An Ninh, Ninh Kieu, Can Tho', 10.021819587, 105.771335363, '0901111017', 'customer2');

-- ================================================
-- 5. SAMPLE ORDERS (ĐƠN HÀNG MẪU)
-- ================================================

-- Đơn hàng đang chờ xử lý (pending)
INSERT INTO `DON_HANG` (`MaDH`, `MaND`, `DiaChi`, `Lat`, `Lon`, `NgayTao`, `TrangThai`, `READY_TIME`, `DUE_DATE`, `SERVICE_TIME`, `GhiChu`) VALUES
('DH001', 'KH_1', 'Đường 30/4, Ninh Kiều, Cần Thơ', 10.027113327, 105.766936541, NOW(), 'pending', 0, 180, 10, 'Giao buổi sáng'),
('DH002', 'KH_2', 'Đường Trần Hưng Đạo, Ninh Kiều, Cần Thơ', 10.026141870, 105.765166283, NOW(), 'pending', 0, 200, 8, NULL),
('DH003', 'KH_3', 'Đường Nguyễn Văn Cừ, Ninh Kiều, Cần Thơ', 10.024419171, 105.765820742, NOW(), 'pending', 10, 190, 12, NULL),
('DH004', 'KH_4', 'Đường Mậu Thân, Ninh Kiều, Cần Thơ', 10.021641388, 105.762612820, NOW(), 'pending', 0, 220, 10, NULL),
('DH005', 'KH_5', 'Đường Hòa Bình, Ninh Kiều, Cần Thơ', 10.022200710, 105.766839981, NOW(), 'pending', 20, 240, 15, NULL),
('DH006', 'KH_6', 'Đường Nguyễn Thị Minh Khai, Ninh Kiều, Cần Thơ', 10.025400826, 105.771389008, NOW(), 'pending', 0, 180, 8, NULL),
('DH007', 'KH_7', 'Đường Trần Phú, Ninh Kiều, Cần Thơ', 10.027102121, 105.773341656, NOW(), 'pending', 15, 210, 10, NULL),
('DH008', 'KH_8', 'Đường Lý Tự Trọng, Ninh Kiều, Cần Thơ', 10.030640705, 105.775068998, NOW(), 'pending', 0, 200, 12, NULL),
('DH009', 'KH_9', 'Đường Phan Đình Phùng, Ninh Kiều, Cần Thơ', 10.035427075, 105.770680904, NOW(), 'pending', 30, 250, 10, NULL),
('DH010', 'KH_10', 'Đường Cao Thắng, Ninh Kiều, Cần Thơ', 10.037518762, 105.771796703, NOW(), 'pending', 0, 190, 8, NULL);

-- ================================================
-- 6. ORDER DETAILS (CHI TIẾT ĐƠN HÀNG)
-- ================================================

INSERT INTO `CTHD` (`MaDH`, `MaSP`, `SoLuong`, `DonGia`) VALUES
-- DH001: 22kg
('DH001', 'SP001', 10, 45000),
('DH001', 'SP003', 12, 35000),

-- DH002: 28kg
('DH002', 'SP002', 15, 60000),
('DH002', 'SP005', 13, 15000),

-- DH003: 25kg
('DH003', 'SP001', 10, 45000),
('DH003', 'SP004', 15, 120000),

-- DH004: 30kg
('DH004', 'SP006', 10, 180000),
('DH004', 'SP007', 20, 50000),

-- DH005: 18kg
('DH005', 'SP008', 8, 25000),
('DH005', 'SP009', 10, 20000),

-- DH006: 26kg
('DH006', 'SP001', 15, 45000),
('DH006', 'SP010', 11, 30000),

-- DH007: 24kg
('DH007', 'SP002', 12, 60000),
('DH007', 'SP003', 12, 35000),

-- DH008: 32kg
('DH008', 'SP004', 20, 120000),
('DH008', 'SP005', 12, 15000),

-- DH009: 20kg
('DH009', 'SP007', 10, 50000),
('DH009', 'SP008', 10, 25000),

-- DH010: 27kg
('DH010', 'SP009', 15, 20000),
('DH010', 'SP001', 12, 45000);

-- ================================================
-- 7. SAMPLE DELIVERY ROUTES (TUYẾN VẬN CHUYỂN MẪU)
-- ================================================

-- Tuyến 1 (đã hoàn thành)
INSERT INTO `VAN_CHUYEN` (`MaVC`, `TenTuyen`, `TrangThai`, `NgayTao`, `NgayBatDau`, `NgayKetThuc`, `TongQuangDuong`, `TongHang`, `TongDonHang`) VALUES
('VC001', 'Tuyến 1 - Khu vực Trung tâm', 'completed', DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY), 15.5, 75, 3);

-- Phân công tài xế cho tuyến 1
INSERT INTO `CTVC` (`MaVC`, `MaTX`, `TrangThai`, `NgayGiao`, `ThoiGianBatDau`, `ThoiGianKetThuc`) VALUES
('VC001', 'TX001', 'completed', DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY));

-- ================================================
-- SUMMARY
-- ================================================

-- Tổng số records đã insert:
SELECT 'USER' as TableName, COUNT(*) as RecordCount FROM USER
UNION ALL
SELECT 'TAI_XE', COUNT(*) FROM TAI_XE
UNION ALL
SELECT 'SAN_PHAM', COUNT(*) FROM SAN_PHAM
UNION ALL
SELECT 'NGUOI_DUNG', COUNT(*) FROM NGUOI_DUNG
UNION ALL
SELECT 'DON_HANG', COUNT(*) FROM DON_HANG
UNION ALL
SELECT 'CTHD', COUNT(*) FROM CTHD
UNION ALL
SELECT 'VAN_CHUYEN', COUNT(*) FROM VAN_CHUYEN
UNION ALL
SELECT 'CTVC', COUNT(*) FROM CTVC;
