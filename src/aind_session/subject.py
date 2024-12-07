from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import codeocean.data_asset
import npc_session

import aind_session.session
import aind_session.utils

if TYPE_CHECKING:
    import aind_session.extensions.smartspim_neuropixels

logger = logging.getLogger(__name__)


class Subject:

    # optional annotations for extensions here to enable IDE type checking,
    # autocompletion, etc.
    neuroglancer: aind_session.extensions.smartspim_neuropixels.NeuroglancerExtension
    ibl_data_converter: (
        aind_session.extensions.smartspim_neuropixels.IBLDataConverterExtension
    )

    def __init__(self, subject_id: str | int) -> None:
        """
        Initialize a subject object from a subject ID, or a string containing one.

        - if subject ID is an integer, it will be converted to a string when stored

        Examples
        --------
        >>> subject = Subject(676909)
        >>> subject.id
        '676909'

        The same subject ID would be extracted from a path:
        >>> subject = Subject('/root/capsule/aind_session/ecephys_676909_2023-12-13_13-43-40')
        >>> subject.id
        '676909'
        """
        extracted_id: int | None = npc_session.extract_subject(str(subject_id))
        if extracted_id is None:
            logger.warning(
                f"Could not extract a recognized subject ID from {subject_id!r}"
            )
        self.id = str(extracted_id or subject_id)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.id!r})"

    def __eq__(self, other: object) -> bool:
        """
        >>> a = Subject(676908)
        >>> b = Subject('676908')
        >>> assert a == b and a is not b, "Subject objects must be equal based on subject ID"
        """
        if not isinstance(other, Subject):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """
        >>> a = Subject(676908)
        >>> b = Subject('676908')
        >>> assert len(set((a, b))) == 1, "Subject objects must be hashable, based on subject ID"
        """
        return hash(self.id)

    def __lt__(self, other: Subject) -> bool:
        """
        >>> a = Subject(676908)
        >>> b = Subject('676909')
        >>> assert a < b, "Subject objects must be comparable based on subject ID"
        """
        return self.id < other.id

    @property
    def sessions(self) -> tuple[aind_session.session.Session, ...]:
        """All sessions associated with the subject.

        - objects are instances of `aind_session.Session`
        - may be empty
        - sorted by ascending session date

        Examples
        --------
        >>> subject = Subject(676909)
        >>> subject.sessions[0].id
        'behavior_676909_2023-10-24_15-15-50'
        """
        return aind_session.session.get_sessions(
            subject_id=self.id,
        )

    @property
    def docdb(self) -> tuple[dict[str, Any], ...]:
        """Contents of all of the DocumentDB records for assets associated with
        the subject (may be empty).

        Examples
        --------
        >>> subject = Subject('676909_2023-12-13_13-43-40')
        >>> docdb = subject.docdb
        >>> type(docdb[0])
        <class 'dict'>
        >>> docdb.keys()       # doctest: +SKIP
        dict_keys(['_id', 'acquisition', 'created', 'data_description', 'describedBy', 'external_links', 'instrument', 'last_modified', 'location', 'metadata_status', 'name', 'procedures', 'processing', 'rig', 'schema_version', 'session', 'subject'])
        """
        return aind_session.utils.get_subject_docdb_records(
            self.id, ttl_hash=aind_session.utils.get_ttl_hash(12 * 3600)
        )

    @property
    def data_assets(self) -> tuple[codeocean.data_asset.DataAsset, ...]:
        """All data assets associated with the subject.

        - objects are instances of `codeocean.data_asset.DataAsset`
        - may be empty
        - sorted by ascending creation date

        Examples
        --------
        >>> subject = Subject(676909)
        >>> subject.data_assets[0].name
        'Example T1 and T2 MRI Images'
        """
        return aind_session.utils.get_subject_data_assets(
            subject_id=self.id,
            ttl_hash=aind_session.utils.get_ttl_hash(),
        )


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
