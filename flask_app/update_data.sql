-- Update data to English and fix passwords
USE vrp_system;

-- Update USER passwords with correct bcrypt hash
UPDATE USER SET password = '$2b$12$stb4t4Fu8g3fj4vim6JZb.BEQEJXVLoAix3en4UJ6yq/JM0o/Hx4O';

-- Update product names to English
UPDATE SAN_PHAM SET 
    TenSP = 'Apple',
    MoTa = 'Fresh red apples, crispy and sweet',
    HinhAnh = 'apple.svg'
WHERE MaSP = 'SP001';

UPDATE SAN_PHAM SET 
    TenSP = 'Mango',
    MoTa = 'Ripe yellow mango, sweet and juicy',
    HinhAnh = 'mango.svg'
WHERE MaSP = 'SP002';

UPDATE SAN_PHAM SET 
    TenSP = 'Orange',
    MoTa = 'Fresh oranges, rich in vitamin C',
    HinhAnh = 'orange.svg'
WHERE MaSP = 'SP003';

UPDATE SAN_PHAM SET 
    TenSP = 'Grape',
    MoTa = 'Sweet seedless grapes, fresh and crunchy',
    HinhAnh = 'grape.svg'
WHERE MaSP = 'SP004';

UPDATE SAN_PHAM SET 
    TenSP = 'Watermelon',
    MoTa = 'Sweet red watermelon, refreshing',
    HinhAnh = 'watermelon.svg'
WHERE MaSP = 'SP005';

UPDATE SAN_PHAM SET 
    TenSP = 'Durian',
    MoTa = 'King of fruits, creamy and aromatic',
    HinhAnh = 'durian.svg'
WHERE MaSP = 'SP006';

UPDATE SAN_PHAM SET 
    TenSP = 'Mangosteen',
    MoTa = 'Queen of fruits, sweet and tangy',
    HinhAnh = 'mangosteen.svg'
WHERE MaSP = 'SP007';

UPDATE SAN_PHAM SET 
    TenSP = 'Rambutan',
    MoTa = 'Hairy fruit, sweet and refreshing',
    HinhAnh = 'rambutan.svg'
WHERE MaSP = 'SP008';

UPDATE SAN_PHAM SET 
    TenSP = 'Dragon Fruit',
    MoTa = 'Pink dragon fruit, mildly sweet',
    HinhAnh = 'dragonfruit.svg'
WHERE MaSP = 'SP009';

UPDATE SAN_PHAM SET 
    TenSP = 'Pomelo',
    MoTa = 'Large citrus fruit, sweet and tangy',
    HinhAnh = 'pomelo.svg'
WHERE MaSP = 'SP010';

-- Update customer names to English
UPDATE NGUOI_DUNG SET TenND = 'Admin User' WHERE MaND = 'DEPOT';
UPDATE NGUOI_DUNG SET TenND = 'John Smith', DiaChi = '123 Main St, Ninh Kieu, Can Tho' WHERE MaND = 'KH_1';
UPDATE NGUOI_DUNG SET TenND = 'Sarah Johnson', DiaChi = '456 Market St, Ninh Kieu, Can Tho' WHERE MaND = 'KH_2';
UPDATE NGUOI_DUNG SET TenND = 'Michael Brown', DiaChi = '789 Park Ave, Ninh Kieu, Can Tho' WHERE MaND = 'KH_3';
UPDATE NGUOI_DUNG SET TenND = 'Emily Davis', DiaChi = '321 Lake Rd, Ninh Kieu, Can Tho' WHERE MaND = 'KH_4';
UPDATE NGUOI_DUNG SET TenND = 'David Wilson', DiaChi = '654 River St, Ninh Kieu, Can Tho' WHERE MaND = 'KH_5';
UPDATE NGUOI_DUNG SET TenND = 'Lisa Martinez', DiaChi = '987 Hill St, Ninh Kieu, Can Tho' WHERE MaND = 'KH_6';
UPDATE NGUOI_DUNG SET TenND = 'James Anderson', DiaChi = '147 Valley Rd, Ninh Kieu, Can Tho' WHERE MaND = 'KH_7';
UPDATE NGUOI_DUNG SET TenND = 'Jennifer Taylor', DiaChi = '258 Garden St, Ninh Kieu, Can Tho' WHERE MaND = 'KH_8';
UPDATE NGUOI_DUNG SET TenND = 'Robert Thomas', DiaChi = '369 Forest Ave, Ninh Kieu, Can Tho' WHERE MaND = 'KH_9';
UPDATE NGUOI_DUNG SET TenND = 'Mary Jackson', DiaChi = '741 Ocean Dr, Ninh Kieu, Can Tho' WHERE MaND = 'KH_10';
UPDATE NGUOI_DUNG SET TenND = 'William White', DiaChi = '852 Beach Blvd, Ninh Kieu, Can Tho' WHERE MaND = 'KH_11';
UPDATE NGUOI_DUNG SET TenND = 'Patricia Harris', DiaChi = '963 Sunset St, Ninh Kieu, Can Tho' WHERE MaND = 'KH_12';
UPDATE NGUOI_DUNG SET TenND = 'Richard Clark', DiaChi = '159 Sunrise Ave, Ninh Kieu, Can Tho' WHERE MaND = 'KH_13';
UPDATE NGUOI_DUNG SET TenND = 'Linda Lewis', DiaChi = '357 Mountain Rd, Ninh Kieu, Can Tho' WHERE MaND = 'KH_14';
UPDATE NGUOI_DUNG SET TenND = 'Charles Robinson', DiaChi = '753 Plains St, Ninh Kieu, Can Tho' WHERE MaND = 'KH_15';
UPDATE NGUOI_DUNG SET TenND = 'Barbara Walker', DiaChi = '951 Meadow Ln, Ninh Kieu, Can Tho' WHERE MaND = 'KH_16';
UPDATE NGUOI_DUNG SET TenND = 'Joseph Hall', DiaChi = '246 Creek Dr, Ninh Kieu, Can Tho' WHERE MaND = 'KH_17';
