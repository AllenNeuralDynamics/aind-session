from __future__ import annotations

import datetime
import logging

import codeocean.data_asset
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
    AttributeError: No raw data asset in CodeOcean and no dir in known data buckets on S3 for SmartSPIM_698260_2024-07-20_21-47-21

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
        # parse ID to make sure it's valid -raises ValueError if no aind session
        # ID is found in the string:
        record = npc_session.AINDSessionRecord(session_id)

        # get some attributes from the record before storing it as a regular string
        self.subject_id = str(record.subject)
        self.platform: str = record.platform
        # npc_session Date/TimeRecords are str subclasses that normalize inputs
        # and add extra attributes like .dt .year, .month, etc.
        self.date: npc_session.DateRecord = record.date
        self.time: npc_session.TimeRecord = (
            record.time
        )  # uses colon separator like isoformat
        self.datetime: npc_session.DatetimeRecord = record.datetime
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

    @property
    def data_assets(self) -> tuple[codeocean.data_asset.DataAsset, ...]:
        """All data assets associated with the session.

        - objects are instances of `codeocean.data_asset.DataAsset`
        - may be empty
        - sorted by ascending creation date

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.data_assets[0].name
        'ecephys_676909_2023-12-13_13-43-40'
        """
        return aind_session.utils.get_session_data_assets(
            session_id=self.id,
            ttl_hash=aind_session.utils.get_ttl_hash(),
        )

    @property
    def is_uploaded(self) -> bool:
        """Check if the session's raw data has been uploaded.

        - returns `True` if any raw data assets exist, or raw data dir found in S3
        - returns `False` otherwise

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.is_uploaded
        True
        """
        if getattr(self, "raw_data_asset", None) is not None:
            return True
        try:
            _ = aind_session.utils.get_source_dir_by_name(
                name=self.id,
                ttl_hash=aind_session.utils.get_ttl_hash(),
            )
        except FileNotFoundError:
            return False
        else:
            return True

    @property
    def raw_data_asset(self) -> codeocean.data_asset.DataAsset:
        """Latest raw data asset associated with the session.

        - raises `AttributeError` if no raw data assets are found, so `getattr()`
          can be used to lookup the attribute without raising an exception

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
            for asset in self.data_assets
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
            msg = f"No raw data assets found for {self.id}."
            try:
                path = aind_session.utils.get_source_dir_by_name(
                    name=self.id,
                    ttl_hash=aind_session.utils.get_ttl_hash(),
                )
            except FileNotFoundError:
                msg += " The session has likely not been uploaded."
            else:
                msg += f" Raw data found in {path.as_posix()}: a raw data asset needs to be created."
            raise AttributeError(msg)
        logger.debug(f"Using {asset.id=} for {self.id} raw data asset")
        return asset

    @property
    def raw_data_dir(self) -> upath.UPath:
        """Path to the dir containing raw data associated with the session, likely
        in an S3 bucket.

        - uses latest raw data asset to get path (existence is checked)
        - if no raw data asset is found, checks for a data dir in S3
        - raises `AttributeError` if no raw data assets are available to link
          to the session

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.raw_data_dir.as_posix()
        's3://aind-ephys-data/ecephys_676909_2023-12-13_13-43-40'
        """
        if getattr(self, "raw_data_asset", None):
            logger.debug(
                f"Using asset {self.raw_data_asset.id} to find raw data path for {self.id}"
            )
            raw_data_dir = aind_session.utils.get_data_asset_source_dir(
                asset_id=self.raw_data_asset.id,
                ttl_hash=aind_session.utils.get_ttl_hash(),
            )
            logger.debug(f"Raw data dir found for {self.id}: {raw_data_dir}")
            return raw_data_dir
        try:
            path = aind_session.utils.get_source_dir_by_name(
                name=self.id,
                ttl_hash=aind_session.utils.get_ttl_hash(),
            )
        except FileNotFoundError:
            raise AttributeError(
                f"No raw data asset in CodeOcean and no dir in known data buckets on S3 for {self.id}"
            ) from None
        else:
            logger.warning(
                f"No raw data asset exists for {self.id}, but uploaded data dir found: {path}"
            )
            return path

    @property
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
        if not self.is_uploaded:
            logger.warning(
                f"Raw data has not been uploaded for {self.id}: no modalities available yet"
            )
            return ()
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


def get_sessions(
    subject_id: int | str,
    platform: str | None = None,
    date: str | datetime.date | datetime.datetime | None = None,
    start_date: str | datetime.date | datetime.datetime | None = None,
    end_date: str | datetime.date | datetime.datetime | None = None,
) -> tuple[Session, ...]:
    """Return all sessions associated with a subject ID, sorted by ascending date.

    Looks up all assets associated with the subject ID, and creates `Session`
    objects based on their names. If successful (i.e. an aind session ID is
    present in name of the asset), the session's attributes are checked against
    the provided filtering arguments. If all criteria are met, the session is
    added to a set of sessions to be returned as a sorted tuple.

    - optionally filter sessions by platform, date, or a range of dates or datetimes
    - date/datetime filtering with `start_date` and `end_date` are inclusive
    - dates and datetimes are normalized, and can be in almost any common format
        - hyphen and colon separators are accepted but not required:
            - '2023-12-13'
            - '2023-12-13 13:43:40'
            - '2023-12-13_13-43-40'
            - '20231213'
            - '20231213134340'
            - '20231213_134340'
        - `datetime.date` and `datetime.datetime` objects are also accepted

    - raises `ValueError` if any of the provided filtering arguments are invalid
    - returns an empty tuple if no sessions are found matching the criteria

    - note on performance and CodeOcean API calls: all assets associated with a
      subject are fetched once and cached, so subsequent calls to this function
      for the same subject are fast

    Examples
    --------
    >>> sessions = get_sessions(676909)
    >>> sessions[0].platform
    'behavior'
    >>> sessions[0].date
    '2023-10-24'

    Filter sessions by platform:
    >>> get_sessions(676909, platform='ecephys')[0].platform
    'ecephys'

    Filter sessions by date (many formats accepted):
    >>> a = get_sessions(676909, date='2023-12-13')
    >>> b = get_sessions(676909, date='2023-12-13_13-43-40')
    >>> c = get_sessions(676909, date='2023-12-13 13:43:40')
    >>> d = get_sessions(676909, date='20231213')
    >>> e = get_sessions(676909, date='20231213_134340')
    >>> a == b == c == d == e
    True

    Filter sessions by date range:
    >>> get_sessions(676909, start_date='2023-12-13')
    (Session('ecephys_676909_2023-12-13_13-43-40'), Session('ecephys_676909_2023-12-14_12-43-11'))
    >>> get_sessions(676909, start_date='2023-12-13', end_date='2023-12-14_10-00-00')
    (Session('ecephys_676909_2023-12-13_13-43-40'),)
    """
    parameters = {k: v for k, v in locals().items() if v}

    if date and (start_date or end_date):
        raise ValueError(
            f"Cannot filter by specific date and date range at the same time: {parameters=}"
        )

    sessions: set[Session] = set()
    logger.debug(f"Getting sessions from CodeOcean with {parameters=}")
    for asset in aind_session.utils.get_subject_data_assets(subject_id):
        try:
            session = Session(asset.name)
        except ValueError:
            continue
        if platform and session.platform != platform:
            continue
        if date and session.date != npc_session.DateRecord(date):
            continue
        if start_date and session.dt <= npc_session.DatetimeRecord(start_date).dt:
            continue
        if end_date and session.dt >= npc_session.DatetimeRecord(end_date).dt:
            continue
        sessions.add(session)
    if not sessions:
        logger.info(f"No sessions found matching {parameters=}")
    return tuple(sorted(sessions))


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
