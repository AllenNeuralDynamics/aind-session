import json
from pathlib import Path
from typing import Any

import pytest

import aind_session.utils.codeocean_utils
from aind_session.extensions.ecephys import EcephysExtension


def test_import_package() -> None:
    import aind_session

    assert aind_session.__name__ == "aind_session"


@pytest.mark.parametrize(
    ("processing", "expected"),
    (
        (
            {
                "data_processes": [
                    {
                        "name": "Spike sorting",
                        "parameters": {"sorter_name": "kilosort2_5"},
                    }
                ]
            },
            "kilosort2_5",
        ),
        (
            {
                "data_processes": [
                    {
                        "name": "Spike sorting - experiment1.ProbeA-AP_recording1",
                        "code": {"parameters": {"sorter_name": "kilosort4"}},
                    }
                ]
            },
            "kilosort4",
        ),
    ),
)
def test_get_sorter_name_from_processing_json_locations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    processing: dict[str, Any],
    expected: str,
) -> None:
    (tmp_path / "processing.json").write_text(json.dumps(processing))
    monkeypatch.setattr(
        aind_session.utils.codeocean_utils,
        "get_data_asset_source_dir",
        lambda _asset_id: tmp_path,
    )
    EcephysExtension.get_sorter_name.cache_clear()

    assert (
        EcephysExtension.get_sorter_name("00000000-0000-0000-0000-000000000000")
        == expected
    )
