from __future__ import annotations

import json
import logging
from typing import Any

import npc_io
import upath

import aind_session.extension
import aind_session.session
import aind_session.utils.codeocean_utils
        json_path = next(p for p in self.json_paths if p.stem == name)
logger = logging.getLogger(__name__)


@aind_session.extension.register_namespace("metadata")
class Metadata(aind_session.extension.ExtensionBaseClass):
    """Extension for metadata, currently fetched from jsons in raw data
    folder.

    Note: files with a '.' in the name are not supported via attribute access
    (e.g. 'metadata.nd.json'), but can be accessed via `gettattr()`
    """

    def __getattr__(self, name: str) -> dict[str, Any]:
        """Fetch metadata from the raw data folder.

        Examples:
            >>> from aind_session import Session
            >>> session = Session('ecephys_676909_2023-12-13_13-43-40')
            >>> session.metadata.subject['genotype']
            'Pvalb-IRES-Cre/wt;Ai32(RCL-ChR2(H134R)_EYFP)/wt'

            # Files with a '.' in the name must be accessed via getattr:
            >>> content = getattr(session.metadata, 'metadata.nd')
        """
        try:
            _ = self.json_paths
        except FileNotFoundError:
            raise AttributeError(
                f"No raw data folder found for {self._session.id}"
            ) from None
        try:
            path = next(p for p in self.json_paths if p.stem == str(name))
        except StopIteration:
            raise AttributeError(
                f"No {name}.json found in cached view of {self.raw_data_folder.as_posix()}. Available files: {[p.name for p in self.json_paths]}"
            ) from None
        else:
            logger.debug(f"Using contents of metadata json at {path.as_posix()}")
        return json.loads(content)

    @npc_io.cached_property
    def json_paths(self) -> tuple[upath.UPath, ...]:
        """All available metadata jsons in the raw data folder.

        Examples:
            >>> from aind_session import Session
            >>> session = Session('ecephys_676909_2023-12-13_13-43-40')
            >>> [path.name for path in session.metadata.json_paths]
            ['data_description.json', 'metadata.nd.json', 'procedures.json', 'processing.json', 'rig.json', 'session.json', 'subject.json']
        """
        return tuple(
            sorted(
                (
                    path
                    for path in self._session.raw_data_folder.iterdir()
                    if path.suffix == ".json"
                ),
                key=lambda p: p.name,
            )
        )


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
