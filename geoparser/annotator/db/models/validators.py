def normalize_newlines(to_normalize: str) -> str:
    return to_normalize.replace("\r\n", "\n").replace("\r", "\n")
