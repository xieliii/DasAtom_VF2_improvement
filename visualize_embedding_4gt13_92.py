#!/usr/bin/env python3
"""
可视化 4gt13_92.qasm 的嵌入结果
"""

import json

print("=" * 80)
print("🎨 4gt13_92.qasm 嵌入可视化")
print("=" * 80)

# 读取嵌入数据
with open("demo_embeddings_4gt13_92.json", "r") as f:
    embeddings = json.load(f)

# 读取结果数据
with open("demo_results_4gt13_92.json", "r") as f:
    results = json.load(f)

print(f"\n文件: {results['文件名']}")
print(f"量子比特数: {results['量子比特数']}")
print(f"分区数: {results['分区数']}")

# 由于只有一个分区，展示唯一的嵌入
embedding = embeddings[0]

print("\n" + "-" * 80)
print("📍 逻辑比特到物理位置的映射:")
print("-" * 80)

for logic_qubit, physical_pos in enumerate(embedding):
    print(f"  逻辑比特 q[{logic_qubit}] → 物理位置 {tuple(physical_pos)}")

# 创建 3x3 网格可视化
print("\n" + "-" * 80)
print("🗺️  硬件网格上的量子比特布局 (3×3, Rb=2):")
print("-" * 80)

grid = [[None for _ in range(3)] for _ in range(3)]
for logic_qubit, physical_pos in enumerate(embedding):
    x, y = physical_pos
    grid[x][y] = logic_qubit

print("\n  网格布局:")
print("  " + "─" * 35)
for i in range(3):
    row_str = "  │"
    for j in range(3):
        if grid[i][j] is not None:
            row_str += f"  q[{grid[i][j]}]  │"
        else:
            row_str += "  空闲  │"
    print(row_str)
    print("  " + "─" * 35)

# 显示物理坐标
print("\n  物理坐标标注:")
print("        y=0      y=1      y=2")
for i in range(3):
    row_str = f"  x={i}  "
    for j in range(3):
        pos_str = f"({i},{j})"
        if grid[i][j] is not None:
            row_str += f" {pos_str:6} "
        else:
            row_str += f" {pos_str:6} "
    print(row_str)

# 分析逻辑连接
print("\n" + "-" * 80)
print("🔗 逻辑连接分析 (从 QASM 文件提取的 CX 门):")
print("-" * 80)

# 从 QASM 提取的门（前面分析的结果）
gates = [
    (4, 0), (4, 1), (0, 4), (1, 0), (1, 4),
    (0, 4), (1, 0), (4, 1), (2, 3), (4, 2),
    (3, 4), (3, 2), (4, 2), (3, 4), (2, 3),
]

# 统计连接
connections = {}
for g0, g1 in gates:
    pair = tuple(sorted([g0, g1]))
    connections[pair] = connections.get(pair, 0) + 1

print("\n  逻辑比特连接频率:")
for (q0, q1), count in sorted(connections.items(), key=lambda x: -x[1])[:10]:
    pos0 = tuple(embedding[q0])
    pos1 = tuple(embedding[q1])
    
    # 计算物理距离
    import math
    dist = math.sqrt((pos0[0] - pos1[0])**2 + (pos0[1] - pos1[1])**2)
    
    print(f"    q[{q0}]━━q[{q1}]: {count:2}次 | {pos0} ━━ {pos1} (距离: {dist:.2f})")

# 显示性能指标
print("\n" + "-" * 80)
print("📊 性能指标:")
print("-" * 80)
print(f"  • 总保真度: {results['总保真度']:.6f}")
print(f"  • 移动保真度: {results['移动保真度']:.6f}")
print(f"  • 移动操作数: {results['移动操作数']}")
print(f"  • 并行门组数: {results['并行门组数']}")
print(f"  • 总运行时间: {results['总运行时间 (μs)']} μs")
print(f"  • 空闲时间: {results['空闲时间 (μs)']} μs")

print("\n" + "=" * 80)
print("✨ 关键洞察:")
print("=" * 80)
print("""
1. 只需要 1 个分区：
   - 整个电路的逻辑拓扑可以一次性嵌入到 3×3 硬件图中
   - 无需在执行过程中重新映射量子比特

2. 零移动操作：
   - 由于只有一个分区，不需要在分区间移动量子比特
   - 移动保真度 = 1.0（完美）

3. 嵌入策略：
   - q[4] 是中心节点，被放置在 (0,2)，与多个比特相邻
   - q[0]、q[1] 在 (1,1)、(1,2)，便于与 q[4] 交互
   - q[2]、q[3] 在 (0,0)、(0,1)，便于彼此交互

4. 保真度损失来源：
   - 主要来自 30 个 CZ 门的累积误差：0.995^30 ≈ 0.8604
   - 没有移动损失
   - 空闲时间相对较短（24 μs），退相干影响小

5. DasAtom 的优势：
   - 对于这种小规模、规则的电路，DasAtom 找到了最优解
   - 充分利用了长程交互（Rb=2），避免了 SWAP 门
   - 并行度保持良好（30 个门 → 30 个并行组，因为大多串行依赖）
""")

print("=" * 80)


