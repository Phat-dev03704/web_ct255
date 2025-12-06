# -*- coding: utf-8 -*-
"""
VRP System - Flask Application
Hệ thống quản lý bán hàng và tối ưu tuyến đường giao hàng
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import bcrypt
from functools import wraps
import os
from datetime import datetime, timedelta
from decimal import Decimal
from dotenv import load_dotenv

# Load environment variables từ file .env
load_dotenv()

from models import (
    db, User, NguoiDung, TaiXe, SanPham, DonHang, CTHD,
    VanChuyen, CTVC, DonHangCTVC,
    UserRole, OrderStatus, DriverStatus, ProductStatus
)
from config import config

def create_app(config_name='development'):
    """Factory function để tạo Flask app"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    from routes import auth_bp, user_bp, admin_bp, driver_bp, customer_bp, api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(driver_bp, url_prefix='/driver')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Thêm UTF-8 encoding và security headers cho response
    @app.after_request
    def after_request(response):
        # Chỉ set charset cho HTML, không động đến JSON
        if response.content_type and 'text/html' in response.content_type:
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
        elif response.content_type and 'application/json' in response.content_type:
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
        
        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Cache control cho static files
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        
        return response
    
    return app

# Decorator kiểm tra đăng nhập
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Vui lòng đăng nhập để tiếp tục', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator kiểm tra role
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                flash('Vui lòng đăng nhập để tiếp tục', 'warning')
                return redirect(url_for('auth.login'))
            
            user = User.query.get(session['username'])
            if not user or user.role.value != role:
                flash('Bạn không có quyền truy cập trang này', 'danger')
                return redirect(url_for('user.index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Helper functions
def generate_order_id():
    """Tạo mã đơn hàng tự động"""
    last_order = DonHang.query.order_by(DonHang.MaDH.desc()).first()
    if last_order:
        last_id = int(last_order.MaDH.replace('DH', ''))
        new_id = f'DH{str(last_id + 1).zfill(3)}'
    else:
        new_id = 'DH001'
    return new_id

def generate_customer_id():
    """Tạo mã khách hàng tự động"""
    last_customer = NguoiDung.query.filter(NguoiDung.MaND.like('KH_%')).order_by(NguoiDung.MaND.desc()).first()
    if last_customer:
        last_num = int(last_customer.MaND.split('_')[1])
        new_id = f'KH_{last_num + 1}'
    else:
        new_id = 'KH_1'
    return new_id

def get_cart_total():
    """Tính tổng tiền giỏ hàng"""
    cart = session.get('cart', {})
    total = 0
    for item_id, item in cart.items():
        total += item['quantity'] * item['price']
    return total

def get_cart_count():
    """Đếm số sản phẩm trong giỏ hàng"""
    cart = session.get('cart', {})
    return sum(item['quantity'] for item in cart.values())

# Main entry point
if __name__ == '__main__':
    app = create_app()
    
    # Thêm context processor để sử dụng trong template
    @app.context_processor
    def utility_processor():
        return {
            'get_cart_count': get_cart_count,
            'get_cart_total': get_cart_total,
            'now': datetime.now()
        }
    
    with app.app_context():
        # Tạo bảng nếu chưa tồn tại
        db.create_all()
        print("Database tables created successfully!")
    
    # Chạy app
    app.run(debug=True, host='0.0.0.0', port=5000)
