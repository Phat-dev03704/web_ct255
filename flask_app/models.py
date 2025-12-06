"""
Models cho VRP System - Định nghĩa các bảng database sử dụng SQLAlchemy ORM
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Enum, JSON
import enum

db = SQLAlchemy()

# ================================================
# ENUMS
# ================================================

class UserRole(enum.Enum):
    admin = "admin"
    customer = "customer"
    driver = "driver"

class OrderStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    assigned = "assigned"
    delivering = "delivering"
    delivered = "delivered"
    cancelled = "cancelled"

class DriverStatus(enum.Enum):
    available = "available"
    busy = "busy"
    offline = "offline"

class ProductStatus(enum.Enum):
    active = "active"
    inactive = "inactive"

class DeliveryStatus(enum.Enum):
    planned = "planned"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"

class CTVCStatus(enum.Enum):
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"

class DHCTVCStatus(enum.Enum):
    pending = "pending"
    delivering = "delivering"
    delivered = "delivered"
    failed = "failed"

# ================================================
# AUTHENTICATION MODELS
# ================================================

class User(db.Model):
    __tablename__ = 'USER'
    
    username = db.Column(db.String(50), primary_key=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(Enum(UserRole), nullable=False, default=UserRole.customer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    nguoi_dung = db.relationship('NguoiDung', backref='user', lazy=True, uselist=False)
    tai_xe = db.relationship('TaiXe', backref='user', lazy=True, uselist=False)
    
    def __repr__(self):
        return f'<User {self.username} - {self.role.value}>'

# ================================================
# CORE ENTITY MODELS
# ================================================

class NguoiDung(db.Model):
    __tablename__ = 'NGUOI_DUNG'
    
    MaND = db.Column(db.String(20), primary_key=True)
    TenND = db.Column(db.String(100), nullable=False)
    DiaChi = db.Column(db.String(255))
    Lat = db.Column(db.Numeric(10, 8))
    Lon = db.Column(db.Numeric(11, 8))
    SDT = db.Column(db.String(20))
    username = db.Column(db.String(50), db.ForeignKey('USER.username', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    don_hangs = db.relationship('DonHang', backref='nguoi_dung', lazy=True)
    
    def __repr__(self):
        return f'<NguoiDung {self.MaND} - {self.TenND}>'
    
    def to_dict(self):
        return {
            'MaND': self.MaND,
            'TenND': self.TenND,
            'DiaChi': self.DiaChi,
            'Lat': float(self.Lat) if self.Lat else None,
            'Lon': float(self.Lon) if self.Lon else None,
            'SDT': self.SDT,
            'username': self.username
        }

class TaiXe(db.Model):
    __tablename__ = 'TAI_XE'
    
    MaTX = db.Column(db.String(20), primary_key=True)
    TenTX = db.Column(db.String(100), nullable=False)
    DiaChi = db.Column(db.String(255))
    SDT = db.Column(db.String(20))
    BienSoXe = db.Column(db.String(20))
    SucChua = db.Column(db.Integer, default=100)
    username = db.Column(db.String(50), db.ForeignKey('USER.username', ondelete='SET NULL'))
    TrangThai = db.Column(Enum(DriverStatus), default=DriverStatus.available)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ct_van_chuyens = db.relationship('CTVC', backref='tai_xe', lazy=True)
    
    def __repr__(self):
        return f'<TaiXe {self.MaTX} - {self.TenTX}>'
    
    def to_dict(self):
        return {
            'MaTX': self.MaTX,
            'TenTX': self.TenTX,
            'DiaChi': self.DiaChi,
            'SDT': self.SDT,
            'BienSoXe': self.BienSoXe,
            'SucChua': self.SucChua,
            'TrangThai': self.TrangThai.value if self.TrangThai else None,
            'username': self.username
        }

class SanPham(db.Model):
    __tablename__ = 'SAN_PHAM'
    
    MaSP = db.Column(db.String(20), primary_key=True)
    TenSP = db.Column(db.String(200), nullable=False)
    MoTa = db.Column(db.Text)
    TonKho = db.Column(db.Integer, default=0)
    DonGia = db.Column(db.Numeric(12, 2), default=0.00)
    DonVi = db.Column(db.String(20), default='kg')
    HinhAnh = db.Column(db.String(255))
    TrangThai = db.Column(Enum(ProductStatus), default=ProductStatus.active)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chi_tiet_hds = db.relationship('CTHD', backref='san_pham', lazy=True)
    
    def __repr__(self):
        return f'<SanPham {self.MaSP} - {self.TenSP}>'
    
    def to_dict(self):
        return {
            'MaSP': self.MaSP,
            'TenSP': self.TenSP,
            'MoTa': self.MoTa,
            'TonKho': self.TonKho,
            'DonGia': float(self.DonGia) if self.DonGia else 0.00,
            'DonVi': self.DonVi,
            'HinhAnh': self.HinhAnh,
            'TrangThai': self.TrangThai.value if self.TrangThai else None
        }

# ================================================
# ORDER MODELS
# ================================================

class DonHang(db.Model):
    __tablename__ = 'DON_HANG'
    
    MaDH = db.Column(db.String(20), primary_key=True)
    MaND = db.Column(db.String(20), db.ForeignKey('NGUOI_DUNG.MaND', ondelete='RESTRICT'), nullable=False)
    DiaChi = db.Column(db.String(255), nullable=False)
    Lat = db.Column(db.Numeric(10, 8), nullable=False)
    Lon = db.Column(db.Numeric(11, 8), nullable=False)
    NgayTao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    TrangThai = db.Column(Enum(OrderStatus), default=OrderStatus.pending)
    TongTien = db.Column(db.Numeric(12, 2), default=0.00)
    READY_TIME = db.Column(db.Integer, default=0)
    DUE_DATE = db.Column(db.Integer, default=1440)
    SERVICE_TIME = db.Column(db.Integer, default=20)
    GhiChu = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chi_tiets = db.relationship('CTHD', backref='don_hang', lazy=True, cascade='all, delete-orphan')
    donhang_ctvcs = db.relationship('DonHangCTVC', backref='don_hang', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<DonHang {self.MaDH} - {self.TrangThai.value}>'
    
    def to_dict(self):
        return {
            'MaDH': self.MaDH,
            'MaND': self.MaND,
            'DiaChi': self.DiaChi,
            'Lat': float(self.Lat) if self.Lat else None,
            'Lon': float(self.Lon) if self.Lon else None,
            'NgayTao': self.NgayTao.isoformat() if self.NgayTao else None,
            'TrangThai': self.TrangThai.value if self.TrangThai else None,
            'TongTien': float(self.TongTien) if self.TongTien else 0.00,
            'READY_TIME': self.READY_TIME,
            'DUE_DATE': self.DUE_DATE,
            'SERVICE_TIME': self.SERVICE_TIME,
            'GhiChu': self.GhiChu
        }

class CTHD(db.Model):
    __tablename__ = 'CTHD'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    MaDH = db.Column(db.String(20), db.ForeignKey('DON_HANG.MaDH', ondelete='CASCADE'), nullable=False)
    MaSP = db.Column(db.String(20), db.ForeignKey('SAN_PHAM.MaSP', ondelete='RESTRICT'), nullable=False)
    SoLuong = db.Column(db.Integer, nullable=False, default=1)
    DonGia = db.Column(db.Numeric(12, 2), nullable=False)
    ThanhTien = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CTHD {self.id} - {self.MaDH} - {self.MaSP}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'MaDH': self.MaDH,
            'MaSP': self.MaSP,
            'SoLuong': self.SoLuong,
            'DonGia': float(self.DonGia) if self.DonGia else 0.00,
            'ThanhTien': float(self.ThanhTien) if self.ThanhTien else 0.00
        }

# ================================================
# DELIVERY & ROUTING MODELS
# ================================================

class VanChuyen(db.Model):
    __tablename__ = 'VAN_CHUYEN'
    
    MaVC = db.Column(db.String(20), primary_key=True)
    TenTuyen = db.Column(db.String(100))
    TrangThai = db.Column(Enum(DeliveryStatus), default=DeliveryStatus.planned)
    NgayTao = db.Column(db.DateTime, default=datetime.utcnow)
    NgayBatDau = db.Column(db.DateTime)
    NgayKetThuc = db.Column(db.DateTime)
    TongQuangDuong = db.Column(db.Float, default=0)
    TongHang = db.Column(db.Integer, default=0)
    TongDonHang = db.Column(db.Integer, default=0)
    RouteData = db.Column(JSON)  # Lưu dữ liệu tuyến đường từ OR-Tools
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ct_van_chuyens = db.relationship('CTVC', backref='van_chuyen', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<VanChuyen {self.MaVC} - {self.TrangThai.value}>'
    
    def to_dict(self):
        return {
            'MaVC': self.MaVC,
            'TenTuyen': self.TenTuyen,
            'TrangThai': self.TrangThai.value if self.TrangThai else None,
            'NgayTao': self.NgayTao.isoformat() if self.NgayTao else None,
            'NgayBatDau': self.NgayBatDau.isoformat() if self.NgayBatDau else None,
            'NgayKetThuc': self.NgayKetThuc.isoformat() if self.NgayKetThuc else None,
            'TongQuangDuong': self.TongQuangDuong,
            'TongHang': self.TongHang,
            'TongDonHang': self.TongDonHang,
            'RouteData': self.RouteData
        }

class CTVC(db.Model):
    __tablename__ = 'CTVC'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    MaVC = db.Column(db.String(20), db.ForeignKey('VAN_CHUYEN.MaVC', ondelete='CASCADE'), nullable=False)
    MaTX = db.Column(db.String(20), db.ForeignKey('TAI_XE.MaTX', ondelete='RESTRICT'), nullable=False)
    TrangThai = db.Column(Enum(CTVCStatus), default=CTVCStatus.assigned)
    NgayGiao = db.Column(db.Date)
    ThoiGianBatDau = db.Column(db.DateTime)
    ThoiGianKetThuc = db.Column(db.DateTime)
    GhiChu = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    donhang_ctvcs = db.relationship('DonHangCTVC', backref='ctvc', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CTVC {self.id} - {self.MaVC} - {self.MaTX}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'MaVC': self.MaVC,
            'MaTX': self.MaTX,
            'TrangThai': self.TrangThai.value if self.TrangThai else None,
            'NgayGiao': self.NgayGiao.isoformat() if self.NgayGiao else None,
            'ThoiGianBatDau': self.ThoiGianBatDau.isoformat() if self.ThoiGianBatDau else None,
            'ThoiGianKetThuc': self.ThoiGianKetThuc.isoformat() if self.ThoiGianKetThuc else None,
            'GhiChu': self.GhiChu
        }

class DonHangCTVC(db.Model):
    __tablename__ = 'DONHANG_CTVC'
    
    MaDH = db.Column(db.String(20), db.ForeignKey('DON_HANG.MaDH', ondelete='CASCADE'), primary_key=True)
    CTVC_id = db.Column(db.BigInteger, db.ForeignKey('CTVC.id', ondelete='CASCADE'), primary_key=True)
    ThuTu = db.Column(db.Integer)
    ThoiGianGiaoDuKien = db.Column(db.DateTime)
    ThoiGianGiaoThucTe = db.Column(db.DateTime)
    TrangThai = db.Column(Enum(DHCTVCStatus), default=DHCTVCStatus.pending)
    GhiChu = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<DonHangCTVC {self.MaDH} - {self.CTVC_id}>'
    
    def to_dict(self):
        return {
            'MaDH': self.MaDH,
            'CTVC_id': self.CTVC_id,
            'ThuTu': self.ThuTu,
            'ThoiGianGiaoDuKien': self.ThoiGianGiaoDuKien.isoformat() if self.ThoiGianGiaoDuKien else None,
            'ThoiGianGiaoThucTe': self.ThoiGianGiaoThucTe.isoformat() if self.ThoiGianGiaoThucTe else None,
            'TrangThai': self.TrangThai.value if self.TrangThai else None,
            'GhiChu': self.GhiChu
        }
