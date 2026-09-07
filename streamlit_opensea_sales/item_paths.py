from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent / "data_opensea_sales"


def resolve_item_path(value: str | Path, data_root: Path = DATA_ROOT) -> Path:
    path = Path(value)
    if not path.is_absolute():
        return data_root / path
    parts = list(path.parts)
    for index, part in enumerate(parts):
        if part.casefold() == "data_opensea_sales":
            return data_root.joinpath(*parts[index + 1:])
    return path
