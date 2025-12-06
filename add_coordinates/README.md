Map editor: tạo điểm khách hàng bằng click trên bản đồ

Hướng dẫn nhanh
- Mở bằng file HTML trực tiếp: mở `add_coordinates/map_editor.html` trong trình duyệt.
- Hoặc chạy server (nên dùng khi trình duyệt chặn một số tính năng khi mở file://):

  ```powershell
  & "d:\\Information System\\Business Intelligence\\code\\.venv\\Scripts\\python.exe" "d:\\Information System\\Business Intelligence\\code\\add_coordinates\\serve_map.py"
  ```

Chức năng
- Click lên bản đồ: chọn vị trí để thêm.
- Điền ID/Tên và nhấn `Thêm từ form` để tạo marker.
- Chọn marker rồi `Đặt điểm được chọn làm Depot` nếu muốn.
- `Import CSV` để load danh sách có sẵn (hỗ trợ `lat/lon` hoặc `XCOORD./YCOORD.`).
- `Xuất CSV` để tải file `khach_hang_tu_tao.csv` xuống (định dạng: id,name,lat,lon,demand,ready_time,due_date,service_time).

Gợi ý
- Sau khi tải CSV, bạn có thể dùng `scripts/run_and_visualize.py --input path/to/khach_hang_tu_tao.csv` để chạy solver và xuất bản đồ.
