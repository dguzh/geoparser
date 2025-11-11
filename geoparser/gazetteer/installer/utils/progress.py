from tqdm.auto import tqdm


def create_progress_bar(
    total: int,
    description: str,
    unit: str = "items",
) -> tqdm:
    """
    Create a standardized progress bar for installation operations.

    This function ensures consistent progress bar formatting across
    all installation stages.

    Args:
        total: Total number of items to process
        description: Description of the operation
        unit: Unit name for items being processed

    Returns:
        A configured tqdm progress bar
    """
    return tqdm(
        total=total,
        desc=description,
        unit=unit,
        unit_scale=unit in ("B", "bytes"),
    )
