from __future__ import annotations

import datetime
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
    """Extension providing an ecephys modality namespace, for handling sorted data
    assets etc.

    Examples
    --------
    >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
    >>> session.ecephys.sorted_data_asset.id
    'a2a54575-b5ca-4cf0-acd0-2933e18bcb2d'
    >>> session.ecephys.sorted_data_asset.name
    'ecephys_676909_2023-12-13_13-43-40_sorted_2024-03-01_16-02-45'
    >>> session.ecephys.clipped_dir.as_posix()
    's3://aind-ephys-data/ecephys_676909_2023-12-13_13-43-40/ecephys_clipped'
    """

    @npc_io.cached_property
    def sorted_data_assets(self) -> tuple[codeocean.data_asset.DataAsset, ...]:
        """All sorted data assets associated with the session (may be empty).

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.ecephys.sorted_data_assets[0].id
        '1e11bdf5-b452-4fd9-bbb1-48383a9b0842'
        >>> session.ecephys.sorted_data_assets[0].name
        'ecephys_676909_2023-12-13_13-43-40_sorted_2023-12-17_03-16-51'
        >>> session.ecephys.sorted_data_assets[0].created
        1702783011

        Empty
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-39')
        >>> session.ecephys.sorted_data_assets
        ()
        """
        assets = tuple(
            asset
            for asset in self._session.data_assets
            if self.is_sorted_data_asset(asset)
        )
        logger.debug(
            f"Found {len(assets)} sorted data asset{'' if len(assets) == 1 else 's'} for {self._session.id}"
        )
        return assets

    @npc_io.cached_property
    def sorted_data_asset(self) -> codeocean.data_asset.DataAsset:
        """Latest sorted data asset associated with the session.

        Raises `LookupError` if no sorted data assets are found.

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> asset = session.ecephys.sorted_data_asset
        >>> asset.id        # doctest: +SKIP
        'a2a54575-b5ca-4cf0-acd0-2933e18bcb2d'
        >>> asset.name      # doctest: +SKIP
        'ecephys_676909_2023-12-13_13-43-40_sorted_2024-03-01_16-02-45'
        >>> asset.created   # doctest: +SKIP
        1709420992
        """
        if len(self.sorted_data_assets) == 1:
            asset = self.sorted_data_assets[0]
        elif len(self.sorted_data_assets) > 1:
            asset = aind_session.utils.sort_data_assets(self.sorted_data_assets)[-1]
            created = datetime.datetime.fromtimestamp(asset.created).isoformat(sep=" ")
            logger.warning(
                f"Found {len(self.sorted_data_assets)} sorted data assets for {self._session.id}: most recent asset will be used ({created=})"
            )
        else:
            raise LookupError(
                f"No sorted data asset found for {self._session.id}. Has session data been uploaded?"
            )
        logger.debug(f"Using {asset.id=} for {self._session.id} sorted data asset")
        return asset

    @npc_io.cached_property
    def sorted_data_dir(self) -> upath.UPath:
        """Path to the dir containing the latest sorted data associated with the
        session, likely in an S3 bucket.

        - uses latest sorted data asset to get path (existence is checked)
        - if no sorted data asset is found, checks for a data dir in S3
        - raises `FileNotFoundError` if no sorted data assets are available to link
          to the session

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.ecephys.sorted_data_dir.as_posix()
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
            sorted_data_dir = (
                aind_session.utils.codeocean_utils.get_data_asset_source_dir(
                    self.sorted_data_asset
                )
            )
            logger.debug(
                f"Sorted data path found for {self._session.id}: {sorted_data_dir}"
            )
            return sorted_data_dir

    @staticmethod
    def is_sorted_data_asset(asset_id: str | codeocean.data_asset.DataAsset) -> bool:
        """Check if the asset is a sorted data asset.

        - assumes sorted asset to be named <session-id>_sorted<unknown-suffix>
        - does not assume platform to be `ecephys`

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.ecephys.is_sorted_data_asset('173e2fdc-0ca3-4a4e-9886-b74207a91a9a')
        True
        >>> session.ecephys.is_sorted_data_asset('83636983-f80d-42d6-a075-09b60c6abd5e')
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

    @npc_io.cached_property
    def _clipped_and_compressed_dirs(
        self,
    ) -> tuple[upath.UPath | None, upath.UPath | None]:
        candidate_parent_dirs = (
            self._session.raw_data_dir
            / "ecephys",  # newer location in dedicated modality folder
            self._session.raw_data_dir,  # original location in root if upload folder
        )
        return_paths: list[upath.UPath | None] = [None, None]
        for parent_dir in candidate_parent_dirs:
            for i, name in enumerate(("clipped", "compressed")):
                if (path := parent_dir / f"ecephys_{name}").exists():
                    if (existing_path := return_paths[i]) is None:
                        return_paths[i] = path
                        logger.debug(f"Found {path.as_posix()}")
                    else:
                        assert existing_path is not None
                        logger.warning(
                            f"Found multiple {name} dirs: using {existing_path.relative_to(self._session.raw_data_dir).as_posix()} over {path.relative_to(self._session.raw_data_dir).as_posix()}"
                        )
        assert len(return_paths) == 2
        return return_paths[0], return_paths[1]

    @npc_io.cached_property
    def clipped_dir(self) -> upath.UPath:
        """Path to the dir containing original Open Ephys recording data, with
        truncated `continuous.dat` files.

        - originally located in the root of the session's raw data dir
        - for later sessions (2024 onwards), located in an `ecephys` subdirectory

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.ecephys.clipped_dir.as_posix()
        's3://aind-ephys-data/ecephys_676909_2023-12-13_13-43-40/ecephys_clipped'
        """
        if (path := self._clipped_and_compressed_dirs[0]) is None:
            raise FileNotFoundError(
                f"No 'clipped' dir found in uploaded raw data for {self._session.id} (checked in root dir and modality subdirectory)"
            )
        return path

    @npc_io.cached_property
    def compressed_dir(self) -> upath.UPath:
        """
        Path to the dir containing compressed zarr format versions of Open Ephys
        recording data (AP and LFP).

        - originally located in the root of the session's raw data dir
        - for later sessions (2024 onwards), located in an `ecephys` subdirectory

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.ecephys.compressed_dir.as_posix()
        's3://aind-ephys-data/ecephys_676909_2023-12-13_13-43-40/ecephys_compressed'
        """
        if (path := self._clipped_and_compressed_dirs[1]) is None:
            raise FileNotFoundError(
                f"No 'compressed' dir found in uploaded raw data for {self._session.id} (checked in root dir and modality subdirectory)"
            )
        return path

    @npc_io.cached_property
    def sorted_probes(self) -> tuple[str, ...]:
        """Names of probes that reached the final stage of the sorting pipeline.

        - checks for probe dirs in the session's sorted data dir
        - checks a specific dir that indicates all processing completed:
            - `sorting_precurated` was original dir name, then changed to `curated`
        - probe folders named `experiment1_Record Node
          104#Neuropix-PXI-100.ProbeF-AP_recording1` - from which `ProbeF` would
          be extracted

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.ecephys.sorted_probes
        ('ProbeA', 'ProbeB', 'ProbeC', 'ProbeD', 'ProbeE', 'ProbeF')
        """
        candidate_parent_dirs = (
            self.sorted_data_dir / "curated",
            self.sorted_data_dir / "sorting_precurated",
        )
        for parent_dir in candidate_parent_dirs:
            if parent_dir.exists():
                break
        else:
            logger.warning(
                f"No 'curated' or 'sorting_precurated' dir found in {self.sorted_data_dir.as_posix()}: assuming no probes completed processing"
            )
            return ()
        probes = set()
        for path in parent_dir.iterdir():
            # e.g. experiment1_Record Node 104#Neuropix-PXI-100.ProbeF-AP_recording1
            probe = path.name.split(".")[1].split("-AP")[0].split("-LFP")[0]
            probes.add(probe)
        logger.debug(f"Found {len(probes)} probes in {parent_dir.as_posix()}: {probes}")
        return tuple(sorted(probes))


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
