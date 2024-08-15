from __future__ import annotations

import json
import logging
from typing import Any

import npc_io
import upath

import aind_session.extension
import aind_session.session
import aind_session.utils.codeocean_utils

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
            _ = self.json_files
        except FileNotFoundError:
            raise AttributeError(
                f"No raw data dir found for {self._session.id}"
            ) from None
        try:
            path = next(p for p in self.json_files if p.stem == str(name))
        except StopIteration:
            raise AttributeError(
                f"No {name}.json found in cached view of {self.json_dir.as_posix()}. Available files: {[p.name for p in self.json_files]}"
            ) from None
        else:
            logger.debug(f"Using contents of metadata json at {path.as_posix()}")
        return json.loads(path.read_text())

    @property
    def json_dir(self) -> upath.UPath:
        """Parent dir containing metadata json files"""
        path = self._session.raw_data_dir  # may raise FileNotFoundError
        logger.debug(f"Using {path.as_posix()} as parent dir for metadata json files")
        return path

    @npc_io.cached_property
    def json_files(self) -> tuple[upath.UPath, ...]:
        """All available metadata jsons in the raw data folder.

        Examples:
            >>> from aind_session import Session
            >>> session = Session('ecephys_676909_2023-12-13_13-43-40')
            >>> [path.name for path in session.metadata.json_files]
            ['data_description.json', 'metadata.nd.json', 'procedures.json', 'processing.json', 'rig.json', 'session.json', 'subject.json']
        """
        return tuple(
            sorted(
                (path for path in self.json_dir.iterdir() if path.suffix == ".json"),
                key=lambda p: p.name,
            )
        )


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
