import math
from itertools import cycle
from collections import defaultdict
from src import Node

class PeriodicFiniteType:
    def __init__(self, phase: int, f_len: int, fwords: list[str], is_beal: bool = True) -> None:
        self.__phase = phase
        self.__f_len = f_len
        self.__nodes: set[Node] = set()
        self.__adj_list: dict[Node, dict[str, Node]] = {}

        if is_beal:
            self.__init_beal_nodes(fwords)
    
    def __init_beal_nodes(self, fwords: list[str]) -> None:
        self.__nodes.update(Node('', t) for t in range(self.__phase))
        for fword in fwords:
            self.__nodes.update(Node(fword[:i+1], 0) for i, _ in enumerate(fword))

    def set_adj_list(self, alphabet: list[str]) -> None:
        def find_dst(base_label: str, base_phase: int) -> Node:
            for i in range(len(base_label)):
                dst = Node(base_label[i:], (base_phase + i) % self.__phase)
                if dst in self.__nodes:
                    return dst
            return Node("", (base_phase + len(base_label)) % self.__phase)

        def set_dsts(src: Node) -> dict[str, Node]:
            return {
                label: find_dst(src.label + label, src.phase)
                for label in alphabet
            }
        
        # [src][label] = dst
        self.__adj_list = {
            src: set_dsts(src)
            for src in self.__nodes if len(src.label) < self.__f_len
        }

    @property
    def dot(self) -> str:
        if (not self.__adj_list):
            self.set_adj_list()

        try:
            def build_node_layers() -> dict[int, list[Node]]:
                """ラベルの長さごとにノードを整理し、各層をソート"""
                layers = defaultdict(list)
                for node in self.__nodes:
                    layers[len(node.label)].append(node)
                for nodes in layers.values():
                    nodes.sort(key=lambda n: n.phase)
                return dict(sorted(layers.items()))

            def calc_pos(idx: int, N: int, r: float) -> tuple[float, float]:
                """ノードの位置を計算"""
                angle = (math.pi / 2) - (idx * (2 * math.pi / N))
                return round(r * math.cos(angle), 2), round(r * math.sin(angle), 2)
            
            def set_N() -> int:
                """配置の調整"""
                return self.__phase if self.__phase > 3 else 6
            
            def build_pos_map() -> dict[Node, tuple[float, float]]:
                """ノードの配置"""
                N = set_N()
                used_cnt = [0] * N
                idx_iter = cycle(range(N))

                pos_map = {}
                for layer_len, nodes in build_node_layers().items():
                    if layer_len == 0:
                        nodes.reverse()
                    for node in nodes:
                        if layer_len == 0:
                            idx = next(idx_iter)
                        x, y = calc_pos(idx+1, N, used_cnt[idx] + 1)
                        pos_map[node] = (x, y)
                        used_cnt[idx] += 1
                    idx = next(idx_iter)

                return pos_map

            def build_idx_map() -> dict[Node, int]:
                """ノードの番号"""
                sorted_nodes = sorted(self.__nodes, key=lambda n: (n.label, n.phase))
                return {node: i for i, node in enumerate(sorted_nodes)}

            pos_map = build_pos_map()
            idx_map = build_idx_map()

            lines = [
                "digraph G {",
                "\tlayout=neato;",
                "\tsplines=true;",
                "\tnode [shape=ellipse, width=0.6, height=0.4, fixedsize=true];"
            ]
            lines.append("")

            for node, idx in idx_map.items():
                x, y = pos_map[node]
                lines.append(f'\t{idx} [texlbl="${node.texlbl}$", pos="{x},{y}!"];')
            lines.append("")

            for src, dsts in self.__adj_list.items():
                for label, dst in dsts.items():
                    lines.append(f'\t{idx_map[src]} -> {idx_map[dst]} [label="{label}", texlbl="${label}$"];')
            lines.append("}")

            return "\n".join(lines)
        
        except Exception as e:
            print(f"[DOT Error] {e}")
            return ""

    def __str__(self) -> str:
        if self.__adj_list:
            return "\n".join(f"{src} -> {', '.join(f'{label} : {dst}' for label, dst in dsts.items())}" for src, dsts in self.__adj_list.items())
        else:
            return "\n".join(str(node) for node in sorted(self.__nodes, key=lambda n: (n.phase, n.label)))