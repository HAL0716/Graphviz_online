import numpy as np
import math
from itertools import cycle
from collections import defaultdict, deque
from src import Node

class PeriodicFiniteType:
    # === 1. 初期化 ===
    def __init__(self, alphabet: list[str], phase: int, forbidden_length: int, forbidden_words: list[str]) -> None:
        self.__alphabet = alphabet
        self.__phase = phase
        self.__forbidden_length = forbidden_length
        self.__nodes = self.__build_nodes(forbidden_words)
        self.__active_adjlist: dict[Node, dict[str, Node]] = defaultdict(dict)
        self.__removed_adjlist: dict[Node, dict[str, Node]] = defaultdict(dict)
        self.__renewMap = dict()

    def __build_nodes(self, fragments: list[str]) -> dict[Node, int]:
        nodes = {Node('', t): 1 for t in range(self.__phase)}
        for word in fragments:
            nodes.update({Node(word[:i + 1], 0): 1 for i in range(len(word))})
        return nodes

    # === 2. 外部向けの主要な処理 ===
    def set_adj_list(self) -> None:
        def find_dst(base_label: str, base_phase: int) -> Node:
            for i in range(len(base_label)):
                dst = Node(base_label[i:], (base_phase + i) % self.__phase)
                if dst in self.__nodes:
                    return dst
            return Node("", (base_phase + len(base_label)) % self.__phase)

        def set_dsts(src: Node) -> dict[str, Node]:
            return {
                label: find_dst(src.label + label, src.phase)
                for label in self.__alphabet
            }

        self.__active_adjlist = {
            src: set_dsts(src)
            for src in self.__nodes if len(src.label) < self.__forbidden_length
        }

    def update_essential(self) -> None:
        if not self.__active_adjlist:
            return
        
        in_degree = defaultdict(int)
        out_degree = defaultdict(int)
        for src, edges in self.__active_adjlist.items():
            out_degree[src] = len(edges)
            for dst in edges.values():
                in_degree[dst] += 1

        erase_nodes = deque(
            node for node in self.__nodes
            if in_degree[node] == 0 or out_degree[node] == 0
        )

        def erase(node):
            self.__nodes[node] = 0

            if node in self.__active_adjlist:
                self.__removed_adjlist[node] = self.__active_adjlist.pop(node)

                for dst in self.__removed_adjlist[node].values():
                    in_degree[dst] -= 1
                    if in_degree[dst] == 0:
                        erase_nodes.append(dst)

            for src in list(self.__active_adjlist.keys()):
                edges = self.__active_adjlist[src]
                to_remove = [label for label, dst in edges.items() if dst == node]

                for label in to_remove:
                    dst = edges.pop(label)
                    self.__removed_adjlist[src][label] = dst
                    out_degree[src] -= 1
                    if out_degree[src] == 0:
                        erase_nodes.append(src)

                if not self.__active_adjlist[src]:
                    del self.__active_adjlist[src]

        while erase_nodes:
            erase(erase_nodes.popleft())

    def update_minimize(self):
        if not self.__active_adjlist:
            return

        # 初期状態のID分類
        def init_id_data() -> tuple[dict[str, set[Node]], dict[Node, str]]:
            id_to_nodes = defaultdict(set)
            node_to_id = {}
            for node, edges in self.__active_adjlist.items():
                node_id = ''.join('1' if label in edges else '0' for label in self.__alphabet)
                id_to_nodes[node_id].add(node)
                node_to_id[node] = node_id
            return id_to_nodes, node_to_id

        # ID分類の更新
        def update_id_data(id_to_nodes: dict[str, set[Node]], node_to_id: dict[Node, str]) -> dict[str, set[Node]]:
            new_id_to_nodes = defaultdict(set)
            for node_id, nodes in id_to_nodes.items():
                if len(nodes) == 1:
                    new_id_to_nodes[node_id].update(nodes)
                else:
                    for src in nodes:
                        edges = self.__active_adjlist.get(src, {})
                        new_id = node_id + ''.join(node_to_id.get(edges.get(label, None), '') for label in self.__alphabet if label in edges)
                        new_id_to_nodes[new_id].add(src)
                        node_to_id[src] = new_id
            return new_id_to_nodes

        # 初期化
        id_to_nodes, node_to_id = init_id_data()

        # ID分類が安定するまで繰り返す
        while True:
            new_id_to_nodes = update_id_data(id_to_nodes, node_to_id)
            if len(new_id_to_nodes) == len(id_to_nodes):
                break
            id_to_nodes = new_id_to_nodes

        # ノード代表の取得（辞書順・位相順で最小）
        def get_representative(nodes: set[Node]):
            return min(nodes, key=lambda node: (node.label, node.phase))

        # ノードの再マッピング
        self.__renewMap.clear()
        for nodes in id_to_nodes.values():
            new_node = get_representative(nodes)
            for old_node in nodes:
                self.__renewMap[old_node] = new_node

        # 新しい隣接リストの構築
        new_adjlist = defaultdict(dict)
        for nodes in id_to_nodes.values():
            for src in nodes:
                for label, dst in self.__active_adjlist[src].items():
                    new_src = self.__renewMap[src]
                    new_dst = self.__renewMap[dst]
                    new_adjlist[new_src][label] = new_dst

                    if src != new_src or dst != new_dst:
                        self.__removed_adjlist[src][label] = dst

        self.__active_adjlist = new_adjlist

    @property
    def max_eigenvalue(self) -> float:
        # 1. ノードと連番の対応
        active_nodes = {node for node, value in self.__nodes.items() if value == 1}
        idx_map = {node: i for i, node in enumerate(active_nodes)}
        n = len(idx_map)

        if n == 0:  # 対象となるノードがない場合
            return 0.0

        # 2. 隣接行列を初期化
        adj_matrix = np.zeros((n, n), dtype=int)

        # 3. 隣接リストから隣接行列に変換（対象ノードのみを考慮）
        for src, edges in self.__active_adjlist.items():
            i = idx_map[src]
            for dst in edges.values():
                j = idx_map[dst]
                adj_matrix[i, j] += 1  # 隣接関係があれば1を加算

        # 4. 固有値を計算し、最大の実部を抽出
        eigenvalues = np.linalg.eigvals(adj_matrix)
        return np.max(np.real(eigenvalues))

    def dot(self, params: dict = None) -> str:
        if not self.__active_adjlist:
            return
        
        try:
            self.__set_graph_params(params)
            pos_map = self.__build_pos_map()
            idx_map = self.__build_index_map()

            lines = list()
            lines += self.__build_dot_header()
            lines += self.__build_dot_nodes(idx_map, pos_map)
            lines += self.__build_dot_edges(idx_map)
            lines.append("}")

            return "\n".join(lines)

        except Exception as e:
            print(f"[DOT Error] {e}")
            return ""

    def __str__(self) -> str:
        if self.__active_adjlist:
            return "\n".join(f"{src} -> {', '.join(f'{label} : {dst}' for label, dst in dsts.items())}" for src, dsts in self.__active_adjlist.items())
        else:
            return "\n".join(str(node) for node in sorted(self.__nodes, key=lambda n: (n.phase, n.label)))

    # === 3. dot 出力設定 ===
    def __set_graph_params(self, params: dict):
        def get(k, default): 
            return float(params[k]) if params and k in params and str(params[k]).strip() else default

        self.wid = get("nodeWidth", 0.6)
        self.hgt = get("nodeHeight", 0.4)
        self.xsp = get("spacingX", 1.0)
        self.ysp = get("spacingY", 1.0)

    # === 4. dot 出力構築用の補助メソッド ===
    def __build_pos_map(self) -> dict[Node, tuple[float, float]]:
        def build_layers() -> dict[int, list[Node]]:
            layers = defaultdict(list)
            for node in self.__nodes:
                layers[len(node.label)].append(node)
            for lst in layers.values():
                lst.sort(key=lambda n: (n.label, n.phase))
            return dict(sorted(layers.items()))

        def calc_pos(idx: int, N: int, r: float) -> tuple[float, float]:
            angle = (math.pi / 2) - ((idx + 1) * (2 * math.pi / N))
            x = round(r * math.cos(angle) * self.xsp, 2)
            y = round(r * math.sin(angle) * self.ysp, 2)
            return (x, y)

        N = self.__phase if self.__phase > 3 else 6
        used_cnt = [0] * N
        idx_iter = cycle(range(N))
        pos_map = {}

        for layer_len, nodes in build_layers().items():
            if layer_len == 0 and N != self.__phase:
                nodes.reverse()
            if layer_len == 1 and N == self.__phase:
                idx = next(idx_iter)
            for node in nodes:
                if layer_len == 0:
                    idx = next(idx_iter)
                pos_map[node] = calc_pos(idx, N, used_cnt[idx]+1)
                used_cnt[idx] += 1
            idx = next(idx_iter)
        return pos_map

    def __build_index_map(self) -> dict[Node, int]:
        sorted_nodes = sorted(self.__nodes, key=lambda n: (n.label, n.phase))
        return {node: i for i, node in enumerate(sorted_nodes)}

    def __build_dot_header(self) -> list[str]:
        return [
            "digraph G {",
            "\tlayout=neato;",
            "\tsplines=true;",
            f"\tnode [shape=ellipse, width={self.wid}, height={self.hgt}, fixedsize=true];",
            ""
        ]

    def __build_dot_nodes(self, idx_map: dict, pos_map: dict) -> list[str]:
        lines = []
        for node, state in self.__nodes.items():
            i = idx_map[node]
            x, y = pos_map[node]
            attrs = [f'texlbl="${node.texlbl}$"', f'pos="{x},{y}!"']
            if state == 0:
                attrs += ['style="dotted"', 'color="gray"']
            elif self.__renewMap and node != self.__renewMap[node]:
                attrs += ['style="dashed"']
            lines.append(f'\t{i} [{", ".join(attrs)}];')
        lines.append("")
        return lines
        
    def __build_dot_edges(self, idx_map: dict) -> list[str]:
        def is_renewed_edge(src, dst) -> bool:
            return src in self.__renewMap and dst in self.__renewMap

        def dot_active_edges() -> list[str]:
            return [
                f'\t{idx_map[src]} -> {idx_map[dst]} [label="{label}", texlbl="${label}$"];'
                for src, edges in self.__active_adjlist.items()
                for label, dst in edges.items()
            ]

        def dot_removed_edges() -> list[str]:
            return [
                f'\t{idx_map[src]} -> {idx_map[dst]} [style="dashed"];'
                if is_renewed_edge(src, dst) else
                f'\t{idx_map[src]} -> {idx_map[dst]} [style="dotted", color="gray"];'
                for src, edges in self.__removed_adjlist.items()
                for _, dst in edges.items()
            ]

        def dot_renewed_mappings() -> list[str]:
            return [
                f'\t{idx_map[src]} -> {idx_map[dst]} [style="dashed", arrowhead="none"];'
                for src, dst in self.__renewMap.items()
                if src != dst
            ]

        return dot_active_edges() + dot_removed_edges() + dot_renewed_mappings()