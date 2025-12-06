# HƯỚNG DẪN SỬ DỤNG TÍNH NĂNG KHÁCH HÀNG

## Tổng quan
Hệ thống đã được bổ sung đầy đủ chức năng cho khách hàng:
- Xem sản phẩm và thêm vào giỏ hàng
- Đặt hàng trực tuyến
- Quản lý đơn hàng của bản thân
- Theo dõi vận chuyển real-time với bản đồ

## Đăng nhập

### Tài khoản khách hàng mẫu:
- **Username**: customer1 hoặc customer2
- **Password**: password123

Sau khi đăng nhập, hệ thống sẽ chuyển đến trang chủ khách hàng.

## Chức năng

### 1. Trang chủ (/customer/)
- Hiển thị danh sách sản phẩm dạng grid
- Mỗi sản phẩm có:
  - Hình ảnh
  - Tên, mô tả
  - Giá, đơn vị
  - Số lượng muốn mua
  - Nút "Thêm vào giỏ"
- Thêm sản phẩm vào giỏ bằng AJAX (không reload page)

### 2. Giỏ hàng (/customer/cart)
- Hiển thị danh sách sản phẩm trong giỏ
- Chức năng:
  - Tăng/giảm số lượng
  - Xóa sản phẩm
  - Xem tổng tiền
  - Nút "Đặt hàng"
- Modal đặt hàng với các thông tin:
  - Địa chỉ giao hàng
  - Tọa độ (Latitude, Longitude)
  - Ghi chú
  - Thời gian giao hàng mong muốn

### 3. Đơn hàng của tôi (/customer/orders)
- Danh sách tất cả đơn hàng đã đặt
- Mỗi đơn hàng hiển thị:
  - Mã đơn hàng
  - Ngày đặt
  - Địa chỉ giao hàng
  - Danh sách sản phẩm (tối đa 3, còn lại hiển thị "...")
  - Tổng tiền
  - Trạng thái: Chờ xử lý / Đang giao / Đã giao
  - Nút "Chi tiết" và "Theo dõi"

### 4. Chi tiết đơn hàng (/customer/orders/<ma_dh>)
- Thông tin đầy đủ về đơn hàng:
  - Mã đơn, ngày đặt, trạng thái
  - Địa chỉ giao hàng với tọa độ
  - Bảng chi tiết sản phẩm (hình ảnh, số lượng, giá)
  - Tổng tiền
- Thông tin vận chuyển (nếu đã được gán tài xế):
  - Tên tài xế
  - Số điện thoại
  - Biển số xe
  - Thứ tự giao hàng trong tuyến
  - Trạng thái giao hàng
  - Thời gian giao thực tế
  - Nút "Theo dõi vận chuyển"

### 5. Theo dõi vận chuyển (/customer/orders/<ma_dh>/track)
**Đây là tính năng chính để khách hàng biết tài xế đang ở đâu!**

#### Bản đồ hiển thị:
- **Vị trí của bạn**: Icon nhà màu đỏ (🏠)
- **Tài xế**: Icon xe tải (🚚) tại điểm giao hàng cuối cùng đã hoàn thành
- **Các điểm giao khác**: Số thứ tự trong vòng tròn
  - Màu xanh lá: Đã giao
  - Màu xanh dương: Chưa giao
- **Tuyến đường**: Đường màu xanh với mũi tên chỉ hướng
- **Route OSRM**: Tuyến đường thực tế trên đường phố

#### Thông tin bên phải:
- **Tài xế**: Tên, SĐT, biển số xe
- **Địa chỉ của bạn**: Địa chỉ giao hàng
- **Tuyến giao hàng**: Danh sách tất cả các điểm giao theo thứ tự
  - Điểm của bạn được highlight màu đỏ
  - Icon check ✓ cho điểm đã giao
  - Icon xe 🚚 cho điểm đang giao

#### Cập nhật real-time:
- Trang tự động reload sau mỗi 30 giây
- Nút "Làm mới" để cập nhật thủ công
- Khi tài xế hoàn thành đơn hàng trước đó, icon 🚚 sẽ di chuyển gần hơn đến bạn

## Luồng hoạt động

### Khách hàng đặt hàng:
1. Đăng nhập với customer1/password123
2. Vào "Trang chủ" → Chọn sản phẩm → "Thêm vào giỏ"
3. Vào "Giỏ hàng" → Điều chỉnh số lượng → "Đặt hàng"
4. Nhập địa chỉ giao hàng và tọa độ → "Xác nhận đặt hàng"
5. Đơn hàng được tạo với trạng thái "Chờ xử lý"

### Admin tối ưu tuyến:
1. Đăng nhập admin/password123
2. Vào "Optimize Routes"
3. Chọn các đơn hàng pending → "Optimize"
4. Hệ thống tạo tuyến và phân công tài xế
5. Đơn hàng chuyển sang "Đang giao"

### Tài xế giao hàng:
1. Đăng nhập driver1/password123
2. Xem tuyến được gán
3. Click "Xem chi tiết" → Xem bản đồ
4. Giao hàng theo thứ tự và đánh dấu "Hoàn thành"

### Khách hàng theo dõi:
1. Vào "Đơn hàng" → Chọn đơn đang giao
2. Click "Theo dõi"
3. Xem bản đồ với vị trí tài xế (🚚)
4. Biết được tài xế đang ở điểm nào trong tuyến
5. Mỗi khi tài xế hoàn thành 1 đơn, icon 🚚 di chuyển đến điểm tiếp theo

## API Endpoints

### Customer Routes:
- `GET /customer/` - Trang chủ sản phẩm
- `GET /customer/cart` - Giỏ hàng
- `POST /customer/cart/add/<ma_sp>` - Thêm vào giỏ
- `POST /customer/cart/update/<ma_sp>` - Cập nhật số lượng
- `POST /customer/cart/remove/<ma_sp>` - Xóa khỏi giỏ
- `GET /customer/orders` - Danh sách đơn hàng
- `POST /customer/orders/create` - Tạo đơn hàng mới
- `GET /customer/orders/<ma_dh>` - Chi tiết đơn hàng
- `GET /customer/orders/<ma_dh>/track` - Theo dõi vận chuyển

## Database Changes

### NGUOI_DUNG:
- KH_16: username = 'customer1'
- KH_17: username = 'customer2'

### Session Cart:
```python
session['cart'] = {
    'SP001': {
        'quantity': 10,
        'price': 45000,
        'name': 'Apple'
    },
    'SP002': {
        'quantity': 5,
        'price': 60000,
        'name': 'Mango'
    }
}
```

## Ghi chú kỹ thuật

### Real-time Tracking:
- Vị trí tài xế = Điểm giao hàng cuối cùng đã hoàn thành (delivered)
- Sử dụng `DonHangCTVC.TrangThai = 'delivered'` để xác định
- Auto-refresh sau 30s hoặc manual refresh
- OSRM API để vẽ tuyến đường thực tế

### Icons:
- 🏠 (Nhà đỏ): Vị trí khách hàng
- 🚚 (Xe tải): Vị trí tài xế hiện tại
- Số trong vòng tròn: Thứ tự các điểm giao (xanh dương = chưa giao, xanh lá = đã giao)

### Performance:
- Giỏ hàng lưu trong session (không cần database)
- AJAX cho add to cart (không reload)
- Lazy load cho order list
- Caching cho product images

## Testing

1. **Đăng nhập customer1**
2. **Thêm sản phẩm vào giỏ**
3. **Đặt hàng**
4. **Đăng nhập admin → Optimize routes** (chọn đơn vừa đặt)
5. **Đăng nhập driver1 → Giao 1-2 đơn trước đó**
6. **Quay lại customer1 → Vào "Theo dõi"**
7. **Quan sát icon 🚚 đang ở điểm nào**
8. **Đợi driver giao xong → Icon 🚚 di chuyển gần hơn**

## Troubleshooting

### Không thấy navbar customer:
- Kiểm tra `session['role'] == 'customer'`
- Đảm bảo đăng nhập với customer1/customer2

### Giỏ hàng không cập nhật:
- Kiểm tra session đang hoạt động
- Clear cookies và đăng nhập lại

### Không theo dõi được:
- Đơn hàng phải ở trạng thái "processing" hoặc "delivered"
- Đơn hàng phải được gán tài xế (có trong DONHANG_CTVC)

### Icon tài xế không hiện:
- Cần có ít nhất 1 đơn hàng đã giao (TrangThai = 'delivered')
- Kiểm tra `DonHangCTVC` có dữ liệu

## URL để test:

```
http://127.0.0.1:5000/auth/login
Username: customer1
Password: password123

→ Tự động chuyển đến: http://127.0.0.1:5000/customer/
```
