# -*- coding: utf-8 -*-
"""
Routes cho VRP System - Các endpoint cho authentication, user, admin, driver và API
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, make_response
import bcrypt
from datetime import datetime
from decimal import Decimal
import json

from models import (
    db, User, NguoiDung, TaiXe, SanPham, DonHang, CTHD,
    VanChuyen, CTVC, DonHangCTVC,
    UserRole, OrderStatus, DriverStatus, ProductStatus, DHCTVCStatus
)

# ================================================
# BLUEPRINTS
# ================================================

auth_bp = Blueprint('auth', __name__)
user_bp = Blueprint('user', __name__)
admin_bp = Blueprint('admin', __name__)
driver_bp = Blueprint('driver', __name__)
customer_bp = Blueprint('customer', __name__)
api_bp = Blueprint('api', __name__)

# ================================================
# HELPER FUNCTIONS
# ================================================

def login_required(f):
    """Decorator yêu cầu đăng nhập"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Vui lòng đăng nhập để tiếp tục', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    """Decorator kiểm tra quyền truy cập"""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                return redirect(url_for('auth.login'))
            user = User.query.get(session['username'])
            if not user or user.role.value != role:
                flash('Bạn không có quyền truy cập', 'danger')
                return redirect(url_for('user.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ================================================
# AUTHENTICATION ROUTES
# ================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Đăng nhập"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.get(username)
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            session['username'] = user.username
            session['role'] = user.role.value
            
            flash(f'Chào mừng {username}!', 'success')
            
            # Redirect theo role
            if user.role.value == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role.value == 'driver':
                return redirect(url_for('driver.dashboard'))
            elif user.role.value == 'customer':
                return redirect(url_for('customer.home'))
            else:
                return redirect(url_for('user.index'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không đúng', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Đăng ký tài khoản khách hàng"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        ten_nd = request.form.get('ten_nd')
        sdt = request.form.get('sdt')
        
        # Validation
        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp', 'danger')
            return render_template('auth/register.html')
        
        if User.query.get(username):
            flash('Tên đăng nhập đã tồn tại', 'danger')
            return render_template('auth/register.html')
        
        # Tạo user
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_user = User(username=username, password=hashed_password, role=UserRole.customer)
        
        # Tạo người dùng
        ma_nd = generate_customer_id()
        new_nguoi_dung = NguoiDung(MaND=ma_nd, TenND=ten_nd, SDT=sdt, username=username)
        
        try:
            db.session.add(new_user)
            db.session.add(new_nguoi_dung)
            db.session.commit()
            
            flash('Đăng ký thành công! Vui lòng đăng nhập', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {str(e)}', 'danger')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    """Đăng xuất"""
    session.clear()
    flash('Đã đăng xuất', 'info')
    return redirect(url_for('user.index'))

def generate_customer_id():
    """Tạo mã khách hàng"""
    # Lấy tất cả mã KH_ và tìm số lớn nhất
    customers = NguoiDung.query.filter(NguoiDung.MaND.like('KH_%')).all()
    if customers:
        max_num = 0
        for customer in customers:
            try:
                num = int(customer.MaND.split('_')[1])
                if num > max_num:
                    max_num = num
            except (ValueError, IndexError):
                continue
        return f'KH_{max_num + 1}'
    else:
        return 'KH_1'

# ================================================
# USER ROUTES (Redirect to customer for logged in users)
# ================================================

@user_bp.route('/')
def index():
    """Trang chủ - redirect to customer nếu đã đăng nhập"""
    if 'username' in session and session.get('role') == 'customer':
        return redirect(url_for('customer.home'))
    # Cho guest xem sản phẩm (có thể đăng ký sau)
    products = SanPham.query.filter_by(TrangThai=ProductStatus.active).all()
    return render_template('user/index.html', products=products)

def generate_order_id():
    """Tạo mã đơn hàng"""
    last = DonHang.query.order_by(DonHang.MaDH.desc()).first()
    if last:
        num = int(last.MaDH.replace('DH', '')) + 1
    else:
        num = 11
    return f'DH{str(num).zfill(3)}'

# ================================================
# ADMIN ROUTES
# ================================================

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@role_required('admin')
def dashboard():
    """Dashboard admin"""
    # Thống kê
    total_orders = DonHang.query.count()
    pending_orders = DonHang.query.filter_by(TrangThai=OrderStatus.pending).count()
    total_products = SanPham.query.count()
    total_drivers = TaiXe.query.count()
    
    # Đơn hàng gần đây
    recent_orders = DonHang.query.order_by(DonHang.NgayTao.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         total_products=total_products,
                         total_drivers=total_drivers,
                         recent_orders=recent_orders)

@admin_bp.route('/products')
@role_required('admin')
def products():
    """Quản lý sản phẩm"""
    products = SanPham.query.all()
    return render_template('admin/products.html', products=products)

@admin_bp.route('/products/add', methods=['GET', 'POST'])
@role_required('admin')
def add_product():
    """Thêm sản phẩm mới"""
    if request.method == 'POST':
        try:
            ma_sp = request.form.get('ma_sp')
            ten_sp = request.form.get('ten_sp')
            mo_ta = request.form.get('mo_ta')
            ton_kho = request.form.get('ton_kho')
            don_gia = request.form.get('don_gia')
            don_vi = request.form.get('don_vi')
            hinh_anh = request.form.get('hinh_anh')
            
            # Kiểm tra mã sản phẩm đã tồn tại
            if SanPham.query.get(ma_sp):
                flash('Mã sản phẩm đã tồn tại!', 'danger')
                return redirect(url_for('admin.add_product'))
            
            product = SanPham(
                MaSP=ma_sp,
                TenSP=ten_sp,
                MoTa=mo_ta,
                TonKho=int(ton_kho),
                DonGia=float(don_gia),
                DonVi=don_vi,
                HinhAnh=hinh_anh if hinh_anh else 'default.png',
                TrangThai=ProductStatus.active
            )
            
            db.session.add(product)
            db.session.commit()
            flash(f'Đã thêm sản phẩm {ten_sp}', 'success')
            return redirect(url_for('admin.products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi thêm sản phẩm: {str(e)}', 'danger')
            return redirect(url_for('admin.add_product'))
    
    return render_template('admin/product_form.html', product=None)

@admin_bp.route('/products/edit/<ma_sp>', methods=['GET', 'POST'])
@role_required('admin')
def edit_product(ma_sp):
    """Sửa sản phẩm"""
    product = SanPham.query.get_or_404(ma_sp)
    
    if request.method == 'POST':
        try:
            product.TenSP = request.form.get('ten_sp')
            product.MoTa = request.form.get('mo_ta')
            product.TonKho = int(request.form.get('ton_kho'))
            product.DonGia = float(request.form.get('don_gia'))
            product.DonVi = request.form.get('don_vi')
            
            hinh_anh = request.form.get('hinh_anh')
            if hinh_anh:
                product.HinhAnh = hinh_anh
            
            db.session.commit()
            flash(f'Đã cập nhật sản phẩm {product.TenSP}', 'success')
            return redirect(url_for('admin.products'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi cập nhật sản phẩm: {str(e)}', 'danger')
    
    return render_template('admin/product_form.html', product=product)

@admin_bp.route('/products/delete/<ma_sp>', methods=['POST'])
@role_required('admin')
def delete_product(ma_sp):
    """Xóa sản phẩm"""
    try:
        product = SanPham.query.get_or_404(ma_sp)
        ten_sp = product.TenSP
        product.TrangThai = ProductStatus.inactive
        db.session.commit()
        return jsonify({'success': True, 'message': f'Đã xóa sản phẩm {ten_sp}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@admin_bp.route('/drivers', methods=['GET', 'POST'])
@role_required('admin')
def drivers():
    """Quản lý tài xế"""
    if request.method == 'POST':
        try:
            ma_tx = request.form.get('ma_tx')
            ten_tx = request.form.get('ten_tx')
            sdt = request.form.get('sdt')
            bien_so_xe = request.form.get('bien_so_xe')
            suc_chua = request.form.get('suc_chua')
            username = request.form.get('username')
            password = request.form.get('password')
            
            # Kiểm tra xem MaTX đã tồn tại chưa
            existing_driver = TaiXe.query.get(ma_tx)
            if existing_driver:
                flash('Mã tài xế đã tồn tại!', 'danger')
                return redirect(url_for('admin.drivers'))
            
            # Kiểm tra username đã tồn tại chưa
            existing_user = User.query.get(username)
            if existing_user:
                flash('Username đã tồn tại!', 'danger')
                return redirect(url_for('admin.drivers'))
            
            # Tạo user account
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            user = User(
                username=username,
                password=hashed_password,
                role=UserRole.driver
            )
            db.session.add(user)
            
            # Tạo tài xế
            driver = TaiXe(
                MaTX=ma_tx,
                TenTX=ten_tx,
                SDT=sdt,
                BienSoXe=bien_so_xe,
                SucChua=int(suc_chua),
                username=username,
                TrangThai='available'
            )
            db.session.add(driver)
            db.session.commit()
            
            flash(f'Đã thêm tài xế {ten_tx} thành công!', 'success')
            return redirect(url_for('admin.drivers'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi thêm tài xế: {str(e)}', 'danger')
            return redirect(url_for('admin.drivers'))
    
    # GET request
    drivers = TaiXe.query.all()
    return render_template('admin/drivers.html', drivers=drivers)

@admin_bp.route('/drivers/<ma_tx>/edit', methods=['GET', 'POST'])
@role_required('admin')
def edit_driver(ma_tx):
    """Sửa thông tin tài xế"""
    driver = TaiXe.query.get_or_404(ma_tx)
    
    if request.method == 'POST':
        try:
            driver.TenTX = request.form.get('ten_tx')
            driver.SDT = request.form.get('sdt')
            driver.BienSoXe = request.form.get('bien_so_xe')
            driver.SucChua = int(request.form.get('suc_chua'))
            driver.TrangThai = request.form.get('trang_thai', 'available')
            
            db.session.commit()
            flash(f'Đã cập nhật thông tin tài xế {driver.TenTX}!', 'success')
            return redirect(url_for('admin.drivers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi cập nhật: {str(e)}', 'danger')
    
    return render_template('admin/edit_driver.html', driver=driver)

@admin_bp.route('/drivers/<ma_tx>/delete', methods=['POST'])
@role_required('admin')
def delete_driver(ma_tx):
    """Xóa tài xế"""
    try:
        driver = TaiXe.query.get_or_404(ma_tx)
        username = driver.username
        
        # Kiểm tra xem driver có đang trong CTVC nào không
        active_ctvcs = CTVC.query.filter_by(MaTX=ma_tx).all()
        if active_ctvcs:
            flash(f'Không thể xóa tài xế {driver.TenTX} vì đang có tuyến đường được gán!', 'warning')
            return redirect(url_for('admin.drivers'))
        
        # Xóa driver trước
        db.session.delete(driver)
        
        # Xóa user account
        user = User.query.get(username)
        if user:
            db.session.delete(user)
        
        db.session.commit()
        
        flash(f'Đã xóa tài xế {driver.TenTX}!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xóa: {str(e)}', 'danger')
    
    return redirect(url_for('admin.drivers'))

@admin_bp.route('/orders')
@role_required('admin')
def orders():
    """Quản lý đơn hàng"""
    orders = DonHang.query.order_by(DonHang.NgayTao.desc()).all()
    
    # Count orders by status
    pending_count = sum(1 for o in orders if o.TrangThai == OrderStatus.pending)
    processing_count = sum(1 for o in orders if o.TrangThai == OrderStatus.processing)
    delivered_count = sum(1 for o in orders if o.TrangThai == OrderStatus.delivered)
    
    return render_template('admin/orders.html', 
                         orders=orders,
                         pending_count=pending_count,
                         processing_count=processing_count,
                         delivered_count=delivered_count)

@admin_bp.route('/orders/<ma_dh>')
@role_required('admin')
def order_detail(ma_dh):
    """Chi tiết đơn hàng"""
    order = DonHang.query.get_or_404(ma_dh)
    return jsonify(order.to_dict())

@admin_bp.route('/orders/update-status', methods=['POST'])
@role_required('admin')
def update_order_status():
    """Cập nhật trạng thái đơn hàng"""
    data = request.get_json()
    order_id = data.get('order_id')
    new_status = data.get('status')
    
    order = DonHang.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404
    
    try:
        # Update order status
        order.TrangThai = OrderStatus[new_status]
        db.session.commit()
        return jsonify({'success': True, 'message': 'Order status updated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@admin_bp.route('/orders/<ma_dh>', methods=['DELETE'])
@role_required('admin')
def delete_order(ma_dh):
    """Xóa đơn hàng"""
    order = DonHang.query.get(ma_dh)
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404
    
    try:
        # Delete related records first
        CTHD.query.filter_by(MaDH=ma_dh).delete()
        db.session.delete(order)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Order deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@admin_bp.route('/routes')
@role_required('admin')
def routes():
    """Quản lý tuyến đường"""
    from sqlalchemy.orm import joinedload
    van_chuyens = VanChuyen.query.options(
        joinedload(VanChuyen.ct_van_chuyens).joinedload(CTVC.tai_xe)
    ).order_by(VanChuyen.NgayTao.desc()).all()
    return render_template('admin/routes.html', routes=van_chuyens)

@admin_bp.route('/routes/<ma_vc>')
@role_required('admin')
def route_detail(ma_vc):
    """Xem chi tiết tuyến đường"""
    from sqlalchemy.orm import joinedload
    van_chuyen = VanChuyen.query.options(
        joinedload(VanChuyen.ct_van_chuyens).joinedload(CTVC.donhang_ctvcs).joinedload(DonHangCTVC.don_hang).joinedload(DonHang.nguoi_dung),
        joinedload(VanChuyen.ct_van_chuyens).joinedload(CTVC.tai_xe)
    ).get_or_404(ma_vc)
    return render_template('admin/route_detail.html', van_chuyen=van_chuyen)

@admin_bp.route('/routes/<ma_vc>/map')
@role_required('admin')
def route_map(ma_vc):
    """Hiển thị bản đồ tất cả các tuyến đường của vận chuyển"""
    from sqlalchemy.orm import joinedload
    van_chuyen = VanChuyen.query.options(
        joinedload(VanChuyen.ct_van_chuyens).joinedload(CTVC.tai_xe),
        joinedload(VanChuyen.ct_van_chuyens).joinedload(CTVC.donhang_ctvcs).joinedload(DonHangCTVC.don_hang).joinedload(DonHang.nguoi_dung)
    ).get_or_404(ma_vc)
    return render_template('admin/route_map_full.html', van_chuyen=van_chuyen)

@admin_bp.route('/optimize', methods=['GET', 'POST'])
@role_required('admin')
def optimize():
    """Tối ưu tuyến đường bằng OR-Tools"""
    if request.method == 'POST':
        try:
            # Import VRP Solver
            from vrp_solver import VRPSolver
            import os
            from sqlalchemy.orm import joinedload
            
            # Lấy các đơn hàng pending hoặc processing với chi_tiets và nguoi_dung
            pending_orders = DonHang.query.options(
                joinedload(DonHang.chi_tiets),
                joinedload(DonHang.nguoi_dung)
            ).filter(
                DonHang.TrangThai.in_([OrderStatus.pending, OrderStatus.processing])
            ).all()
            
            if not pending_orders:
                flash('Không có đơn hàng nào cần tối ưu', 'warning')
                return redirect(url_for('admin.optimize'))
            
            # Lấy danh sách tài xế được chọn từ form
            selected_driver_ids = request.form.get('selected_drivers', '').split(',')
            selected_driver_ids = [id.strip() for id in selected_driver_ids if id.strip()]
            
            if not selected_driver_ids:
                flash('Vui lòng chọn ít nhất 1 tài xế!', 'warning')
                return redirect(url_for('admin.optimize'))
            
            # Lấy thông tin tài xế đã chọn
            selected_drivers = TaiXe.query.filter(TaiXe.MaTX.in_(selected_driver_ids)).all()
            
            if not selected_drivers:
                flash('Không tìm thấy tài xế đã chọn', 'warning')
                return redirect(url_for('admin.optimize'))
            
            # Lấy các tham số từ form
            service_time = int(request.form.get('service_time', 20))
            avg_speed = int(request.form.get('avg_speed', 30))
            time_limit = int(request.form.get('time_limit', 30))
            search_strategy = request.form.get('search_strategy', 'PATH_CHEAPEST_ARC')
            metaheuristic = request.form.get('metaheuristic', 'AUTOMATIC')
            depot_id = request.form.get('depot_id', 'DEPOT')
            
            # Tạo solver và giải bài toán
            solver = VRPSolver(service_time=service_time, avg_speed=avg_speed, depot_id=depot_id)
            solution = solver.solve(
                pending_orders, 
                selected_drivers, 
                time_limit=time_limit,
                search_strategy=search_strategy,
                metaheuristic=metaheuristic
            )
            
            if not solution:
                flash('Không tìm được giải pháp tối ưu. Vui lòng thử lại', 'danger')
                return redirect(url_for('admin.optimize'))
            
            # Lưu vào database
            van_chuyen = solver.save_to_database(solution)
            
            # Tạo map HTML
            map_html = solver.generate_map_html(solution)
            if map_html:
                # Lưu map vào file
                map_filename = f'route_{van_chuyen.MaVC}.html'
                map_path = os.path.join('maps', map_filename)
                os.makedirs('maps', exist_ok=True)
                with open(map_path, 'w', encoding='utf-8') as f:
                    f.write(map_html)
            
            flash(f'Đã tạo {solution["num_vehicles_used"]} tuyến giao hàng với tổng quãng đường {solution["total_distance"]:.2f} km', 'success')
            return redirect(url_for('admin.routes'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi tối ưu: {str(e)}', 'danger')
            return redirect(url_for('admin.optimize'))
    
    # GET request - hiển thị form
    from sqlalchemy.orm import joinedload
    
    pending_orders = DonHang.query.options(
        joinedload(DonHang.chi_tiets),
        joinedload(DonHang.nguoi_dung)
    ).filter(
        DonHang.TrangThai.in_([OrderStatus.pending, OrderStatus.processing])
    ).all()
    
    # Lấy tài xế available hoặc đã hoàn thành tuyến (sẵn sàng nhận tuyến mới)
    available_drivers = TaiXe.query.filter(
        TaiXe.TrangThai.in_(['available', 'completed'])
    ).order_by(TaiXe.TrangThai.desc(), TaiXe.TenTX).all()
    
    return render_template('admin/optimize.html', 
                         orders=pending_orders,
                         drivers=available_drivers)

# ================================================
# DRIVER ROUTES
# ================================================

@driver_bp.route('/')
@driver_bp.route('/dashboard')
@role_required('driver')
def dashboard():
    """Dashboard tài xế"""
    from sqlalchemy.orm import joinedload
    # Lấy thông tin tài xế
    tai_xe = TaiXe.query.filter_by(username=session['username']).first()
    
    if not tai_xe:
        flash('Không tìm thấy thông tin tài xế', 'danger')
        return redirect(url_for('user.index'))
    
    # Lấy các chuyến được giao
    ct_van_chuyens = CTVC.query.options(
        joinedload(CTVC.van_chuyen),
        joinedload(CTVC.donhang_ctvcs).joinedload(DonHangCTVC.don_hang).joinedload(DonHang.nguoi_dung)
    ).filter_by(MaTX=tai_xe.MaTX).order_by(CTVC.created_at.desc()).all()
    
    return render_template('driver/dashboard.html', tai_xe=tai_xe, ct_van_chuyens=ct_van_chuyens)

@driver_bp.route('/route/<int:ctvc_id>')
@role_required('driver')
def route_detail(ctvc_id):
    """Xem chi tiết tuyến giao hàng"""
    from sqlalchemy.orm import joinedload
    tai_xe = TaiXe.query.filter_by(username=session['username']).first()
    
    ctvc = CTVC.query.options(
        joinedload(CTVC.van_chuyen),
        joinedload(CTVC.donhang_ctvcs).joinedload(DonHangCTVC.don_hang).joinedload(DonHang.nguoi_dung),
        joinedload(CTVC.donhang_ctvcs).joinedload(DonHangCTVC.don_hang).joinedload(DonHang.chi_tiets)
    ).filter_by(id=ctvc_id, MaTX=tai_xe.MaTX).first_or_404()
    
    donhang_ctvcs = sorted(ctvc.donhang_ctvcs, key=lambda x: x.ThuTu)
    
    # Refresh để lấy data mới nhất từ DB
    db.session.expire_all()
    
    response = make_response(render_template('driver/route_detail.html', ctvc=ctvc, tai_xe=tai_xe, donhang_ctvcs=donhang_ctvcs))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@driver_bp.route('/route/<int:ctvc_id>/map')
@role_required('driver')
def route_map(ctvc_id):
    """Hiển thị bản đồ tuyến giao hàng của tài xế"""
    from sqlalchemy.orm import joinedload
    tai_xe = TaiXe.query.filter_by(username=session['username']).first()
    
    ctvc = CTVC.query.options(
        joinedload(CTVC.van_chuyen),
        joinedload(CTVC.donhang_ctvcs).joinedload(DonHangCTVC.don_hang).joinedload(DonHang.nguoi_dung)
    ).filter_by(id=ctvc_id, MaTX=tai_xe.MaTX).first_or_404()
    
    return render_template('driver/route_map.html', ctvc=ctvc, tai_xe=tai_xe)

@driver_bp.route('/order/<ma_dh>/complete', methods=['POST'])
@role_required('driver')
def complete_order(ma_dh):
    """Đánh dấu đơn hàng đã giao"""
    tai_xe = TaiXe.query.filter_by(username=session['username']).first()
    
    # Lấy ctvc_id từ request body
    data = request.get_json() or {}
    ctvc_id = data.get('ctvc_id')
    
    if not ctvc_id:
        return jsonify({'success': False, 'message': 'Thiếu thông tin CTVC_id'}), 400
    
    # Kiểm tra đơn hàng thuộc về tài xế này VÀ đúng tuyến
    dh_ctvc = DonHangCTVC.query.join(CTVC).filter(
        DonHangCTVC.MaDH == ma_dh,
        DonHangCTVC.CTVC_id == ctvc_id,
        CTVC.MaTX == tai_xe.MaTX
    ).first()
    
    if not dh_ctvc:
        return jsonify({'success': False, 'message': 'Không tìm thấy đơn hàng hoặc không có quyền'}), 404
    
    try:
        dh_ctvc.TrangThai = DHCTVCStatus.delivered
        dh_ctvc.ThoiGianGiaoThucTe = datetime.now()
        
        # Cập nhật trạng thái đơn hàng
        order = DonHang.query.get(ma_dh)
        if order:
            order.TrangThai = OrderStatus.delivered
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã đánh dấu giao thành công'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# ================================================
# API ROUTES
# ================================================

@api_bp.route('/products')
def get_products():
    """API lấy danh sách sản phẩm"""
    products = SanPham.query.filter_by(TrangThai=ProductStatus.active).all()
    return jsonify([p.to_dict() for p in products])

@api_bp.route('/orders')
@login_required
def get_orders():
    """API lấy danh sách đơn hàng"""
    orders = DonHang.query.all()
    return jsonify([o.to_dict() for o in orders])

@api_bp.route('/orders/<ma_dh>')
def get_order(ma_dh):
    """API lấy chi tiết đơn hàng"""
    order = DonHang.query.get_or_404(ma_dh)
    order_dict = order.to_dict()
    order_dict['chi_tiets'] = [ct.to_dict() for ct in order.chi_tiets]
    return jsonify(order_dict)

# ================================================
# CUSTOMER ROUTES
# ================================================

@customer_bp.route('/')
@role_required('customer')
def home():
    """Trang chủ khách hàng - danh sách sản phẩm"""
    products = SanPham.query.filter_by(TrangThai=ProductStatus.active).all()
    
    # Get cart count
    cart = session.get('cart', {})
    cart_count = sum(item['quantity'] for item in cart.values())
    
    return render_template('customer/home.html', products=products, cart_count=cart_count)

@customer_bp.route('/cart')
@role_required('customer')
def cart():
    """Giỏ hàng"""
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    
    for ma_sp, item in cart.items():
        product = SanPham.query.get(ma_sp)
        if product:
            subtotal = item['quantity'] * float(product.DonGia)
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'subtotal': subtotal
            })
            total += subtotal
    
    return render_template('customer/cart.html', cart_items=cart_items, total=total)

@customer_bp.route('/cart/add/<ma_sp>', methods=['POST'])
@role_required('customer')
def add_to_cart(ma_sp):
    """Thêm sản phẩm vào giỏ hàng"""
    product = SanPham.query.get_or_404(ma_sp)
    quantity = int(request.form.get('quantity', 1))
    
    cart = session.get('cart', {})
    
    if ma_sp in cart:
        cart[ma_sp]['quantity'] += quantity
    else:
        cart[ma_sp] = {
            'quantity': quantity,
            'price': float(product.DonGia),
            'name': product.TenSP
        }
    
    session['cart'] = cart
    return jsonify({'success': True, 'message': f'Đã thêm {quantity} {product.DonVi} {product.TenSP} vào giỏ hàng'})

@customer_bp.route('/cart/update/<ma_sp>', methods=['POST'])
@role_required('customer')
def update_cart(ma_sp):
    """Cập nhật số lượng trong giỏ hàng"""
    quantity = int(request.form.get('quantity', 1))
    cart = session.get('cart', {})
    
    if ma_sp in cart:
        if quantity > 0:
            cart[ma_sp]['quantity'] = quantity
        else:
            del cart[ma_sp]
    
    session['cart'] = cart
    return jsonify({'success': True})

@customer_bp.route('/cart/remove/<ma_sp>', methods=['POST'])
@role_required('customer')
def remove_from_cart(ma_sp):
    """Xóa sản phẩm khỏi giỏ hàng"""
    cart = session.get('cart', {})
    
    if ma_sp in cart:
        del cart[ma_sp]
        session['cart'] = cart
    
    return jsonify({'success': True})

@customer_bp.route('/orders')
@role_required('customer')
def orders():
    """Danh sách đơn hàng của khách"""
    from sqlalchemy.orm import joinedload
    
    nguoi_dung = NguoiDung.query.filter_by(username=session['username']).first()
    if not nguoi_dung:
        flash('Không tìm thấy thông tin khách hàng', 'danger')
        return redirect(url_for('customer.home'))
    
    orders = DonHang.query.options(
        joinedload(DonHang.chi_tiets).joinedload(CTHD.san_pham)
    ).filter_by(MaND=nguoi_dung.MaND).order_by(DonHang.NgayTao.desc()).all()
    
    return render_template('customer/orders.html', orders=orders)

@customer_bp.route('/orders/create', methods=['POST'])
@role_required('customer')
def create_order():
    """Tạo đơn hàng từ giỏ hàng"""
    cart = session.get('cart', {})
    
    if not cart:
        return jsonify({'success': False, 'message': 'Giỏ hàng trống'}), 400
    
    try:
        # Lấy thông tin khách hàng
        nguoi_dung = NguoiDung.query.filter_by(username=session['username']).first()
        if not nguoi_dung:
            return jsonify({'success': False, 'message': 'Không tìm thấy thông tin khách hàng'}), 400
        
        # Lấy thông tin từ form
        dia_chi = request.form.get('dia_chi', nguoi_dung.DiaChi)
        lat = request.form.get('lat', nguoi_dung.Lat)
        lon = request.form.get('lon', nguoi_dung.Lon)
        ghi_chu = request.form.get('ghi_chu', '')
        ready_time = int(request.form.get('ready_time', 0))
        due_date = int(request.form.get('due_date', 240))
        service_time = int(request.form.get('service_time', 10))
        
        # Tạo đơn hàng
        ma_dh = generate_order_id()
        don_hang = DonHang(
            MaDH=ma_dh,
            MaND=nguoi_dung.MaND,
            DiaChi=dia_chi,
            Lat=Decimal(str(lat)) if lat else nguoi_dung.Lat,
            Lon=Decimal(str(lon)) if lon else nguoi_dung.Lon,
            NgayTao=datetime.now(),
            TrangThai=OrderStatus.pending,
            GhiChu=ghi_chu,
            READY_TIME=ready_time,
            DUE_DATE=due_date,
            SERVICE_TIME=service_time
        )
        db.session.add(don_hang)
        
        # Tạo chi tiết đơn hàng
        total_weight = 0
        for ma_sp, item in cart.items():
            product = SanPham.query.get(ma_sp)
            if product:
                cthd = CTHD(
                    MaDH=ma_dh,
                    MaSP=ma_sp,
                    SoLuong=item['quantity'],
                    DonGia=product.DonGia,
                    ThanhTien=Decimal(str(item['quantity'])) * product.DonGia
                )
                db.session.add(cthd)
                total_weight += item['quantity']
        
        db.session.commit()
        
        # Xóa giỏ hàng
        session.pop('cart', None)
        
        return jsonify({'success': True, 'ma_dh': ma_dh, 'message': f'Đặt hàng thành công! Mã đơn hàng: {ma_dh}'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@customer_bp.route('/orders/<ma_dh>')
@role_required('customer')
def order_detail(ma_dh):
    """Chi tiết đơn hàng"""
    from sqlalchemy.orm import joinedload
    
    nguoi_dung = NguoiDung.query.filter_by(username=session['username']).first()
    
    order = DonHang.query.options(
        joinedload(DonHang.chi_tiets).joinedload(CTHD.san_pham)
    ).filter_by(MaDH=ma_dh, MaND=nguoi_dung.MaND).first_or_404()
    
    # Lấy thông tin vận chuyển nếu có
    donhang_ctvc = DonHangCTVC.query.filter_by(MaDH=ma_dh).first()
    ctvc = None
    tai_xe = None
    if donhang_ctvc:
        ctvc = CTVC.query.get(donhang_ctvc.CTVC_id)
        if ctvc:
            tai_xe = TaiXe.query.get(ctvc.MaTX)
    
    return render_template('customer/order_detail.html', 
                         order=order, 
                         donhang_ctvc=donhang_ctvc,
                         ctvc=ctvc,
                         tai_xe=tai_xe)

@customer_bp.route('/orders/<ma_dh>/track')
@role_required('customer')
def track_order(ma_dh):
    """Theo dõi vận chuyển đơn hàng"""
    from sqlalchemy.orm import joinedload
    
    nguoi_dung = NguoiDung.query.filter_by(username=session['username']).first()
    
    order = DonHang.query.options(
        joinedload(DonHang.chi_tiets).joinedload(CTHD.san_pham)
    ).filter_by(MaDH=ma_dh, MaND=nguoi_dung.MaND).first_or_404()
    
    # Lấy thông tin vận chuyển
    donhang_ctvc = DonHangCTVC.query.filter_by(MaDH=ma_dh).first()
    if not donhang_ctvc:
        flash('Đơn hàng chưa được gán tài xế', 'warning')
        return redirect(url_for('customer.order_detail', ma_dh=ma_dh))
    
    ctvc = CTVC.query.options(joinedload(CTVC.tai_xe)).get(donhang_ctvc.CTVC_id)
    
    # Lấy tất cả đơn hàng trong cùng tuyến để hiển thị route
    all_orders = DonHangCTVC.query.options(
        joinedload(DonHangCTVC.don_hang).joinedload(DonHang.nguoi_dung)
    ).filter_by(CTVC_id=donhang_ctvc.CTVC_id).order_by(DonHangCTVC.ThuTu).all()
    
    return render_template('customer/tracking.html', 
                         order=order,
                         donhang_ctvc=donhang_ctvc,
                         ctvc=ctvc,
                         all_orders=all_orders)
