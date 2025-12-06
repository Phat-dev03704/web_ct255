"""
Visualization Tool for Solomon VRPTW Dataset
Công cụ trực quan hóa dataset Solomon cho bài toán VRP với cửa sổ thời gian
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import os

# Thiết lập style cho biểu đồ
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10

class VRPTWVisualizer:
    """Class để trực quan hóa dataset Solomon VRPTW"""
    
    def __init__(self, dataset_path):
        """
        Khởi tạo visualizer
        
        Args:
            dataset_path: Đường dẫn đến file CSV dataset
        """
        self.dataset_path = dataset_path
        self.data = pd.read_csv(dataset_path)
        self.dataset_name = Path(dataset_path).stem
        
        # Tách depot và customers
        self.depot = self.data.iloc[0]
        self.customers = self.data.iloc[1:]
        
        # Xác định thư mục gốc của visualize dataset
        self.base_dir = Path(__file__).parent
        self.images_dir = self.base_dir / 'visualize dataset images'
        self.txt_dir = self.base_dir / 'visulize dataset txt'
        
        # Tạo thư mục nếu chưa tồn tại
        self.images_dir.mkdir(exist_ok=True)
        self.txt_dir.mkdir(exist_ok=True)
        
    def plot_customer_locations(self, save=False):
        """
        Biểu đồ 1: Scatter plot - Vị trí các khách hàng và depot
        """
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # Vẽ customers với màu theo demand
        scatter = ax.scatter(self.customers['XCOORD.'], 
                           self.customers['YCOORD.'],
                           c=self.customers['DEMAND'],
                           s=100,
                           cmap='YlOrRd',
                           alpha=0.7,
                           edgecolors='black',
                           linewidth=1)
        
        # Vẽ depot
        ax.scatter(self.depot['XCOORD.'], 
                  self.depot['YCOORD.'],
                  c='blue',
                  s=500,
                  marker='s',
                  edgecolors='black',
                  linewidth=2,
                  label='Depot',
                  zorder=5)
        
        # Thêm số thứ tự khách hàng
        for idx, row in self.customers.iterrows():
            ax.annotate(str(int(row['CUST NO.'])), 
                       (row['XCOORD.'], row['YCOORD.']),
                       fontsize=8,
                       ha='center',
                       va='center')
        
        # Colorbar cho demand
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Demand (Nhu cầu)', rotation=270, labelpad=20)
        
        ax.set_xlabel('X Coordinate (Tọa độ X)')
        ax.set_ylabel('Y Coordinate (Tọa độ Y)')
        ax.set_title(f'Vị trí khách hàng và Depot - {self.dataset_name}', 
                    fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        if save:
            output_path = self.images_dir / f'{self.dataset_name}_locations.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
        
    def plot_time_windows(self, save=False):
        """
        Biểu đồ 2: Gantt chart - Cửa sổ thời gian của các khách hàng
        """
        fig, ax = plt.subplots(figsize=(14, 10))
        
        # Sắp xếp theo READY TIME
        customers_sorted = self.customers.sort_values('READY TIME')
        
        # Vẽ time windows
        for idx, (_, row) in enumerate(customers_sorted.iterrows()):
            ready_time = row['READY TIME']
            due_date = row['DUE DATE']
            service_time = row['SERVICE TIME']
            
            # Vẽ cửa sổ thời gian (màu xanh lá)
            ax.barh(idx, due_date - ready_time, 
                   left=ready_time, 
                   height=0.8,
                   color='lightgreen',
                   edgecolor='darkgreen',
                   alpha=0.7)
            
            # Vẽ service time (màu đỏ)
            ax.barh(idx, service_time,
                   left=ready_time,
                   height=0.4,
                   color='red',
                   alpha=0.8)
            
            # Thêm label customer number
            ax.text(-50, idx, f"C{int(row['CUST NO.'])}", 
                   va='center', ha='right', fontsize=8)
        
        ax.set_xlabel('Time (Thời gian)', fontsize=12)
        ax.set_ylabel('Customers (Khách hàng)', fontsize=12)
        ax.set_title(f'Cửa sổ thời gian của các khách hàng - {self.dataset_name}',
                    fontsize=14, fontweight='bold')
        ax.set_yticks([])
        
        # Legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='lightgreen', edgecolor='darkgreen', label='Time Window'),
            Patch(facecolor='red', label='Service Time')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        plt.tight_layout()
        if save:
            output_path = self.images_dir / f'{self.dataset_name}_time_windows.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
        
    def plot_demand_distribution(self, save=False):
        """
        Biểu đồ 3: Histogram - Phân phối nhu cầu
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Histogram
        axes[0].hist(self.customers['DEMAND'], 
                    bins=20, 
                    color='skyblue',
                    edgecolor='black',
                    alpha=0.7)
        axes[0].set_xlabel('Demand (Nhu cầu)')
        axes[0].set_ylabel('Frequency (Tần suất)')
        axes[0].set_title('Phân phối nhu cầu khách hàng')
        axes[0].grid(True, alpha=0.3)
        
        # Box plot
        axes[1].boxplot(self.customers['DEMAND'], vert=True)
        axes[1].set_ylabel('Demand (Nhu cầu)')
        axes[1].set_title('Box Plot - Nhu cầu khách hàng')
        axes[1].grid(True, alpha=0.3)
        
        fig.suptitle(f'Phân tích nhu cầu - {self.dataset_name}', 
                    fontsize=14, fontweight='bold', y=1.02)
        
        plt.tight_layout()
        if save:
            output_path = self.images_dir / f'{self.dataset_name}_demand.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
        
    def plot_time_window_width(self, save=False):
        """
        Biểu đồ 4: Scatter plot - Độ rộng cửa sổ thời gian vs Demand
        """
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Tính độ rộng time window
        tw_width = self.customers['DUE DATE'] - self.customers['READY TIME']
        
        scatter = ax.scatter(tw_width, 
                           self.customers['DEMAND'],
                           c=self.customers['READY TIME'],
                           s=100,
                           cmap='viridis',
                           alpha=0.7,
                           edgecolors='black',
                           linewidth=1)
        
        # Thêm colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Ready Time (Thời gian sẵn sàng)', rotation=270, labelpad=20)
        
        ax.set_xlabel('Time Window Width (Độ rộng cửa sổ thời gian)', fontsize=12)
        ax.set_ylabel('Demand (Nhu cầu)', fontsize=12)
        ax.set_title(f'Mối quan hệ giữa độ rộng Time Window và Demand - {self.dataset_name}',
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        if save:
            output_path = self.images_dir / f'{self.dataset_name}_tw_demand.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
        
    def plot_spatial_temporal_heatmap(self, save=False):
        """
        Biểu đồ 5: Heatmap - Phân bố không gian-thời gian
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 12))
        
        # 1. Heatmap theo vùng không gian (chia lưới)
        x_bins = np.linspace(self.data['XCOORD.'].min(), self.data['XCOORD.'].max(), 10)
        y_bins = np.linspace(self.data['YCOORD.'].min(), self.data['YCOORD.'].max(), 10)
        
        # Tạo heatmap cho demand
        hist_demand, x_edges, y_edges = np.histogram2d(
            self.customers['XCOORD.'], 
            self.customers['YCOORD.'],
            bins=[x_bins, y_bins],
            weights=self.customers['DEMAND']
        )
        
        im1 = axes[0, 0].imshow(hist_demand.T, origin='lower', cmap='YlOrRd', 
                               extent=[x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]],
                               aspect='auto')
        axes[0, 0].set_title('Heatmap - Tổng Demand theo vùng')
        axes[0, 0].set_xlabel('X Coordinate')
        axes[0, 0].set_ylabel('Y Coordinate')
        plt.colorbar(im1, ax=axes[0, 0], label='Total Demand')
        
        # 2. Histogram thời gian
        axes[0, 1].hist([self.customers['READY TIME'], self.customers['DUE DATE']], 
                       bins=30, 
                       label=['Ready Time', 'Due Date'],
                       color=['green', 'red'],
                       alpha=0.6)
        axes[0, 1].set_title('Phân phối thời gian')
        axes[0, 1].set_xlabel('Time')
        axes[0, 1].set_ylabel('Frequency')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Service time vs Distance from depot
        distances = np.sqrt((self.customers['XCOORD.'] - self.depot['XCOORD.'])**2 + 
                           (self.customers['YCOORD.'] - self.depot['YCOORD.'])**2)
        
        axes[1, 0].scatter(distances, self.customers['SERVICE TIME'], 
                          alpha=0.6, c=self.customers['DEMAND'], 
                          cmap='plasma', s=100, edgecolors='black', linewidth=1)
        axes[1, 0].set_title('Service Time vs Khoảng cách từ Depot')
        axes[1, 0].set_xlabel('Distance from Depot')
        axes[1, 0].set_ylabel('Service Time')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Correlation heatmap
        corr_data = self.customers[['XCOORD.', 'YCOORD.', 'DEMAND', 
                                    'READY TIME', 'DUE DATE', 'SERVICE TIME']].corr()
        sns.heatmap(corr_data, annot=True, fmt='.2f', cmap='coolwarm', 
                   center=0, ax=axes[1, 1], square=True)
        axes[1, 1].set_title('Correlation Matrix')
        
        fig.suptitle(f'Phân tích không gian-thời gian - {self.dataset_name}',
                    fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        if save:
            output_path = self.images_dir / f'{self.dataset_name}_heatmaps.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
        
    def plot_comprehensive_summary(self, save=False):
        """
        Tạo 1 biểu đồ tổng hợp duy nhất với 6 sub-plots được sắp xếp tối ưu
        Layout: Vị trí KH chiếm 50%, 4 biểu đồ nhỏ, 1 bảng thống kê
        """
        fig = plt.figure(figsize=(22, 14))
        gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.35, 
                             height_ratios=[2, 2, 0.8], width_ratios=[2, 1, 1])
        
        # Tính toán các giá trị cần dùng
        tw_width = self.customers['DUE DATE'] - self.customers['READY TIME']
        distances = np.sqrt((self.customers['XCOORD.'] - self.depot['XCOORD.'])**2 + 
                           (self.customers['YCOORD.'] - self.depot['YCOORD.'])**2)
        
        # ============= 1. VỊ TRÍ KHÔNG GIAN KHÁCH HÀNG & KHO (CHÍNH - LỚN) =============
        ax1 = fig.add_subplot(gs[0:2, 0])  # Chiếm 2 hàng, cột đầu
        
        # Vẽ customers với size theo time window width
        scatter1 = ax1.scatter(self.customers['XCOORD.'], 
                              self.customers['YCOORD.'],
                              c=self.customers['DEMAND'],
                              s=tw_width * 0.5 + 50,  # Size theo TW width
                              cmap='YlOrRd',
                              alpha=0.7,
                              edgecolors='black',
                              linewidth=1.5,
                              vmin=self.customers['DEMAND'].min(),
                              vmax=self.customers['DEMAND'].max())
        
        # Vẽ kho
        ax1.scatter(self.depot['XCOORD.'], 
                   self.depot['YCOORD.'],
                   c='blue',
                   s=800,
                   marker='s',
                   edgecolors='black',
                   linewidth=3,
                   label='Kho',
                   zorder=5)
        
        # Thêm số thứ tự khách hàng
        for idx, row in self.customers.iterrows():
            ax1.annotate(str(int(row['CUST NO.'])), 
                        (row['XCOORD.'], row['YCOORD.']),
                        fontsize=9,
                        ha='center',
                        va='center',
                        fontweight='bold')
        
        cbar1 = plt.colorbar(scatter1, ax=ax1, pad=0.02)
        cbar1.set_label('Nhu cầu (màu) | Kích thước = Độ rộng cửa sổ TG', 
                       rotation=270, labelpad=25, fontsize=10)
        ax1.set_xlabel('Tọa độ X', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Tọa độ Y', fontsize=12, fontweight='bold')
        ax1.set_title('① Phân bố không gian khách hàng và kho', 
                     fontweight='bold', fontsize=14, pad=12)
        ax1.legend(fontsize=11, loc='best', framealpha=0.9)
        ax1.grid(True, alpha=0.3, linestyle='--')
        
        # ============= 2. CỬA SỔ THỜI GIAN (GANTT CHART MINI) =============
        ax2 = fig.add_subplot(gs[0, 1:3])  # Chiếm 2 cột bên phải, hàng 1
        
        # Sắp xếp theo READY TIME
        customers_sorted = self.customers.sort_values('READY TIME').reset_index(drop=True)
        
        # Hiển thị tối đa 30 khách hàng để dễ nhìn
        max_display = min(30, len(customers_sorted))
        customers_display = customers_sorted.head(max_display)
        
        for idx, row in customers_display.iterrows():
            ready_time = row['READY TIME']
            due_date = row['DUE DATE']
            service_time = row['SERVICE TIME']
            
            # Vẽ cửa sổ thời gian
            ax2.barh(idx, due_date - ready_time, 
                    left=ready_time, 
                    height=0.8,
                    color='lightgreen',
                    edgecolor='darkgreen',
                    alpha=0.7,
                    linewidth=0.8)
            
            # Vẽ service time
            ax2.barh(idx, service_time,
                    left=ready_time,
                    height=0.4,
                    color='crimson',
                    alpha=0.9)
        
        ax2.set_xlabel('Thời gian', fontsize=11, fontweight='bold')
        ax2.set_ylabel(f'Khách hàng (top {max_display})', fontsize=11, fontweight='bold')
        ax2.set_title('② Cửa sổ thời gian phục vụ (Gantt Chart)', 
                     fontweight='bold', fontsize=14, pad=10)
        ax2.set_yticks([])
        
        # Legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='lightgreen', edgecolor='darkgreen', label='Khoảng TG được phép'),
            Patch(facecolor='crimson', label='TG phục vụ')
        ]
        ax2.legend(handles=legend_elements, loc='upper right', fontsize=9, framealpha=0.9)
        ax2.grid(True, alpha=0.3, axis='x', linestyle='--')
        
        # ============= 3. PHÂN PHỐI NHU CẦU =============
        ax3 = fig.add_subplot(gs[1, 1])
        
        n, bins, patches = ax3.hist(self.customers['DEMAND'], bins=18, 
                    color='steelblue', edgecolor='navy', alpha=0.75, linewidth=1.5)
        
        # Tô màu theo giá trị
        cm = plt.cm.YlOrRd
        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        col = bin_centers - min(bin_centers)
        col /= max(col)
        for c, p in zip(col, patches):
            plt.setp(p, 'facecolor', cm(c))
        
        ax3.axvline(self.customers['DEMAND'].mean(), color='red', 
                   linestyle='--', linewidth=2.5, label=f'TB: {self.customers["DEMAND"].mean():.1f}')
        ax3.axvline(self.customers['DEMAND'].median(), color='green',
                   linestyle=':', linewidth=2.5, label=f'Median: {self.customers["DEMAND"].median():.1f}')
        
        ax3.set_xlabel('Nhu cầu', fontsize=11, fontweight='bold')
        ax3.set_ylabel('Số lượng KH', fontsize=11, fontweight='bold')
        ax3.set_title('③ Phân phối nhu cầu', fontsize=13, fontweight='bold', pad=10)
        ax3.legend(fontsize=9, framealpha=0.9)
        ax3.grid(True, alpha=0.3, linestyle='--')
        
        # ============= 4. PHÂN PHỐI THỜI GIAN PHỤC VỤ =============
        ax4 = fig.add_subplot(gs[1, 2])
        
        ax4.hist(self.customers['SERVICE TIME'], bins=15,
                color='lightcoral', edgecolor='darkred', alpha=0.75, linewidth=1.5)
        ax4.axvline(self.customers['SERVICE TIME'].mean(), color='blue',
                   linestyle='--', linewidth=2.5, label=f'TB: {self.customers["SERVICE TIME"].mean():.1f}')
        
        ax4.set_xlabel('Thời gian phục vụ', fontsize=11, fontweight='bold')
        ax4.set_ylabel('Số lượng KH', fontsize=11, fontweight='bold')
        ax4.set_title('④ Phân phối TG phục vụ', fontsize=13, fontweight='bold', pad=10)
        ax4.legend(fontsize=9, framealpha=0.9)
        ax4.grid(True, alpha=0.3, linestyle='--')
        
        # ============= 5. KHOẢNG CÁCH vs ĐỘ RỘNG CỬA SỔ THỜI GIAN =============
        ax5 = fig.add_subplot(gs[2, 0])
        
        scatter5 = ax5.scatter(distances, 
                              tw_width,
                              c=self.customers['DEMAND'],
                              s=100,
                              cmap='plasma',
                              alpha=0.7,
                              edgecolors='black',
                              linewidth=1)
        
        cbar5 = plt.colorbar(scatter5, ax=ax5, pad=0.02)
        cbar5.set_label('Nhu cầu', rotation=270, labelpad=15, fontsize=10)
        
        ax5.set_xlabel('Khoảng cách từ kho', fontsize=11, fontweight='bold')
        ax5.set_ylabel('Độ rộng cửa sổ TG', fontsize=11, fontweight='bold')
        ax5.set_title('⑤ Tương quan: Khoảng cách - Cửa sổ thời gian', 
                     fontweight='bold', fontsize=13, pad=10)
        ax5.grid(True, alpha=0.3, linestyle='--')
        
        # ============= 6. THỐNG KÊ TỔNG HỢP =============
        ax6 = fig.add_subplot(gs[2, 1:3])
        ax6.axis('off')
        
        # Tạo bảng thống kê đẹp
        stats_data = [
            ['CHỈ SỐ', 'GIÁ TRỊ', 'CHỈ SỐ', 'GIÁ TRỊ'],
            ['Số khách hàng', f'{len(self.customers)}', 
             'Tổng nhu cầu', f'{self.customers["DEMAND"].sum()}'],
            ['Nhu cầu TB', f'{self.customers["DEMAND"].mean():.1f}',
             'Nhu cầu Min-Max', f'{self.customers["DEMAND"].min()}-{self.customers["DEMAND"].max()}'],
            ['Khoảng cách TB', f'{distances.mean():.1f}',
             'Khoảng cách Max', f'{distances.max():.1f}'],
            ['TW Width TB', f'{tw_width.mean():.1f}',
             'TW Width Min-Max', f'{tw_width.min():.0f}-{tw_width.max():.0f}'],
            ['Service Time TB', f'{self.customers["SERVICE TIME"].mean():.1f}',
             'Tổng Service Time', f'{self.customers["SERVICE TIME"].sum():.0f}'],
            ['Ready Time', f'{self.customers["READY TIME"].min():.0f} - {self.customers["READY TIME"].max():.0f}',
             'Due Date', f'{self.customers["DUE DATE"].min():.0f} - {self.customers["DUE DATE"].max():.0f}']
        ]
        
        table = ax6.table(cellText=stats_data, 
                         cellLoc='center',
                         loc='center',
                         bbox=[0, 0, 1, 1])
        
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2.2)
        
        # Định dạng header
        for i in range(4):
            cell = table[(0, i)]
            cell.set_facecolor('#4CAF50')
            cell.set_text_props(weight='bold', color='white', fontsize=11)
        
        # Định dạng các hàng xen kẽ
        for i in range(1, len(stats_data)):
            for j in range(4):
                cell = table[(i, j)]
                if i % 2 == 0:
                    cell.set_facecolor('#f0f0f0')
                else:
                    cell.set_facecolor('#ffffff')
                
                if j % 2 == 0:  # Cột label
                    cell.set_text_props(weight='bold', fontsize=10)
                else:  # Cột giá trị
                    cell.set_text_props(fontsize=10)
                    cell.set_facecolor('#e3f2fd' if i % 2 == 0 else '#f5f5f5')
        
        ax6.set_title('⑥ Thống kê tổng hợp', fontsize=13, fontweight='bold', pad=15)
        
        # ============= TIÊU ĐỀ CHÍNH =============
        fig.suptitle(f'TRỰC QUAN HÓA DATASET SOLOMON VRPTW - {self.dataset_name}', 
                    fontsize=19, fontweight='bold', y=0.998,
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.3))
        
        plt.tight_layout(rect=[0, 0, 1, 0.985])
        
        if save:
            # Lưu vào thư mục visualize dataset images
            output_path = self.images_dir / f'{self.dataset_name}_summary.png'
            plt.savefig(str(output_path), dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()
    
    def generate_text_report(self, save=False):
        """
        Tạo file báo cáo TXT chi tiết về dataset
        """
        # Tính toán các giá trị cần thiết
        tw_width = self.customers['DUE DATE'] - self.customers['READY TIME']
        distances = np.sqrt((self.customers['XCOORD.'] - self.depot['XCOORD.'])**2 + 
                           (self.customers['YCOORD.'] - self.depot['YCOORD.'])**2)
        
        # Tạo nội dung báo cáo
        report = []
        report.append("=" * 80)
        report.append(f"BÁO CÁO TRỰC QUAN HÓA DATASET SOLOMON VRPTW")
        report.append(f"Dataset: {self.dataset_name}")
        report.append("=" * 80)
        report.append("")
        
        # 1. THÔNG TIN TỔNG QUAN
        report.append("1. THÔNG TIN TỔNG QUAN")
        report.append("-" * 80)
        report.append(f"   Số lượng khách hàng: {len(self.customers)}")
        report.append(f"   Vị trí kho: ({self.depot['XCOORD.']:.1f}, {self.depot['YCOORD.']:.1f})")
        report.append("")
        
        # 2. PHÂN TÍCH NHU CẦU (DEMAND)
        report.append("2. PHÂN TÍCH NHU CẦU")
        report.append("-" * 80)
        report.append(f"   Tổng nhu cầu: {self.customers['DEMAND'].sum()}")
        report.append(f"   Nhu cầu trung bình: {self.customers['DEMAND'].mean():.2f}")
        report.append(f"   Nhu cầu median: {self.customers['DEMAND'].median():.2f}")
        report.append(f"   Nhu cầu min: {self.customers['DEMAND'].min()}")
        report.append(f"   Nhu cầu max: {self.customers['DEMAND'].max()}")
        report.append(f"   Độ lệch chuẩn: {self.customers['DEMAND'].std():.2f}")
        report.append("")
        
        # 3. PHÂN TÍCH CỬA SỔ THỜI GIAN
        report.append("3. PHÂN TÍCH CỬA SỔ THỜI GIAN")
        report.append("-" * 80)
        report.append(f"   Ready Time sớm nhất: {self.customers['READY TIME'].min():.0f}")
        report.append(f"   Ready Time muộn nhất: {self.customers['READY TIME'].max():.0f}")
        report.append(f"   Due Date sớm nhất: {self.customers['DUE DATE'].min():.0f}")
        report.append(f"   Due Date muộn nhất: {self.customers['DUE DATE'].max():.0f}")
        report.append(f"   Độ rộng TW trung bình: {tw_width.mean():.2f}")
        report.append(f"   Độ rộng TW median: {tw_width.median():.2f}")
        report.append(f"   Độ rộng TW min: {tw_width.min():.0f}")
        report.append(f"   Độ rộng TW max: {tw_width.max():.0f}")
        report.append(f"   Tổng khoảng thời gian: {self.customers['DUE DATE'].max() - self.customers['READY TIME'].min():.0f}")
        report.append("")
        
        # 4. PHÂN TÍCH THỜI GIAN PHỤC VỤ
        report.append("4. PHÂN TÍCH THỜI GIAN PHỤC VỤ")
        report.append("-" * 80)
        report.append(f"   Service Time trung bình: {self.customers['SERVICE TIME'].mean():.2f}")
        report.append(f"   Service Time median: {self.customers['SERVICE TIME'].median():.2f}")
        report.append(f"   Service Time min: {self.customers['SERVICE TIME'].min():.0f}")
        report.append(f"   Service Time max: {self.customers['SERVICE TIME'].max():.0f}")
        report.append(f"   Tổng Service Time: {self.customers['SERVICE TIME'].sum():.0f}")
        report.append("")
        
        # 5. PHÂN TÍCH KHÔNG GIAN
        report.append("5. PHÂN TÍCH KHÔNG GIAN")
        report.append("-" * 80)
        report.append(f"   Phạm vi tọa độ X: {self.customers['XCOORD.'].min():.1f} - {self.customers['XCOORD.'].max():.1f}")
        report.append(f"   Phạm vi tọa độ Y: {self.customers['YCOORD.'].min():.1f} - {self.customers['YCOORD.'].max():.1f}")
        report.append(f"   Khoảng cách trung bình từ kho: {distances.mean():.2f}")
        report.append(f"   Khoảng cách median từ kho: {distances.median():.2f}")
        report.append(f"   Khoảng cách min từ kho: {distances.min():.2f}")
        report.append(f"   Khoảng cách max từ kho: {distances.max():.2f}")
        report.append("")
        
        # 6. PHÂN TÍCH TƯƠNG QUAN
        report.append("6. PHÂN TÍCH TƯƠNG QUAN")
        report.append("-" * 80)
        corr_dist_tw = np.corrcoef(distances, tw_width)[0, 1]
        corr_dist_demand = np.corrcoef(distances, self.customers['DEMAND'])[0, 1]
        corr_tw_demand = np.corrcoef(tw_width, self.customers['DEMAND'])[0, 1]
        corr_service_demand = np.corrcoef(self.customers['SERVICE TIME'], self.customers['DEMAND'])[0, 1]
        
        report.append(f"   Tương quan (Khoảng cách - Độ rộng TW): {corr_dist_tw:.4f}")
        report.append(f"   Tương quan (Khoảng cách - Nhu cầu): {corr_dist_demand:.4f}")
        report.append(f"   Tương quan (Độ rộng TW - Nhu cầu): {corr_tw_demand:.4f}")
        report.append(f"   Tương quan (Thời gian phục vụ - Nhu cầu): {corr_service_demand:.4f}")
        report.append("")
        
        # 7. THỐNG KÊ CHI TIẾT CÁC KHÁCH HÀNG
        report.append("7. DANH SÁCH CHI TIẾT CÁC KHÁCH HÀNG")
        report.append("-" * 80)
        report.append(f"{'STT':<5} {'Tọa độ X':<10} {'Tọa độ Y':<10} {'Nhu cầu':<10} {'Ready':<10} {'Due':<10} {'Service':<10} {'KC từ kho':<12}")
        report.append("-" * 80)
        
        for idx, row in self.customers.iterrows():
            cust_no = int(row['CUST NO.'])
            x = row['XCOORD.']
            y = row['YCOORD.']
            demand = row['DEMAND']
            ready = row['READY TIME']
            due = row['DUE DATE']
            service = row['SERVICE TIME']
            dist = np.sqrt((x - self.depot['XCOORD.'])**2 + (y - self.depot['YCOORD.'])**2)
            
            report.append(f"{cust_no:<5} {x:<10.1f} {y:<10.1f} {demand:<10} {ready:<10.0f} {due:<10.0f} {service:<10.0f} {dist:<12.2f}")
        
        report.append("")
        report.append("=" * 80)
        report.append(f"Báo cáo được tạo tự động từ VRPTWVisualizer")
        report.append("=" * 80)
        
        # Lưu file nếu được yêu cầu
        if save:
            # Lưu vào thư mục visulize dataset txt
            output_path = self.txt_dir / f'{self.dataset_name}_report.txt'
            with open(str(output_path), 'w', encoding='utf-8') as f:
                f.write('\n'.join(report))
            print(f"   ✓ Đã tạo file báo cáo: {output_path.name}")
        
        return '\n'.join(report)
    
    def plot_all(self, save=False):
        """Tạo biểu đồ tổng hợp duy nhất và file báo cáo TXT"""
        print(f"Đang tạo biểu đồ tổng hợp cho dataset: {self.dataset_name}")
        self.plot_comprehensive_summary(save)
        
        # Tạo file báo cáo TXT
        if save:
            self.generate_text_report(save)
        
        print("Hoàn thành!")
        
    def print_statistics(self):
        """In thống kê cơ bản về dataset"""
        print(f"\n{'='*60}")
        print(f"THỐNG KÊ DATASET: {self.dataset_name}")
        print(f"{'='*60}")
        print(f"Số lượng khách hàng: {len(self.customers)}")
        print(f"\nDepot location: ({self.depot['XCOORD.']}, {self.depot['YCOORD.']})")
        print(f"\nDemand Statistics:")
        print(f"  - Tổng demand: {self.customers['DEMAND'].sum()}")
        print(f"  - Trung bình: {self.customers['DEMAND'].mean():.2f}")
        print(f"  - Min: {self.customers['DEMAND'].min()}")
        print(f"  - Max: {self.customers['DEMAND'].max()}")
        print(f"\nTime Window Statistics:")
        print(f"  - Earliest ready time: {self.customers['READY TIME'].min()}")
        print(f"  - Latest due date: {self.customers['DUE DATE'].max()}")
        print(f"  - Average window width: {(self.customers['DUE DATE'] - self.customers['READY TIME']).mean():.2f}")
        print(f"\nService Time:")
        print(f"  - Average: {self.customers['SERVICE TIME'].mean():.2f}")
        print(f"  - Total: {self.customers['SERVICE TIME'].sum()}")
        print(f"{'='*60}\n")


def main():
    """Hàm chính để chạy visualization"""
    
    # Ví dụ sử dụng - Thay đổi đường dẫn phù hợp
    dataset_path = "../dataset/C1/C101.csv"
    
    # Tạo visualizer
    viz = VRPTWVisualizer(dataset_path)
    
    # In thống kê
    viz.print_statistics()
    
    # Tạo biểu đồ tổng hợp duy nhất (save=True để lưu ảnh)
    viz.plot_all(save=True)
    
    # Nếu muốn tạo từng biểu đồ riêng lẻ (5 ảnh):
    # viz.plot_customer_locations(save=True)
    # viz.plot_time_windows(save=True)
    # viz.plot_demand_distribution(save=True)
    # viz.plot_time_window_width(save=True)
    # viz.plot_spatial_temporal_heatmap(save=True)


if __name__ == "__main__":
    main()
