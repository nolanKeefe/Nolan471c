from collections import defaultdict


class SequentialNameGenerator:
    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict[str, int](int)

    def __call__(self, candidate: str) -> str:
        current: int = self._counters[candidate]
        self._counters[candidate] += 1
        return f"{candidate}{current}"
