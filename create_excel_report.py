#!/usr/bin/env python3
"""
生成Excel格式的测试结果报告
"""

import json
import pandas as pd
from datetime import datetime

# 读取JSON结果
with open('key_circuits_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

test_info = data['test_info']
results = [r for r in data['results'] if r.get('success', False)]

# 创建Excel写入器
excel_file = 'Key_Circuits_Test_Results.xlsx'
with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
    
    # ========================================================================
    # Sheet 1: 测试概览
    # ========================================================================
    overview_data = []
    for r in results:
        overview_data.append({
            '电路名称': r['circuit_name'],
            '优先级': r['priority'],
            '描述': r['description'],
            '量子比特数': r['num_qubits'],
            '双量子比特门数': r['num_2q_gates'],
            '电路深度': r['circuit_depth'],
            '预期分区数': r['expected_partitions'],
            '实际分区数': r['num_partitions'],
            '分区降低比例': f"{(1 - r['num_partitions']/r['expected_partitions'])*100:.1f}%" 
                if isinstance(r['expected_partitions'], int) else 'N/A',
            '移动阶段': r['num_movement_stages'],
            '原子移动次数': r['total_atoms_moved'],
            '总保真度': r['fidelity'],
            '移动保真度': r['move_fidelity'],
            '运行时间(μs)': r['total_runtime_us'],
            '执行时间(s)': r['execution_time_s']
        })
    
    df_overview = pd.DataFrame(overview_data)
    df_overview.to_excel(writer, sheet_name='测试概览', index=False)
    
    # ========================================================================
    # Sheet 2: 分区详细信息
    # ========================================================================
    partition_data = []
    for r in results:
        partition_data.append({
            '电路名称': r['circuit_name'],
            '预期分区数': r['expected_partitions'],
            '实际分区数': r['num_partitions'],
            '降低数量': r['expected_partitions'] - r['num_partitions'] 
                if isinstance(r['expected_partitions'], int) else 'N/A',
            '降低比例(%)': (1 - r['num_partitions']/r['expected_partitions'])*100 
                if isinstance(r['expected_partitions'], int) else None,
            '平均分区大小': r['partition_avg_size'],
            '最小分区大小': r['partition_min_size'],
            '最大分区大小': r['partition_max_size'],
            '网格大小': r['grid_size'],
            '硬件节点数': r['hardware_nodes'],
            '硬件边数': r['hardware_edges']
        })
    
    df_partition = pd.DataFrame(partition_data)
    df_partition.to_excel(writer, sheet_name='分区分析', index=False)
    
    # ========================================================================
    # Sheet 3: 移动效率分析
    # ========================================================================
    movement_data = []
    for r in results:
        movement_data.append({
            '电路名称': r['circuit_name'],
            '分区数': r['num_partitions'],
            '移动阶段': r['num_movement_stages'],
            '移动步数': r['total_move_steps'],
            '原子移动总次数': r['total_atoms_moved'],
            '平均移动/阶段': r['avg_atoms_per_stage'],
            '平均移动/分区': r['total_atoms_moved'] / r['num_partitions'],
            '移动距离(μm)': r['total_move_distance_um'],
            '转移操作次数': r['num_transfers'],
            '移动保真度': r['move_fidelity'],
            '移动效率评分': (1 - r['total_atoms_moved'] / (r['num_qubits'] * r['num_partitions'])) * 100
        })
    
    df_movement = pd.DataFrame(movement_data)
    df_movement.to_excel(writer, sheet_name='移动效率', index=False)
    
    # ========================================================================
    # Sheet 4: 保真度分析
    # ========================================================================
    fidelity_data = []
    for r in results:
        fidelity_data.append({
            '电路名称': r['circuit_name'],
            '量子比特数': r['num_qubits'],
            '门数': r['num_2q_gates'],
            '总保真度': r['fidelity'],
            '移动保真度': r['move_fidelity'],
            '总运行时间(μs)': r['total_runtime_us'],
            '空闲时间(μs)': r['idle_time_us'],
            '每门平均运行时间(ns)': (r['total_runtime_us'] * 1000) / r['num_2q_gates'],
            '保真度/门': r['fidelity'] ** (1/r['num_2q_gates']) if r['fidelity'] > 0 else 0,
            '综合评分': r['fidelity'] * 100
        })
    
    df_fidelity = pd.DataFrame(fidelity_data)
    df_fidelity.to_excel(writer, sheet_name='保真度分析', index=False)
    
    # ========================================================================
    # Sheet 5: 对比排名
    # ========================================================================
    ranking_data = []
    for r in results:
        ranking_data.append({
            '电路名称': r['circuit_name'],
            '优先级': r['priority'],
            '量子比特': r['num_qubits'],
            '门数': r['num_2q_gates'],
            '分区数': r['num_partitions'],
            '保真度': r['fidelity'],
            '移动效率': r['total_atoms_moved'] / r['num_partitions'],
            '运行时间': r['total_runtime_us']
        })
    
    df_ranking = pd.DataFrame(ranking_data)
    
    # 按不同指标排序
    df_fidelity_rank = df_ranking.sort_values('保真度', ascending=False).copy()
    df_fidelity_rank['保真度排名'] = range(1, len(df_fidelity_rank) + 1)
    
    df_partition_rank = df_ranking.sort_values('分区数', ascending=True).copy()
    df_partition_rank['分区优化排名'] = range(1, len(df_partition_rank) + 1)
    
    df_movement_rank = df_ranking.sort_values('移动效率', ascending=True).copy()
    df_movement_rank['移动效率排名'] = range(1, len(df_movement_rank) + 1)
    
    # 合并排名
    df_combined = df_ranking.copy()
    df_combined = df_combined.merge(
        df_fidelity_rank[['电路名称', '保真度排名']], on='电路名称'
    )
    df_combined = df_combined.merge(
        df_partition_rank[['电路名称', '分区优化排名']], on='电路名称'
    )
    df_combined = df_combined.merge(
        df_movement_rank[['电路名称', '移动效率排名']], on='电路名称'
    )
    
    df_combined['综合得分'] = (
        (7 - df_combined['保真度排名']) + 
        (7 - df_combined['分区优化排名']) + 
        (7 - df_combined['移动效率排名'])
    )
    df_combined = df_combined.sort_values('综合得分', ascending=False)
    
    df_combined.to_excel(writer, sheet_name='综合排名', index=False)
    
    # ========================================================================
    # Sheet 6: 统计摘要
    # ========================================================================
    summary_data = {
        '指标': [
            '测试时间',
            '交互半径',
            '测试电路数',
            '成功测试数',
            '平均量子比特数',
            '平均门数',
            '平均分区数',
            '平均移动阶段',
            '平均原子移动次数',
            '平均保真度',
            '最高保真度',
            '最低保真度',
            '平均运行时间(μs)',
            '平均执行时间(s)'
        ],
        '数值': [
            test_info['test_time'],
            test_info['interaction_radius'],
            test_info['circuits_tested'],
            test_info['successful'],
            sum(r['num_qubits'] for r in results) / len(results),
            sum(r['num_2q_gates'] for r in results) / len(results),
            sum(r['num_partitions'] for r in results) / len(results),
            sum(r['num_movement_stages'] for r in results) / len(results),
            sum(r['total_atoms_moved'] for r in results) / len(results),
            sum(r['fidelity'] for r in results) / len(results),
            max(r['fidelity'] for r in results),
            min(r['fidelity'] for r in results),
            sum(r['total_runtime_us'] for r in results) / len(results),
            sum(r['execution_time_s'] for r in results) / len(results)
        ]
    }
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel(writer, sheet_name='统计摘要', index=False)

print(f"✅ Excel报告已生成: {excel_file}")
print(f"\n包含以下工作表:")
print("  1. 测试概览 - 所有电路的关键指标")
print("  2. 分区分析 - 分区优化效果详细数据")
print("  3. 移动效率 - 原子移动效率分析")
print("  4. 保真度分析 - 保真度与性能指标")
print("  5. 综合排名 - 电路性能排名对比")
print("  6. 统计摘要 - 测试结果统计汇总")

