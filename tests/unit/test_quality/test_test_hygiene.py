from pathlib import Path

from tests.conftest import _cleanup_training_outputs


def test_training_output_cleanup_removes_only_known_model_directories(
    tmp_path: Path,
) -> None:
    retained = tmp_path / "fixture-data"
    retained.mkdir()
    (retained / "input.txt").write_text("keep", encoding="utf-8")
    training_output = tmp_path / "trained_model"
    training_output.mkdir()
    (training_output / "checkpoint.bin").write_bytes(b"large model")

    _cleanup_training_outputs(tmp_path)

    assert retained.exists()
    assert training_output.exists() is False
