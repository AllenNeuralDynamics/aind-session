import csv
import dataclasses
import io
import logging

import codeocean.computation
import codeocean.data_asset
import upath

import aind_session
import aind_session.extensions
import aind_session.utils
import aind_session.utils.codeocean_utils
import aind_session.utils.misc_utils

logger = logging.getLogger(__name__)


@aind_session.register_namespace(name="ibl_annotation", cls=aind_session.Subject)
class IBLAnnotationExtension(aind_session.ExtensionBaseClass):

    _base: aind_session.Subject

    DATA_CONVERTER_CAPSULE_ID = "372263e6-d942-4241-ba71-763a1062f2b7"  #! test capsule
    # TODO switch to actual capsule: "d4ba01c4-5665-4163-95d2-e481f4465b86"
    """https://codeocean.allenneuraldynamics.org/capsule/1376129/tree"""

    @property
    def ecephys_sessions(self) -> tuple[aind_session.Session, ...]:
        return tuple(
            sorted(
                session
                for session in self._base.sessions
                if session.platform == "ecephys"
            )
        )

    @property
    def ecephys_data_assets(self) -> tuple[codeocean.data_asset.DataAsset, ...]:
        assets = []
        for session in self.ecephys_sessions:
            if not (asset := session.raw_data_asset):
                logger.warning(
                    f"{session.id} raw data has not been uploaded: cannot use for annotation"
                )
                continue
            assets.append(asset)
            logger.debug(f"Using {asset.name} for annotation")
        return aind_session.utils.codeocean_utils.sort_by_created(assets)

    @property
    def sorted_data_assets(
        self,
    ) -> tuple[aind_session.extensions.ecephys.SortedDataAsset, ...]:
        assets = []
        for session in self._base.sessions:
            if session.platform != "ecephys":
                continue
            correct_assets = aind_session.utils.codeocean_utils.sort_by_created(
                a
                for a in session.ecephys.sorter.kilosort2_5.sorted_data_assets
                if not a.is_sorting_error
                # and not a.is_sorting_analyzer #TODO are both supported?
            )
            if not correct_assets:
                logger.warning(
                    f"{session.id} has no sorted data (in a non-errored state): cannot use for annotation"
                )
                continue
            asset = correct_assets[-1]
            assets.append(asset)
            logger.debug(f"Using {asset.name} for annotation")
        return aind_session.utils.codeocean_utils.sort_by_created(assets)

    @property
    def smartspim_data_asset(self) -> codeocean.data_asset.DataAsset:
        assets = []
        for session in self._base.sessions:
            if session.platform != "SmartSPIM":
                continue
            if not hasattr(session, "raw_data_asset"):
                logger.warning(f"{session.id} has no raw data asset")
                continue
            assets.append(session.raw_data_asset)
            logger.debug(f"Found asset {session.raw_data_asset.name!r}")
        if not assets:
            raise AttributeError(f"No SmartSPIM data asset found for {self._base.id}")
        if len(assets) > 1:
            logger.info(
                f"Multiple SmartSPIM raw data assets found for {self._base.id}: using most-recent"
            )
        return aind_session.utils.codeocean_utils.sort_by_created(assets)[-1]

    @dataclasses.dataclass
    class ManifestRecord:
        mouseid: str
        sorted_recording: str
        probe_name: str
        probe_file: int
        probe_id: int = 0  # not currently supported
        surface_finding: int | None = None  # not currently used
        annotation_format: str = "swc"

    @property
    def csv_manifest(self) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                field.name
                for field in dataclasses.fields(IBLAnnotationExtension.ManifestRecord)
            ],
        )
        writer.writeheader()
        for sorted_asset in self.sorted_data_assets:
            for probe_name in sorted_asset.sorted_probes:
                row = IBLAnnotationExtension.ManifestRecord(
                    mouseid=self._base.id,
                    sorted_recording=sorted_asset.name,
                    surface_finding=None,
                    probe_name=probe_name,
                    probe_file=999,  # TODO get real value (from Horta or Neuroglancer?)
                )
                writer.writerow(dataclasses.asdict(row))
        content = output.getvalue()
        output.close()
        return content

    @property
    def csv_manifest_path(self) -> upath.UPath:
        return upath.UPath(
            f"s3://aind-scratch-data/ben.hardcastle/ibl_annotation_test/{self._base.id}_ibl_annotation_manifest.csv"
        )

    def create_manifest_asset(
        self, skip_existing: bool = True
    ) -> codeocean.data_asset.DataAsset:
        if skip_existing and hasattr(self, "manifest_data_asset"):
            logger.info(
                f"Manifest asset already exists for {self._base.id}. Use `self.create_manifest_asset(skip_existing=False)` to force creation"
            )
            return self.manifest_data_asset
        logger.debug(f"Writing annotation manifest to {self.csv_manifest_path}")
        self.csv_manifest_path.write_text(self.csv_manifest)
        if not self.csv_manifest_path.exists():
            raise FileNotFoundError(
                f"Failed to write annotation manifest to {self.csv_manifest_path}"
            )
        asset_params = codeocean.data_asset.DataAssetParams(
            name=self.csv_manifest_path.stem,
            mount=self.csv_manifest_path.stem,
            tags=["ibl", "annotation", "manifest", self._base.id],
            source=codeocean.data_asset.Source(
                aws=codeocean.data_asset.AWSS3Source(
                    bucket=(bucket := self.csv_manifest_path.as_posix().split("/")[2]),
                    prefix=(
                        self.csv_manifest_path.as_posix().split(bucket)[1].strip("/")
                    ),
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
        updated_asset = aind_session.utils.codeocean_utils.get_codeocean_client().data_assets.wait_until_ready(
            data_asset=asset,
            timeout=60,
        )
        logger.debug(f"Asset {updated_asset.name} is ready")
        return updated_asset

    @property
    def manifest_data_asset(self) -> codeocean.data_asset.DataAsset:
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

    def run_data_converter_capsule(self) -> codeocean.computation.Computation:
        run_params = codeocean.computation.RunParams(
            capsule_id=self.DATA_CONVERTER_CAPSULE_ID,
            data_assets=[
                codeocean.computation.DataAssetsRunParam(id=asset.id, mount=asset.name)
                for asset in (
                    *self.ecephys_data_assets,
                    *self.sorted_data_assets,
                    self.smartspim_data_asset,
                    self.manifest_data_asset,
                )
            ],
            parameters=[],
            named_parameters=[],
        )
        logger.debug(f"Running data converter capsule: {run_params.capsule_id}")
        return aind_session.utils.codeocean_utils.get_codeocean_client().computations.run_capsule(
            run_params
        )


if __name__ == "__main__":
    subject = aind_session.Subject("729293")
    asset = subject.ibl_annotation.create_manifest_asset(skip_existing=True)
    print(aind_session.utils.codeocean_utils.get_data_asset_source_dir(asset.id))
    subject.ibl_annotation.run_data_converter_capsule()
    # print(ibl_annotation.manifest_data_asset)
    # print([asset.name for asset in ibl_annotation.ecephys_data_assets])
    # print([asset.name for asset in ibl_annotation.sorted_data_assets])
    # print(ibl_annotation.smartspim_data_asset.name)
    # print(ibl_annotation.csv_manifest)
