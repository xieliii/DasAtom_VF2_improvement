#!/usr/bin/env python3
"""
7类可扩展通用电路测试脚本 - 稳健版本
测试算法随量子比特数增加的扩展性（5-50 qubits）
"""

import os
import json
import time
import math
import traceback
from datetime import datetime
from DasAtom_fun import *
from Enola.route import QuantumRouter

# ============================================================================
# 电路配置
# ============================================================================

CIRCUITS = [
    # QFT - 全连接图结构
    {
        "name": "QFT",
        "path": "Data/qiskit-bench/qft",
        "files": [f"qft_{n}.qasm" for n in [5, 10, 15, 20, 25, 30]],
        "topology": "全连接",
        "description": "量子傅里叶变换"
    },
    # Quantum Volume - 几乎全连接
    {
        "name": "Quantum_Volume",
        "path": "Data/qiskit-bench/quantum_volume",
        "files": [f"quantum_volume_{n}.qasm" for n in [5, 10, 15, 20, 25, 30]],
        "topology": "几乎全连接",
        "description": "量子体积"
    },
    # Two-local random - 全连接
    {
        "name": "Two_Local_Random",
        "path": "Data/mqt-bench/two_local_random",
        "files": [f"twolocalrandom_indep_qiskit_{n}.qasm" for n in [5, 10, 15, 20, 25, 30]],
        "topology": "全连接",
        "description": "随机电路"
    },
    # 3-regular graph
    {
        "name": "3_Regular",
        "path": "Data/3_regular_graph",
        "files": [f"3_regular_{n}.qasm" for n in [10, 12, 14, 16, 18, 20, 22, 30]],
        "topology": "3-正则图",
        "description": "MaxCut QAOA"
    },
    # Deutsch-Jozsa - 星型拓扑
    {
        "name": "Deutsch_Jozsa",
        "path": "Data/mqt-bench/DJ",
        "files": [f"dj_indep_qiskit_{n}.qasm" for n in [5, 10, 15, 20, 25, 30]],
        "topology": "星型",
        "description": "Deutsch-Jozsa算法"
    },
    # GHZ - 线性拓扑
    {
        "name": "GHZ",
        "path": "Data/mqt-bench/GHZ",
        "files": [f"ghz_indep_qiskit_{n}.qasm" for n in [5, 10, 15, 20, 25, 30]],
        "topology": "线性",
        "description": "GHZ态制备"
    },
    # W-state - 线性拓扑
    {
        "name": "W_State",
        "path": "Data/mqt-bench/Wstate",
        "files": [f"wstate_indep_qiskit_{n}.qasm" for n in [5, 10, 15, 20, 25, 30]],
        "topology": "线性",
        "description": "W态制备"
    }
]

INTERACTION_RADIUS = 2

# ============================================================================
# 核心测试函数
# ============================================================================

def test_one_circuit(circuit_file, circuit_path, Rb=2):
    """测试单个电路并返回结果"""
    try:
        print(f"    测试: {circuit_file}...", end=" ", flush=True)
        start = time.time()
        
        # 1. 加载电路
        qasm_circuit = CreateCircuitFromQASM(circuit_file, circuit_path)
        two_qubit_gates = get_2q_gates_list(qasm_circuit)
        
        if len(two_qubit_gates) == 0:
            print("无双量子比特门，跳过")
            return None
        
        # 2. 转换为电路对象
        qc, dag = gates_list_to_QC(two_qubit_gates)
        num_qubits = get_qubits_num(two_qubit_gates)
        
        # 3. DAG层次
        gate_layers = get_layer_gates(dag)
        
        # 4. 硬件拓扑
        grid_size = math.ceil(math.sqrt(num_qubits))
        coupling_graph = generate_grid_with_Rb(grid_size, grid_size, Rb)
        
        # 5. 分区
        partitions = partition_from_DAG(dag, coupling_graph)
        
        # 6. 嵌入
        embeddings, extend_pos = get_embeddings(
            partitions, coupling_graph, num_qubits, grid_size, Rb
        )
        
        # 7. 并行门
        all_parallel = []
        for i, part in enumerate(partitions):
            pg = get_parallel_gates(part, coupling_graph, embeddings[i], 2*Rb)
            all_parallel.extend(pg)
        
        # 8. 移动
        router = QuantumRouter(num_qubits, embeddings, partitions, [grid_size, grid_size])
        router.run()
        movements = router.movement_list
        
        # 9. 保真度
        para = set_parameters()
        t_idle, fidelity, move_fid, t_total, n_trans, n_move, move_dist = compute_fidelity(
            all_parallel, movements, num_qubits, len(two_qubit_gates), para
        )
        
        elapsed = time.time() - start
        
        result = {
            "file": circuit_file,
            "qubits": num_qubits,
            "gates": len(two_qubit_gates),
            "depth": qc.depth(),
            "partitions": len(partitions),
            "parallel_groups": len(all_parallel),
            "fidelity": fidelity,
            "runtime_us": t_total,
            "time_s": elapsed,
            "success": True
        }
        
        print(f"✓ ({elapsed:.1f}s, F={fidelity:.6f})")
        return result
        
    except Exception as e:
        print(f"✗ 失败: {str(e)}")
        return {
            "file": circuit_file,
            "success": False,
            "error": str(e)
        }

def test_circuit_family(family_config):
    """测试一个电路家族"""
    print(f"\n{'='*80}")
    print(f"📊 {family_config['name']} - {family_config['description']}")
    print(f"   拓扑: {family_config['topology']}")
    print(f"{'='*80}")
    
    results = []
    for circuit_file in family_config['files']:
        full_path = os.path.join(family_config['path'], circuit_file)
        
        if not os.path.exists(full_path):
            print(f"    ⚠️  {circuit_file}: 文件不存在")
            continue
        
        result = test_one_circuit(circuit_file, family_config['path'])
        if result:
            result['family'] = family_config['name']
            result['topology'] = family_config['topology']
            results.append(result)
    
    success_count = sum(1 for r in results if r.get('success', False))
    print(f"  ✓ 完成: {success_count}/{len(family_config['files'])} 个测试成功\n")
    
    return results

# ============================================================================
# 结果保存和展示
# ============================================================================

def save_results(all_results, filename="scalable_circuits_results.json"):
    """保存结果到JSON"""
    output = {
        "test_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "interaction_radius": INTERACTION_RADIUS,
        "total_tests": len(all_results),
        "successful": sum(1 for r in all_results if r.get('success', False)),
        "results": all_results
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ 结果已保存: {filename}")

def print_summary(all_results):
    """打印汇总统计"""
    successful = [r for r in all_results if r.get('success', False)]
    
    if not successful:
        print("\n⚠️  没有成功的测试")
        return
    
    print(f"\n{'='*80}")
    print("📈 测试汇总")
    print(f"{'='*80}\n")
    
    # 按家族统计
    families = {}
    for r in successful:
        family = r['family']
        if family not in families:
            families[family] = []
        families[family].append(r)
    
    print(f"{'家族':<20} {'测试数':>8} {'平均保真度':>12} {'最低保真度':>12}")
    print("-" * 80)
    
    for family, results in sorted(families.items()):
        avg_fid = sum(r['fidelity'] for r in results) / len(results)
        min_fid = min(r['fidelity'] for r in results)
        print(f"{family:<20} {len(results):>8} {avg_fid:>12.6f} {min_fid:>12.6f}")
    
    print(f"\n总计: {len(successful)} 个成功测试")
    print(f"平均保真度: {sum(r['fidelity'] for r in successful) / len(successful):.6f}")

def create_comparison_table(all_results):
    """创建对比表格"""
    successful = [r for r in all_results if r.get('success', False)]
    
    if not successful:
        return
    
    print(f"\n{'='*80}")
    print("📊 详细对比（按量子比特数）")
    print(f"{'='*80}\n")
    
    # 按量子比特数分组
    by_qubits = {}
    for r in successful:
        q = r['qubits']
        if q not in by_qubits:
            by_qubits[q] = []
        by_qubits[q].append(r)
    
    for qubits in sorted(by_qubits.keys()):
        print(f"\n{qubits} Qubits:")
        print(f"  {'家族':<20} {'门数':>6} {'深度':>6} {'分区':>5} {'保真度':>10}")
        print("  " + "-" * 70)
        
        for r in sorted(by_qubits[qubits], key=lambda x: x['family']):
            print(f"  {r['family']:<20} {r['gates']:>6} {r['depth']:>6} "
                  f"{r['partitions']:>5} {r['fidelity']:>10.6f}")

# ============================================================================
# 主程序
# ============================================================================

def main():
    print("=" * 80)
    print("🚀 7类可扩展通用电路基准测试")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"交互半径: {INTERACTION_RADIUS}")
    print("=" * 80)
    
    all_results = []
    
    # 逐个测试电路家族
    for circuit_config in CIRCUITS:
        family_results = test_circuit_family(circuit_config)
        all_results.extend(family_results)
        
        # 每个家族测试完后保存中间结果
        save_results(all_results, "scalable_circuits_results_temp.json")
    
    # 最终结果
    save_results(all_results, "scalable_circuits_results.json")
    
    # 打印汇总
    print_summary(all_results)
    create_comparison_table(all_results)
    
    print(f"\n{'='*80}")
    print("✅ 所有测试完成！")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

if __name__ == "__main__":
    main()

