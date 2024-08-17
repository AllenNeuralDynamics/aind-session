from __future__ import annotations

import contextlib
import datetime
import logging

import codeocean.data_asset
import npc_io
import npc_session
import upath

import aind_session.utils

logger = logging.getLogger(__name__)


class Session:
    """
    Session object for Allen Institute for Neural Dynamics sessions (all platforms).
    Provides paths, metadata and methods for working with session data in
    CodeOcean.

    - makes use of, and returns, objects from `https://github.com/codeocean/codeocean-sdk-python`

    Examples
    --------
    >>> session = Session('ecephys_676909_2023-12-13_13-43-40')

    The same session ID would be extracted from a path:
    >>> session = Session('/root/capsule/aind_session/ecephys_676909_2023-12-13_13-43-40')

    And the same session ID would be extracted from a longer string:
    >>> session = Session('ecephys_676909_2023-12-13_13-43-40_sorted_2024-03-01_16-02-45')

    Common attributes available for all sessions:
    >>> session = Session('ecephys_676909_2023-12-13_13-43-40')
    >>> session.platform
    'ecephys'
    >>> session.subject_id
    '676909'
    >>> session.dt
    datetime.datetime(2023, 12, 13, 13, 43, 40)
    >>> session.raw_data_asset.id
    '16d46411-540a-4122-b47f-8cb2a15d593a'
    >>> session.raw_data_dir.as_posix()
    's3://aind-ephys-data/ecephys_676909_2023-12-13_13-43-40'
    >>> session.modalities
    ('behavior', 'behavior_videos', 'ecephys')

    Should be able to handle all platforms:
    >>> session = Session('multiplane-ophys_741863_2024-08-13_09-26-41')
    >>> session.raw_data_dir.as_posix()
    's3://aind-private-data-prod-o5171v/multiplane-ophys_741863_2024-08-13_09-26-41'

    >>> session = Session('behavior_717121_2024-06-16_11-39-34')
    >>> session.raw_data_dir.as_posix()
    's3://aind-private-data-prod-o5171v/behavior_717121_2024-06-16_11-39-34'

    >>> session = Session('SmartSPIM_698260_2024-07-20_21-47-21')
    >>> session.raw_data_dir.as_posix()
    Traceback (most recent call last):
    ...
    FileNotFoundError: No raw data asset in CodeOcean and no dir in known data buckets on S3 for SmartSPIM_698260_2024-07-20_21-47-21

    Additional functionality for modalities added by extensions:
    >>> session = Session('ecephys_676909_2023-12-13_13-43-40')
    >>> session.ecephys.sorted_data_asset.id            # doctest: +SKIP

    """

    def __init__(self, session_id: str) -> None:
        """
        Initialize a session object from a session ID, or a string containing one.

        Examples
        --------
        >>> session = Session('ecephys_676909_2023-12-13_13-43-40')

        The same session ID would be extracted from a path:
        >>> session = Session('/root/capsule/aind_session/ecephys_676909_2023-12-13_13-43-40')

        And the same session ID would be extracted from a longer string:
        >>> session = Session('ecephys_676909_2023-12-13_13-43-40_sorted_2024-03-01_16-02-45')
        """
        # parse ID to make sure it's valid
        record = npc_session.AINDSessionRecord(session_id)
        # get some attributes from the record before storing it as a regular string
        self.subject_id = str(record.subject)
        self.platform: str = record.platform
        self.date: npc_session.DateRecord = record.date
        self.time: npc_session.TimeRecord = record.time
        self.dt: datetime.datetime = record.dt
        self.id = str(record.id)
        logger.debug(f"Created {self!r} from {session_id}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.id!r})"

    def __eq__(self, other: object) -> bool:
        """
        >>> a = Session('ecephys_676909_2023-12-13_13-43-40')
        >>> b = Session('ecephys_676909_2023-12-13_13-43-40_sorted_2024-03-01_16-02-45')
        >>> assert a == b and a is not b, "Session objects must be equal based on session ID"
        """
        if not isinstance(other, Session):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """
        >>> a = Session('ecephys_676909_2023-12-13_13-43-40')
        >>> b = Session('ecephys_676909_2023-12-13_13-43-40_sorted_2024-03-01_16-02-45')
        >>> assert len(set((a, b))) == 1, "Session objects must be hashable, based on session ID"
        """
        return hash(self.id)

    def __lt__(self, other: Session) -> bool:
        """
        >>> a = Session('ecephys_676909_2023-12-11_14-24-35')
        >>> b = Session('ecephys_676909_2023-12-13_13-43-40')
        >>> assert a < b, "Session objects must be comparable based on session ID"
        """
        return self.id < other.id

    @npc_io.cached_property
    def assets(self) -> tuple[codeocean.data_asset.DataAsset, ...]:
        """All data assets associated with the session.

        - objects are instances of `codeocean.data_asset.DataAsset`
        - may be empty
        - sorted by ascending creation date

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.assets[0].name
        'ecephys_676909_2023-12-13_13-43-40'
        """
        return aind_session.utils.get_session_data_assets(self.id)

    @npc_io.cached_property
    def raw_data_asset(self) -> codeocean.data_asset.DataAsset:
        """Latest raw data asset associated with the session.

        - raises `LookupError` if no raw data assets are found

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.raw_data_asset.id
        '16d46411-540a-4122-b47f-8cb2a15d593a'
        >>> session.raw_data_asset.name
        'ecephys_676909_2023-12-13_13-43-40'
        >>> session.raw_data_asset.created
        1702620828
        """
        assets = tuple(
            asset
            for asset in self.assets
            if aind_session.utils.is_raw_data_asset(asset)
        )
        if len(assets) == 1:
            asset = assets[0]
        elif len(assets) > 1:
            asset = aind_session.utils.sort_data_assets(assets)[-1]
            created = datetime.datetime.fromtimestamp(asset.created).isoformat()
            logger.warning(
                f"Found {len(assets)} raw data assets for {self.id}: latest asset will be used ({created=})"
            )
        else:
            raise LookupError(
                f"No raw data asset found for {self.id}. Has session data been uploaded?"
            )
        logger.debug(f"Using {asset.id=} for {self.id} raw data asset")
        return asset

    @npc_io.cached_property
    def raw_data_dir(self) -> upath.UPath:
        """Path to the dir containing raw data associated with the session, likely
        in an S3 bucket.

        - uses latest raw data asset to get path (existence is checked)
        - if no raw data asset is found, checks for a data dir in S3
        - raises `FileNotFoundError` if no raw data assets are available to link
          to the session

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.raw_data_dir.as_posix()
        's3://aind-ephys-data/ecephys_676909_2023-12-13_13-43-40'
        """
        try:
            _ = self.raw_data_asset
        except LookupError:
            with contextlib.suppress(FileNotFoundError):
                path = aind_session.utils.get_source_dir_by_name(self.id)
                logger.debug(
                    f"No raw data asset uploaded for {self.id}, but data dir found: {path}"
                )
                return path
            raise FileNotFoundError(
                f"No raw data asset in CodeOcean and no dir in known data buckets on S3 for {self.id}"
            ) from None
        else:
            logger.debug(
                f"Using asset {self.raw_data_asset.id} to find raw data path for {self.id}"
            )
            raw_data_dir = aind_session.utils.get_data_asset_source_dir(
                self.raw_data_asset
            )
            logger.debug(f"Raw data dir found for {self.id}: {raw_data_dir}")
            return raw_data_dir

    @npc_io.cached_property
    def modalities(self) -> tuple[str, ...]:
        """Names of modalities available in the session's raw data dir.

        - modality names do not exactly match folder names
            - if 'ecephys_compresed' and 'ecephys_clipped' are found, they're
            represented as 'ecephys'
        - excludes '*metadata*' folders

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.modalities
        ('behavior', 'behavior_videos', 'ecephys')
        """
        dir_names: set[str] = {
            d.name for d in self.raw_data_dir.iterdir() if d.is_dir()
        }
        for name in ("ecephys_compressed", "ecephys_clipped"):
            dir_names.remove(name)
            logger.debug(
                f"Returning modality names with {name!r} represented as 'ecephys'"
            )
            dir_names.add("ecephys")
        for term in ("metadata",):
            for name in tuple(dir_names):
                if term in name:
                    dir_names.remove(name)
                    logger.debug(f"Excluding {name!r} from modality names")
        return tuple(sorted(dir_names))


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
