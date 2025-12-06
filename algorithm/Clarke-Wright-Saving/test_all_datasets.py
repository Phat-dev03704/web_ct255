"""
Script để test Clarke-Wright solver trên tất cả 56 datasets
Kết quả được lưu vào thư mục result/ với cấu trúc:
- result/images/: Chứa các file PNG trực quan hóa
- result/text/: Chứa các file TXT báo cáo
"""

import sys
from pathlib import Path
import time
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Sử dụng backend không hiển thị GUI
import matplotlib.pyplot as plt

# Import solver
from cw_vrptw_solver import ClarkeWrightVRPTWSolver


def test_all_datasets():
    """Test Clarke-Wright solver trên tất cả 56 datasets"""
    
    # Đường dẫn đến thư mục dataset
    current_dir = Path(__file__).parent
    code_dir = current_dir.parent.parent
    dataset_base = code_dir / "dataset"
    
    print(f"📁 Thư mục hiện tại: {current_dir}")
    print(f"📁 Thư mục code: {code_dir}")
    print(f"📁 Thư mục dataset: {dataset_base}")
    print(f"📁 Dataset tồn tại: {dataset_base.exists()}")
    print()
    
    # Danh sách các categories và files
    categories = {
        'C1': ['C101', 'C102', 'C103', 'C104', 'C105', 'C106', 'C107', 'C108', 'C109'],
        'C2': ['C201', 'C202', 'C203', 'C204', 'C205', 'C206', 'C207', 'C208'],
        'R1': ['R101', 'R102', 'R103', 'R104', 'R105', 'R106', 'R107', 'R108', 'R109', 'R110', 'R111', 'R112'],
        'R2': ['R201', 'R202', 'R203', 'R204', 'R205', 'R206', 'R207', 'R208', 'R209', 'R210', 'R211'],
        'RC1': ['RC101', 'RC102', 'RC103', 'RC104', 'RC105', 'RC106', 'RC107', 'RC108'],
        'RC2': ['RC201', 'RC202', 'RC203', 'RC204', 'RC205', 'RC206', 'RC207', 'RC208']
    }
    
    # Tạo thư mục kết quả
    result_dir = Path(__file__).parent / 'result'
    images_dir = result_dir / 'images'
    text_dir = result_dir / 'text'
    images_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    
    # Thống kê
    total_datasets = sum(len(files) for files in categories.values())
    success_count = 0
    failed_count = 0
    results_summary = []
    
    print("="*100)
    print("TEST CLARKE-WRIGHT SAVINGS ALGORITHM TRÊN TẤT CẢ 56 DATASETS")
    print("="*100)
    print(f"Thư mục kết quả: {result_dir}")
    print(f"  - Images: {images_dir}")
    print(f"  - Text: {text_dir}")
    print("="*100)
    print(f"✓ Clarke-Wright: Thuật toán Heuristic nhanh và hiệu quả")
    print(f"✓ Có thể giải toàn bộ dataset (100+ khách hàng)")
    print(f"✓ Thời gian giải: Rất nhanh (< 5 giây/dataset)")
    print("="*100)
    
    start_time_all = time.time()
    dataset_count = 0
    
    # Duyệt qua từng category
    for category, files in categories.items():
        print(f"\n{'#'*100}")
        print(f"CATEGORY: {category} ({len(files)} datasets)")
        print(f"{'#'*100}")
        
        for dataset_name in files:
            dataset_count += 1
            dataset_path = dataset_base / category / f"{dataset_name}.csv"
            
            print(f"\n[{dataset_count}/{total_datasets}] Testing: {dataset_name}")
            print("-"*100)
            
            try:
                # Tạo solver
                solver = ClarkeWrightVRPTWSolver(
                    dataset_path=str(dataset_path),
                    vehicle_capacity=200,
                    max_vehicles=25
                )
                
                # Giải bài toán
                result = solver.solve()
                
                if result:
                    # Lưu kết quả
                    solver.visualize_solution(save=True)
                    solver.save_solution(solve_time=result['time'], status=result['status'])
                    
                    success_count += 1
                    results_summary.append({
                        'Dataset': dataset_name,
                        'Category': category,
                        'Status': result['status'],
                        'Vehicles': len(result['routes']),
                        'Distance': result['objective'],
                        'Time': result['time']
                    })
                    
                    print(f"✓ Thành công: {dataset_name}")
                    print(f"  - Trạng thái: {result['status']}")
                    print(f"  - Số xe: {len(result['routes'])}")
                    print(f"  - Quãng đường: {result['objective']:.2f}")
                    print(f"  - Thời gian: {result['time']:.2f}s")
                else:
                    failed_count += 1
                    results_summary.append({
                        'Dataset': dataset_name,
                        'Category': category,
                        'Status': 'Failed',
                        'Vehicles': 0,
                        'Distance': 0,
                        'Time': 0
                    })
                    print(f"✗ Thất bại: {dataset_name}")
                
            except Exception as e:
                failed_count += 1
                results_summary.append({
                    'Dataset': dataset_name,
                    'Category': category,
                    'Status': f'Error: {str(e)}',
                    'Vehicles': 0,
                    'Distance': 0,
                    'Time': 0
                })
                print(f"✗ Lỗi: {dataset_name} - {str(e)}")
    
    total_time = time.time() - start_time_all
    
    # In tóm tắt
    print("\n" + "="*100)
    print("TÓM TẮT KẾT QUẢ TEST")
    print("="*100)
    print(f"Tổng số datasets: {total_datasets}")
    print(f"Thành công: {success_count} ({success_count/total_datasets*100:.1f}%)")
    print(f"Thất bại: {failed_count} ({failed_count/total_datasets*100:.1f}%)")
    print(f"Tổng thời gian: {total_time:.2f}s ({total_time/60:.2f} phút)")
    print(f"Thời gian trung bình/dataset: {total_time/total_datasets:.2f}s")
    print("="*100)
    
    # Lưu tóm tắt vào file
    summary_df = pd.DataFrame(results_summary)
    summary_path = result_dir / 'test_summary.csv'
    summary_df.to_csv(str(summary_path), index=False, encoding='utf-8')
    print(f"\n✓ Đã lưu tóm tắt: {summary_path}")
    
    # Tạo báo cáo chi tiết
    report_path = result_dir / 'test_report.txt'
    with open(str(report_path), 'w', encoding='utf-8') as f:
        f.write("="*100 + "\n")
        f.write("BÁO CÁO TEST CLARKE-WRIGHT SAVINGS ALGORITHM TRÊN 56 DATASETS\n")
        f.write("="*100 + "\n\n")
        
        f.write(f"Ngày giờ test: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Tổng số datasets: {total_datasets}\n")
        f.write(f"Thành công: {success_count} ({success_count/total_datasets*100:.1f}%)\n")
        f.write(f"Thất bại: {failed_count} ({failed_count/total_datasets*100:.1f}%)\n")
        f.write(f"Tổng thời gian: {total_time:.2f}s ({total_time/60:.2f} phút)\n")
        f.write(f"Thời gian trung bình: {total_time/total_datasets:.2f}s/dataset\n\n")
        
        f.write("="*100 + "\n")
        f.write("CHI TIẾT KẾT QUẢ THEO CATEGORY\n")
        f.write("="*100 + "\n\n")
        
        for category in categories.keys():
            cat_results = summary_df[summary_df['Category'] == category]
            f.write(f"\n{category}:\n")
            f.write("-"*100 + "\n")
            f.write(f"{'Dataset':<15} {'Status':<30} {'Vehicles':<10} {'Distance':<15} {'Time (s)':<10}\n")
            f.write("-"*100 + "\n")
            
            for _, row in cat_results.iterrows():
                f.write(f"{row['Dataset']:<15} {row['Status']:<30} {row['Vehicles']:<10} "
                       f"{row['Distance']:<15.2f} {row['Time']:<10.2f}\n")
        
        f.write("\n" + "="*100 + "\n")
        f.write("KẾT THÚC BÁO CÁO\n")
        f.write("="*100 + "\n")
    
    print(f"✓ Đã lưu báo cáo chi tiết: {report_path}")
    
    print("\n" + "="*100)
    print("HOÀN THÀNH TEST TẤT CẢ DATASETS!")
    print("="*100)
    print(f"\nKết quả được lưu tại: {result_dir}")
    print(f"  📊 Tóm tắt CSV: test_summary.csv")
    print(f"  📄 Báo cáo TXT: test_report.txt")
    print(f"  🖼️ Hình ảnh: images/ ({success_count} files)")
    print(f"  📝 Chi tiết: text/ ({success_count} files)")


if __name__ == "__main__":
    test_all_datasets()
