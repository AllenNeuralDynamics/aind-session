from __future__ import annotations

import logging

import npc_session

import aind_session.extension
import aind_session.utils.codeocean_utils

logger = logging.getLogger(__name__)


@aind_session.extension.register_namespace("lims")
class LimsExtension(aind_session.extension.ExtensionBaseClass):
    """Extension providing a namespace for legacy sessions with data in LIMS2.

    Examples
    --------
    Get a session from a LabTracks mouse ID and a LIMS2 session ID:
    >>> aind_session.lims.get_session(747816, 1386750279)
    Session('ecephys_747816_2024-08-14_13-57-37')

    Get a lims ID associated with a session object:
    >>> session = aind_session.Session('ecephys_747816_2024-08-14_13-57-37')
    >>> session.lims.id
    1386750279

    Attempt to extract a lims ID from a string:
    >>> aind_session.lims.extract_id('1386750279_747816_20240814.sync')
    1386750279
    """

    _base: aind_session.Session

    @staticmethod
    def get_session(
        labtracks_mouse_id: str | int, lims_session_id: str | int
    ) -> aind_session.Session:
        """Get a session object from a labtracks mouse ID and a LIMS2 session ID.

        Implementation:
        - get session objects for all sessions in CodeOcean matching the given LabTracks mouse ID
        - iterate over the modality folders in each session's raw data dir on S3
        - check if any path names contain the LIMS session ID: if so, break and return the session object

        Examples
        --------
        Get a session from a LabTracks mouse ID and a LIMS2 session ID:
        >>> aind_session.lims.get_session(747816, 1386750279)
        Session('ecephys_747816_2024-08-14_13-57-37')
        """
        subject_sessions = aind_session.get_sessions(
            subject_id=labtracks_mouse_id,
        )
        if not subject_sessions:
            raise ValueError(
                f"No sessions found for subject {labtracks_mouse_id} in CodeOcean - has raw data been uploaded?"
            )
        for session in subject_sessions:
            logger.debug(f"Checking raw data folder: {session.raw_data_dir.as_posix()}")
            for modality_folder in (
                p for p in session.raw_data_dir.iterdir() if p.is_dir()
            ):
                try:
                    matching_path = next(modality_folder.glob(f"*{lims_session_id}*"))
                except StopIteration:
                    continue
                else:
                    logger.info(
                        f"Found path name containing lims session ID: {matching_path.as_posix()}"
                    )
                    return session
            else:
                logger.debug(
                    f"No path names contain {lims_session_id} in {session.id} raw data folder"
                )
        else:
            raise ValueError(
                f"No raw data paths containing {lims_session_id} found in raw data dirs in S3 for {labtracks_mouse_id} - has raw data been uploaded?"
            )

    @staticmethod
    def extract_id(value: str) -> int:
        """Attempt to extract a lims session ID from a string and return it as an
        integer, or raise a ValueError if no lims ID is found.

        Assumes lims ID and other components are separated by underscores (and
        maybe dots).

        Examples
        --------
        Attempt to extract a lims ID from a string:
        >>> aind_session.lims.extract_id('1386750279_747816_20240814.sync')
        1386750279

        Raises a ValueError if no lims ID is found:
        >>> aind_session.lims.extract_id('747816_20240814.sync')
        Traceback (most recent call last):
        ...
        ValueError: No lims ID found in '747816_20240814.sync'
        """
        components = [c for c_ in value.split(".") for c in c_.split("_")]
        logger.debug(f"Checking individual componetns for lims ID: {components}")
        for component in components:
            try:
                _ = int(component)
            except ValueError:
                logger.debug(f"{component} is not an integer: ignoring")
                continue
            logger.debug(f"Found integer component: {component}")
            if len(component) < 9:
                logger.debug(
                    f"{len(component)=} is too short to be a lims ID: ignoring"
                )
                continue
            try:
                npc_session.DatetimeRecord(component)
            except ValueError:
                logger.debug(f"{component} is not a valid datetime")
                pass
            else:
                logger.debug(f"{component} is a valid datetime: ignoring")
                continue
            logger.debug(f"Extracted lims ID: {component}")
            return int(component)
        else:
            raise ValueError(f"No lims ID found in {value!r}")

    @staticmethod
    def get_id(aind_session_id: str) -> int:
        """Get the LIMS2 session ID for a given AIND session ID.

        Examples
        --------
        >>> aind_session.lims.get_id('ecephys_747816_2024-08-14_13-57-37')
        1386750279
        """
        session = aind_session.Session(aind_session_id)
        logger.debug(f"Checking raw data folder: {session.raw_data_dir.as_posix()}")
        for modality_folder in (
            p for p in session.raw_data_dir.iterdir() if p.is_dir()
        ):
            for path in modality_folder.iterdir():
                try:
                    lims_id = LimsExtension.extract_id(
                        path.name
                    )  # name instead of stem as path may be a dir name containung "."
                except ValueError:
                    continue
                else:
                    logger.info(f"Found lims ID in path: {path.as_posix()}")
                    return lims_id
        else:
            raise ValueError(
                f"No path names contain a lims ID for paths in raw data folder for {aind_session_id!r}"
            )

    @property
    def id(self) -> int:
        """The LIMS2 session ID.

        Examples
        --------
        >>> session = aind_session.Session('ecephys_747816_2024-08-14_13-57-37')
        >>> session.lims.id
        1386750279
        """
        return self.get_id(self._base.id)


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
