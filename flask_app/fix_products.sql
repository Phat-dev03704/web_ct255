-- ================================================
-- FIX UTF-8 ENCODING AND UPDATE PRODUCT IMAGES
-- ================================================

USE `vrp_system`;

-- Update product names to English and link to SVG images
UPDATE `SAN_PHAM` SET 
    `TenSP` = 'Apple', 
    `MoTa` = 'Fresh imported apple from USA, rich in vitamins',
    `HinhAnh` = 'apple.svg'
WHERE `MaSP` = 'SP001';

UPDATE `SAN_PHAM` SET 
    `TenSP` = 'Mango', 
    `MoTa` = 'Hoa Loc mango specialty from Tien Giang',
    `HinhAnh` = 'mango.svg'
WHERE `MaSP` = 'SP002';

UPDATE `SAN_PHAM` SET 
    `TenSP` = 'Orange', 
    `MoTa` = 'Sanh orange from Ha Giang, sweet and juicy',
    `HinhAnh` = 'orange.svg'
WHERE `MaSP` = 'SP003';

UPDATE `SAN_PHAM` SET 
    `TenSP` = 'Grape', 
    `MoTa` = 'Seedless green grape imported from Australia',
    `HinhAnh` = 'grape.svg'
WHERE `MaSP` = 'SP004';

UPDATE `SAN_PHAM` SET 
    `TenSP` = 'Watermelon', 
    `MoTa` = 'Seedless watermelon from Long An',
    `HinhAnh` = 'watermelon.svg'
WHERE `MaSP` = 'SP005';

UPDATE `SAN_PHAM` SET 
    `TenSP` = 'Durian', 
    `MoTa` = 'Ri6 durian from Dak Lak, golden flesh',
    `HinhAnh` = 'durian.svg'
WHERE `MaSP` = 'SP006';

UPDATE `SAN_PHAM` SET 
    `TenSP` = 'Mangosteen', 
    `MoTa` = 'Fresh mangosteen from Can Tho',
    `HinhAnh` = 'mangosteen.svg'
WHERE `MaSP` = 'SP007';

UPDATE `SAN_PHAM` SET 
    `TenSP` = 'Rambutan', 
    `MoTa` = 'Sweet rambutan from Ben Tre',
    `HinhAnh` = 'rambutan.svg'
WHERE `MaSP` = 'SP008';

UPDATE `SAN_PHAM` SET 
    `TenSP` = 'Dragon Fruit', 
    `MoTa` = 'Organic red dragon fruit from Long An',
    `HinhAnh` = 'dragonfruit.svg'
WHERE `MaSP` = 'SP009';

UPDATE `SAN_PHAM` SET 
    `TenSP` = 'Pomelo', 
    `MoTa` = 'Green skin pomelo from Ben Tre',
    `HinhAnh` = 'pomelo.svg'
WHERE `MaSP` = 'SP010';

-- Display results
SELECT 'Products updated successfully!' AS Status;
SELECT `MaSP`, `TenSP`, `HinhAnh` FROM `SAN_PHAM`;
