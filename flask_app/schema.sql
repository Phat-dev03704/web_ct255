-- ================================================
-- VRP SYSTEM DATABASE SCHEMA
-- ================================================

-- Drop database if exists and create new
DROP DATABASE IF EXISTS `vrp_system`;
CREATE DATABASE `vrp_system` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `vrp_system`;

-- ================================================
-- AUTHENTICATION & USER MANAGEMENT
-- ================================================

-- Bảng USER: tài khoản đăng nhập
CREATE TABLE `USER` (
  `username` VARCHAR(50) NOT NULL,
  `password` VARCHAR(255) NOT NULL,
  `role` ENUM('admin', 'customer', 'driver') NOT NULL DEFAULT 'customer',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ================================================
-- CORE ENTITIES
-- ================================================

-- Bảng NGUOI_DUNG: người dùng / khách hàng
CREATE TABLE `NGUOI_DUNG` (
  `MaND` VARCHAR(20) NOT NULL,
  `TenND` VARCHAR(100) NOT NULL,
  `DiaChi` VARCHAR(255),
  `Lat` DECIMAL(10, 8),
  `Lon` DECIMAL(11, 8),
  `SDT` VARCHAR(20),
  `username` VARCHAR(50), -- liên kết tới USER (nếu có tài khoản)
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`MaND`),
  CONSTRAINT `fk_ngd_user` FOREIGN KEY (`username`) REFERENCES `USER`(`username`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Bảng TAI_XE: tài xế
CREATE TABLE `TAI_XE` (
  `MaTX` VARCHAR(20) NOT NULL,
  `TenTX` VARCHAR(100) NOT NULL,
  `DiaChi` VARCHAR(255),
  `SDT` VARCHAR(20),
  `BienSoXe` VARCHAR(20),
  `SucChua` INT DEFAULT 100,
  `username` VARCHAR(50), -- nếu tài xế có tài khoản hệ thống
  `TrangThai` ENUM('available', 'busy', 'offline') DEFAULT 'available',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`MaTX`),
  CONSTRAINT `fk_tax_user` FOREIGN KEY (`username`) REFERENCES `USER`(`username`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Bảng SAN_PHAM: sản phẩm
CREATE TABLE `SAN_PHAM` (
  `MaSP` VARCHAR(20) NOT NULL,
  `TenSP` VARCHAR(200) NOT NULL,
  `MoTa` TEXT,
  `TonKho` INT DEFAULT 0,
  `DonGia` DECIMAL(12,2) DEFAULT 0.00,
  `DonVi` VARCHAR(20) DEFAULT 'kg',
  `HinhAnh` VARCHAR(255),
  `TrangThai` ENUM('active', 'inactive') DEFAULT 'active',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`MaSP`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ================================================
-- ORDER MANAGEMENT
-- ================================================

-- Bảng DON_HANG: đơn hàng
CREATE TABLE `DON_HANG` (
  `MaDH` VARCHAR(20) NOT NULL,
  `MaND` VARCHAR(20) NOT NULL, -- khách hàng
  `DiaChi` VARCHAR(255) NOT NULL,
  `Lat` DECIMAL(10, 8) NOT NULL,
  `Lon` DECIMAL(11, 8) NOT NULL,
  `NgayTao` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `TrangThai` ENUM('pending', 'processing', 'assigned', 'delivering', 'delivered', 'cancelled') DEFAULT 'pending',
  `TongTien` DECIMAL(12,2) DEFAULT 0.00,
  `READY_TIME` INT DEFAULT 0, -- thời gian sớm nhất có thể giao (phút từ 0h)
  `DUE_DATE` INT DEFAULT 1440,   -- thời gian muộn nhất phải giao (phút từ 0h, 1440 = 24h)
  `SERVICE_TIME` INT DEFAULT 20, -- thời gian phục vụ tại điểm (phút)
  `GhiChu` TEXT,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`MaDH`),
  KEY `idx_dh_ngd` (`MaND`),
  KEY `idx_dh_trangthai` (`TrangThai`),
  KEY `idx_dh_ngaytao` (`NgayTao`),
  CONSTRAINT `fk_dh_ngd` FOREIGN KEY (`MaND`) REFERENCES `NGUOI_DUNG`(`MaND`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Bảng CTHD (chi tiết đơn hàng)
CREATE TABLE `CTHD` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `MaDH` VARCHAR(20) NOT NULL,
  `MaSP` VARCHAR(20) NOT NULL,
  `SoLuong` INT NOT NULL DEFAULT 1, -- DEMAND / số lượng
  `DonGia` DECIMAL(12,2) NOT NULL,
  `ThanhTien` DECIMAL(12,2) NOT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_cthd_madh` (`MaDH`),
  KEY `idx_cthd_masp` (`MaSP`),
  CONSTRAINT `fk_cthd_dh` FOREIGN KEY (`MaDH`) REFERENCES `DON_HANG`(`MaDH`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_cthd_sp` FOREIGN KEY (`MaSP`) REFERENCES `SAN_PHAM`(`MaSP`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ================================================
-- DELIVERY & ROUTING
-- ================================================

-- Bảng VAN_CHUYEN: chuyến/tuyến vận chuyển
CREATE TABLE `VAN_CHUYEN` (
  `MaVC` VARCHAR(20) NOT NULL,
  `TenTuyen` VARCHAR(100),
  `TrangThai` ENUM('planned', 'in_progress', 'completed', 'cancelled') DEFAULT 'planned',
  `NgayTao` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `NgayBatDau` DATETIME,
  `NgayKetThuc` DATETIME,
  `TongQuangDuong` FLOAT DEFAULT 0, -- tổng quãng đường (km)
  `TongHang` INT DEFAULT 0, -- tổng số hàng (khối lượng)
  `TongDonHang` INT DEFAULT 0, -- tổng số đơn hàng
  `RouteData` JSON, -- Lưu thông tin tuyến đường từ OR-Tools
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`MaVC`),
  KEY `idx_vc_trangthai` (`TrangThai`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Bảng CTVC: chi tiết phân công vận chuyển (gán Tài xế -> Tuyến)
CREATE TABLE `CTVC` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `MaVC` VARCHAR(20) NOT NULL,
  `MaTX` VARCHAR(20) NOT NULL,
  `TrangThai` ENUM('assigned', 'in_progress', 'completed') DEFAULT 'assigned',
  `NgayGiao` DATE,
  `ThoiGianBatDau` DATETIME,
  `ThoiGianKetThuc` DATETIME,
  `GhiChu` TEXT,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ctvc_mavc` (`MaVC`),
  KEY `idx_ctvc_matx` (`MaTX`),
  CONSTRAINT `fk_ctvc_vc` FOREIGN KEY (`MaVC`) REFERENCES `VAN_CHUYEN`(`MaVC`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_ctvc_tx` FOREIGN KEY (`MaTX`) REFERENCES `TAI_XE`(`MaTX`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Bảng DONHANG_CTVC: liên kết DonHang với CTVC
CREATE TABLE `DONHANG_CTVC` (
  `MaDH` VARCHAR(20) NOT NULL,
  `CTVC_id` BIGINT NOT NULL,
  `ThuTu` INT, -- thứ tự giao hàng trong tuyến
  `ThoiGianGiaoDuKien` DATETIME,
  `ThoiGianGiaoThucTe` DATETIME,
  `TrangThai` ENUM('pending', 'delivering', 'delivered', 'failed') DEFAULT 'pending',
  `GhiChu` TEXT,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`MaDH`,`CTVC_id`),
  KEY `idx_dhctvc_ctvc` (`CTVC_id`),
  CONSTRAINT `fk_dhctvc_dh` FOREIGN KEY (`MaDH`) REFERENCES `DON_HANG`(`MaDH`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_dhctvc_ctvc` FOREIGN KEY (`CTVC_id`) REFERENCES `CTVC`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ================================================
-- INDEXES FOR PERFORMANCE
-- ================================================

CREATE INDEX idx_cthd_madh_masp ON CTHD(MaDH, MaSP);
CREATE INDEX idx_donhang_lat_lon ON DON_HANG(Lat, Lon);
CREATE INDEX idx_nguoidung_lat_lon ON NGUOI_DUNG(Lat, Lon);
CREATE INDEX idx_vanchuyen_ngaytao ON VAN_CHUYEN(NgayTao);
CREATE INDEX idx_ctvc_trangthai ON CTVC(TrangThai);

-- ================================================
-- VIEWS FOR REPORTING
-- ================================================

-- View: Thống kê đơn hàng theo trạng thái
CREATE VIEW v_donhang_stats AS
SELECT 
    TrangThai,
    COUNT(*) as SoDonHang,
    SUM(TongTien) as TongDoanhThu,
    AVG(TongTien) as GiaTriTrungBinh,
    DATE(NgayTao) as NgayTao
FROM DON_HANG
GROUP BY TrangThai, DATE(NgayTao);

-- View: Chi tiết tuyến vận chuyển
CREATE VIEW v_tuyen_vanchuyen AS
SELECT 
    vc.MaVC,
    vc.TenTuyen,
    vc.TrangThai,
    vc.TongQuangDuong,
    vc.TongDonHang,
    tx.TenTX,
    tx.BienSoXe,
    ctvc.TrangThai as TrangThaiGiao
FROM VAN_CHUYEN vc
LEFT JOIN CTVC ctvc ON vc.MaVC = ctvc.MaVC
LEFT JOIN TAI_XE tx ON ctvc.MaTX = tx.MaTX;

-- ================================================
-- STORED PROCEDURES
-- ================================================

DELIMITER //

-- Procedure: Tính tổng tiền đơn hàng
CREATE PROCEDURE sp_calculate_order_total(IN p_MaDH VARCHAR(20))
BEGIN
    UPDATE DON_HANG
    SET TongTien = (
        SELECT IFNULL(SUM(ThanhTien), 0)
        FROM CTHD
        WHERE MaDH = p_MaDH
    )
    WHERE MaDH = p_MaDH;
END //

-- Procedure: Cập nhật tồn kho khi đặt hàng
CREATE PROCEDURE sp_update_inventory(IN p_MaDH VARCHAR(20))
BEGIN
    UPDATE SAN_PHAM sp
    INNER JOIN CTHD ct ON sp.MaSP = ct.MaSP
    SET sp.TonKho = sp.TonKho - ct.SoLuong
    WHERE ct.MaDH = p_MaDH;
END //

DELIMITER ;

-- ================================================
-- TRIGGERS
-- ================================================

DELIMITER //

-- Trigger: Tự động tính thành tiền khi thêm chi tiết đơn hàng
CREATE TRIGGER tr_cthd_before_insert
BEFORE INSERT ON CTHD
FOR EACH ROW
BEGIN
    SET NEW.ThanhTien = NEW.SoLuong * NEW.DonGia;
END //

-- Trigger: Tự động cập nhật tổng tiền đơn hàng
CREATE TRIGGER tr_cthd_after_insert
AFTER INSERT ON CTHD
FOR EACH ROW
BEGIN
    CALL sp_calculate_order_total(NEW.MaDH);
END //

CREATE TRIGGER tr_cthd_after_update
AFTER UPDATE ON CTHD
FOR EACH ROW
BEGIN
    CALL sp_calculate_order_total(NEW.MaDH);
END //

CREATE TRIGGER tr_cthd_after_delete
AFTER DELETE ON CTHD
FOR EACH ROW
BEGIN
    CALL sp_calculate_order_total(OLD.MaDH);
END //

DELIMITER ;
