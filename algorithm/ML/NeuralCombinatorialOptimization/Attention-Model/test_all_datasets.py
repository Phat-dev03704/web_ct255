"""
Test Attention Model solver với tất cả datasets Solomon
Chạy 56 datasets, tạo tổng kết và báo cáo chi tiết
"""

import sys
from pathlib import Path
import time
import pandas as pd

# Add parent directory to path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from attention_vrptw_solver import AttentionModelVRPTWSolver


def test_all_datasets():
    """Test tất cả datasets với Attention Model"""
    
    print("="*80)
    print("TEST ATTENTION MODEL (DEEP RL) VỚI TẤT CẢ DATASETS SOLOMON")
    print("="*80)
    print("📊 Tổng số datasets: 56")
    print("🧠 Phương pháp: Attention Model (Neural Combinatorial Optimization)")
    print("✓ Transformer-based Deep Reinforcement Learning")
    print("="*80 + "\n")
    
    # Đường dẫn đến thư mục dataset
    code_dir = current_dir.parent.parent.parent.parent
    dataset_base = code_dir / "dataset"
    model_path = current_dir / "models" / "attention_model_best.pth"
    
    # Danh sách các thư mục và files
    categories = {
        "C1": ["C101", "C102", "C103", "C104", "C105", "C106", "C107", "C108", "C109"],
        "C2": ["C201", "C202", "C203", "C204", "C205", "C206", "C207", "C208"],
        "R1": ["R101", "R102", "R103", "R104", "R105", "R106", "R107", "R108", "R109", "R110", "R111", "R112"],
        "R2": ["R201", "R202", "R203", "R204", "R205", "R206", "R207", "R208", "R209", "R210", "R211"],
        "RC1": ["RC101", "RC102", "RC103", "RC104", "RC105", "RC106", "RC107", "RC108"],
        "RC2": ["RC201", "RC202", "RC203", "RC204", "RC205", "RC206", "RC207", "RC208"]
    }
    
    # Tổng hợp kết quả
    results = []
    
    total_start_time = time.time()
    dataset_count = 0
    
    # Duyệt qua tất cả datasets
    for category, files in categories.items():
        print(f"\n{'='*80}")
        print(f"CATEGORY: {category}")
        print(f"{'='*80}")
        
        for file_name in files:
            dataset_count += 1
            dataset_path = dataset_base / category / f"{file_name}.csv"
            
            if not dataset_path.exists():
                print(f"❌ Không tìm thấy: {dataset_path}")
                continue
            
            print(f"\n--- Dataset {dataset_count}: {file_name} ---")
            
            try:
                # Tạo solver
                solver = AttentionModelVRPTWSolver(
                    dataset_path=str(dataset_path),
                    vehicle_capacity=200,
                    max_vehicles=25,
                    model_path=str(model_path) if model_path.exists() else None
                )
                
                # Giải bài toán
                result = solver.solve(n_samples=10, use_beam_search=False)
                
                if result:
                    # Tạo hình ảnh trực quan
                    solver.visualize_solution(save=True)
                    
                    # Lưu báo cáo text
                    solver.save_solution(
                        solve_time=result['time'],
                        status=result['status'],
                        n_samples=result['n_samples']
                    )
                    
                    results.append({
                        'dataset': file_name,
                        'category': category,
                        'objective': result['objective'],
                        'time': result['time'],
                        'n_samples': result['n_samples'],
                        'num_routes': len(result['routes'])
                    })
                    
                    print(f"✓ Hoàn thành: {len(result['routes'])} xe, {result['objective']:.2f} km")
            
            except Exception as e:
                print(f"❌ Lỗi khi giải {file_name}: {str(e)}")
                results.append({
                    'dataset': file_name,
                    'category': category,
                    'objective': None,
                    'time': None,
                    'n_samples': None,
                    'num_routes': None,
                    'error': str(e)
                })
    
    total_time = time.time() - total_start_time
    
    # Tạo báo cáo tổng kết
    print("\n" + "="*80)
    print(f"TỔNG KẾT TEST ATTENTION MODEL - Tổng thời gian: {total_time:.2f} giây")
    print("="*80)
    
    # Lưu kết quả ra CSV
    df = pd.DataFrame(results)
    summary_path = current_dir / "result" / "test_summary.csv"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(summary_path, index=False)
    
    print(f"✓ Đã lưu tổng kết: {summary_path}")
    
    # In thống kê
    successful = df['objective'].notna().sum()
    print(f"\n📊 THỐNG KÊ:")
    print(f"  - Tổng số datasets: {len(df)}")
    print(f"  - Giải thành công: {successful}")
    print(f"  - Thất bại: {len(df) - successful}")
    
    if successful > 0:
        print(f"\n📈 KẾT QUẢ (các dataset thành công):")
        print(f"  - Trung bình quãng đường: {df['objective'].mean():.2f}")
        print(f"  - Trung bình số xe: {df['num_routes'].mean():.2f}")
        print(f"  - Trung bình thời gian: {df['time'].mean():.2f}s")
    
    # Tạo báo cáo chi tiết
    report_path = current_dir / "result" / "test_report.txt"
    with open(str(report_path), 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("BÁO CÁO TEST ATTENTION MODEL (DEEP RL) TRÊN TẤT CẢ DATASETS\n")
        f.write("="*80 + "\n\n")
        f.write(f"Tổng thời gian test: {total_time:.2f} giây\n")
        f.write(f"Ngày giờ: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("="*80 + "\n")
        f.write("THỐNG KÊ TỔNG QUÁT\n")
        f.write("="*80 + "\n")
        f.write(f"Tổng số datasets: {len(df)}\n")
        f.write(f"Giải thành công: {successful}\n")
        f.write(f"Thất bại: {len(df) - successful}\n\n")
        
        if successful > 0:
            f.write("="*80 + "\n")
            f.write("KẾT QUẢ (CÁC DATASET THÀNH CÔNG)\n")
            f.write("="*80 + "\n")
            f.write(f"Trung bình quãng đường: {df['objective'].mean():.2f}\n")
            f.write(f"Trung bình số xe: {df['num_routes'].mean():.2f}\n")
            f.write(f"Trung bình thời gian: {df['time'].mean():.2f}s\n\n")
        
        f.write("="*80 + "\n")
        f.write("CHI TIẾT TỪNG CATEGORY\n")
        f.write("="*80 + "\n\n")
        
        for category in categories.keys():
            cat_df = df[df['category'] == category]
            if len(cat_df) > 0:
                f.write(f"{category}:\n")
                f.write(f"  - Số datasets: {len(cat_df)}\n")
                f.write(f"  - Thành công: {cat_df['objective'].notna().sum()}\n")
                if cat_df['objective'].notna().sum() > 0:
                    f.write(f"  - TB quãng đường: {cat_df['objective'].mean():.2f}\n")
                    f.write(f"  - TB số xe: {cat_df['num_routes'].mean():.2f}\n")
                    f.write(f"  - TB thời gian: {cat_df['time'].mean():.2f}s\n")
                f.write("\n")
        
        f.write("="*80 + "\n")
        f.write("KẾT THÚC BÁO CÁO\n")
        f.write("="*80 + "\n")
    
    print(f"✓ Đã lưu báo cáo chi tiết: {report_path}")


def main():
    test_all_datasets()


if __name__ == "__main__":
    main()
