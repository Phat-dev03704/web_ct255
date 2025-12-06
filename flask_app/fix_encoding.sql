-- Fix encoding cho các bảng trong vrp_system
-- Chạy script này để sửa các ký tự bị lỗi encoding

USE vrp_system;

-- Fix bảng VAN_CHUYEN - Cập nhật tên tuyến
UPDATE VAN_CHUYEN SET TenTuyen = 'Tuyen 1 - Khu vuc Trung tam' WHERE MaVC = 'VC001' AND TenTuyen LIKE '%?%';
UPDATE VAN_CHUYEN SET TenTuyen = 'Tuyen 2 - Khu vuc Bac' WHERE MaVC = 'VC002' AND TenTuyen LIKE '%?%';
UPDATE VAN_CHUYEN SET TenTuyen = 'Tuyen 3 - Khu vuc Nam' WHERE MaVC = 'VC003' AND TenTuyen LIKE '%?%';

-- Fix bảng CTVC - bỏ qua vì không có cột text cần fix

-- Fix bảng TAI_XE nếu có
UPDATE TAI_XE SET TenTX = REPLACE(REPLACE(REPLACE(TenTX, '???', ''), '??', ''), '?', '') WHERE TenTX LIKE '%?%';

-- Fix bảng NGUOI_DUNG nếu có
UPDATE NGUOI_DUNG SET TenND = REPLACE(REPLACE(REPLACE(TenND, '???', ''), '??', ''), '?', '') WHERE TenND LIKE '%?%';
UPDATE NGUOI_DUNG SET DiaChi = REPLACE(REPLACE(REPLACE(DiaChi, '???', ''), '??', ''), '?', '') WHERE DiaChi LIKE '%?%';

-- Fix bảng SAN_PHAM nếu có
UPDATE SAN_PHAM SET TenSP = REPLACE(REPLACE(REPLACE(TenSP, '???', ''), '??', ''), '?', '') WHERE TenSP LIKE '%?%';
UPDATE SAN_PHAM SET MoTa = REPLACE(REPLACE(REPLACE(MoTa, '???', ''), '??', ''), '?', '') WHERE MoTa LIKE '%?%';

-- Fix bảng DON_HANG nếu có  
UPDATE DON_HANG SET DiaChi = REPLACE(REPLACE(REPLACE(DiaChi, '???', ''), '??', ''), '?', '') WHERE DiaChi LIKE '%?%';
UPDATE DON_HANG SET GhiChu = REPLACE(REPLACE(REPLACE(GhiChu, '???', ''), '??', ''), '?', '') WHERE GhiChu LIKE '%?%';

-- Kiểm tra kết quả
SELECT 'VAN_CHUYEN' as Bang, COUNT(*) as SoLuong FROM VAN_CHUYEN WHERE TenTuyen LIKE '%?%'
UNION ALL
SELECT 'TAI_XE', COUNT(*) FROM TAI_XE WHERE TenTX LIKE '%?%'
UNION ALL
SELECT 'NGUOI_DUNG', COUNT(*) FROM NGUOI_DUNG WHERE TenND LIKE '%?%' OR DiaChi LIKE '%?%'
UNION ALL
SELECT 'SAN_PHAM', COUNT(*) FROM SAN_PHAM WHERE TenSP LIKE '%?%' OR MoTa LIKE '%?%'
UNION ALL
SELECT 'DON_HANG', COUNT(*) FROM DON_HANG WHERE DiaChi LIKE '%?%' OR GhiChu LIKE '%?%';
