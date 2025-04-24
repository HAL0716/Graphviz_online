import numpy as np
import math
from itertools import cycle
from collections import defaultdict, deque
from src import Node

class PeriodicFiniteType:
    """Bealらのアルゴリズムを用いたグラフ生成"""

    # === 初期化 ===
    def __init__(self, alphabet: list[str], period: int, forbidden_words: list[str]) -> None:
        def build_node_states(words: list[str]) -> dict[Node, bool]:
            """禁止語の接頭辞で頂点集合を構成"""
            state_map = {Node('', t): True for t in range(self.__period)}
            for word in words:
                state_map.update({Node(word[:i+1], 0): True for i in range(len(word))})
            return state_map
        
        self.__alphabet: list[str] = alphabet
        self.__period: int = period
        self.__forbidden_words: list[str] = forbidden_words
        self.__node_states: dict[Node, bool] = build_node_states(forbidden_words)
        self.__renew_map: dict[Node, Node] = {}
        self.__adjlist_active: dict[Node, dict[str, Node]] = defaultdict(dict)
        self.__adjlist_removed: dict[Node, dict[str, Node]] = defaultdict(dict)

    # === メイン処理 ===
    def set_adj_list(self) -> None:
        """隣接リストを構成"""
        def find_dst(label: str, phase: int) -> Node:
            for i in range(len(label)):
                candidate = Node(label[i:], (phase + i) % self.__period)
                if candidate in self.__node_states:
                    return candidate
            return Node("", (phase + len(label)) % self.__period)

        def build_dsts(node: Node) -> dict[str, Node]:
            return {symbol: find_dst(node.label + symbol, node.phase) for symbol in self.__alphabet}
        
        self.__adjlist_active = {
            node: build_dsts(node)
            for node, state in self.__node_states.items()
            if state and node.label not in self.__forbidden_words
        }

    def update_essential(self) -> None:
        """孤立した頂点を削除"""
        if not self.__adjlist_active:
            return

        # 入次数・出次数のカウント
        degree_in = defaultdict(int)
        degree_out = defaultdict(int)
        for src, edges in self.__adjlist_active.items():
            degree_out[src] = len(edges)
            for dst in edges.values():
                degree_in[dst] += 1

        # 入次数か出次数が0な頂点をリストアップ
        erase_nodes = deque(
            node for node, state in self.__node_states.items()
            if state and (degree_in[node] == 0 or degree_out[node] == 0)
        )

        def erase(node: Node):
            """頂点の削除処理"""
            self.__node_states[node] = False

            # 削除した頂点を始点とするエッジの削除
            if node in self.__adjlist_active:
                self.__adjlist_removed[node] = self.__adjlist_active.pop(node)
                for dst in self.__adjlist_removed[node].values():
                    degree_in[dst] -= 1
                    if degree_in[dst] == 0:
                        erase_nodes.append(dst)

            # 削除した頂点を終点とするエッジの削除
            for src in list(self.__adjlist_active.keys()):
                edges = self.__adjlist_active[src]
                for label, dst in list(edges.items()):
                    if dst == node:
                        edges.pop(label)
                        self.__adjlist_removed[src][label] = dst
                        degree_out[src] -= 1
                        if degree_out[src] == 0:
                            erase_nodes.append(src)

                if not self.__adjlist_active[src]:
                    del self.__adjlist_active[src]

        while erase_nodes:
            erase(erase_nodes.popleft())

    def update_minimize(self) -> None:
        """頂点数の最小化 (Moore's algorithm)"""
        if not self.__adjlist_active:
            return

        def init_id_data() -> tuple[dict[str, set[Node]], dict[Node, str]]:
            """ID分類の初期化"""
            id_to_nodes = defaultdict(set)
            node_to_id = {}
            for node, edges in self.__adjlist_active.items():
                node_id = ''.join('1' if label in edges else '0' for label in self.__alphabet)
                id_to_nodes[node_id].add(node)
                node_to_id[node] = node_id
            return id_to_nodes, node_to_id

        def update_id_data(id_to_nodes: dict[str, set[Node]], node_to_id: dict[Node, str]) -> dict[str, set[Node]]:
            """ID分類の更新"""
            new_id_to_nodes = defaultdict(set)
            for node_id, nodes in id_to_nodes.items():
                if len(nodes) == 1:
                    new_id_to_nodes[node_id].update(nodes)
                else:
                    for src in nodes:
                        edges = self.__adjlist_active.get(src, {})
                        new_id = node_id + ''.join(node_to_id.get(edges.get(label), '') for label in self.__alphabet if label in edges)
                        new_id_to_nodes[new_id].add(src)
                        node_to_id[src] = new_id
            return new_id_to_nodes

        # ID分類が安定するまでループ
        id_to_nodes, node_to_id = init_id_data()
        while True:
            new_id_to_nodes = update_id_data(id_to_nodes, node_to_id)
            if len(new_id_to_nodes) == len(id_to_nodes):
                break
            id_to_nodes = new_id_to_nodes

        def get_representative(nodes: set[Node]) -> Node:
            """ノードの選定"""
            return min(nodes, key=lambda node: (node.label, node.phase))

        # ノードの再マッピング
        self.__renew_map.clear()
        for nodes in id_to_nodes.values():
            new_node = get_representative(nodes)
            for old_node in nodes:
                self.__renew_map[old_node] = new_node

        # 新しい隣接リストの構築
        new_adjlist = defaultdict(dict)
        for nodes in id_to_nodes.values():
            for src in nodes:
                for label, dst in self.__adjlist_active[src].items():
                    new_src = self.__renew_map[src]
                    new_dst = self.__renew_map[dst]
                    new_adjlist[new_src][label] = new_dst
                    if src != new_src or dst != new_dst:
                        self.__adjlist_removed[src][label] = dst

        self.__adjlist_active = new_adjlist

    @property
    def max_eigenvalue(self) -> float:
        """最大固有値を計算"""
        active_nodes = {node for node, state in self.__node_states.items() if state}
        idx_map = {node: i for i, node in enumerate(active_nodes)}
        n = len(idx_map)

        if n == 0:
            return 0.0

        adjmatrix = np.zeros((n, n), dtype=int)
        for src, edges in self.__adjlist_active.items():
            i = idx_map[src]
            for dst in edges.values():
                j = idx_map[dst]
                adjmatrix[i, j] += 1

        eigenvalues = np.linalg.eigvals(adjmatrix)
        return np.max(np.real(eigenvalues))

    def dot(self, params: dict = None) -> str:
        """GraphをDOT形式で出力"""
        if not self.__adjlist_active:
            return ""

        try:
            self.__set_graph_params(params)
            pos_map = self.__build_pos_map()
            idx_map = self.__build_index_map()

            lines = [
                *self.__build_dot_header(),
                *self.__build_dot_nodes(idx_map, pos_map),
                *self.__build_dot_edges(idx_map),
                '}'
            ]
            return "\n".join(lines)

        except Exception as e:
            print(f"[DOT Error] {e}")
            return ""

    def __str__(self) -> str:
        """隣接リストの文字列表現"""
        if self.__adjlist_active:
            return "\n".join(f"{src} -> {', '.join(f'{label} : {dst}' for label, dst in dsts.items())}" for src, dsts in self.__adjlist_active.items())
        else:
            return "\n".join(str(node) for node in sorted(self.__node_states, key=lambda n: (n.phase, n.label)))
    
    # === DOT出力設定 ===
    def __set_graph_params(self, params: dict):
        def get(k, default): 
            return float(params[k]) if params and k in params and str(params[k]).strip() else default

        self.wid = get("nodeWidth", 0.6)
        self.hgt = get("nodeHeight", 0.4)
        self.xsp = get("spacingX", 1.0)
        self.ysp = get("spacingY", 1.0)

    # === DOT出力構築用補助メソッド ===
    def __build_pos_map(self) -> dict[Node, tuple[float, float]]:
        """ノードの配置位置を計算"""
        def build_layers() -> dict[int, list[Node]]:
            layers = defaultdict(list)
            for node in self.__node_states:
                layers[len(node.label)].append(node)
            for lst in layers.values():
                lst.sort(key=lambda n: (n.label, n.phase))
            return dict(sorted(layers.items()))

        def calc_pos(idx: int, N: int, r: float) -> tuple[float, float]:
            angle = (math.pi / 2) - ((idx + 1) * (2 * math.pi / N))
            x = round(r * math.cos(angle) * self.xsp, 2)
            y = round(r * math.sin(angle) * self.ysp, 2)
            return (x, y)

        N = self.__period if self.__period > 3 else 6
        used_cnt = [0] * N
        idx_iter = cycle(range(N))
        pos_map = {}

        for layer_len, nodes in build_layers().items():
            if layer_len == 0 and N != self.__period:
                nodes.reverse()
            if layer_len == 1 and N == self.__period:
                idx = next(idx_iter)
            for node in nodes:
                if layer_len == 0:
                    idx = next(idx_iter)
                pos_map[node] = calc_pos(idx, N, used_cnt[idx] + 1)
                used_cnt[idx] += 1
            idx = next(idx_iter)
        return pos_map

    def __build_index_map(self) -> dict[Node, int]:
        """ノードをインデックスにマッピング"""
        sorted_nodes = sorted(self.__node_states, key=lambda n: (n.label, n.phase))
        return {node: i for i, node in enumerate(sorted_nodes)}

    def __build_dot_header(self) -> list[str]:
        """DOT形式のヘッダを構築"""
        return [
            "digraph G {",
            "\tlayout=neato;",
            "\tsplines=true;",
            f"\tnode [shape=ellipse, width={self.wid}, height={self.hgt}, fixedsize=true];",
            ""
        ]

    def __build_dot_nodes(self, idx_map: dict, pos_map: dict) -> list[str]:
        """ノード情報をDOT形式で構築"""
        lines = []
        for node, state in self.__node_states.items():
            i = idx_map[node]
            x, y = pos_map[node]
            attrs = [f'texlbl="${node.texlbl}$"', f'pos="{x},{y}!"']
            if not state:
                attrs += ['style="dotted"', 'color="gray"']
            elif self.__renew_map and node != self.__renew_map[node]:
                attrs += ['style="dashed"']
            lines.append(f'\t{i} [{", ".join(attrs)}];')
        lines.append("")
        return lines
        
    def __build_dot_edges(self, idx_map: dict) -> list[str]:
        """エッジ情報をDOT形式で構築"""
        def is_renewed_edge(src, dst) -> bool:
            return src in self.__renew_map and dst in self.__renew_map

        def dot_active_edges() -> list[str]:
            return [
                f'\t{idx_map[src]} -> {idx_map[dst]} [label="{label}", texlbl="${label}$"];'
                for src, edges in self.__adjlist_active.items()
                for label, dst in edges.items()
            ]

        def dot_removed_edges() -> list[str]:
            return [
                f'\t{idx_map[src]} -> {idx_map[dst]} [style="dashed"];'
                if is_renewed_edge(src, dst) else
                f'\t{idx_map[src]} -> {idx_map[dst]} [style="dotted", color="gray"];'
                for src, edges in self.__adjlist_removed.items()
                for _, dst in edges.items()
            ]

        def dot_renewed_mappings() -> list[str]:
            return [
                f'\t{idx_map[src]} -> {idx_map[dst]} [style="dashed", arrowhead="none"];'
                for src, dst in self.__renew_map.items()
                if src != dst
            ]

        return dot_active_edges() + dot_removed_edges() + dot_renewed_mappings()