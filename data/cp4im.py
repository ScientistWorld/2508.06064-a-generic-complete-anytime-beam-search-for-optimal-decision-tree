"""Load CP4IM annotated transaction datasets for binary classification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BinaryDataset:
    name: str
    features: tuple[int, ...]
    rows: tuple[frozenset[int], ...]
    labels: tuple[int, ...]


def load_transaction_file(path: str | Path, name: str | None = None) -> BinaryDataset:
    path = Path(path)
    rows: list[frozenset[int]] = []
    labels: list[int] = []
    features: set[int] = set()
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("@") or line.startswith("%"):
                continue
            values = [int(tok) for tok in line.split()]
            if len(values) < 2:
                continue
            label = values[-1]
            items = frozenset(values[:-1])
            rows.append(items)
            labels.append(label)
            features.update(items)
    if not rows:
        raise ValueError(f"no examples found in {path}")
    return BinaryDataset(
        name=name or path.stem,
        features=tuple(sorted(features)),
        rows=tuple(rows),
        labels=tuple(labels),
    )


def subset_dataset(ds: BinaryDataset, max_rows: int | None = None, max_features: int | None = None) -> BinaryDataset:
    rows = ds.rows[:max_rows] if max_rows else ds.rows
    labels = ds.labels[:max_rows] if max_rows else ds.labels
    counts = {f: 0 for f in ds.features}
    for row in rows:
        for f in row:
            if f in counts:
                counts[f] += 1
    features = tuple(
        f for f, _ in sorted(counts.items(), key=lambda kv: (-min(kv[1], len(rows) - kv[1]), kv[0]))[:max_features]
    ) if max_features else ds.features
    return BinaryDataset(ds.name, features, tuple(rows), tuple(labels))


def load_named(download_dir: str | Path, name: str, max_rows: int | None = None, max_features: int | None = None) -> BinaryDataset:
    ds = load_transaction_file(Path(download_dir) / f"{name}.txt", name=name)
    return subset_dataset(ds, max_rows=max_rows, max_features=max_features)
