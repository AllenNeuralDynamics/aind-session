from __future__ import annotations

import concurrent.futures
import contextlib
import csv
import dataclasses
import datetime
import json
import logging
import time
from collections.abc import Iterable, Mapping
from typing import Any

import codeocean.computation
import codeocean.data_asset
import npc_io
import npc_session
import upath
from typing_extensions import Self

import aind_session
import aind_session.extensions
import aind_session.utils
import aind_session.utils.codeocean_utils
import aind_session.utils.misc_utils
import aind_session.utils.s3_utils
from aind_session.extensions.ecephys import EcephysExtension

logger = logging.getLogger(__name__)

SCRATCH_STORAGE_DIR = upath.UPath("s3://aind-scratch-data/aind-session")


class NeuroglancerState:

    content: Mapping[str, Any]

    def __init__(
        self, path_or_dict: npc_io.PathLike | Mapping[str, Any] | Self
    ) -> None:
        """Interpret a Neuroglancer state json file and extract relevant information for annotation.

        Examples
        --------
        Pass a dict with the json contents or a path to a json file:
        >>> state = NeuroglancerState("tests/resources/example_neuroglancer_state.json")
        >>> state.session
        Session('SmartSPIM_717381_2024-07-03_10-49-01')
        >>> state.session.subject
        Subject('717381')
        >>> state.annotation_names
        ('268', '269', '270', '265', '263', '262', 'targets')
        >>> state.image_sources[0]
        'zarr://s3://aind-msma-morphology-data/test_data/SmartSPIM/SmartSPIM_717381_2024-07-03_10-49-01_stitched_2024-08-16_23-15-47/image_tile_fusing/OMEZarr/Ex_561_Em_593.ome.zarr/'
        """
        self._session = None
        if isinstance(path_or_dict, str):
            with contextlib.suppress(Exception):
                path_or_dict = json.loads(path_or_dict)
        if isinstance(path_or_dict, NeuroglancerState):
            self._session = path_or_dict._session
            self.content = path_or_dict.content
        elif isinstance(path_or_dict, Mapping):
            self.content = path_or_dict  # we won't mutate, so no need to copy
        else:
            self.content = json.loads(npc_io.from_pathlike(path_or_dict).read_text())

    def __repr__(self) -> str:
        """
        Examples
        --------
        >>> NeuroglancerState("tests/resources/example_neuroglancer_state.json")
        NeuroglancerState(SmartSPIM_717381_2024-07-03_10-49-01)
        """
        try:
            return f"{self.__class__.__name__}({self.session.id})"
        except ValueError:
            return f"{self.__class__.__name__}({list(self.content.keys())})"

    @property
    def image_sources(self) -> tuple[str, ...]:
        """Image source urls in order of appearance in the Neuroglancer state json.

        Examples
        --------
        >>> NeuroglancerState("tests/resources/example_neuroglancer_state.json").image_sources[0]
        'zarr://s3://aind-msma-morphology-data/test_data/SmartSPIM/SmartSPIM_717381_2024-07-03_10-49-01_stitched_2024-08-16_23-15-47/image_tile_fusing/OMEZarr/Ex_561_Em_593.ome.zarr/'
        """
        with contextlib.suppress(KeyError):
            return tuple(
                (
                    layer["source"]
                    if isinstance(layer["source"], str)
                    else layer["source"]["url"]
                )
                for layer in self.content["layers"]
                if layer["type"] == "image"
            )
        return ()

    @property
    def session(self) -> aind_session.Session:
        """The session associated with the Neuroglancer state json, extracted from the image source urls.

        Examples
        --------
        >>> NeuroglancerState("tests/resources/example_neuroglancer_state.json").session
        Session('SmartSPIM_717381_2024-07-03_10-49-01')
        """
        session_ids = set()
        if self._session is None:
            for source in self.image_sources:
                try:
                    session_ids.add(npc_session.AINDSessionRecord(source))
                except ValueError:
                    continue
            if not session_ids:
                raise ValueError(
                    "No session ID could be extracted from Neuroglancer state json (expected to extract SmartSPIM session ID from image source)"
                )
            if len(session_ids) > 1:
                raise NotImplementedError(
                    f"Cannot currently handle Neuroglancer state json from multiple image sources: {session_ids}"
                )
            self._session = aind_session.Session(session_ids.pop())  # type: ignore[assignment]
        assert self._session is not None
        return self._session

    @property
    def annotation_names(self) -> tuple[str, ...]:
        """The names of the annotation layers in the Neuroglancer state json.

        Examples
        --------
        >>> NeuroglancerState("tests/resources/example_neuroglancer_state.json").annotation_names
        ('268', '269', '270', '265', '263', '262', 'targets')
        """
        names = []
        with contextlib.suppress(KeyError):
            for layer in self.content["layers"]:
                if layer["type"] != "annotation":
                    continue
                names.append(layer["name"])
        return tuple(names)

    @staticmethod
    def get_new_file_name(session_id: str) -> str:
        """Generate a new file name for a Neuroglancer state json file based on a session ID and current time.

        Examples
        --------
        >>> NeuroglancerState.get_new_file_name('SmartSPIM_717381_2024-07-03_10-49-01') # doctest: +SKIP
        'SmartSPIM_717381_2024-07-03_10-49-01_neuroglancer-state_2024-08-16_23-15-47.json'
        """
        return f"{session_id}_neuroglancer-state_{datetime.datetime.now():%Y-%m-%d_%H-%M-%S}.json"

    def write(
        self, path: npc_io.PathLike | None = None, timeout_sec: float = 10
    ) -> upath.UPath:
        """Write the Neuroglancer state json to file and return the path.

        If no path is provided, a new file name will be generated based on the session ID and current time,
        and saved in a temporary scratch directory in S3 so that it can be added to an internal data asset.

        Examples
        --------
        >>> state = NeuroglancerState("tests/resources/example_neuroglancer_state.json")
        >>> path = state.write()
        >>> path.name                                                                   # doctest: +SKIP
        'SmartSPIM_717381_2024-07-03_10-49-01_neuroglancer-state_2024-08-16_23-15-47.json'
        """
        if path is not None:
            path = npc_io.from_pathlike(path)
        else:
            name = NeuroglancerState.get_new_file_name(self.session.id)
            path = (
                self.session.subject.neuroglancer.state_json_dir
                / name.rsplit(".")[
                    0
                ]  # subfolder ensures 1 file per folder, for creating dedicated data assets
                / name
            )
        logger.debug(f"Writing Neuroglancer annotation file to {path.as_posix()}")
        path.write_text(json.dumps(self.content, indent=2))
        t0 = time.time()
        while time.time() - t0 < timeout_sec:
            if path.exists():
                break
            time.sleep(1)
        else:
            raise TimeoutError(
                f"Failed to write Neuroglancer annotation file to {path.as_posix()}: "
                f"file not found after {timeout_sec} seconds"
            )
        logger.debug(f"Neuroglancer annotation file written to {path.as_posix()}")
        return path

    def create_data_asset(self) -> codeocean.data_asset.DataAsset:
        """Create a CodeOcean data asset from the Neuroglancer state json file.

        - name and tags are created automatically based on the SmartSPIM session ID
        - waits until the asset is ready before returning

        Examples
        --------
        >>> state = NeuroglancerState("tests/resources/example_neuroglancer_state.json")
        >>> asset = state.create_data_asset()
        >>> asset.name                                              # doctest: +SKIP
        'SmartSPIM_717381_2024-07-03_10-49-01_neuroglancer-state_2024-08-16_23-15-47'
        >>> asset.tags
        ['neuroglancer', 'ecephys', 'annotation', '717381']
        >>> asset.files
        1
        >>> next(aind_session.utils.codeocean_utils.get_data_asset_source_dir(asset.id).glob("*")).name  # doctest: +SKIP
        'SmartSPIM_717381_2024-07-03_10-49-01_neuroglancer-state_2024-08-16_23-15-47.json'
        """
        path = self.write()
        bucket, prefix = aind_session.utils.s3_utils.get_bucket_and_prefix(path)
        asset_params = codeocean.data_asset.DataAssetParams(
            name=path.stem,
            mount=path.stem,
            tags=["neuroglancer", "ecephys", "annotation", self.session.subject.id],
            source=codeocean.data_asset.Source(
                aws=codeocean.data_asset.AWSS3Source(
                    bucket=bucket,
                    prefix=prefix,
                    keep_on_external_storage=False,
                    public=False,
                )
            ),
        )
        logger.debug(f"Creating asset {asset_params.name}")
        asset = aind_session.utils.codeocean_utils.get_codeocean_client().data_assets.create_data_asset(
            asset_params
        )
        logger.debug(f"Waiting for new asset {asset.name} to be ready")
        updated_asset = aind_session.utils.codeocean_utils.wait_until_ready(
            data_asset=asset,
            timeout=60,
        )
        logger.debug(f"Asset {updated_asset.name} is ready")
        return updated_asset


@aind_session.register_namespace(name="ibl_data_converter", cls=aind_session.Subject)
class IBLDataConverterExtension(aind_session.ExtensionBaseClass):
    """

    Examples
    --------
    >>> subject = aind_session.Subject(717381)
    >>> subject.ibl_data_converter.ecephys_sessions[0].id
    'ecephys_717381_2024-04-09_11-14-13'
    """

    _base: aind_session.Subject

    def __init__(self, base: aind_session.Subject) -> None:
        self._base = base
        self.storage_dir = SCRATCH_STORAGE_DIR
        self.use_data_assets_with_errors = False
        self.use_data_assets_with_sorting_analyzer = True

    DATA_CONVERTER_CAPSULE_ID = "372263e6-d942-4241-ba71-763a1062f2b7"  #! test capsule
    # TODO switch to actual capsule: "d4ba01c4-5665-4163-95d2-e481f4465b86"
    """https://codeocean.allenneuraldynamics.org/capsule/1376129/tree"""

    @property
    def ecephys_sessions(self) -> tuple[aind_session.Session, ...]:
        """All ecephys sessions associated with the subject, sorted by ascending session date.

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> subject.ibl_data_converter.ecephys_sessions[0].id
        'ecephys_717381_2024-04-09_11-14-13'
        """
        return tuple(
            session for session in self._base.sessions if session.platform == "ecephys"
        )

    @property
    def ecephys_data_assets(self) -> tuple[codeocean.data_asset.DataAsset, ...]:
        """All ecephys raw data assets associated with the subject, 0 or 1 per ecephys session,
        sorted in order of session date.

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> subject.ibl_data_converter.ecephys_data_assets[0].name
        'ecephys_717381_2024-04-09_11-14-13'
        """
        assets = []
        for session in self.ecephys_sessions:
            if not (asset := session.raw_data_asset):
                logger.warning(
                    f"{session.id} raw data has not been uploaded: cannot use for annotation"
                )
                continue
            assets.append(asset)
            logger.debug(f"Using {asset.name} for annotation")
        return tuple(assets)

    @property
    def sorted_data_assets(
        self,
    ) -> tuple[EcephysExtension.SortedDataAsset, ...]:
        """All ecephys sorted data assets associated with the subject, 0 or more per ecephys session,
        sorted by session date, then asset creation date.

        - can be configured to exclude assets with errors or from the sorting analyzer by setting properties
          `use_data_assets_with_errors` and `use_data_assets_with_sorting_analyzer` on the namespace instance

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> subject.ibl_data_converter.sorted_data_assets       # doctest: +SKIP
        ()
        >>> subject.ibl_data_converter.use_data_assets_with_errors = True
        >>> subject.ibl_data_converter.sorted_data_assets[0].name
        'ecephys_717381_2024-04-09_11-14-13_sorted_2024-04-10_22-15-25'
        """

        def get_session_assets(
            session: aind_session.Session,
        ) -> tuple[EcephysExtension.SortedDataAsset, ...]:
            return tuple(
                a
                for a in session.ecephys.sorted_data_assets
                if (self.use_data_assets_with_errors or not a.is_sorting_error)
                and (
                    self.use_data_assets_with_sorting_analyzer
                    or not a.is_sorting_analyzer
                )
            )

        session_id_to_assets: dict[
            str, tuple[EcephysExtension.SortedDataAsset, ...]
        ] = {}
        future_to_session: dict[concurrent.futures.Future, aind_session.Session] = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for session in self._base.sessions:
                if session.platform != "ecephys":
                    continue
                future = executor.submit(get_session_assets, session)
                future_to_session[future] = session
            for future in concurrent.futures.as_completed(future_to_session):
                session = future_to_session[future]
                assets_this_session = future.result()
                if not assets_this_session:
                    logger.warning(
                        f"{session.id} has no sorted data in a non-errored state: cannot use for annotation"
                    )
                    continue
                session_id_to_assets[session.id] = assets_this_session
        all_assets: list[EcephysExtension.SortedDataAsset] = []
        for session in self._base.sessions:
            if session.id in session_id_to_assets:
                all_assets.extend(session_id_to_assets[session.id])
        return tuple(all_assets)

    @property
    def smartspim_sessions(self) -> tuple[aind_session.Session, ...]:
        """All sessions associated with the subject with platform=='SmartSPIM', sorted by ascending session date.

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> subject.ibl_data_converter.smartspim_sessions[0].id
        'SmartSPIM_717381_2024-05-20_15-19-15'
        """
        return tuple(
            session
            for session in self._base.sessions
            if session.platform == "SmartSPIM"
        )

    @property
    def smartspim_data_assets(self) -> tuple[codeocean.data_asset.DataAsset, ...]:
        """All SmartSPIM raw data assets associated with the subject, 0 or 1 per SmartSPIM session (latest only),
        sorted in order of session date.

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> subject.ibl_data_converter.smartspim_data_assets[0].name
        'SmartSPIM_717381_2024-05-20_15-19-15'
        """
        assets = []
        for session in self.smartspim_sessions:
            if not hasattr(session, "raw_data_asset"):
                logger.warning(f"{session.id} has no raw data asset")
                continue
            assets.append(session.raw_data_asset)
            logger.debug(f"Found asset {session.raw_data_asset.name!r}")
        if not assets:
            logger.warning(f"No SmartSPIM data asset found for {self._base.id}")
        if len(assets) > 1:
            logger.warning(
                f"Multiple SmartSPIM raw data assets found for {self._base.id}"
            )
        return tuple(assets)

    @dataclasses.dataclass
    class ManifestRecord:
        """Dataclass for a single row in the IBL data converter manifest csv."""

        mouseid: str
        sorted_recording: str
        probe_file: str
        probe_name: str
        probe_id: str | None = (
            None  # can't be found automatically, must be provided by user
        )
        surface_finding: int | None = None  # not currently used
        annotation_format: str = "json"

    def get_partial_manifest_records(
        self,
        neuroglancer_state_json_name: str | None = None,
        sorted_data_asset_names: Iterable[str] = (),
    ) -> list[dict[str, Any]]:
        """
        Create a the partially-completed rows for a manifest file (for the IBL data converter
        capsule) from Neuroglancer state json files, for a single subject.

        - each row is a dict of key-value pairs, with keys corresponding to the columns in the manifest csv
        - the 'probe_name' value will be an empty string: a user needs to update this manually to
          map the probe ID in Neuroglancer to the probe name used in Open Ephys

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> rows = subject.ibl_data_converter.get_partial_manifest_records()
        >>> rows[0]     # doctest: +SKIP
        {'mouseid': '717381', 'sorted_recording': 'ecephys_717381_2024-04-09_11-14-13_sorted_2024-04-10_22-15-25', 'probe_file': 'SmartSPIM_717381_2024-07-03_10-49-01_neuroglancer-state_2024-12-06_19-25-10', 'probe_name': '', 'probe_id': '268', 'surface_finding': None, 'annotation_format': 'json'}
        """
        ng: NeuroglancerExtension = self._base.neuroglancer
        if not neuroglancer_state_json_name:
            try:
                latest = ng.state_json_paths[-1]
            except IndexError:
                raise FileNotFoundError(
                    f"No Neuroglancer annotation json found for {self._base.id} in {ng.state_json_dir}"
                )
            logger.debug(
                f"Using most-recent Neuroglancer annotation file: {latest.as_posix()}"
            )
            neuroglancer_state_json_name = latest.stem
            neuroglancer_state = NeuroglancerState(latest)
        else:
            neuroglancer_state = NeuroglancerState(
                ng.state_json_dir
                / neuroglancer_state_json_name
                / f"{neuroglancer_state_json_name}.json"
            )

        if isinstance(sorted_data_asset_names, str):
            sorted_data_asset_names = (sorted_data_asset_names,)
        if not sorted_data_asset_names:
            sorted_data_asset_names = sorted(
                asset.name for asset in self.sorted_data_assets
            )

        records = []
        for annotation_name in neuroglancer_state.annotation_names:
            for sorted_data_asset_name in sorted_data_asset_names:
                row = IBLDataConverterExtension.ManifestRecord(
                    mouseid=self._base.id,
                    probe_name="",
                    probe_id=annotation_name,
                    sorted_recording=sorted_data_asset_name,
                    probe_file=neuroglancer_state_json_name,
                )
                records.append(row)
        return list(dataclasses.asdict(record) for record in records)

    @property
    def csv_manifest_path(self) -> upath.UPath:
        """Temporary S3 location for the annotation manifest csv file before being made into an internal data asset.

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> subject.ibl_data_converter.csv_manifest_path.as_posix()
        's3://aind-scratch-data/aind-session/manifests/717381/717381_data_converter_manifest.csv'
        """
        return (
            self.storage_dir
            / "manifests"
            / f"{self._base.id}"
            / f"{self._base.id}_data_converter_manifest.csv"
        )

    def create_manifest_asset(
        self,
        completed_records: Iterable[Mapping[str, Any]] | Iterable[ManifestRecord],
        asset_name: str | None = None,
        skip_existing: bool = True,
        timeout_sec: float = 10,
    ) -> codeocean.data_asset.DataAsset:
        """Create a CodeOcean data asset from one or more completed annotation manifest records (see
        `self.get_partial_manifest()` and `ManifestRecord`).

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> rows = [{'mouseid': 717381, 'sorted_recording': 'recording1', 'probe_file': 'file1', 'probe_name': 'probeA', 'probe_id': '100'}]
        >>> asset = subject.ibl_data_converter.create_manifest_asset(rows, skip_existing=False)
        >>> asset.name  # doctest: +SKIP
        '717381_data_converter_manifest'
        >>> next(aind_session.utils.codeocean_utils.get_data_asset_source_dir(asset.id).glob("*.csv")).read_text()
        'mouseid,sorted_recording,probe_file,probe_name,probe_id\\n717381,recording1,file1,probeA,100\\n'
        """
        if skip_existing and (existing := getattr(self, "manifest_data_asset", None)):
            logger.info(
                f"Manifest asset already exists for {self._base.id}. Use `self.create_manifest_asset(skip_existing=False)` to force creation"
            )
            return existing
        records: list[Mapping[str, Any]] = [
            (
                dataclasses.asdict(record)
                if isinstance(record, self.ManifestRecord)
                else record
            )
            for record in completed_records
        ]
        for row in records:
            if row["probe_name"] == "" or row["probe_name"] is None:  # int(0) accepted
                raise ValueError(
                    f"'probe_name' must be provided for each row in the manifest: {row}"
                )
        logger.debug(f"Writing annotation manifest to {self.csv_manifest_path}")
        with self.csv_manifest_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
        t0 = time.time()
        while time.time() - t0 < timeout_sec:
            if self.csv_manifest_path.exists():
                break
            time.sleep(1)
        else:
            raise TimeoutError(
                f"Failed to write annotation manifest to {self.csv_manifest_path}: "
                f"file not found after {timeout_sec} seconds"
            )
        bucket, prefix = aind_session.utils.s3_utils.get_bucket_and_prefix(
            self.csv_manifest_path
        )
        asset_params = codeocean.data_asset.DataAssetParams(
            name=asset_name or self.csv_manifest_path.stem,
            mount=asset_name or self.csv_manifest_path.stem,
            tags=["ibl", "annotation", "manifest", self._base.id],
            source=codeocean.data_asset.Source(
                aws=codeocean.data_asset.AWSS3Source(
                    bucket=bucket,
                    prefix=prefix,
                    keep_on_external_storage=False,
                    public=False,
                )
            ),
        )
        logger.debug(f"Creating asset {asset_params.name}")
        asset = aind_session.utils.codeocean_utils.get_codeocean_client().data_assets.create_data_asset(
            asset_params
        )
        logger.debug(f"Waiting for new asset {asset.name} to be ready")
        updated_asset = aind_session.utils.codeocean_utils.wait_until_ready(
            data_asset=asset,
            timeout=60,
        )
        logger.debug(f"Asset {updated_asset.name} is ready")
        return updated_asset

    @property
    def manifest_data_asset(self) -> codeocean.data_asset.DataAsset:
        """Most-recent data asset containing an annotation manifest csv file for the subject, if one exists.
        Otherwise raises an AttributeError.

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> asset = subject.ibl_data_converter.manifest_data_asset
        >>> asset.name  # doctest: +SKIP
        '717381_data_converter_manifest'
        """
        try:
            assets = aind_session.utils.codeocean_utils.get_data_assets(
                self.csv_manifest_path.stem,
                ttl_hash=aind_session.utils.misc_utils.get_ttl_hash(seconds=1),
            )
        except ValueError:
            assets = ()
        if not assets:
            raise AttributeError(
                f"No manifest asset has been created yet for {self._base.id}: run `self.create_manifest_asset()`"
            )
        if len(assets) > 1:
            logger.debug(
                f"Multiple manifest assets found for {self._base.id}: using most-recent"
            )
        return assets[-1]

    def run_data_converter_capsule(
        self,
        capsule_id: str = DATA_CONVERTER_CAPSULE_ID,
        additional_assets: Iterable[codeocean.data_asset.DataAsset] = (),
        parameters: list[str] | None = None,
        named_parameters: list[codeocean.computation.NamedRunParam] | None = None,
    ) -> codeocean.computation.Computation:
        """
        Run the IBL data converter capsule on CodeOcean with auto-discovered raw data assets, sorted
        assets, SmartSPIM data asset, and the manifest csv asset.

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> computation = subject.ibl_data_converter.run_data_converter_capsule()
        """
        run_params = codeocean.computation.RunParams(
            capsule_id=capsule_id,
            data_assets=[
                codeocean.computation.DataAssetsRunParam(id=asset.id, mount=asset.name)
                for asset in (
                    *self.ecephys_data_assets,
                    *self.sorted_data_assets,
                    self.smartspim_data_assets[-1],
                    self.manifest_data_asset,
                    *additional_assets,
                )
            ],
            parameters=parameters or [],
            named_parameters=named_parameters or [],
        )
        logger.debug(f"Running data converter capsule: {run_params.capsule_id}")
        return aind_session.utils.codeocean_utils.get_codeocean_client().computations.run_capsule(
            run_params
        )


@aind_session.register_namespace(name="neuroglancer", cls=aind_session.Subject)
class NeuroglancerExtension(aind_session.extension.ExtensionBaseClass):

    _base: aind_session.Subject

    state_json_dir: upath.UPath = SCRATCH_STORAGE_DIR / "neuroglancer_states"

    @property
    def state_json_paths(self) -> tuple[upath.UPath, ...]:
        """
        Paths to all Neuroglancer state .json files in temporary storage associated with the subject, sorted by file name.

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> paths = subject.neuroglancer.state_json_paths
        >>> paths[0].name  # doctest: +SKIP
        'SmartSPIM_717381_2024-07-03_10-49-01_neuroglancer-state_2024-08-16_23-15-47.json'
        """
        return tuple(
            sorted(
                self.state_json_dir.rglob(f"*_{self._base.id}_*.json"),
                key=lambda p: p.stem,
            )
        )

    @property
    def states(
        self,
    ) -> tuple[NeuroglancerState, ...]:
        """
        All Neuroglancer state objects associated with the subject, one per state json file, sorted by file name.

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> subject.neuroglancer.states[0]
        NeuroglancerState(SmartSPIM_717381_2024-07-03_10-49-01)
        """
        return tuple(NeuroglancerState(p) for p in self.state_json_paths)


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
