"""
Test Particle Swarm Optimization solver với tất cả datasets Solomon
Chạy 56 datasets, tạo tổng kết và báo cáo chi tiết
"""

import sys
from pathlib import Path
import time
import pandas as pd

# Add parent directory to path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from pso_vrptw_solver import ParticleSwarmVRPTWSolver

def test_all_datasets():
    print("="*80)
    print("TEST PARTICLE SWARM OPTIMIZATION VỚI TẤT CẢ DATASETS SOLOMON")
    print("="*80)
    print("📊 Tổng số datasets: 56")
    print("🐦 Phương pháp: Particle Swarm Optimization (Swarm Intelligence)")
    print("✓ Tự động điều chỉnh hyperparameters theo kích thước bài toán")
    print("="*80 + "\n")
    code_dir = current_dir.parent.parent
    dataset_base = code_dir / "dataset"
    categories = {
        "C1": ["C101", "C102", "C103", "C104", "C105", "C106", "C107", "C108", "C109"],
        "C2": ["C201", "C202", "C203", "C204", "C205", "C206", "C207", "C208"],
        "R1": ["R101", "R102", "R103", "R104", "R105", "R106", "R107", "R108", "R109", "R110", "R111", "R112"],
        "R2": ["R201", "R202", "R203", "R204", "R205", "R206", "R207", "R208", "R209", "R210", "R211"],
        "RC1": ["RC101", "RC102", "RC103", "RC104", "RC105", "RC106", "RC107", "RC108"],
        "RC2": ["RC201", "RC202", "RC203", "RC204", "RC205", "RC206", "RC207", "RC208"]
    }
    results = []
    total_start_time = time.time()
    dataset_count = 0
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
            solver = ParticleSwarmVRPTWSolver(
                dataset_path=str(dataset_path),
                vehicle_capacity=200,
                max_vehicles=25
            )
            hyperparams = solver.get_recommended_hyperparameters()
            result = solver.solve(**hyperparams)
            if result:
                # Tạo hình ảnh trực quan
                solver.visualize_solution(save=True)
                # Lưu báo cáo text
                solver.save_solution(
                    solve_time=result['time'],
                    status=result['status'],
                    iterations=result['iterations']
                )
                results.append({
                    'dataset': file_name,
                    'category': category,
                    'objective': result['objective'],
                    'time': result['time'],
                    'iterations': result['iterations'],
                    'num_routes': len(result['routes'])
                })
                print(f"✓ Hoàn thành: {len(result['routes'])} xe, {result['objective']:.2f} km")
    total_time = time.time() - total_start_time
    print("\n" + "="*80)
    print(f"TỔNG KẾT TEST PSO - Tổng thời gian: {total_time:.2f} giây")
    print("="*80)
    df = pd.DataFrame(results)
    summary_path = current_dir / "result" / "test_summary.csv"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(summary_path, index=False)
    print(f"✓ Đã lưu tổng kết: {summary_path}")

def main():
    test_all_datasets()

if __name__ == "__main__":
    main()
