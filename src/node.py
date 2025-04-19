from dataclasses import dataclass

@dataclass(frozen=True, order=True)
class Node:
    label: str = ""
    phase: int = 0

    @property
    def texlbl(self) -> str:
        return f"({self.label if self.label else r"\epsilon"}, {self.phase})"

    def __repr__(self) -> str:
        return f"({self.label}, {self.phase})"
    
    __str__ = __repr__