#!/usr/bin/env python3
"""
生成原始 vs 改进算法的对比Excel报告
"""

import json
import pandas as pd
from datetime import datetime

# 读取对比结果
with open('comparison_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = [r for r in data['results'] if r.get('success', False)]

# 电路列表（用于统计）
KEY_CIRCUITS = [
    {"name": "square_root_7"},
    {"name": "adr4_197"},
    {"name": "radd_250"},
    {"name": "z4_268"},
    {"name": "sym6_145"},
    {"name": "QFT_30"}
]

# 创建Excel写入器
excel_file = 'DasAtom_Original_vs_Improved_Comparison.xlsx'
with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
    
    # ========================================================================
    # Sheet 1: 总览对比
    # ========================================================================
    overview_data = []
    for r in results:
        overview_data.append({
            '电路名称': r['circuit_name'],
            '量子比特数': r['num_qubits'],
            '门数': r['num_2q_gates'],
            '分区数': r['num_partitions'],
            
            # 原始算法
            '原始-保真度': r['original']['fidelity'],
            '原始-移动距离(μm)': r['original']['total_move_distance_um'],
            '原始-原子移动次数': r['original']['total_atoms_moved'],
            '原始-运行时间(μs)': r['original']['total_runtime_us'],
            
            # 改进算法
            '改进-保真度': r['improved']['fidelity'],
            '改进-移动距离(μm)': r['improved']['total_move_distance_um'],
            '改进-原子移动次数': r['improved']['total_atoms_moved'],
            '改进-运行时间(μs)': r['improved']['total_runtime_us'],
            
            # 改进幅度
            '保真度提升(%)': r['improvement']['fidelity_gain'],
            '移动距离减少(%)': r['improvement']['move_distance_reduction'],
            '原子移动减少(%)': r['improvement']['atoms_moved_reduction'],
            '运行时间减少(%)': r['improvement']['runtime_reduction']
        })
    
    df_overview = pd.DataFrame(overview_data)
    df_overview.to_excel(writer, sheet_name='总览对比', index=False)
    
    # ========================================================================
    # Sheet 2: 保真度对比
    # ========================================================================
    fidelity_data = []
    for r in results:
        fidelity_data.append({
            '电路名称': r['circuit_name'],
            '量子比特': r['num_qubits'],
            '门数': r['num_2q_gates'],
            '原始-总保真度': r['original']['fidelity'],
            '改进-总保真度': r['improved']['fidelity'],
            '保真度提升(%)': r['improvement']['fidelity_gain'],
            '原始-移动保真度': r['original']['move_fidelity'],
            '改进-移动保真度': r['improved']['move_fidelity'],
            '原始-空闲时间(μs)': r['original']['idle_time_us'],
            '改进-空闲时间(μs)': r['improved']['idle_time_us']
        })
    
    df_fidelity = pd.DataFrame(fidelity_data)
    df_fidelity.to_excel(writer, sheet_name='保真度对比', index=False)
    
    # ========================================================================
    # Sheet 3: 移动效率对比
    # ========================================================================
    movement_data = []
    for r in results:
        orig_moves_per_partition = r['original']['total_atoms_moved'] / r['num_partitions']
        impr_moves_per_partition = r['improved']['total_atoms_moved'] / r['num_partitions']
        
        movement_data.append({
            '电路名称': r['circuit_name'],
            '分区数': r['num_partitions'],
            '原始-移动阶段': r['original']['num_movement_stages'],
            '改进-移动阶段': r['improved']['num_movement_stages'],
            '原始-原子移动次数': r['original']['total_atoms_moved'],
            '改进-原子移动次数': r['improved']['total_atoms_moved'],
            '移动次数减少(%)': r['improvement']['atoms_moved_reduction'],
            '原始-移动距离(μm)': r['original']['total_move_distance_um'],
            '改进-移动距离(μm)': r['improved']['total_move_distance_um'],
            '移动距离减少(%)': r['improvement']['move_distance_reduction'],
            '原始-每分区移动': orig_moves_per_partition,
            '改进-每分区移动': impr_moves_per_partition,
            '效率提升': (orig_moves_per_partition - impr_moves_per_partition) / orig_moves_per_partition * 100
        })
    
    df_movement = pd.DataFrame(movement_data)
    df_movement.to_excel(writer, sheet_name='移动效率对比', index=False)
    
    # ========================================================================
    # Sheet 4: 详细指标对比（并排）
    # ========================================================================
    detailed_data = []
    for r in results:
        # 原始算法行
        detailed_data.append({
            '电路名称': r['circuit_name'],
            '版本': '原始算法',
            '保真度': r['original']['fidelity'],
            '移动保真度': r['original']['move_fidelity'],
            '运行时间(μs)': r['original']['total_runtime_us'],
            '空闲时间(μs)': r['original']['idle_time_us'],
            '移动阶段': r['original']['num_movement_stages'],
            '原子移动次数': r['original']['total_atoms_moved'],
            '移动距离(μm)': r['original']['total_move_distance_um'],
            '转移操作': r['original']['num_transfers']
        })
        
        # 改进算法行
        detailed_data.append({
            '电路名称': r['circuit_name'],
            '版本': '改进算法',
            '保真度': r['improved']['fidelity'],
            '移动保真度': r['improved']['move_fidelity'],
            '运行时间(μs)': r['improved']['total_runtime_us'],
            '空闲时间(μs)': r['improved']['idle_time_us'],
            '移动阶段': r['improved']['num_movement_stages'],
            '原子移动次数': r['improved']['total_atoms_moved'],
            '移动距离(μm)': r['improved']['total_move_distance_um'],
            '转移操作': r['improved']['num_transfers']
        })
        
        # 改进幅度行
        detailed_data.append({
            '电路名称': r['circuit_name'],
            '版本': '📈 改进幅度(%)',
            '保真度': r['improvement']['fidelity_gain'],
            '移动保真度': 0,  # 占位
            '运行时间(μs)': r['improvement']['runtime_reduction'],
            '空闲时间(μs)': 0,  # 占位
            '移动阶段': 0,  # 占位
            '原子移动次数': r['improvement']['atoms_moved_reduction'],
            '移动距离(μm)': r['improvement']['move_distance_reduction'],
            '转移操作': 0  # 占位
        })
        
        # 空行分隔
        detailed_data.append({
            '电路名称': '',
            '版本': '',
            '保真度': None,
            '移动保真度': None,
            '运行时间(μs)': None,
            '空闲时间(μs)': None,
            '移动阶段': None,
            '原子移动次数': None,
            '移动距离(μm)': None,
            '转移操作': None
        })
    
    df_detailed = pd.DataFrame(detailed_data)
    df_detailed.to_excel(writer, sheet_name='详细对比', index=False)
    
    # ========================================================================
    # Sheet 5: 改进效果排名
    # ========================================================================
    ranking_data = []
    for r in results:
        ranking_data.append({
            '电路名称': r['circuit_name'],
            '保真度提升(%)': r['improvement']['fidelity_gain'],
            '移动距离减少(%)': r['improvement']['move_distance_reduction'],
            '原子移动减少(%)': r['improvement']['atoms_moved_reduction'],
            '运行时间减少(%)': r['improvement']['runtime_reduction'],
            '综合改进得分': (
                r['improvement']['fidelity_gain'] * 0.4 +
                r['improvement']['move_distance_reduction'] * 0.3 +
                r['improvement']['atoms_moved_reduction'] * 0.3
            )
        })
    
    df_ranking = pd.DataFrame(ranking_data)
    df_ranking = df_ranking.sort_values('综合改进得分', ascending=False)
    df_ranking.to_excel(writer, sheet_name='改进效果排名', index=False)
    
    # ========================================================================
    # Sheet 6: 统计摘要
    # ========================================================================
    
    # 计算平均值
    avg_fidelity_gain = sum(r['improvement']['fidelity_gain'] for r in results) / len(results)
    avg_distance_reduction = sum(r['improvement']['move_distance_reduction'] for r in results) / len(results)
    avg_atoms_reduction = sum(r['improvement']['atoms_moved_reduction'] for r in results) / len(results)
    avg_runtime_reduction = sum(r['improvement']['runtime_reduction'] for r in results) / len(results)
    
    # 原始算法平均值
    avg_orig_fidelity = sum(r['original']['fidelity'] for r in results) / len(results)
    avg_orig_distance = sum(r['original']['total_move_distance_um'] for r in results) / len(results)
    avg_orig_atoms = sum(r['original']['total_atoms_moved'] for r in results) / len(results)
    
    # 改进算法平均值
    avg_impr_fidelity = sum(r['improved']['fidelity'] for r in results) / len(results)
    avg_impr_distance = sum(r['improved']['total_move_distance_um'] for r in results) / len(results)
    avg_impr_atoms = sum(r['improved']['total_atoms_moved'] for r in results) / len(results)
    
    summary_data = {
        '指标类别': [
            '测试时间',
            '测试电路数',
            '成功测试数',
            '',
            '平均保真度 - 原始',
            '平均保真度 - 改进',
            '保真度平均提升(%)',
            '',
            '平均移动距离(μm) - 原始',
            '平均移动距离(μm) - 改进',
            '移动距离平均减少(%)',
            '',
            '平均原子移动次数 - 原始',
            '平均原子移动次数 - 改进',
            '原子移动平均减少(%)',
            '',
            '平均运行时间减少(%)',
            '',
            '最佳改进电路(保真度)',
            '最佳改进电路(移动距离)',
            '最佳改进电路(原子移动)'
        ],
        '数值': [
            data['test_time'],
            len(KEY_CIRCUITS),
            len(results),
            '',
            f"{avg_orig_fidelity:.6e}",
            f"{avg_impr_fidelity:.6e}",
            f"{avg_fidelity_gain:.2f}",
            '',
            f"{avg_orig_distance:.2f}",
            f"{avg_impr_distance:.2f}",
            f"{avg_distance_reduction:.2f}",
            '',
            f"{avg_orig_atoms:.1f}",
            f"{avg_impr_atoms:.1f}",
            f"{avg_atoms_reduction:.2f}",
            '',
            f"{avg_runtime_reduction:.2f}",
            '',
            max(results, key=lambda x: x['improvement']['fidelity_gain'])['circuit_name'],
            max(results, key=lambda x: x['improvement']['move_distance_reduction'])['circuit_name'],
            max(results, key=lambda x: x['improvement']['atoms_moved_reduction'])['circuit_name']
        ]
    }
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel(writer, sheet_name='统计摘要', index=False)

print(f"✅ 对比Excel报告已生成: {excel_file}")
print(f"\n包含以下工作表:")
print("  1. 总览对比 - 原始vs改进的关键指标并排对比")
print("  2. 保真度对比 - 保真度相关指标详细对比")
print("  3. 移动效率对比 - 原子移动效率详细对比")
print("  4. 详细对比 - 所有指标完整对比（分组展示）")
print("  5. 改进效果排名 - 按改进幅度排名")
print("  6. 统计摘要 - 整体改进效果统计")

print(f"\n📊 主要改进效果:")
print(f"  ⭐ 平均保真度提升: {avg_fidelity_gain:.2f}%")
print(f"  ⭐ 平均移动距离减少: {avg_distance_reduction:.2f}%")
print(f"  ⭐ 平均原子移动减少: {avg_atoms_reduction:.2f}%")
print(f"  ⭐ 平均运行时间减少: {avg_runtime_reduction:.2f}%")

# 找出改进最显著的电路
best_circuit = max(results, key=lambda x: x['improvement']['move_distance_reduction'])
print(f"\n🏆 改进最显著的电路: {best_circuit['circuit_name']}")
print(f"   移动距离减少: {best_circuit['improvement']['move_distance_reduction']:.1f}%")
print(f"   原子移动减少: {best_circuit['improvement']['atoms_moved_reduction']:.1f}%")

