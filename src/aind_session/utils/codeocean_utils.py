from __future__ import annotations

import contextlib
import functools
import logging
import os
import uuid
from collections.abc import Iterable

import codeocean
import codeocean.data_asset
import npc_session
import upath

import aind_session.utils

logger = logging.getLogger(__name__)


@functools.cache
def get_codeocean_client() -> codeocean.CodeOcean:
    """
    Get a CodeOcean client using environment variables.

    - `CODE_OCEAN_API_TOKEN` is the preferred key
    - if not found, the first environment variable starting with `COP_` is used
      (case-insensitive)
    - domain name defaults to `https://codeocean.allenneuraldynamics.org`, but can
      be overridden by setting `CODE_OCEAN_DOMAIN`

    Examples:
        >>> client = get_codeocean_client()
        >>> assert client.domain == "https://codeocean.allenneuraldynamics.org"
    """
    token = os.getenv(
        key="CODE_OCEAN_API_TOKEN",
        default=next(
            (v for v in os.environ.values() if v.lower().startswith("cop_")),
            None,
        ),
    )
    if token is None:
        raise KeyError(
            "`CODE_OCEAN_API_TOKEN` not found in environment variables and no `COP_` variable found",
        )
    return codeocean.CodeOcean(
        domain=os.getenv(
            key="CODE_OCEAN_DOMAIN",
            default="https://codeocean.allenneuraldynamics.org",
        ),
        token=token,
    )


def sort_data_assets(
    assets: Iterable[codeocean.data_asset.DataAsset],
) -> tuple[codeocean.data_asset.DataAsset, ...]:
    """Sort data assets by ascending creation date"""
    return tuple(sorted(assets, key=lambda asset: asset.created))


def get_data_asset(
    asset_id: str | uuid.UUID | codeocean.data_asset.DataAsset,
) -> codeocean.data_asset.DataAsset:
    """Normalizes an asset ID (uuid) to a data asset model.

    Examples:
        >>> asset = get_data_asset('83636983-f80d-42d6-a075-09b60c6abd5e')
        >>> assert isinstance(asset, codeocean.data_asset.DataAsset)
    """
    if isinstance(asset_id, codeocean.data_asset.DataAsset):
        return asset_id
    return get_codeocean_client().data_assets.get_data_asset(str(asset_id))


def is_raw_data_asset(asset: str | uuid.UUID | codeocean.data_asset.DataAsset) -> bool:
    """
    Determine if a data asset is raw data based on custom metadata or tags or
    name.

    In order of precedence:
    - custom metadata with "data level": "raw data" is considered raw data
    - tags containing "raw" are considered raw data
    - if no custom metadata or tags are present, the asset name is checked: if it
    is a session ID alone, with no suffixes, it is considered raw data

    Examples:
        >>> is_raw_data_asset('83636983-f80d-42d6-a075-09b60c6abd5e')
        True
        >>> is_raw_data_asset('173e2fdc-0ca3-4a4e-9886-b74207a91a9a')
        False
    """
    asset = get_data_asset(asset)
    if asset.custom_metadata and asset.custom_metadata.get("data level") == "raw data":
        logger.debug(
            f"{asset.id=} determined to be raw data based on custom_metadata containing 'data level': 'raw data'"
        )
        return True
    else:
        logger.debug(f"{asset.id=} has no custom metadata")
    if asset.tags and any("raw" in tag for tag in asset.tags):
        logger.debug(
            f"{asset.id=} determined to be raw data based on tag(s) containing 'raw'"
        )
        return True
    else:
        logger.debug(f"{asset.id=} has no tags")
    logger.info(
        f"No custom metadata or tags for {asset.id=}: determining if raw data asset based on name alone"
    )
    try:
        session_id = str(npc_session.AINDSessionRecord(asset.name))
    except ValueError:
        logger.debug(
            f"{asset.id=} name does not contain a valid session ID: {asset.name=}"
        )
        return False
    if session_id == asset.name:
        logger.debug(
            f"{asset.id=} name is a session ID alone, with no additional suffixes: it is considered raw data {asset.name=}"
        )
        return True
    else:
        logger.debug(
            f"{asset.id=} name is not a session ID alone: it is not considered raw data {asset.name=}"
        )
        return False


def get_data_asset_source_folder(
    asset: str | uuid.UUID | codeocean.data_asset.DataAsset,
) -> upath.UPath:
    """Get the source folder for a data asset.

    - the path is constructed from the asset's `source_bucket` metadata
    - otherwise, the path is constructed from the asset's ID and known S3
      buckets, and existence is checked
    - otherwse, the path is constructed from the asset's name and known S3
      buckets, and existence is checked

    - raises `FileNotFoundError` if a folder is not found

    Examples:
        >>> get_data_asset_source_folder('83636983-f80d-42d6-a075-09b60c6abd5e').as_posix()
        's3://aind-ephys-data/ecephys_668759_2023-07-11_13-07-32'
    """

    def get_folder_from_known_s3_locations(
        asset: codeocean.data_asset.DataAsset,
    ) -> upath.UPath:
        for key in (asset.id, asset.name):
            with contextlib.suppress(FileNotFoundError):
                return aind_session.utils.get_source_folder_by_name(
                    key, ttl_hash=aind_session.utils.get_ttl_hash(10 * 60)
                )
        raise FileNotFoundError(
            f"No source folder found for {asset.id=} or {asset.name=} in known S3 buckets"
        )

    asset = get_data_asset(asset)
    if asset.source_bucket:
        protocol = {"aws": "s3", "gcp": "gs", "local": "file"}.get(
            asset.source_bucket.origin
        )
        if protocol:
            path = upath.UPath(
                f"{protocol}://{asset.source_bucket.bucket}/{asset.source_bucket.prefix}"
            )
            if not path.exists():
                raise FileNotFoundError(
                    f"{path.as_posix()} found from data asset, but does not exist (or access is denied)"
                )
            logger.debug(
                f"Path for {asset.name}, {asset.id} returned (existence has been checked): {path.as_posix()}"
            )
            return path
        else:
            logger.warning(
                f"Unsupported storage protocol: {asset.source_bucket.origin} for {asset.id}, {asset.name}"
            )
    else:
        logger.debug(
            f"No source_bucket metadata available for {asset.id}, {asset.name}"
        )
    return get_folder_from_known_s3_locations(asset)


@functools.cache
def get_subject_data_assets(
    subject_id: str | int,
    page_size: int = 200,
    max_pages: int = 100,
    offset: int = 0,
    ttl_hash: int | None = None,
    **search_parameters,
) -> tuple[codeocean.data_asset.DataAsset, ...]:
    """
    Get all assets associated with a subject ID.

    - assets are sorted by ascending creation date
    - provide additional search parameters to filter results, as schematized in `codeocean.data_asset.DataAssetSearchParams`:
    https://github.com/codeocean/codeocean-sdk-python/blob/4d9cf7342360820f3d9bd59470234be3e477883e/src/codeocean/data_asset.py#L199

    Examples:
        >>> assets = get_subject_data_assets(668759)
        >>> assert len(assets) > 0
    """
    del ttl_hash  # only used for functools.cache
    for key in ("limit", "offset"):
        if key in search_parameters:
            logger.warning(
                f"Removing {key} from user-provided search_parameters: pagination is handled by this function"
            )
            search_parameters.pop(key)
    if "query" in search_parameters:
        logger.warning(
            "Removing query from user-provided search_parameters: subject ID is used to assets"
        )
        search_parameters.pop("query")

    # set required fields if not provided
    search_parameters.setdefault("archived", False)
    search_parameters.setdefault("favorite", False)

    try:
        _ = npc_session.extract_subject(str(subject_id))
    except ValueError:
        logger.warning(
            f"Subject ID {subject_id=} does not appear to be a Labtracks MID: assets may not be found"
        )

    results: list[codeocean.data_asset.DataAsset] = []
    while offset < max_pages:
        search_results = get_codeocean_client().data_assets.search_data_assets(
            codeocean.data_asset.DataAssetSearchParams(
                query=f"subject id: {subject_id}",
                limit=page_size,
                offset=offset * page_size,
                **search_parameters,
            )
        )
        results.extend(search_results.results)
        if not search_results.has_more:
            break
        offset += 1
    else:
        raise TimeoutError(
            f"Max pages reached fetching codeocean data assets for {subject_id=}: {max_pages=}"
        )
    return sort_data_assets(results)


def get_session_data_assets(
    session_id_or_search_term: str | npc_session.AINDSessionRecord,
    **search_parameters,
) -> tuple[codeocean.data_asset.DataAsset, ...]:
    """
    Get all data assets that include the search term in their name.

    - currently requires search term to include a subject ID (Labtracks MID) in order to find assets
    - assets are sorted by ascending creation date
    - provide additional search parameters to filter results, as schematized in `codeocean.data_asset.DataAssetSearchParams`:
    https://github.com/codeocean/codeocean-sdk-python/blob/4d9cf7342360820f3d9bd59470234be3e477883e/src/codeocean/data_asset.py#L199

    Examples:
        # Use a full session ID
        >>> assets = get_session_data_assets('ecephys_676909_2023-12-13_13-43-40')
        >>> assert len(assets) > 0
        >>> latest_asset = assets[-1]

        # Use a partial ID
        >>> assets = get_session_data_assets('676909_2023-12-13')
        >>> assert len(assets) > 0
        >>> assert latest_asset in assets

        # Filter by asset type
        >>> filtered_assets = get_session_data_assets('676909_2023-12-13', type='dataset')
        >>> assert len(assets) > len(filtered_assets) > 0
    """
    subject_id = npc_session.extract_subject(session_id_or_search_term)
    if subject_id is None:
        raise ValueError(
            f"Search term must include a subject ID: {session_id_or_search_term=!r}"
        )
    subject_assets = get_subject_data_assets(
        subject_id, ttl_hash=aind_session.utils.get_ttl_hash(), **search_parameters
    )
    return sort_data_assets(
        asset for asset in subject_assets if session_id_or_search_term in asset.name
    )


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
