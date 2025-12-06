"""
Script tự động tạo trực quan hóa cho TẤT CẢ 56 datasets Solomon VRPTW
"""

from visualize_vrptw import VRPTWVisualizer
from pathlib import Path
import time

def visualize_all_datasets():
    """Tạo trực quan hóa cho tất cả 56 datasets"""
    
    # Đường dẫn đến thư mục dataset
    dataset_root = Path("../dataset")
    
    # Các categories
    categories = ['C1', 'C2', 'R1', 'R2', 'RC1', 'RC2']
    
    # Đếm số lượng
    total_datasets = 0
    processed = 0
    failed = []
    
    print("="*80)
    print("BẮT ĐẦU TRỰC QUAN HÓA TẤT CẢ DATASETS SOLOMON VRPTW")
    print("="*80)
    
    # Đếm tổng số file
    for category in categories:
        category_path = dataset_root / category
        if category_path.exists():
            csv_files = list(category_path.glob("*.csv"))
            total_datasets += len(csv_files)
    
    print(f"\nTổng số datasets tìm thấy: {total_datasets}")
    print(f"Thời gian ước tính: ~{total_datasets * 0.5:.1f} phút")
    print("\n" + "="*80 + "\n")
    
    start_time = time.time()
    
    # Xử lý từng category
    for category in categories:
        category_path = dataset_root / category
        
        if not category_path.exists():
            print(f"⚠️  Bỏ qua {category} - Thư mục không tồn tại")
            continue
        
        # Lấy tất cả file CSV trong category
        csv_files = sorted(category_path.glob("*.csv"))
        
        print(f"\n{'='*80}")
        print(f"📁 CATEGORY: {category} - {len(csv_files)} datasets")
        print(f"{'='*80}\n")
        
        # Xử lý từng dataset
        for idx, dataset_file in enumerate(csv_files, 1):
            try:
                processed += 1
                dataset_name = dataset_file.stem
                
                print(f"[{processed}/{total_datasets}] Đang xử lý: {category}/{dataset_name}.csv")
                
                # Tạo visualizer
                viz = VRPTWVisualizer(str(dataset_file))
                
                # In thống kê ngắn gọn
                print(f"  ├─ Số khách hàng: {len(viz.customers)}")
                print(f"  ├─ Tổng demand: {viz.customers['DEMAND'].sum()}")
                
                # Tạo các biểu đồ và LƯU ẢNH
                print(f"  ├─ Đang tạo 5 biểu đồ...")
                viz.plot_all(save=True)
                
                print(f"  └─ ✅ Hoàn thành: {dataset_name}")
                print()
                
            except Exception as e:
                print(f"  └─ ❌ LỖI: {str(e)}")
                failed.append(f"{category}/{dataset_file.name}")
                print()
    
    # Tổng kết
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print("\n" + "="*80)
    print("KẾT QUẢ TỔNG KẾT")
    print("="*80)
    print(f"✅ Đã xử lý thành công: {processed - len(failed)}/{total_datasets} datasets")
    print(f"❌ Thất bại: {len(failed)}/{total_datasets} datasets")
    print(f"⏱️  Thời gian thực hiện: {elapsed_time/60:.2f} phút")
    
    if failed:
        print(f"\n⚠️  Các file bị lỗi:")
        for f in failed:
            print(f"   - {f}")
    
    print(f"\n📁 Tất cả ảnh đã được lưu trong thư mục: visualize dataset/")
    print("="*80)
    
    # Tạo summary report
    create_summary_report(total_datasets, processed - len(failed), failed, elapsed_time)


def create_summary_report(total, success, failed_list, elapsed_time):
    """Tạo file báo cáo tổng kết"""
    
    report_path = "visualization_summary.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("BÁO CÁO TRỰC QUAN HÓA DATASETS SOLOMON VRPTW\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Thời gian thực hiện: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Tổng số datasets: {total}\n")
        f.write(f"Thành công: {success}\n")
        f.write(f"Thất bại: {len(failed_list)}\n")
        f.write(f"Thời gian: {elapsed_time/60:.2f} phút\n\n")
        
        if failed_list:
            f.write("Các file bị lỗi:\n")
            for item in failed_list:
                f.write(f"  - {item}\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("CÁC LOẠI ẢNH ĐÃ TẠO CHO MỖI DATASET:\n")
        f.write("="*80 + "\n\n")
        f.write("1. [dataset_name]_locations.png - Vị trí khách hàng và depot\n")
        f.write("2. [dataset_name]_time_windows.png - Gantt chart cửa sổ thời gian\n")
        f.write("3. [dataset_name]_demand.png - Phân phối nhu cầu\n")
        f.write("4. [dataset_name]_tw_demand.png - Time window vs Demand\n")
        f.write("5. [dataset_name]_heatmaps.png - Phân tích không gian-thời gian\n")
        f.write("\n" + "="*80 + "\n")
    
    print(f"\n📄 Báo cáo chi tiết đã được lưu: {report_path}")


def visualize_by_category(category_name):
    """Trực quan hóa chỉ một category cụ thể"""
    
    dataset_root = Path("../dataset")
    category_path = dataset_root / category_name
    
    if not category_path.exists():
        print(f"❌ Thư mục {category_name} không tồn tại!")
        return
    
    csv_files = sorted(category_path.glob("*.csv"))
    print(f"\n📁 Trực quan hóa category: {category_name}")
    print(f"Số lượng datasets: {len(csv_files)}\n")
    
    for idx, dataset_file in enumerate(csv_files, 1):
        try:
            print(f"[{idx}/{len(csv_files)}] Đang xử lý: {dataset_file.name}")
            viz = VRPTWVisualizer(str(dataset_file))
            viz.plot_all(save=True)
            print(f"✅ Hoàn thành\n")
        except Exception as e:
            print(f"❌ Lỗi: {str(e)}\n")


if __name__ == "__main__":
    # Chạy trực quan hóa tất cả datasets
    visualize_all_datasets()
    
    # Hoặc chỉ trực quan hóa một category:
    # visualize_by_category('C1')
