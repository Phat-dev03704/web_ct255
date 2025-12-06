"""
Quick test - Chạy 1 dataset để kiểm tra visualization
"""
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simplified_hybrid_vrptw_solver import SimplifiedHybridVRPTWSolver

print("="*100)
print("QUICK TEST - HYBRID SOLVER WITH VISUALIZATION")
print("="*100)

# Dataset path
dataset_path = r"d:\My Studing\Nghiệp vụ thông minh\project\Vehicle Routing Problem\code\dataset\C1\C101.csv"

if not os.path.exists(dataset_path):
    print(f"❌ Dataset not found: {dataset_path}")
    sys.exit(1)

print(f"\n✓ Dataset: {dataset_path}")

# Create output directory
output_dir = Path(r"d:\My Studing\Nghiệp vụ thông minh\project\Vehicle Routing Problem\code\algorithm\Hybrid-CW-LNS\result")
output_dir.mkdir(parents=True, exist_ok=True)

print(f"✓ Output directory: {output_dir}")

# Test with cw_only mode (fastest)
print("\n" + "="*100)
print("Testing CW_ONLY mode...")
print("="*100)

try:
    solver = SimplifiedHybridVRPTWSolver(
        dataset_path=dataset_path,
        mode='cw_only'
    )
    print("✓ Solver created")
    
    solution = solver.solve(verbose=True)
    print(f"\n✓ Solution found")
    print(f"  Distance: {solution['total_distance']:.2f}")
    print(f"  Vehicles: {solution['num_vehicles']}")
    print(f"  Time: {solver.solve_time:.2f}s")
    
    # Save results
    print(f"\nSaving results...")
    result_data = solver.save_all_results(output_dir=str(output_dir))
    
    print("\n" + "="*100)
    print("✅ TEST SUCCESSFUL!")
    print("="*100)
    print(f"Check results in: {output_dir}")
    print(f"  - Images: {output_dir / 'images'}")
    print(f"  - Text:   {output_dir / 'text'}")
    
except Exception as e:
    print("\n" + "="*100)
    print("❌ TEST FAILED!")
    print("="*100)
    print(f"Error: {str(e)}")
    
    import traceback
    traceback.print_exc()
