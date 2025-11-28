# DasAtom 完整流程详解 - 以 4gt13_92.qasm 为例

## 📋 目录
1. [QASM → 量子电路对象](#步骤1)
2. [提取双量子比特门列表](#步骤2)
3. [获取DAG层次结构](#步骤3)
4. [构建硬件拓扑图](#步骤4)
5. [贪心分区](#步骤5)
6. [VF2子图同构嵌入](#步骤6)
7. [并行门分组](#步骤7)
8. [原子穿梭](#步骤8)
9. [保真度计算](#步骤9)

---

## 步骤1: QASM → 量子电路对象

### 📌 代码位置
**文件**: `DasAtom_fun.py`, 第 20-29 行

### 💻 关键代码
```python
def CreateCircuitFromQASM(file, path):
    filePath = os.path.join(path, file)
    cir = qasm2.load(filePath, custom_instructions=custom)
    gates_in_circuit = {op[0].name for op in cir.data}
    allowed_basis_gates = {'cz', 'h', 's', 't', 'rx', 'ry', 'rz'}
    if gates_in_circuit - allowed_basis_gates:
        cir = transpile(cir, basis_gates=list(allowed_basis_gates))
    return cir
```

### 📥 输入
- `file`: `"4gt13_92.qasm"`
- `path`: `"Data/Q_Tetris"`

### 📤 输出
- `cir`: Qiskit QuantumCircuit 对象
  - 量子比特数: 16（声明的）
  - 实际使用: 5 个（q[0]-q[4]）
  - 总门数: 126
  - 电路深度: 67
  - 门类型: h×68, t×16, cz×30, rz×12

### ✨ 功能说明
1. 加载 QASM 文件
2. 检查门类型是否在允许的基础门集合中
3. 如果有不允许的门，使用 transpile 转换

### 🎯 实际效果
对于 `4gt13_92.qasm`:
- 原始门: cx（CNOT）
- 转换后: cz（Controlled-Z）
- CX 和 CZ 在算法中等价处理

---

## 步骤2: 提取双量子比特门列表

### 📌 代码位置
**文件**: `DasAtom_fun.py`
- `get_2q_gates_list`: 第 110-116 行
- `gates_list_to_QC`: 第 124-132 行

### 💻 关键代码

#### 2a. 提取双量子比特门
```python
def get_2q_gates_list(circ):
    gate_2q_list = []
    instruction = circ.data
    for ins in instruction:
        if ins.operation.num_qubits == 2:
            gate_2q_list.append((ins.qubits[0]._index, ins.qubits[1]._index))
    return gate_2q_list
```

#### 2b. 转换为纯CZ门电路
```python
def gates_list_to_QC(gate_list):
    Lqubit = get_qubits_num(gate_list)  # 计算量子比特数
    circ = QuantumCircuit(Lqubit)
    for two_qubit_gate in gate_list:
        circ.cz(two_qubit_gate[0], two_qubit_gate[1])
    dag = circuit_to_dag(circ)
    return circ, dag
```

### 📥 输入
- `circ`: 步骤1的 QuantumCircuit 对象

### 📤 输出
- `gate_2q_list`: 30个双量子比特门
  ```python
  [(2,3), (4,0), (4,1), (0,4), (1,0), (1,4), ...]
  ```
- `qc_object`: 新的纯CZ门电路
  - 量子比特数: 5
  - CZ门数: 30
  - 电路深度: 26

### ✨ 功能说明
1. 从原始电路中筛选出所有双量子比特门
2. 忽略所有单量子比特门（在原子阵列中局部执行）
3. 创建只包含双量子比特门的新电路
4. 生成DAG（有向无环图）表示

### 🎯 实际效果
- 原电路: 126个门（包括单比特门）
- 提取后: 30个CZ门
- 深度降低: 67 → 26（移除单比特门依赖）

---

## 步骤3: 获取DAG层次结构

### 📌 代码位置
**文件**: `DasAtom_fun.py`, 第 62-72 行

### 💻 关键代码
```python
def get_layer_gates(dag):
    gate_layer_list = []
    for item in dag.layers():
        gate_layer = []
        for gate in item['partition']:
            c0 = gate[0]._index
            c1 = gate[1]._index
            gate_layer.append([c0, c1])
        gate_layer_list.append(gate_layer)
    return gate_layer_list
```

### 📥 输入
- `dag`: 步骤2生成的 DAGCircuit 对象

### 📤 输出
- `gate_layer_list`: 26层，每层是可以并行的门
  ```python
  [
      [[2,3], [4,0]],  # 层0: 2个门可并行
      [[4,1]],         # 层1: 1个门
      [[0,4]],         # 层2
      [[1,0]],         # 层3
      ...
      [[2,3], [0,4]]   # 层25
  ]
  ```

### ✨ 功能说明
1. 利用 Qiskit 的 `dag.layers()` 获取层次结构
2. 每层内的门没有数据依赖，理论上可以并行执行
3. 层与层之间有数据依赖，必须按顺序执行

### 🎯 实际效果
- 总层数: 26
- 总门数: 30（分布在26层中）
- 第0层有2个门可并行: `[[2,3], [4,0]]`

---

## 步骤4: 构建硬件拓扑图

### 📌 代码位置
**文件**: `DasAtom_fun.py`
- `generate_grid_with_Rb`: 第 140-149 行
- `euclidean_distance`: 第 135-138 行

### 💻 关键代码
```python
def euclidean_distance(node1, node2):
    x1, y1 = node1
    x2, y2 = node2
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def generate_grid_with_Rb(n, m, Rb):
    G = nx.grid_2d_graph(n, m)  # 基础网格
    for node1 in G.nodes():
        for node2 in G.nodes():
            if node1 != node2:
                distance = euclidean_distance(node1, node2)
                if distance <= Rb:  # 在交互半径内
                    G.add_edge(node1, node2)
    return G
```

### 📥 输入
- `n`: 3（网格行数）
- `m`: 3（网格列数）
- `Rb`: 2（交互半径）
- 计算依据: `grid_size = ceil(sqrt(5)) = 3`

### 📤 输出
- `coupling_graph`: NetworkX Graph
  - 节点数: 9
  - 节点: `(0,0), (0,1), (0,2), (1,0), (1,1), (1,2), (2,0), (2,1), (2,2)`
  - 边数: 26
  - 连接规则: 欧氏距离 ≤ 2

### ✨ 功能说明
1. 创建 n×m 的二维网格
2. 添加所有在交互半径 Rb 内的边
3. 支持长程相互作用（不仅仅是最近邻）

### 🎯 连接示例
```
Rb=2 时的连接:
- 距离=1.00: 相邻节点（最近邻）
- 距离=1.41: 对角线（√2）
- 距离=2.00: 两格距离（骑士步）
```

### 🗺️ 网格可视化
```
(0,0)━━━(0,1)━━━(0,2)
 ┃ ╲ ╲  ┃ ╲ ╲  ┃
 ┃  ╲ ╲ ┃  ╲ ╲ ┃
(1,0)━━━(1,1)━━━(1,2)
 ┃  ╱ ╱ ┃  ╱ ╱ ┃
 ┃ ╱ ╱  ┃ ╱ ╱  ┃
(2,0)━━━(2,1)━━━(2,2)
```

---

## 步骤5: 贪心分区（基于子图同构）

### 📌 代码位置
**文件**: `DasAtom_fun.py`, 第 74-108 行

### 💻 关键代码
```python
def partition_from_DAG(dag, coupling_graph):
    gate_layer_list = get_layer_gates(dag)
    partition_gates = []
    last_index = 0
    
    for i in range(len(gate_layer_list)):
        # 贪心合并：从 last_index 到 i+1
        merge_gates = sum(gate_layer_list[last_index:i+1], [])
        tmp_graph = nx.Graph()
        tmp_graph.add_edges_from(merge_gates)  # 构建逻辑图
        
        # 检查每个连通分量
        connected_components = list(nx.connected_components(tmp_graph))
        isIso = True
        
        for component in connected_components:
            subgraph = tmp_graph.subgraph(component)
            # 路径拓扑优化
            if len(subgraph.edges()) == nx.diameter(subgraph):
                continue
            # VF2 子图同构检查
            if not rx_is_subgraph_iso(coupling_graph, subgraph):
                isIso = False
                break
        
        if not isIso:  # 无法继续合并
            merge_gates = sum(gate_layer_list[last_index:i], [])
            partition_gates.append(merge_gates)
            last_index = i
        
        if i == len(gate_layer_list) - 1:
            merge_gates = sum(gate_layer_list[last_index:i+1], [])
            partition_gates.append(merge_gates)
    
    return partition_gates
```

### 📥 输入
- `dag`: DAGCircuit 对象
- `coupling_graph`: 硬件拓扑图（9节点，26边）

### 📤 输出
- `partition_gates`: 1个分区
  ```python
  [
      [[2,3], [4,0], [4,1], ..., [0,4]]  # 所有30个门
  ]
  ```
- 逻辑图特征:
  - 5个节点: {0, 1, 2, 3, 4}
  - 6条边: {(0,1), (0,4), (1,4), (2,3), (2,4), (3,4)}

### ✨ 功能说明
1. **贪心策略**: 逐层合并，尽量扩大分区
2. **终止条件**: 逻辑图无法在硬件图中找到子图同构
3. **子图同构**: 使用 VF2 算法检查嵌入可行性
4. **优化**: 路径拓扑（链状）直接通过，无需检查

### 🎯 实际效果
- 对于 `4gt13_92.qasm`:
  - 整个电路只需 1 个分区
  - 逻辑图可以完整嵌入 3×3 硬件图
  - 无需中途重新映射

### 🔍 逻辑图结构
```
    0 ━━━ 1
     ╲   ╱
      ╲ ╱
       4
       ║
       2 ━━━ 3
```

---

## 步骤6: VF2 子图同构嵌入

### 📌 代码位置
**文件**: `DasAtom_fun.py`
- `get_embeddings`: 第 389-411 行
- `get_rx_one_mapping`: 第 32-54 行
- `map2list`: 第 156-161 行
- `complete_mapping`: 第 163-208 行

### 💻 关键代码

#### 6a. VF2 算法核心
```python
def get_rx_one_mapping(graph_max, G):
    sub_graph = rx.networkx_converter(graph_max)
    big_graph = rx.networkx_converter(G)
    
    # 建立索引映射
    nx_edge_s = list(graph_max.edges())
    rx_edge_s = list(sub_graph.edge_list())
    rx_nx_s = dict()
    for i in range(len(rx_edge_s)):
        if rx_edge_s[i][0] not in rx_nx_s:
            rx_nx_s[rx_edge_s[i][0]] = nx_edge_s[i][0]
        if rx_edge_s[i][1] not in rx_nx_s:
            rx_nx_s[rx_edge_s[i][1]] = nx_edge_s[i][1]
    
    # 对硬件图做同样处理
    nx_edge_G = list(G.edges())
    rx_edge_G = list(big_graph.edge_list())
    rx_nx_G = dict()
    for i in range(len(rx_edge_G)):
        if rx_edge_G[i][0] not in rx_nx_G:
            rx_nx_G[rx_edge_G[i][0]] = nx_edge_G[i][0]
        if rx_edge_G[i][1] not in rx_nx_G:
            rx_nx_G[rx_edge_G[i][1]] = nx_edge_G[i][1]
    
    # VF2 算法
    vf2 = rx.vf2_mapping(big_graph, sub_graph, subgraph=True, induced=False)
    item = next(vf2)
    
    # 反向映射
    reverse_mapping = {rx_nx_s[value]: rx_nx_G[key] 
                      for key, value in item.items()}
    return reverse_mapping
```

#### 6b. 整合嵌入流程
```python
def get_embeddings(partition_gates, coupling_graph, num_q, arch_size, Rb):
    embeddings = []
    extend_position = []
    
    for i, partition in enumerate(partition_gates):
        # 1. 构建逻辑拓扑图
        tmp_graph = nx.Graph()
        tmp_graph.add_edges_from(partition)
        
        # 2. 检查是否需要扩展硬件图
        if not rx_is_subgraph_iso(coupling_graph, tmp_graph):
            coupling_graph = extend_graph(coupling_graph, arch_size, Rb)
            extend_position.append(i)
        
        # 3. VF2 获取嵌入
        next_embedding = get_rx_one_mapping(tmp_graph, coupling_graph)
        next_embedding = map2list(next_embedding, num_q)
        embeddings.append(next_embedding)
    
    # 4. 补齐未参与的量子比特映射
    for i in range(len(embeddings)):
        indices = [idx for idx, val in enumerate(embeddings[i]) if val == -1]
        if indices:
            embeddings[i] = complete_mapping(i, embeddings, indices, 
                                            coupling_graph)
    
    return embeddings, extend_position
```

#### 6c. 补齐映射
```python
def complete_mapping(i, embeddings, indices, coupling_graph):
    cur_map = embeddings[i]
    unoccupied = [value for value in coupling_graph.nodes() 
                  if value not in cur_map]
    
    for index in indices:
        flag = False
        # 策略1: 继承前一个分区的位置
        if i != 0:
            if embeddings[i-1][index] in unoccupied:
                cur_map[index] = embeddings[i-1][index]
                flag = True
                unoccupied.remove(cur_map[index])
        
        # 策略2: 参考后续分区的位置
        if i != len(embeddings) - 1 and flag == False:
            for j in range(i+1, len(embeddings)):
                if embeddings[j][index] != -1 and \
                   embeddings[j][index] in unoccupied:
                    cur_map[index] = embeddings[j][index]
                    unoccupied.remove(cur_map[index])
                    flag = True
                    break
        
        # 策略3: 选择距离最近的空位
        if flag == False and i != 0:
            source = embeddings[i-1][index]
            node_of_shortest = dict()
            for node in unoccupied:
                distance = nx.shortest_path_length(coupling_graph, 
                                                   source=source, 
                                                   target=node)
                node_of_shortest[node] = distance
            min_node = min(node_of_shortest, key=node_of_shortest.get)
            cur_map[index] = min_node
            unoccupied.remove(min_node)
        
        # 策略4: 随机选择
        if flag == False:
            min_node = random.choice(unoccupied)
            cur_map[index] = min_node
            unoccupied.remove(min_node)
    
    return cur_map
```

### 📥 输入
- `partition_gates`: 1个分区
- `coupling_graph`: 硬件拓扑图
- `num_q`: 5
- `arch_size`: 3
- `Rb`: 2

### 📤 输出
- `embeddings`: 1个嵌入
  ```python
  [
      [(1,1), (1,2), (0,0), (0,1), (0,2)]
  ]
  ```
  解读:
  - 逻辑比特 0 → 物理位置 (1,1)
  - 逻辑比特 1 → 物理位置 (1,2)
  - 逻辑比特 2 → 物理位置 (0,0)
  - 逻辑比特 3 → 物理位置 (0,1)
  - 逻辑比特 4 → 物理位置 (0,2)

- `extend_position`: `[]`（无需扩展）

### ✨ 功能说明
1. **VF2算法**: 经典的子图同构算法
2. **映射策略**: 
   - 优先保持与前后分区的一致性（减少移动）
   - 选择距离最近的空位（减少移动距离）
3. **扩展机制**: 如果逻辑图太大，自动扩展硬件图

### 🎯 实际效果
- VF2 找到的映射是可行解之一
- 所有逻辑连接都在物理距离 ≤ 2 的范围内
- q[4] 在 (0,2)，与多个比特相邻，是中心节点

### 🗺️ 嵌入可视化
```
硬件网格:
  ───────────────────────────
  │ q[2]  │ q[3]  │ q[4]  │
  ───────────────────────────
  │ 空闲  │ q[0]  │ q[1]  │
  ───────────────────────────
  │ 空闲  │ 空闲  │ 空闲  │
  ───────────────────────────

逻辑连接 → 物理距离:
  q[0]━q[4]: (1,1)━(0,2) = √2 ≈ 1.41 ✓
  q[1]━q[4]: (1,2)━(0,2) = 1.00 ✓
  q[2]━q[3]: (0,0)━(0,1) = 1.00 ✓
  q[0]━q[1]: (1,1)━(1,2) = 1.00 ✓
  q[2]━q[4]: (0,0)━(0,2) = 2.00 ✓
  q[3]━q[4]: (0,1)━(0,2) = 1.00 ✓
```

---

## 步骤7: 并行门分组（基于扩展半径）

### 📌 代码位置
**文件**: `DasAtom_fun.py`
- `get_parallel_gates`: 第 281-306 行
- `check_intersect_ver2`: 第 272-279 行

### 💻 关键代码

#### 7a. 并行门分组主函数
```python
def get_parallel_gates(gates, coupling_graph, mapping, r_re):
    gates_list = []
    _, dag = gates_list_to_QC(gates)  # 重新生成DAG
    gate_layer_list = get_layer_gates(dag)
    
    for items in gate_layer_list:
        gates_copy = deepcopy(items)
        while len(gates_copy) != 0:
            parallel_gates = []
            parallel_gates.append(gates_copy[0])  # 第一个门
            
            # 贪心选择可以并行的门
            for i in range(1, len(gates_copy)):
                flag = True
                for gate in parallel_gates:
                    # 检查是否与已选门冲突
                    if check_intersect_ver2(gate, gates_copy[i],
                                           coupling_graph, mapping, r_re):
                        continue  # 不冲突
                    else:
                        flag = False
                        break
                if flag:
                    parallel_gates.append(gates_copy[i])
            
            # 移除已分组的门
            for gate in parallel_gates:
                gates_copy.remove(gate)
            gates_list.append(parallel_gates)
    
    return gates_list
```

#### 7b. 冲突检查函数
```python
def check_intersect_ver2(gate1, gate2, coupling_graph, mapping, r_re):
    # 检查两个门的4个量子比特之间的距离
    # 如果所有距离都 > r_re，则可以并行
    if euclidean_distance(mapping[gate1[0]], mapping[gate2[0]]) > r_re and \
       euclidean_distance(mapping[gate1[0]], mapping[gate2[1]]) > r_re and \
       euclidean_distance(mapping[gate1[1]], mapping[gate2[0]]) > r_re and \
       euclidean_distance(mapping[gate1[1]], mapping[gate2[1]]) > r_re:
        return True  # 可以并行
    else:
        return False  # 会相互干扰
```

### 📥 输入
- `gates`: 分区0的30个门
- `coupling_graph`: 硬件拓扑图
- `mapping`: 嵌入映射
- `r_re`: 4（扩展半径，2×Rb）

### 📤 输出
- `gates_list`: 30个并行组
  ```python
  [
      [[2,3]],   # 组0: 1个门
      [[4,0]],   # 组1: 1个门
      [[4,1]],   # 组2: 1个门
      ...
      [[0,4]]    # 组29: 1个门
  ]
  ```

### ✨ 功能说明
1. **并行条件**: 两个门的所有量子比特距离都 > Re
2. **贪心策略**: 每层尽量打包多个门到一组
3. **物理约束**: 避免激光束相互干扰

### 🎯 实际效果
- 对于 `4gt13_92.qasm`:
  - 大多数门由于共享量子比特无法并行
  - 30个门 → 30个并行组
  - 第0层的 `[[2,3], [4,0]]` 理论上可并行，但检查后发现:
    - q[2]在(0,0), q[3]在(0,1)
    - q[4]在(0,2), q[0]在(1,1)
    - d((0,0), (0,2)) = 2.00 ≤ 4 ✗（不满足 > Re）

### 📊 距离检查示例
```
门1: q[2]━q[3]  位置: (0,0)━(0,1)
门2: q[4]━q[0]  位置: (0,2)━(1,1)

需要检查的4个距离:
  d((0,0), (0,2)) = 2.00 ≤ 4 ✗  会干扰！
  d((0,0), (1,1)) = 1.41 ≤ 4 ✗
  d((0,1), (0,2)) = 1.00 ≤ 4 ✗
  d((0,1), (1,1)) = 1.00 ≤ 4 ✗

结论: 无法并行
```

---

## 步骤8: 原子穿梭（量子比特移动）

### 📌 代码位置
**文件**: `Enola/route.py`
- `QuantumRouter`: 类定义
- `get_movements`: 第 94-123 行
- `compatible_2D`: 第 5-38 行

### 💻 关键代码

#### 8a. QuantumRouter 类
```python
class QuantumRouter:
    def __init__(self, num_qubits, embeddings, partitioned_gates, window_size):
        self.num_qubits = num_qubits
        self.embeddings = embeddings
        self.partitioned_gates = partitioned_gates
        self.window_size = window_size
        self.movement_list = []
    
    def run(self):
        # 对每对相邻分区计算移动
        for i in range(len(self.embeddings) - 1):
            current_map = self.embeddings[i]
            next_map = self.embeddings[i + 1]
            movements = get_movements(current_map, next_map, self.window_size)
            self.movement_list.append(movements)
        return self.movement_list
```

#### 8b. 获取移动序列
```python
def get_movements(current_map: list, next_map: list, window_size=None):
    n = len(current_map)
    movements = []
    
    # 找出需要移动的量子比特
    for i in range(n):
        if current_map[i] != next_map[i]:
            movements.append([i, current_map[i], next_map[i]])
    
    if not movements:
        return []
    
    # 构建冲突图
    conflict_graph = Graph()
    for i in range(len(movements)):
        conflict_graph.add_node(i)
    
    # 检查移动冲突
    for i in range(len(movements)):
        for j in range(i+1, len(movements)):
            a = movements[i][1:] + movements[i][2:]  # 起点+终点
            b = movements[j][1:] + movements[j][2:]
            if not compatible_2D(a, b):
                conflict_graph.add_edge(i, j)
    
    # 使用最大独立集分组
    movement_groups = []
    remaining_nodes = set(range(len(movements)))
    
    while remaining_nodes:
        independent_set = maximal_independent_set(
            conflict_graph.subgraph(remaining_nodes), seed=0)
        movement_group = [movements[i] for i in independent_set]
        movement_groups.append(movement_group)
        remaining_nodes -= set(independent_set)
    
    return movement_groups
```

#### 8c. 冲突检查
```python
def compatible_2D(a: list[int], b: list[int]) -> bool:
    """
    检查两个移动是否冲突
    a, b 格式: [x_before, y_before, x_after, y_after]
    """
    # X坐标冲突检查
    if a[0] == b[0] and a[2] != b[2]:
        return False  # 起点相同，终点不同
    if a[2] == b[2] and a[0] != b[0]:
        return False  # 终点相同，起点不同
    if a[0] < b[0] and a[2] >= b[2]:
        return False  # X方向交叉
    if a[0] > b[0] and a[2] <= b[2]:
        return False  # X方向交叉
    
    # Y坐标冲突检查（同上）
    if a[1] == b[1] and a[3] != b[3]:
        return False
    if a[3] == b[3] and a[1] != b[1]:
        return False
    if a[1] < b[1] and a[3] >= b[3]:
        return False
    if a[1] > b[1] and a[3] <= b[3]:
        return False
    
    return True  # 无冲突
```

### 📥 输入
- `num_qubits`: 5
- `embeddings`: 1个嵌入（只有1个分区）
- `partitioned_gates`: 1个分区
- `window_size`: [3, 3]

### 📤 输出
- `movement_list`: `[]`（空列表）
  - 原因: 只有1个分区，没有分区间移动

### ✨ 功能说明
1. **移动触发**: 只在分区切换时发生
2. **并行优化**: 使用最大独立集找到可以同时进行的移动
3. **冲突检测**: 避免路径交叉、起/终点冲突

### 🎯 实际效果
- 对于 `4gt13_92.qasm`:
  - 0个分区间移动
  - 移动操作数 = 0
  - 移动保真度 = 1.0（完美）

### 📊 移动示例（假设有2个分区）
```
分区0 → 分区1:
  当前映射: [q0→(0,0), q1→(0,1), q2→(1,0)]
  下个映射: [q0→(0,0), q1→(1,1), q2→(0,1)]

需要移动:
  q1: (0,1) → (1,1)
  q2: (1,0) → (0,1)

冲突检查:
  q1的路径: y不变=1, x: 0→1
  q2的路径: x不变=0, y: 0→1
  结论: 不冲突，可以并行

移动组:
  [
      [[1, (0,1), (1,1)], [2, (1,0), (0,1)]]  # 两个移动并行
  ]
```

---

## 步骤9: 保真度计算

### 📌 代码位置
**文件**: `DasAtom_fun.py`
- `compute_fidelity`: 第 358-387 行
- `set_parameters`: 第 321-332 行

### 💻 关键代码

#### 9a. 物理参数设置
```python
def set_parameters(T_cz=0.2, T_eff=1.5e6, T_trans=20, 
                   AOD_width=3, AOD_height=3, 
                   Move_speed=0.55, F_cz=0.995, F_trans=1):
    para = {}
    para['T_cz'] = T_cz          # CZ门时间 (μs)
    para['T_eff'] = T_eff        # 有效相干时间 (μs)
    para['T_trans'] = T_trans    # 原子转移时间 (μs)
    para['AOD_width'] = AOD_width   # AOD网格宽度 (μm)
    para['AOD_height'] = AOD_height # AOD网格高度 (μm)
    para['Move_speed'] = Move_speed # 移动速度 (μm/μs)
    para['F_cz'] = F_cz          # CZ门保真度
    para['F_trans'] = F_trans    # 转移保真度
    return para
```

#### 9b. 保真度计算主函数
```python
def compute_fidelity(parallel_gates, all_movements, num_q, gate_num, para=None):
    if para is None:
        para = set_parameters()
    
    # 1. 门执行时间（并行）
    t_total = 0
    t_total += len(parallel_gates) * para['T_cz']
    
    # 2. 移动时间
    t_move = 0
    num_trans = 0
    num_move = 0
    all_move_dis = 0
    
    for move in all_movements:
        # pick/drop 操作: 4次（pick1, drop1, pick2, drop2）
        t_total += 4 * para['T_trans']
        t_move += 4 * para['T_trans']
        num_trans += 4
        
        # 计算该组的最大移动距离（并行移动取最大）
        max_dis = 0
        for each_move in move:
            num_move += 1
            x1, y1 = each_move[1]  # 起点
            x2, y2 = each_move[2]  # 终点
            
            # 物理距离
            dis = math.sqrt(
                (abs(x2-x1) * para['AOD_width'])**2 + 
                (abs(y2-y1) * para['AOD_height'])**2
            )
            if dis > max_dis:
                max_dis = dis
        
        all_move_dis += max_dis
        t_total += max_dis / para['Move_speed']
        t_move += max_dis / para['Move_speed']
    
    # 3. 空闲时间（所有量子比特的累积空闲时间）
    t_idle = num_q * t_total - gate_num * para['T_cz']
    
    # 4. 保真度计算
    Fidelity = (
        math.exp(-t_idle / para['T_eff']) *     # 退相干
        (para['F_cz'] ** gate_num) *            # 门误差
        (para['F_trans'] ** num_trans)          # 转移误差
    )
    
    # 5. 移动保真度
    move_fidelity = math.exp(-t_move / para['T_eff'])
    
    return (t_idle, Fidelity, move_fidelity, t_total, 
            num_trans, num_move, all_move_dis)
```

### 📥 输入
- `parallel_gates`: 30个并行组
- `all_movements`: 0个移动序列
- `num_q`: 5
- `gate_num`: 30
- `para`: 物理参数字典

### 📤 输出
- `t_idle`: 24.0 μs
- `Fidelity`: 0.8603704259
- `move_fidelity`: 1.0
- `total_runtime`: 6.0 μs
- `num_trans`: 0
- `num_move`: 0
- `total_move_dis`: 0.0 μm

### ✨ 功能说明
1. **时间计算**:
   - 门时间: 并行组数 × T_cz
   - 移动时间: 转移时间 + 移动距离/速度
2. **保真度模型**:
   - 退相干: exp(-t_idle / T_eff)
   - 门误差: F_cz^gate_num
   - 转移误差: F_trans^num_trans
3. **并行考虑**: 移动组内取最大距离

### 🎯 详细计算（4gt13_92.qasm）

#### 时间计算
```
门执行时间:
  t_gate = 30组 × 0.2 μs = 6.0 μs

移动时间:
  t_move = 0 (无移动)

总时间:
  t_total = 6.0 μs

空闲时间:
  t_idle = 5个比特 × 6.0 μs - 30个门 × 0.2 μs
         = 30.0 - 6.0
         = 24.0 μs
```

#### 保真度计算
```
退相干因子:
  exp(-24.0 / 1500000) = exp(-0.000016) ≈ 0.999984

门误差因子:
  0.995^30 = 0.860372

转移误差因子:
  1^0 = 1.0

总保真度:
  F = 0.999984 × 0.860372 × 1.0
    ≈ 0.8603704

移动保真度:
  F_move = exp(-0 / 1500000) = 1.0
```

### 📊 保真度分析
```
总保真度 = 0.8604
├─ 退相干损失: 0.016% (很小)
├─ 门误差损失: 13.96% (主要)
└─ 移动损失: 0% (无移动)

结论: 保真度损失主要来自 CZ 门的累积误差
```

---

## 🎯 完整流程总结

### 代码-步骤对应表

| 步骤 | 函数名 | 文件位置 | 行号 | 输入 | 输出 |
|------|--------|----------|------|------|------|
| 1 | `CreateCircuitFromQASM` | DasAtom_fun.py | 20-29 | QASM文件 | QuantumCircuit |
| 2a | `get_2q_gates_list` | DasAtom_fun.py | 110-116 | QuantumCircuit | 门列表 |
| 2b | `gates_list_to_QC` | DasAtom_fun.py | 124-132 | 门列表 | QC + DAG |
| 3 | `get_layer_gates` | DasAtom_fun.py | 62-72 | DAG | 层次结构 |
| 4 | `generate_grid_with_Rb` | DasAtom_fun.py | 140-149 | 网格尺寸, Rb | 硬件图 |
| 5 | `partition_from_DAG` | DasAtom_fun.py | 74-108 | DAG, 硬件图 | 分区列表 |
| 6a | `get_rx_one_mapping` | DasAtom_fun.py | 32-54 | 逻辑图, 硬件图 | VF2映射 |
| 6b | `get_embeddings` | DasAtom_fun.py | 389-411 | 分区, 硬件图 | 嵌入列表 |
| 6c | `complete_mapping` | DasAtom_fun.py | 163-208 | 嵌入, 索引 | 完整映射 |
| 7 | `get_parallel_gates` | DasAtom_fun.py | 281-306 | 门, 映射, Re | 并行组 |
| 8a | `QuantumRouter.run` | Enola/route.py | 类方法 | 嵌入列表 | 移动序列 |
| 8b | `get_movements` | Enola/route.py | 94-123 | 当前/下个映射 | 移动组 |
| 9 | `compute_fidelity` | DasAtom_fun.py | 358-387 | 并行组, 移动 | 保真度指标 |

### 数据流示意图

```
4gt13_92.qasm (QASM文件)
    ↓ [步骤1: CreateCircuitFromQASM]
QuantumCircuit (126门, 深度67)
    ↓ [步骤2: get_2q_gates_list + gates_list_to_QC]
门列表 (30个CZ门) + DAG (深度26)
    ↓ [步骤3: get_layer_gates]
层次结构 (26层)
    ↓ [步骤4: generate_grid_with_Rb]
    ↓ + 硬件拓扑图 (3×3网格, Rb=2, 9节点, 26边)
    ↓ [步骤5: partition_from_DAG]
分区列表 (1个分区, 30门)
    ↓ [步骤6: get_embeddings + VF2]
嵌入映射 (1个嵌入, 5个量子比特)
    ↓ [步骤7: get_parallel_gates]
并行组 (30组)
    ↓ [步骤8: QuantumRouter]
移动序列 (0组)
    ↓ [步骤9: compute_fidelity]
结果 (保真度=0.8604, 时间=6.0μs)
```

### 关键参数配置

| 参数名 | 值 | 说明 |
|--------|-----|------|
| interaction_radius (Rb) | 2 | 交互半径 |
| extended_radius (Re) | 4 | 扩展半径 (2×Rb) |
| grid_size | 3 | 网格尺寸 (3×3) |
| T_cz | 0.2 μs | CZ门时间 |
| T_eff | 1.5×10⁶ μs | 相干时间 |
| F_cz | 0.995 | CZ门保真度 |
| AOD_width | 3 μm | 网格宽度 |
| Move_speed | 0.55 μm/μs | 移动速度 |

### 最终结果对比

| 指标 | 值 | 说明 |
|------|-----|------|
| 量子比特数 | 5 | 实际使用 |
| CZ门数 | 30 | 双量子比特门 |
| 原始深度 | 26 | 只计算CZ门 |
| 分区数 | 1 | 无需重映射 |
| 并行组数 | 30 | 串行为主 |
| 移动操作数 | 0 | 无移动 |
| 总保真度 | **0.8604** | 与实验一致 |
| 移动保真度 | 1.0 | 完美 |
| 总时间 | 6.0 μs | 高效 |

---

## 📚 文件清单

本次演示生成的文件:
1. `demo_4gt13_92.py` - 完整流程演示脚本
2. `demo_embeddings_4gt13_92.json` - 嵌入数据
3. `demo_results_4gt13_92.json` - 结果数据
4. `visualize_embedding_4gt13_92.py` - 可视化脚本
5. `STEP_BY_STEP_GUIDE_4gt13_92.md` - 本文档

运行方式:
```bash
# 1. 完整流程演示
python demo_4gt13_92.py

# 2. 可视化嵌入
python visualize_embedding_4gt13_92.py
```

---

**文档生成时间**: 2025-01-XX  
**基于版本**: DasAtom (Rb=2, Re=4)  
**测试电路**: 4gt13_92.qasm (5 qubits, 30 CZ gates)


