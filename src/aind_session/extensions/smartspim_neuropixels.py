from __future__ import annotations

import concurrent.futures
import contextlib
import csv
import dataclasses
import datetime
import json
import logging
import re
import time
import zoneinfo
from collections.abc import Iterable, Mapping
from typing import Any, Literal

import aind_codeocean_pipeline_monitor.models
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
    def image_data_assets(self) -> tuple[codeocean.data_asset.DataAsset, ...]:
        """Data assets with image source session ID in their name

        Examples
        --------
        >>> NeuroglancerState("tests/resources/example_neuroglancer_state.json").image_data_assets[0].name
        'SmartSPIM_717381_2024-07-03_10-49-01_stitched_2024-08-16_23-15-47'
        """
        assets: list[codeocean.data_asset.DataAsset] = []
        for source in self.image_sources:
            session_id = next(
                p for p in reversed(source.split("/")) if p.startswith("SmartSPIM_")
            )
            results = aind_session.utils.codeocean_utils.get_data_assets(
                name_startswith=session_id,
                ttl_hash=aind_session.utils.misc_utils.get_ttl_hash(seconds=1),
            )
            if results:
                assets.extend(results)
        return aind_session.utils.codeocean_utils.sort_by_created(assets)

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
        # name is coupled with NeuroglancerExtension.state_json_data_assets
        return f"{session_id}_neuroglancer-state_{datetime.datetime.now(tz=zoneinfo.ZoneInfo('US/Pacific')):%Y-%m-%d_%H-%M-%S}.json"

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

    def create_data_asset(
        self, path: npc_io.PathLike | None = None
    ) -> codeocean.data_asset.DataAsset:
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
        if path is None:
            path = self.write()
        else:
            path = npc_io.from_pathlike(path)
        bucket, prefix = aind_session.utils.s3_utils.get_bucket_and_prefix(path)
        asset_params = codeocean.data_asset.DataAssetParams(
            name=path.stem,
            mount=path.stem,
            tags=["neuroglancer", "ecephys", "annotation", self.session.subject.id],
            custom_metadata={
                "experiment type": "SmartSPIM",
                "subject id": str(self.session.subject_id),
            },
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
            check_files=True,
            timeout=120,
        )
        logger.debug(f"Asset {updated_asset.name} is ready")
        return updated_asset


@aind_session.register_namespace(name="ibl_data_converter", cls=aind_session.Subject)
class IBLDataConverterExtension(aind_session.ExtensionBaseClass):

    _base: aind_session.Subject

    def __init__(self, base: aind_session.Subject) -> None:
        self._base = base
        self.storage_dir = SCRATCH_STORAGE_DIR
        self.use_data_assets_with_errors = False
        self.use_data_assets_with_sorting_analyzer = True

    DATA_CONVERTER_CAPSULE_ID = "9fe42995-ffff-40ff-9c4c-c8206b8aacb5"
    """https://codeocean.allenneuraldynamics.org/capsule/8363069/tree"""

    PIPELINE_MONITOR_CAPUSLE_ID = "567b5b98-8d41-413b-9375-9ca610ca2fd3"
    """Pipeline monitor capsule for capturing data assets e.g. https://codeocean.allenneuraldynamics.org/capsule/5449547/tree"""

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
    def surface_recording_names(self) -> dict[str, str]:
        """A mapping of ecephys session names to corresponding surface recording names.

            - surface recordings are assumed to be the second raw ecephys data asset on a given day for a particular subject
            - not all ecpehys sessions have a surface recording (in which case they will not be in the mapping)

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> subject.ibl_data_converter.surface_recording_names
        {'ecephys_717381_2024-04-09_11-14-13': 'ecephys_717381_2024-04-09_11-44-16', 'ecephys_717381_2024-04-10_16-29-12': 'ecephys_717381_2024-04-10_16-51-20'}
        """
        date_to_session_names: dict[str, list[str]] = {}
        for asset in self.ecephys_data_assets:
            session = aind_session.Session(asset.name)
            date_to_session_names.setdefault(session.date, []).append(asset.name)
        first_to_second_recording = {}
        for session_names in date_to_session_names.values():
            if len(session_names) == 1:
                logger.debug(
                    f"Only one recording found ({session_names[0]}): no option for surface recording available"
                )
                continue
            session_names = sorted(session_names)
            first, second = session_names[0], session_names[1]
            if len(session_names) > 2:
                logger.warning(
                    f"{len(session_names)} ecephys data assets found when trying to find surface recording: using first and second only"
                )
            first_to_second_recording[first] = second
        return first_to_second_recording

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

    @staticmethod
    def get_stitched_data_assets(
        smartspim_session_id: str,
    ) -> tuple[codeocean.data_asset.DataAsset, ...]:
        """
        >>> stitched_assets = IBLDataConverterExtension.get_stitched_data_assets('SmartSPIM_717381_2024-05-20_15-19-15')
        >>> stitched_assets[0].name
        'SmartSPIM_717381_2024-05-20_15-19-15_stitched_2024-06-23_02-34-02'
        """
        return aind_session.utils.codeocean_utils.sort_by_created(
            asset
            for asset in aind_session.Session(smartspim_session_id).data_assets
            if "_stitched_" in asset.name
        )

    @dataclasses.dataclass
    class ManifestRecord:
        """Dataclass for a single row in the IBL data converter manifest csv."""

        mouseid: str
        sorted_recording: str
        probe_file: str
        # ---------------------------------------------------------------- #
        # these can't be mapped automatically, need be updated by user:
        probe_name: str | None = None
        probe_shank: str | None = None
        probe_id: str | None = None
        # ---------------------------------------------------------------- #
        surface_finding: str | None = None
        annotation_format: str = "json"

    @staticmethod
    def get_mindscope_probe_day_from_ng_state(
        neuroglancer_state: NeuroglancerState,
    ) -> dict[str, dict[Literal["probe", "day"], str]]:
        # extract probe A-F and day 1-9, with optional separators
        pattern = r"(?P<probe>[A-F])[-_ ]*(?P<day>[1-9])"
        results = {}
        for name in neuroglancer_state.annotation_names:
            result = re.search(pattern, name)
            if result is None:
                continue
            results[name] = {key: str(result.group(key)) for key in ("probe", "day")}
        return results  # type: ignore[return-value]

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

        if not any(self.get_mindscope_probe_day_from_ng_state(neuroglancer_state)):
            for annotation_name in neuroglancer_state.annotation_names:
                for sorted_data_asset_name in sorted_data_asset_names:
                    row = IBLDataConverterExtension.ManifestRecord(
                        mouseid=self._base.id,
                        probe_name="",
                        probe_id=annotation_name,
                        sorted_recording=sorted_data_asset_name,
                        probe_file=neuroglancer_state_json_name,
                        surface_finding=self.surface_recording_names.get(
                            sorted_data_asset_name.split("_sorted")[0]
                        ),
                    )
                    records.append(row)
        else:
            ng_to_probe_day = self.get_mindscope_probe_day_from_ng_state(
                neuroglancer_state
            )
            days = sorted({int(v["day"]) for v in ng_to_probe_day.values()})
            ephys_sessions = sorted({asset.name for asset in self.ecephys_data_assets})
            for i, ephys_session in enumerate(ephys_sessions):
                day = i + 1
                if day not in days:
                    continue
                for ng_annotation, probe_day in ng_to_probe_day.items():
                    if int(probe_day["day"]) == day:
                        sorted_asset_name = next(
                            (
                                n
                                for n in sorted_data_asset_names
                                if n.startswith(ephys_session)
                            ),
                            None,
                        )
                        if sorted_asset_name is None:
                            raise ValueError(
                                f"No sorted asset found for {ephys_session} (day {day})"
                            )
                        row = IBLDataConverterExtension.ManifestRecord(
                            mouseid=self._base.id,
                            probe_name=f"Probe{probe_day['probe']}",
                            probe_id=ng_annotation,
                            sorted_recording=sorted_asset_name,
                            probe_file=neuroglancer_state_json_name,
                            surface_finding=self.surface_recording_names.get(
                                sorted_asset_name.split("_sorted")[0]
                            ),
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
            custom_metadata={
                "experiment type": "SmartSPIM",
                "subject id": str(self._base.id),
            },
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
            timeout=120,
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

    @property
    def neuroglancer_state_json_asset(self) -> codeocean.data_asset.DataAsset:
        """Most-recent data asset containing a Neuroglancer state json file for the subject, if one exists."""
        ng: NeuroglancerExtension = self._base.neuroglancer
        assets = ng.state_json_data_assets
        if not assets:
            raise AttributeError(
                f"No Neuroglancer state json asset has been created yet for {self._base.id}: run `subject.neuroglancer.from_json({{'...'}}).create_data_asset()`"
            )
        return assets[-1]

    def run_data_converter_capsule(
        self,
        capsule_id: str = DATA_CONVERTER_CAPSULE_ID,
        manifest_asset: str | codeocean.data_asset.DataAsset | None = None,
        neuroglancer_state_json_asset: (
            str | codeocean.data_asset.DataAsset | None
        ) = None,
        additional_assets: Iterable[codeocean.data_asset.DataAsset] = (),
        named_parameters: list[codeocean.computation.NamedRunParam] | None = None,
        pipeline_monitor_capsule_id: str | None = PIPELINE_MONITOR_CAPUSLE_ID,
    ) -> codeocean.computation.Computation:
        """
        Run the IBL data converter capsule on CodeOcean with auto-discovered raw data assets, sorted
        assets, SmartSPIM data asset, plus manifest csv asset (optionally specified or auto-discovered)
        and Neuroglancer state json asset (auto-discovered).

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> computation = subject.ibl_data_converter.run_data_converter_capsule()
        """
        if manifest_asset is not None:
            manifest_asset = aind_session.utils.codeocean_utils.get_data_asset_model(
                manifest_asset
            )
        else:
            manifest_asset = self.manifest_data_asset

        if neuroglancer_state_json_asset is not None:
            neuroglancer_state_json_asset = (
                aind_session.utils.codeocean_utils.get_data_asset_model(
                    neuroglancer_state_json_asset
                )
            )
        else:
            neuroglancer_state_json_asset = self.neuroglancer_state_json_asset

        ng_state_path = next(
            aind_session.utils.codeocean_utils.get_data_asset_source_dir(
                neuroglancer_state_json_asset.id
            ).glob("*.json")
        )
        image_sources = NeuroglancerState(ng_state_path).image_sources
        smartspim_data_assets = [
            asset
            for asset in self.smartspim_data_assets
            if any(asset.name in source for source in image_sources)
        ]
        if not smartspim_data_assets:
            raise ValueError(
                f"No SmartSPIM data asset found matching image source(s) in Neuroglancer state json: {image_sources}. Cannot run IBL data converter capsule"
            )

        stitched_data_assets = []
        for smartspim_session in (asset.name for asset in smartspim_data_assets):
            stitched = self.get_stitched_data_assets(smartspim_session)
            if stitched:
                stitched_data_assets.append(stitched[-1])
        if not stitched_data_assets:
            smartspim_session = next(
                asset.name
                for asset in smartspim_data_assets
                if asset.name in image_sources[0]
            )
            stitched_id = next(
                p
                for p in reversed(image_sources[0].split("/"))
                if p.startswith(f"{smartspim_session}_stitched_")
            )
            path = "".join(
                image_sources[0].removeprefix("zarr://").rpartition(stitched_id)[:2]
            )
            raise ValueError(
                f"No stitched data asset found for SmartSPIM session: try creating an asset for {path}"
            )

        data_assets = [
            codeocean.computation.DataAssetsRunParam(id=asset.id, mount=asset.name)
            for asset in (
                *self.ecephys_data_assets,
                *self.sorted_data_assets,
                *smartspim_data_assets,
                *stitched_data_assets,
                manifest_asset,
                neuroglancer_state_json_asset,
                *additional_assets,
            )
        ]
        logger.debug(
            f"Using data assets for IBL data converter: {dict(zip([a.mount for a in data_assets], [a.id for a in data_assets]))}"
        )

        named_parameters = named_parameters or [
            codeocean.computation.NamedRunParam(
                param_name="manifest",
                value=f"{manifest_asset.name}/{manifest_asset.name}.csv",
            ),
            codeocean.computation.NamedRunParam(
                param_name="neuroglancer",
                value=f"{neuroglancer_state_json_asset.name}/{neuroglancer_state_json_asset.name}.json",
            ),
        ]
        logger.debug(
            f"Using named parameters for IBL data converter: {dict(zip([p.param_name for p in named_parameters], [p.value for p in named_parameters]))}"
        )

        if not pipeline_monitor_capsule_id:
            run_params = codeocean.computation.RunParams(
                capsule_id=capsule_id,
                data_assets=data_assets,
                named_parameters=named_parameters,
            )
        else:
            logger.info(
                f"Using monitor capsule {pipeline_monitor_capsule_id} to capture IBL data converter output as a data asset"
            )

            pipeline_monitor_settings = aind_codeocean_pipeline_monitor.models.PipelineMonitorSettings(
                run_params=codeocean.computation.RunParams(
                    capsule_id=capsule_id,
                    data_assets=data_assets,
                    named_parameters=named_parameters,
                ),
                computation_polling_interval=1 * 60,
                computation_timeout=48 * 3600,
                capture_settings=aind_codeocean_pipeline_monitor.models.CaptureSettings(
                    name=f"{smartspim_session}_ibl-converted_{datetime.datetime.now(tz=zoneinfo.ZoneInfo('US/Pacific')):%Y-%m-%d_%H-%M-%S}",
                    tags=[
                        str(self._base.id),
                        "smartSPIM",
                        "ecephys",
                        "IBL",
                        "annotation",
                    ],
                    custom_metadata={
                        "data level": "derived",
                        "experiment type": "ecephys",
                        "subject id": str(self._base.id),
                    },
                ),
            )
            run_params = codeocean.computation.RunParams(
                capsule_id=pipeline_monitor_capsule_id,
                data_assets=data_assets,
                parameters=[pipeline_monitor_settings.model_dump_json()],
            )

        logger.info(f"Running IBL data converter capsule {capsule_id}")
        return aind_session.utils.codeocean_utils.get_codeocean_client().computations.run_capsule(
            run_params
        )


@aind_session.register_namespace(name="neuroglancer", cls=aind_session.Subject)
class NeuroglancerExtension(aind_session.extension.ExtensionBaseClass):

    _base: aind_session.Subject

    state_json_dir: upath.UPath = SCRATCH_STORAGE_DIR / "neuroglancer_states"

    def from_json(
        self,
        content: str | Mapping[str, Any],
    ) -> NeuroglancerState:
        """ """
        return NeuroglancerState(content)

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
    def state_json_data_assets(self) -> tuple[codeocean.data_asset.DataAsset, ...]:
        """All Neuroglancer state json data assets associated with the subject, sorted by name.

        Examples
        --------
        >>> subject = aind_session.Subject(717381)
        >>> subject.neuroglancer.state_json_data_assets[0].name     # doctest: +SKIP
        'SmartSPIM_717381_2024-07-03_10-49-01_neuroglancer-state_2024-08-16_23-15-47'
        """
        # name is coupled with NeuroglancerState.get_new_file_name()
        return tuple(
            sorted(
                (
                    asset
                    for asset in self._base.data_assets
                    if "neuroglancer-state" in asset.name
                ),
                key=lambda a: a.name,
            )
        )


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
