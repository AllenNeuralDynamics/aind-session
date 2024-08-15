from __future__ import annotations

import logging

import codeocean.data_asset
import npc_io
import npc_session
import upath

import aind_session.extension
import aind_session.session
import aind_session.utils.codeocean_utils

logger = logging.getLogger(__name__)


@aind_session.extension.register_namespace("ecephys")
class Ecephys(aind_session.extension.ExtensionBaseClass):
    """Extension for the ecephys modality for handling sorted data assets, etc."""

    @property
    def sorted_data_asset(self) -> codeocean.data_asset.DataAsset:
        """Latest sorted data asset associated with the session.

        Raises `LookupError` if no sorted data assets are found.

        Examples:
            >>> from aind_session import Session
            >>> session = Session('ecephys_676909_2023-12-13_13-43-40')
            >>> session.ecephys.sorted_data_asset.id
            'a2a54575-b5ca-4cf0-acd0-2933e18bcb2d'
        """
        assets = tuple(
            asset for asset in self._session.assets if self.is_sorted_data_asset(asset)
        )
        if len(assets) == 1:
            asset = assets[0]
        elif len(assets) > 1:
            logger.warning(
                f"Found multiple raw data assets for {self._session.id}: latest asset will be used as raw data"
            )
            asset = aind_session.utils.sort_data_assets(assets)[-1]
        else:
            raise LookupError(
                f"No raw data asset found for {self._session.id}. Has session data been uploaded?"
            )
        logger.debug(f"Using {asset.id=} for {self._session.id} raw data asset")
        return asset

    @npc_io.cached_property
    def sorted_data_folder(self) -> upath.UPath:
        """Path to the sorted data associated with the session, likely in an S3
        bucket.

        - uses latest sorted data asset to get path (existence is checked)
        - if no sorted data asset is found, checks for a data folder in S3
        - raises `FileNotFoundError` if no sorted data assets are available to link
          to the session

        Examples:
            >>> from aind_session import Session
            >>> session = Session('ecephys_676909_2023-12-13_13-43-40')
            >>> session.ecephys.sorted_data_folder.as_posix()
            's3://codeocean-s3datasetsbucket-1u41qdg42ur9/a2a54575-b5ca-4cf0-acd0-2933e18bcb2d'
        """
        try:
            _ = self.sorted_data_asset
        except LookupError:
            raise FileNotFoundError(
                f"No sorted data asset found in CodeOcean for {self._session.id}. Has the session been sorted?"
            ) from None
        else:
            logger.debug(
                f"Using asset {self.sorted_data_asset.id} to find sorted data path for {self._session.id}"
            )
            sorted_data_folder = (
                aind_session.utils.codeocean_utils.get_data_asset_source_folder(
                    self.sorted_data_asset
                )
            )
            logger.debug(
                f"Sorted data path found for {self._session.id}: {sorted_data_folder}"
            )
            return sorted_data_folder

    @staticmethod
    def is_sorted_data_asset(asset_id: str | codeocean.data_asset.DataAsset) -> bool:
        """Check if the asset is a sorted data asset.

        - assumed sorted asset to be named <session-id>_sorted<unknown-suffix>
        - does not assume platform to be `ecephys`

        Examples:
            >>> Ecephys.is_sorted_data_asset('173e2fdc-0ca3-4a4e-9886-b74207a91a9a')
            True
            >>> Ecephys.is_sorted_data_asset('83636983-f80d-42d6-a075-09b60c6abd5e')
            False
        """
        asset = aind_session.utils.codeocean_utils.get_data_asset(asset_id)
        try:
            session_id = str(npc_session.AINDSessionRecord(asset.name))
        except ValueError:
            logger.debug(
                f"{asset.name=} does not contain a valid session ID: determined to be not a sorted data asset"
            )
            return False
        if asset.name.startswith(f"{session_id}_sorted"):
            logger.debug(
                f"{asset.name=} determined to be a sorted data asset based on name starting with '<session-id>_sorted'"
            )
            return True
        else:
            logger.debug(
                f"{asset.name=} determined to be not a sorted data asset based on name starting with '<session-id>_sorted'"
            )
            return False


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
