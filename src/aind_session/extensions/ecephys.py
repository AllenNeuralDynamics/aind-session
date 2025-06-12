from __future__ import annotations

import concurrent.futures
import contextlib
import functools
import itertools
import json
import logging
from typing import ClassVar, Literal

import codeocean.computation
import codeocean.data_asset
import npc_session
import upath

import aind_session.extension
import aind_session.utils.codeocean_utils

logger = logging.getLogger(__name__)


@aind_session.extension.register_namespace("ecephys")
class EcephysExtension(aind_session.extension.ExtensionBaseClass):
    """Extension providing an ecephys modality namespace, for handling sorted data
    assets etc.

    Examples
    --------
    Access the ecephys extension namespace on a session object:
    >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
    >>> session.ecephys
    EcephysExtension(Session('ecephys_676909_2023-12-13_13-43-40'))
    >>> session.ecephys.clipped_dir.as_posix()
    's3://aind-ephys-data/ecephys_676909_2023-12-13_13-43-40/ecephys_clipped'

    The extension mostly provides static methods, which can be used without
    a session object if necessary:
    >>> aind_session.ecephys
    <class 'aind_session.extensions.ecephys.EcephysExtension'>
    >>> clipped, compressed = aind_session.ecephys.get_clipped_and_compressed_dirs('16d46411-540a-4122-b47f-8cb2a15d593a')

    Access all sorted assets for a session (may be empty, or may include
    incomplete assets failed pipeline runs):
    >>> session.ecephys.sorted_data_assets[0].name
    'ecephys_676909_2023-12-13_13-43-40_sorted_2023-12-17_03-16-51'

    Access subsets of data assets by sorter name:
    >>> session.ecephys.sorter.kilosort2_5.sorted_data_assets[0].id
    '1e11bdf5-b452-4fd9-bbb1-48383a9b0842'
    >>> session.ecephys.sorter.kilosort2_5.sorted_data_assets[0].name
    'ecephys_676909_2023-12-13_13-43-40_sorted_2023-12-17_03-16-51'
    >>> session.ecephys.sorter.names
    ('kilosort2_5',)

    Returned models are enhanced with sorting pipeline-related properties:
    >>> session.ecephys.sorted_data_assets[0].sorted_probes
    ('ProbeA', 'ProbeB', 'ProbeC', 'ProbeD', 'ProbeE', 'ProbeF')
    >>> session.ecephys.sorted_data_assets[0].sorter_name
    'kilosort2_5'
    """

    _base: aind_session.Session

    DEFAULT_SORTING_PIPELINE_ID: ClassVar[str] = "1f8f159a-7670-47a9-baf1-078905fc9c2e"
    DEFAULT_TRIGGER_CAPSULE_ID: ClassVar[str] = "eb5a26e4-a391-4d79-9da5-1ab65b71253f"

    @property
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
        if (
            path := EcephysExtension.get_clipped_and_compressed_dirs(
                self._base.raw_data_asset.id
            )[0]
        ) is None:
            raise AttributeError(
                f"No 'clipped' dir found in uploaded raw data for {self._base.id} (checked in root dir and modality subdirectory)"
            )
        return path

    @property
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
        if (
            path := EcephysExtension.get_clipped_and_compressed_dirs(
                self._base.raw_data_asset.id
            )[1]
        ) is None:
            raise AttributeError(
                f"No 'compressed' dir found in uploaded raw data for {self._base.id} (checked in root dir and modality subdirectory)"
            )
        return path

    @staticmethod
    def get_clipped_and_compressed_dirs(
        raw_data_asset_id_or_model: str | codeocean.data_asset.DataAsset,
    ) -> tuple[upath.UPath | None, upath.UPath | None]:
        """
        Paths to the dirs containing Open Ephys recording data in CodeOcean upload
        dir.

        - originally located in the root of the session's raw data dir
        - for later sessions (2024 onwards), located in an `ecephys` subdirectory

        Examples
        --------
        >>> clipped, compressed = aind_session.ecephys.get_clipped_and_compressed_dirs('16d46411-540a-4122-b47f-8cb2a15d593a')
        >>> clipped.as_posix()
        's3://aind-ephys-data/ecephys_676909_2023-12-13_13-43-40/ecephys_clipped'
        """
        asset_id = aind_session.utils.codeocean_utils.get_normalized_uuid(
            raw_data_asset_id_or_model
        )
        raw_data_dir = aind_session.utils.get_data_asset_source_dir(asset_id=asset_id)
        candidate_parent_dirs = (
            raw_data_dir / "ecephys",  # newer location in dedicated modality folder
            raw_data_dir,  # original location in root if upload folder
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
                        logger.info(
                            f"Found multiple {name} dirs: using {existing_path.relative_to(raw_data_dir).as_posix()} over {path.relative_to(raw_data_dir).as_posix()}"
                        )
        assert len(return_paths) == 2
        return return_paths[0], return_paths[1]

    @property
    def is_sorted(self) -> bool:
        """A sorted data asset exists, and it is in an error-free state.

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.ecephys.is_sorted
        True
        """
        if not self.sorted_data_assets:
            return False
        if self.sorted_data_assets[-1].is_sorting_error:
            return False
        logger.debug(
            f"The latest sorted data asset for {self._base.id} appears to have been sorted successfully: {self.sorted_data_assets[-1].id}"
        )
        return True

    @property
    def sorted_data_assets(self) -> tuple[SortedDataAsset, ...]:
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

        Empty if no sorted data assets are found:
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-39')
        >>> session.ecephys.sorted_data_assets
        ()
        """
        assets = tuple(
            EcephysExtension.get_sorted_data_asset_model(asset)
            for asset in self._base.data_assets
            if EcephysExtension.is_sorted_data_asset(asset.id)
        )
        logger.debug(
            f"Found {len(assets)} sorted data asset{'' if len(assets) == 1 else 's'} for {self._base.id}"
        )
        return assets

    class SortedDataAsset(codeocean.data_asset.DataAsset):
        """An instance of `codeocean.data_asset.DataAsset` with additional property
        getters related to output from the spike sorting pipeline"""

        @property
        def path(self) -> upath.UPath:
            """Path to source dir (likely on S3).

            Examples
            --------
            >>> asset = aind_session.ecephys.get_sorted_data_asset_model('1e11bdf5-b452-4fd9-bbb1-48383a9b0842')
            >>> asset.path.as_posix()
            's3://codeocean-s3datasetsbucket-1u41qdg42ur9/1e11bdf5-b452-4fd9-bbb1-48383a9b0842'
            """
            return aind_session.utils.codeocean_utils.get_data_asset_source_dir(self.id)

        @property
        def output(self) -> str:
            """Contents of the `output` file in the asset's data dir.

            Examples
            --------
            >>> asset = aind_session.ecephys.get_sorted_data_asset_model('1e11bdf5-b452-4fd9-bbb1-48383a9b0842')
            >>> asset.output[-32:-1]
            'FULL PIPELINE time:  161658.77s'
            """
            return aind_session.utils.codeocean_utils.get_output_text(self)

        @property
        def sorted_probes(self) -> tuple[str, ...]:
            """Names of probes that reached the final stage of the sorting pipeline.


            - checks for probe dirs in the asset's data dir
            - checks a specific dir that indicates all processing completed:
                - `sorting_precurated` was original dir name, then changed to `curated`
            - probe folders named `experiment1_Record Node
            104#Neuropix-PXI-100.ProbeF-AP_recording1` - from which `ProbeF` would
            be extracted

            Examples
            --------
            >>> asset = aind_session.ecephys.get_sorted_data_asset_model('1e11bdf5-b452-4fd9-bbb1-48383a9b0842')
            >>> asset.sorted_probes
            ('ProbeA', 'ProbeB', 'ProbeC', 'ProbeD', 'ProbeE', 'ProbeF')
            """
            return EcephysExtension.get_sorted_probe_names(self.id)

        @property
        def sorter_name(self) -> str:
            """Name of the sorter used to create the sorted data asset (as specified
            by SpikeInterface).

            Examples
            --------
            >>> asset = aind_session.ecephys.get_sorted_data_asset_model('1e11bdf5-b452-4fd9-bbb1-48383a9b0842')
            >>> asset.sorter_name
            'kilosort2_5'
            """
            return EcephysExtension.get_sorter_name(self.id)

        @property
        def is_sorting_error(self) -> bool:
            """The sorting pipeline failed for one or more probes, determined by the
            files available in the asset's data dir and the presence of certain keywords
            in the `output` file.

            Examples
            --------
            >>> asset = aind_session.ecephys.get_sorted_data_asset_model('1e11bdf5-b452-4fd9-bbb1-48383a9b0842')
            >>> asset.is_sorting_error
            False
            """
            return aind_session.utils.codeocean_utils.is_output_error(self.output)

        @property
        def is_sorting_analyzer(self) -> bool:
            """The sorting pipeline used the `SortingAnalyzer` introduced in
            `SpikeInterface==0.101.1`. Results are organized in `.zarr` format.
            """
            return EcephysExtension.is_sorting_analyzer_asset(self.id)

    @staticmethod
    def get_sorted_data_asset_model(
        asset_id: str | codeocean.data_asset.DataAsset,
    ) -> SortedDataAsset:
        """Get an instance of `codeocean.data_asset.DataAsset` for the given asset
        ID, with additional property getters related to output from the
        spike-sorting pipeline.

        Examples
        --------
        >>> asset = aind_session.ecephys.get_sorted_data_asset_model('1e11bdf5-b452-4fd9-bbb1-48383a9b0842')
        >>> asset.id
        '1e11bdf5-b452-4fd9-bbb1-48383a9b0842'
        """
        return EcephysExtension.SortedDataAsset.from_dict(
            aind_session.utils.codeocean_utils.get_data_asset_model(asset_id).to_dict()
        )

    @staticmethod
    @functools.cache
    def is_sorted_data_asset(asset_id: str) -> bool:
        """Check if the asset is a sorted data asset.

        - assumes sorted asset to be named `<session-id>_sorted<unknown-suffix>`
        - does not assume platform to be `ecephys`

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.ecephys.is_sorted_data_asset('173e2fdc-0ca3-4a4e-9886-b74207a91a9a')
        True
        >>> session.ecephys.is_sorted_data_asset('83636983-f80d-42d6-a075-09b60c6abd5e')
        False
        """
        asset = aind_session.utils.codeocean_utils.get_data_asset_model(asset_id)
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

    @staticmethod
    @functools.cache
    def is_sorting_analyzer_asset(
        asset_id: str,
    ) -> bool:
        """The sorting pipeline used the `SortingAnalyzer` introduced in
        `SpikeInterface==0.101.1`.

        - checks if results are organized in `.zarr` format
        #TODO use spikeinterface version instead

        Examples
        --------

        >>> aind_session.ecephys.is_sorting_analyzer_asset('616375f1-836b-4187-823f-3457f07b7223')
        True
        >>> aind_session.ecephys.is_sorting_analyzer_asset('1e11bdf5-b452-4fd9-bbb1-48383a9b0842')
        False
        """
        asset = EcephysExtension.get_sorted_data_asset_model(asset_id)
        if next(asset.path.glob("*/*.zarr"), None):
            return True
        return False

    @property
    def sorter(self) -> _SorterNamespace:
        """Namespace for accessing sorting pipeline output for different sorter
        names.

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> session.ecephys.sorter.kilosort2_5
        SorterExtension(Session('ecephys_676909_2023-12-13_13-43-40'))
        >>> session.ecephys.sorter.kilosort4
        SorterExtension(Session('ecephys_676909_2023-12-13_13-43-40'))
        """
        return EcephysExtension._SorterNamespace(base=self)

    class _SorterNamespace:
        """Namespace for accessing sorting pipeline output for different
        sorter names.

        - new sorter names can be accessed without modification: getattr creates
          namespaces dynamically
        - `sorter_names` property returns a list of all sorter names found in the
          session's sorted data assets
        """

        _base: EcephysExtension

        # known sorter names can be added here to aid static typing/autocomplete:
        kilosort2_5: EcephysExtension.SorterExtension
        kilosort4: EcephysExtension.SorterExtension
        spykingcircus2: EcephysExtension.SorterExtension

        def __init__(self, base: EcephysExtension):
            self._base = base

        def __getattr__(self, sorter_name: str) -> EcephysExtension.SorterExtension:
            return EcephysExtension.SorterExtension(
                ecephys=self._base, sorter_name=sorter_name
            )

        @property
        def names(self) -> tuple[str, ...]:
            """Names of spike-sorters used across all of the session's sorted data
            assets.

            - names are determined by SpikeInterface and stored in `sorter_name`
                - e.g. 'kilosort2_5', 'kilosort4'

            Examples
            --------
            >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
            >>> session.ecephys.sorter.names   # doctest: +SKIP
            ('kilosort2_5', 'kilosort4')
            """
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return tuple(
                    sorted(
                        set(
                            executor.map(
                                EcephysExtension.get_sorter_name,
                                (asset.id for asset in self._base.sorted_data_assets),
                            )
                        )
                    )
                )

    class SorterExtension(aind_session.extension.ExtensionBaseClass):
        """Extension for different spike-sorters used by the sorting pipeline
        (identified by SpikeInterface `sorter_name`), providing access to data
        assets created by a specific sorter"""

        def __init__(self, ecephys: EcephysExtension, sorter_name: str) -> None:
            super().__init__(base=ecephys._base)
            self._ecephys = ecephys
            self._sorter_name = sorter_name

        @property
        def sorted_data_assets(self) -> tuple[EcephysExtension.SortedDataAsset, ...]:
            """All data assets produced using the given SpikeInterface `sorter_name`
            associated with the session (may be empty).

            Examples
            --------
            >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
            >>> session.ecephys.sorter.kilosort2_5.sorted_data_assets[0].id
            '1e11bdf5-b452-4fd9-bbb1-48383a9b0842'
            >>> session.ecephys.sorter.kilosort2_5.sorted_data_assets[0].name
            'ecephys_676909_2023-12-13_13-43-40_sorted_2023-12-17_03-16-51'
            >>> session.ecephys.sorter.kilosort2_5.sorted_data_assets[0].created
            1702783011

            Empty if no sorted data assets are found:
            >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-39')
            >>> session.ecephys.sorter.kilosort2_5.sorted_data_assets
            ()
            """
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_asset = {
                    executor.submit(EcephysExtension.get_sorter_name, asset.id): asset
                    for asset in self._ecephys.sorted_data_assets
                }
            assets = []
            for future, asset in future_to_asset.items():
                try:
                    sorter_name = future.result()
                except (
                    ValueError
                ):  # asset missing required information (e.g. sorting failed)
                    continue
                if sorter_name == self._sorter_name:
                    assets.append(asset)
            logger.debug(
                f"Found {len(assets)} {self._sorter_name} sorted data asset{'' if len(assets) == 1 else 's'} for {self._base.id}"
            )
            return tuple(assets)

    @staticmethod
    def get_sorted_probe_names(
        sorted_data_asset_id_or_model: str | codeocean.data_asset.DataAsset,
    ) -> tuple[str, ...]:
        """Names of probes that reached the final stage of the sorting pipeline.

        - checks for probe dirs in the asset's data dir
        - checks a specific dir that indicates all processing completed:
            - `sorting_precurated` was original dir name, then changed to `curated`
        - probe folders named `experiment1_Record Node
          104#Neuropix-PXI-100.ProbeF-AP_recording1` - from which `ProbeF` would
          be extracted

        Examples
        --------
        >>> aind_session.ecephys.get_sorted_probe_names('1e11bdf5-b452-4fd9-bbb1-48383a9b0842')
        ('ProbeA', 'ProbeB', 'ProbeC', 'ProbeD', 'ProbeE', 'ProbeF')
        """
        asset_id = aind_session.utils.codeocean_utils.get_normalized_uuid(
            sorted_data_asset_id_or_model
        )
        sorted_data_dir = aind_session.utils.get_data_asset_source_dir(
            asset_id=asset_id
        )
        candidate_parent_dirs = (
            sorted_data_dir / "curated",
            sorted_data_dir / "sorting_precurated",
        )
        for parent_dir in candidate_parent_dirs:
            if parent_dir.exists():
                break
        else:
            logger.info(
                f"No 'curated' or 'sorting_precurated' dir found in {sorted_data_dir.as_posix()}: assuming no probes completed processing"
            )
            return ()
        probes = set()
        for path in parent_dir.iterdir():
            # e.g. experiment1_Record Node 104#Neuropix-PXI-100.ProbeF-AP_recording1
            probe = (
                path.name.split(".")[1]
                .split("_recording")[0]
                .removesuffix("-AP")
                .removesuffix("-LFP")
            )
            probes.add(probe)
        logger.debug(f"Found {len(probes)} probes in {parent_dir.as_posix()}: {probes}")
        return tuple(sorted(probes))

    def run_sorting(
        self,
        pipeline_type: Literal[
            "ecephys_ks25",
            "ecephys_ks25_v0.1.0",
            "ecephys_opto_ks25",
            "ecephys_ks4",
            "ecephys_sc2",
        ] = "ecephys_ks25",
        trigger_capsule_id: str = "eb5a26e4-a391-4d79-9da5-1ab65b71253f",
        override_parameters: list[str] | None = None,
        skip_already_sorting: bool = True,
    ) -> codeocean.computation.Computation | None:
        """Run the sorting trigger capsule with the session's raw data asset
        (assumed to be only one). Launches the sorting pipeline then creates a new
        sorted data asset.

        - **note: the trigger capsule needs user secrets attached in order to run**
        - defaults to this capsule:
            https://codeocean.allenneuraldynamics.org/capsule/6726080/tree
        - the capsule uses positional arguments, so passing extra parameters is
          currently awkward: will update to pass named parameter kwargs in the
          future
            - if needed, you can override the parameters used with a custom list
        - if `skip_already_sorting` is `True`, a new pipeline run will not be
          triggered if the session's raw data asset is already being sorted
          (and this function returns None)

        Examples
        --------
        >>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
        >>> computation = session.ecephys.run_sorting()       # doctest: +SKIP

        Supply list of positional arguments (pipeline type and data asset ID are
        required)
        >>> override_parameters = ['ecephys_opto', session.raw_data_asset.id]
        >>> session.ecephys.run_sorting(override_parameters) # doctest: +SKIP
        """
        if override_parameters:
            if len(override_parameters) < 2:
                raise ValueError(
                    "At least two parameters are required: data asset ID is the second parameter. See https://codeocean.allenneuraldynamics.org/capsule/6726080/tree"
                )
            logger.debug("Using custom parameters to trigger sorting pipeline")
            parameters = override_parameters
            asset = aind_session.utils.codeocean_utils.get_data_asset_model(
                parameters[1]
            )
        else:
            asset = self._base.raw_data_asset
            parameters = [pipeline_type, asset.id]
        if skip_already_sorting:
            current_computations = (
                aind_session.utils.codeocean_utils.search_computations(
                    capsule_or_pipeline_id=self.DEFAULT_SORTING_PIPELINE_ID,
                    attached_data_asset_id=asset.id,
                    in_progress=True,
                    ttl_hash=aind_session.utils.get_ttl_hash(
                        1
                    ),  # 1 sec, we want a current check
                )
            )
            if current_computations:
                logger.warning(
                    f"Sorting is already running for {asset.id}: {[c.name for c in current_computations]}. Use `skip_already_sorting=False` to force a new pipeline run"
                )
                return None
        logger.debug(f"Triggering sorting pipeline with {parameters=}")
        computation = aind_session.utils.codeocean_utils.get_codeocean_client().computations.run_capsule(
            codeocean.computation.RunParams(
                capsule_id=trigger_capsule_id,
                parameters=parameters,
            )
        )
        logger.info(
            f"Triggered sorting pipeline for {asset.id} {asset.name}: monitor {computation.name!r} at https://codeocean.allenneuraldynamics.org/capsule/6726080/tree"
        )
        return computation

    @property
    def current_sorting_pipeline_computations(
        self,
    ) -> tuple[codeocean.computation.Computation, ...]:
        """
        All sorting pipeline computations that have the session's raw data asset
        attached and are still in progress.

        - "in progress" defined as `computation.end_status is None`
        - sorted by ascending creation time
        - checks https://codeocean.allenneuraldynamics.org/capsule/8510735/tree
        - result cached for 1 minute

        Examples
        --------
        >>> session = aind_session.Session('ecephys_733887_2024-08-16_12-16-49')
        >>> computations = session.ecephys.current_sorting_pipeline_computations
        >>> [c.name for c in computations]   # doctest: +SKIP
        ['Run With Parameters 4689084']
        """
        return EcephysExtension.get_current_sorting_pipeline_computations(
            pipeline_id=self.DEFAULT_SORTING_PIPELINE_ID,
            raw_data_asset_id_or_model=self._base.raw_data_asset.id,
        )

    @staticmethod
    def get_current_sorting_pipeline_computations(
        pipeline_id: str = "1f8f159a-7670-47a9-baf1-078905fc9c2e",
        raw_data_asset_id_or_model: str | codeocean.data_asset.DataAsset | None = None,
    ) -> tuple[codeocean.computation.Computation, ...]:
        """
        All sorting pipeline computations that are still in progress.

        - additionally filtered for computations using the given raw data asset ID
        - "in progress" defined as `computation.end_status is None`
        - sorted by ascending creation time
        - result cached for 1 minute
        - checks https://codeocean.allenneuraldynamics.org/capsule/8510735/tree by default
            - can be overridden with a different pipeline ID by

        Examples
        --------
        >>> computations = aind_session.ecephys.current_sorting_pipeline_computations
        >>> [c.name for c in computations]   # doctest: +SKIP
        ['Run With Parameters 4689084']
        """
        return aind_session.utils.codeocean_utils.search_computations(
            capsule_or_pipeline_id=pipeline_id,
            attached_data_asset_id=aind_session.utils.codeocean_utils.get_normalized_uuid(
                raw_data_asset_id_or_model
            ),
            in_progress=True,
            ttl_hash=aind_session.utils.get_ttl_hash(1 * 60),
        )

    @staticmethod
    @functools.cache
    def get_sorter_name(sorted_data_asset_id: str) -> str:
        """
        Get the version of the Kilosort pipeline used to create the sorted data asset.

        Tries to find `sorter_name` in the following json files, in order, for any
        probe:
        - `processing.json` (in root of asset)
        - `si_folder.json` (in `spikesorted` dir)
        - `sorting.json` (in `postprocessed` dir)
        - `params.json` (in root of asset, for older assets)

        Raises `ValueError` if none of the json files exist, or if none contain the
        `sorter_name` key, either of which indicates that the asset data is
        incomplete due to the sorting pipeline failing for all probes.

        Examples
        --------

        - processing.json['processing_pipeline']['data_processes'][index]['parameters']['sorter_name']:
        >>> aind_session.ecephys.get_sorter_name('d50a3447-7f12-4da7-83c5-845744c4d4f9')
        'kilosort2_5'

        - processing.json['processing_pipeline']['data_processes'][index]['parameters']['sorter_name']:
        >>> aind_session.ecephys.get_sorter_name('01d9d159-96f0-43f1-9d14-29b5c2521d94')
        'kilosort4'

        - processing.json['data_processes'][index]['parameters']['sorter_name']:
        >>> aind_session.ecephys.get_sorter_name('205fc2d0-5f00-468f-a82d-47c94afcd40c')
        'kilosort2_5'

        - spikesorted/si_folder.json['annotations']['__sorting_info__']['params']['sorter_name']:
        >>> aind_session.ecephys.get_sorter_name('bd0ad804-4a33-4613-9d6c-6281e442bade')
        'kilosort2_5'

        - params.json['spikesorting']['sorter_name']
        >>> aind_session.ecephys.get_sorter_name('0eca2d35-5c8c-48bb-a921-e48cf3d871de')
        'kilosort2_5'

        - no sorter_name available:
        >>> aind_session.ecephys.get_sorter_name('b4a7757c-6826-49eb-b3dd-d6cd871c5e7c')
        Traceback (most recent call last):
        ...
        ValueError: Sorting data are incomplete for
        data_asset_id='b4a7757c-6826-49eb-b3dd-d6cd871c5e7c' (pipeline likely failed) - cannot get sorter name
        """
        source_dir = aind_session.utils.codeocean_utils.get_data_asset_source_dir(
            aind_session.utils.codeocean_utils.get_normalized_uuid(sorted_data_asset_id)
        )

        def _get_sorter_name_from_processing_json(source_dir: upath.UPath) -> str:
            processing_path = source_dir / "processing.json"
            if not processing_path.exists():
                raise FileNotFoundError(f"No 'processing.json' found in {source_dir}")
            processing_text = processing_path.read_text()
            if '"sorter_name":' not in processing_text:
                raise KeyError(
                    f"No 'sorter_name' value found in processing.json for {sorted_data_asset_id=}"
                )
            processing: dict = json.loads(processing_text)
            if "processing_pipeline" in processing:
                data_processes = processing["processing_pipeline"]["data_processes"]
            else:
                assert (
                    "data_processes" in processing
                ), f"Fix method of getting sorter name: 'data_processes' not in processing.json for {sorted_data_asset_id=}"
                data_processes = processing["data_processes"]
            for p in data_processes:
                if isinstance(p, list):
                    sorting: dict = next(
                        (d for d in p if d.get("name") == "Spike sorting"),
                        {},
                    )
                    break
                else:
                    if p.get("name") == "Spike sorting":
                        sorting = p
                        break
            else:
                raise AssertionError(
                    f"Fix method of getting sorter name: 'sorter_name' is in processing.json, but not in expected location for {sorted_data_asset_id=}"
                )
            assert (
                "parameters" in sorting
            ), f"Fix method of getting sorter name: 'parameters' not in 'Spike sorting' data process in processing.json for {sorted_data_asset_id=}"
            if "sorter_name" not in sorting["parameters"]:
                raise KeyError(
                    "No 'sorter_name' key found in sorting parameters in processing.json"
                )
            sorter_name: str = sorting["parameters"]["sorter_name"]
            logger.debug(f"Found sorter_name key in processing.json: {sorter_name}")
            return sorter_name

        def _get_sorter_name_from_sorted_folders(source_dir: upath.UPath) -> str:
            json_paths = []
            for json_path in itertools.chain(
                (source_dir / "spikesorted").rglob("si_folder.json"),
                (source_dir / "postprocessed").rglob("sorting.json"),
            ):
                json_paths.append(json_path)
                info = json_path.read_text()
                if '"sorter_name":' in info:
                    sorter_name = json.loads(info)["annotations"]["__sorting_info__"][
                        "params"
                    ]["sorter_name"]
                    logger.debug(
                        f"Found sorter_name key in {json_path.name}: {sorter_name}"
                    )
                    return sorter_name
            else:
                if not json_paths:
                    raise FileNotFoundError(
                        f"No 'processing.json', 'si_folder.json', or 'sorting.json' files found - asset {sorted_data_asset_id} likely contains incomplete data"
                    )
                else:
                    raise KeyError(
                        f"Fix method of getting sorter name: 'sorter_name' not a value in {set(p.name for p in json_paths)} for {sorted_data_asset_id=}"
                    )

        def _get_sorter_name_from_params_json(source_dir: upath.UPath) -> str:
            params_path = source_dir / "params.json"
            if not params_path.exists():
                raise FileNotFoundError(f"No 'params.json' found in {source_dir}")
            params_text = params_path.read_text()
            if '"sorter_name":' not in params_text:
                raise KeyError(f"No 'sorter_name' key found in {params_path.name}")
            params: dict = json.loads(params_text)
            assert (
                params
            ), f"Fix method of getting sorter name: {params=} for {sorted_data_asset_id=}"
            assert (
                "spikesorting" in params
            ), f"Fix method of getting sorter name: 'spikesorting' not in {params_path.name} for {sorted_data_asset_id=}"
            assert (
                "sorter_name" in params["spikesorting"]
            ), f"Fix method of getting sorter name: 'sorter_name' not in 'spikesorting' in {params_path.name} for {sorted_data_asset_id=}"
            sorter_name = params["spikesorting"]["sorter_name"]
            logger.debug(f"Found sorter_name key in params.json: {sorter_name}")
            return sorter_name

        with contextlib.suppress(FileNotFoundError, KeyError):
            return _get_sorter_name_from_processing_json(source_dir)
        with contextlib.suppress(FileNotFoundError, KeyError):
            return _get_sorter_name_from_sorted_folders(source_dir)
        with contextlib.suppress(FileNotFoundError, KeyError):
            return _get_sorter_name_from_params_json(source_dir)
        raise ValueError(
            f"Cannot get sorter name: sorting data are incomplete for {sorted_data_asset_id=!r} (pipeline likely failed)"
        )


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
