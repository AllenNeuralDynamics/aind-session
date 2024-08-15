from __future__ import annotations

import contextlib
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

    Examples:
        # Common attributes available for all sessions:
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

        # Should be able to handle all platforms:
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

        # Additional functionality for modalities added by extensions:
        >>> session = Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.ecephys.sorted_data_asset.id                    # doctest: +SKIP
    """

    def __init__(self, session_id: str) -> None:
        """
        Initialize a session object from a session ID.

        Examples:
            >>> session = Session('ecephys_676909_2023-12-13_13-43-40')
        """
        # parse ID to make sure it's valid
        record = npc_session.AINDSessionRecord(session_id)
        # get some attributes from the record before storing it as a regular string
        self.subject_id = str(record.subject)
        self.platform = record.platform
        self.date = record.date
        self.time = record.time
        self.dt = record.dt
        self.id = str(record.id)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.id!r})"

    @npc_io.cached_property
    def assets(self) -> tuple[codeocean.data_asset.DataAsset, ...]:
        """All data assets associated with the session - may be empty.

        - sorted by ascending creation date
        """
        return aind_session.utils.get_session_data_assets(self.id)

    @npc_io.cached_property
    def raw_data_asset(self) -> codeocean.data_asset.DataAsset:
        """Latest raw data asset associated with the session.

        Raises `LookupError` if no raw data assets are found.
        """
        assets = tuple(
            asset
            for asset in self.assets
            if aind_session.utils.is_raw_data_asset(asset)
        )
        if len(assets) == 1:
            asset = assets[0]
        elif len(assets) > 1:
            logger.warning(
                f"Found multiple raw data assets for {self.id}: latest asset will be used as raw data"
            )
            asset = aind_session.utils.sort_data_assets(assets)[-1]
        else:
            raise LookupError(
                f"No raw data asset found for {self.id}. Has session data been uploaded?"
            )
        logger.debug(f"Using {asset.id=} for {self.id} raw data asset")
        return asset

    @npc_io.cached_property
    def raw_data_dir(self) -> upath.UPath:
        """Path to the raw data associated with the session, likely in an S3
        bucket.

        - uses latest raw data asset to get path (existence is checked)
        - if no raw data asset is found, checks for a data dir in S3
        - raises `FileNotFoundError` if no raw data assets are available to link
          to the session
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


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
