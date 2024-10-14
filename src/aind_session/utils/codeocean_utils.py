# mypy: disable-error-code=unused-ignore
# types-requests has compatibility issue with boto3 https://github.com/python/typeshed/issues/10825
from __future__ import annotations

import contextlib
import functools
import logging
import os
import time
import uuid
from collections.abc import Iterable
from typing import Any, Literal

import codeocean
import codeocean.components
import codeocean.computation
import codeocean.data_asset
import npc_session
import requests  # type: ignore # to avoid checking types/installing types-requests
import upath

import aind_session.utils

logger = logging.getLogger(__name__)


@functools.cache
def get_codeocean_client(check_credentials: bool = True) -> codeocean.CodeOcean:
    """
    Get a CodeOcean client using environment variables.

    - `CODE_OCEAN_API_TOKEN` is the preferred key
    - if not found, the first environment variable starting with `COP_` is used
      (case-insensitive)
    - domain name defaults to `https://codeocean.allenneuraldynamics.org`, but can
      be overridden by setting `CODE_OCEAN_DOMAIN`

    Examples
    --------
    >>> client = get_codeocean_client()
    >>> client.domain
    'https://codeocean.allenneuraldynamics.org'
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
            "`CODE_OCEAN_API_TOKEN` not found in environment variables and no `COP_` variable found"
        )
    client = codeocean.CodeOcean(
        domain=os.getenv(
            key="CODE_OCEAN_DOMAIN",
            default="https://codeocean.allenneuraldynamics.org",
        ),
        token=token,
    )
    if check_credentials:
        logger.debug(
            f"Checking CodeOcean credentials for read datasets scope on {client.domain}"
        )
        t0 = time.time()
        try:
            _ = client.data_assets.search_data_assets(
                codeocean.data_asset.DataAssetSearchParams(
                    query=f"subject id: {366122}",
                    limit=1,
                    offset=0,
                    archived=False,
                    favorite=False,
                )
            )
        except requests.HTTPError as exc:
            if exc.response.status_code == 401:
                raise ValueError(
                    "CodeOcean API token was found in environment variables, but does not have permissions to read datasets: check `CODE_OCEAN_API_TOKEN`"
                ) from None
            else:
                raise
        else:
            logger.debug(
                f"CodeOcean credentials verified as having read datasets scope, in {time.time() - t0:.2f}s"
            )
    return client


def get_normalized_uuid(
    id_or_model: (
        str
        | uuid.UUID
        | codeocean.data_asset.DataAsset
        | codeocean.computation.Computation
    ),
) -> str:
    """
    Accepts a data or computation ID or model and returns a string with the format expected
    by the CodeOcean API.

    Examples
    --------
    >>> a = get_normalized_uuid('867ed56f-f9cc-4649-8b9f-97efc4dbd4cd')
    >>> b = get_normalized_uuid('867ed56ff9cc46498b9f97efc4dbd4cd')
    >>> c = get_normalized_uuid(get_subject_data_assets(668759)[0])
    >>> assert a == b == c
    >>> a
    '867ed56f-f9cc-4649-8b9f-97efc4dbd4cd'

    Badly-formed UUIDs will raise a ValueError:
    >>> get_normalized_uuid('867ed56f')
    Traceback (most recent call last):
    ...
    ValueError: Cannot create a valid UUID from '867ed56f'

    Incorrect types will raise a TypeError:
    >>> get_normalized_uuid(867)
    Traceback (most recent call last):
    ...
    TypeError: Cannot convert 867 (<class 'int'>) to a UUID
    """
    if (id_ := getattr(id_or_model, "id", None)) is not None:
        return id_
    try:
        return str(uuid.UUID(id_or_model))  # type: ignore [arg-type]
    except ValueError:
        raise ValueError(f"Cannot create a valid UUID from {id_or_model!r}") from None
    except AttributeError:
        raise TypeError(
            f"Cannot convert {id_or_model!r} ({type(id_or_model)}) to a UUID"
        ) from None


def get_codeocean_model(
    asset_or_computation_id: (
        str
        | uuid.UUID
        | codeocean.data_asset.DataAsset
        | codeocean.computation.Computation
    ),
    is_computation: Literal[True] | None = None,
) -> codeocean.data_asset.DataAsset | codeocean.computation.Computation:
    """Fetches data asset or computation metadata model from an ID.

    - use to ensure we have a `DataAsset` or `Computation` object
    - if model is already a `DataAsset` or `Computation`, it is returned as-is
    - if a str/uuid is supplied, a matching data asset will first be looked-up, and
      then a computation if no data asset is found
        - if `is_computation` is set to True, the initial data asset lookup will
          be skipped

    Examples
    --------
    >>> asset = get_codeocean_model('83636983-f80d-42d6-a075-09b60c6abd5e')
    >>> assert isinstance(asset, codeocean.data_asset.DataAsset)
    >>> asset = get_codeocean_model('7646f92f-d225-464c-b7aa-87a87f34f408')
    >>> assert isinstance(asset, codeocean.computation.Computation)

    If no data asset or computation is found, a ValueError is raised:
    >>> asset = get_codeocean_model('867ed56f-f9cc-4649-8b9f-97efc4dbd4ca')
    Traceback (most recent call last):
    ...
    ValueError: No data asset or computation found matching ID 867ed56f-f9cc-4649-8b9f-97efc4dbd4ca
    """
    if isinstance(
        asset_or_computation_id, codeocean.data_asset.DataAsset
    ) or isinstance(asset_or_computation_id, codeocean.computation.Computation):
        return asset_or_computation_id
    if not is_computation:
        with contextlib.suppress(ValueError):
            return get_data_asset_model(asset_or_computation_id)
    try:
        return get_codeocean_client().computations.get_computation(
            get_normalized_uuid(asset_or_computation_id)
        )
    except requests.HTTPError as exc:
        if exc.response.status_code == 404:
            raise ValueError(
                f"No data asset or computation found matching ID {asset_or_computation_id}"
            ) from None
        else:
            raise


def get_data_asset_model(
    asset_id_or_model: str | uuid.UUID | codeocean.data_asset.DataAsset,
) -> codeocean.data_asset.DataAsset:
    """Fetches data asset metadata model from an ID.

    - use to ensure we have a `DataAsset` object
    - if model is already a `DataAsset`, it is returned as-is

    Examples
    --------
    >>> asset = get_data_asset_model('83636983-f80d-42d6-a075-09b60c6abd5e')
    >>> assert isinstance(asset, codeocean.data_asset.DataAsset)
    >>> asset.name
    'ecephys_668759_2023-07-11_13-07-32'
    """
    if isinstance(asset_id_or_model, codeocean.data_asset.DataAsset):
        return asset_id_or_model
    try:
        return get_codeocean_client().data_assets.get_data_asset(
            get_normalized_uuid(asset_id_or_model)
        )
    except requests.HTTPError as exc:
        if exc.response.status_code == 404:
            raise ValueError(
                f"No data asset found matching ID {asset_id_or_model}"
            ) from exc
        else:
            raise


def sort_by_created(
    ids_or_models: Iterable[
        str
        | uuid.UUID
        | codeocean.data_asset.DataAsset
        | codeocean.computation.Computation
    ],
) -> tuple[codeocean.data_asset.DataAsset, ...]:
    """Sort data assets or computations by ascending creation date. Accepts IDs or models."""
    return tuple(
        sorted(
            (get_codeocean_model(a) for a in ids_or_models),
            key=lambda asset: asset.created,
        )
    )


@functools.cache
def get_data_asset_source_dir(
    asset_id: (
        str | uuid.UUID
    ),  # cannot accept model while it has a dict component and unsafe_hash=False
    ttl_hash: int | None = None,
) -> upath.UPath:
    """Get the source dir for a data asset.

    - the path is constructed from the asset's `source_bucket` metadata
    - otherwise, the path is constructed from the asset's ID and known S3
      buckets, and existence is checked
    - otherwse, the path is constructed from the asset's name and known S3
      buckets, and existence is checked

    - raises `FileNotFoundError` if a dir is not found

    - `ttl_hash` is used to cache the result for a given number of seconds (time-to-live)
        - default None means cache indefinitely
        - use `aind_utils.get_ttl_hash(seconds)` to generate a new ttl_hash periodically

    Examples
    --------
    >>> get_data_asset_source_dir('83636983-f80d-42d6-a075-09b60c6abd5e').as_posix()
    's3://aind-ephys-data/ecephys_668759_2023-07-11_13-07-32'
    """

    asset = get_data_asset_model(asset_id)

    def get_dir_from_known_s3_locations(
        asset: codeocean.data_asset.DataAsset,
    ) -> upath.UPath:
        for key in (asset.id, asset.name):
            with contextlib.suppress(FileNotFoundError):
                return aind_session.utils.get_source_dir_by_name(
                    key,
                    ttl_hash=aind_session.utils.get_ttl_hash(
                        10 * 60 if ttl_hash is None else ttl_hash
                    ),
                )
        raise FileNotFoundError(
            f"No source dir found for {asset.id=} or {asset.name=} in known S3 buckets"
        )

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
    return get_dir_from_known_s3_locations(asset)


def get_data_asset_search_query(
    name: str | None = None,
    subject_id: str | int | None = None,
    tag: str | Iterable[str] | None = None,
    description: str | None = None,
) -> str:
    """
    Create a search string for feeding into the 'query' field when searching for
    data assets in the CodeOcean API.

    Note: current understanding of the operation of the 'query' field is largely
    undocumented, so the following is based on empirical testing and is not
    exhaustive.
    """
    params = {
        k: v for k, v in locals().items() if v not in ("", None)
    }  # careful not to exclude 0s
    query: list[str] = []

    def append(param_name: str, value: Any) -> None:
        query.append(f'{param_name.lower().replace("_", " ")}:{value}')

    for k, v in params.items():
        if k == "tag":
            # the CO API supports searching tags multiple times in the same 'query'
            tags = v if (isinstance(v, Iterable) and not isinstance(v, str)) else (v,)
            for t in tags:
                append(k, t)
        else:
            append(k, v)
    query_text = " ".join(query)
    logger.debug(f"Generated search query: {query_text!r}")
    return query_text


def search_data_assets(
    search_params: dict[str, Any] | codeocean.data_asset.DataAssetSearchParams,
    page_size: int = 100,
    max_pages: int = 1000,
    raise_on_page_limit: bool = True,
) -> tuple[codeocean.data_asset.DataAsset, ...]:
    """A wrapper around `codeocean.data_assets.search_data_assets` that makes it
    slightly easier to use.

    - handles pagination and fetches all available assets matching search parameters
    - returns `DataAsset` objects instead of `DataAssetSearchResults`
        - `DataAssetSearchResults` only exists to store assets and signal `has_more`
    - fills in required fields with sensible defaults if not provided:
        - `archived=False`
        - `favorite=False`
    - raises a `ValueError` if the page limit is reached, unless
      `raise_on_page_limit=False`

    Examples
    --------
    >>> assets = search_data_assets({"query": "subject id:676909", "sort_field": "created", "sort_order": "asc"})
    >>> type(assets[0])
    <class 'codeocean.data_asset.DataAsset'>
    >>> assets[0].name
    'Example T1 and T2 MRI Images'
    >>> assets[0].created
    1673996872
    """
    if isinstance(search_params, codeocean.data_asset.DataAssetSearchParams):
        updated_params = search_params.to_dict()
    else:
        updated_params = search_params.copy()
    for key in ("limit", "offset"):
        if key in search_params:
            logger.info(
                f"Removing {key} from provided search parameters: pagination is handled by this function"
            )
            updated_params.pop(key)

    # set required fields if not provided
    updated_params.setdefault("archived", False)
    updated_params.setdefault("favorite", False)

    logger.debug(
        f"Fetching data assets results matching search parameters: {updated_params}"
    )

    assets: list[codeocean.data_asset.DataAsset] = []
    page = 0
    while page < max_pages:
        search_results = get_codeocean_client().data_assets.search_data_assets(
            codeocean.data_asset.DataAssetSearchParams(
                limit=page_size,
                offset=page * page_size,
                **updated_params,
            )
        )
        assets.extend(search_results.results)
        if not search_results.has_more:
            break
        page += 1
    else:
        if raise_on_page_limit:
            raise ValueError(
                f"Reached page limit fetching data asset search results: try increasing parameters ({max_pages=}, {page_size=}), narrowing the search, or setting `raise_on_page_limit=False`"
            )
        logger.warning(
            f"Reached page limit fetching data asset search results: returning {len(assets)} assets, but others exist"
        )
    logger.debug(f"Search returned {len(assets)} data assets")
    return tuple(assets)


@functools.cache
def search_computations(
    capsule_or_pipeline_id: str | uuid.UUID,
    name: str | None = None,
    attached_data_asset_id: str | None = None,
    has_results: bool | None = None,
    in_progress: bool | None = None,
    computation_state: codeocean.computation.ComputationState | None = None,
    ttl_hash: int | None = None,
) -> tuple[codeocean.computation.Computation, ...]:
    """
    Search for capsule or pipeline computations with specific attributes.

    - implements the same get request as `codeocean.client.Computations.list_computations` but
    with pre-filtering on the response json
    - with no filters, this may be slow:
        - test with 1300 computations took ~1.5s to get the response and ~8s to
          make the `codeocean.computation.Computation` models from json
    - sorted by ascending creation time
    - `in_progress` True/False can be used to filter on whether the computation
      has ended
    - `attached_data_asset_id` can be used to filter on whether the computation was run
      with the given data asset attached as an input
    - by default, this function caches the result indefinitely: supply with a
      `aind_session.utils.ttl_hash(sec)` to cache for a given number of seconds

    Examples
    --------
    Get all computations for a capsule or pipeline:
    >>> capsule_id = "eb5a26e4-a391-4d79-9da5-1ab65b71253f"
    >>> computations = search_computations(capsule_id)

    >>> pipeline_id = "1f8f159a-7670-47a9-baf1-078905fc9c2e"
    >>> computations = search_computations(pipeline_id)

    >>> len(computations)               # doctest: +SKIP
    1

    Filter by computation metadata:
    >>> computations = search_computations(pipeline_id, in_progress=True)
    >>> computations = search_computations(pipeline_id, has_results=True)
    >>> computations = search_computations(pipeline_id, computation_state="failed")
    >>> computations = search_computations(pipeline_id, name="Run With Parameters 4689084")
    >>> computations = search_computations(pipeline_id, attached_data_asset_id="83636983-f80d-42d6-a075-09b60c6abd5e")
    """
    del ttl_hash  # only used for functools.cache

    capsule_or_pipeline_id = get_normalized_uuid(capsule_or_pipeline_id)

    t0 = time.time()
    records = (
        get_codeocean_client()
        .session.get(f"capsules/{capsule_or_pipeline_id}/computations")
        .json()
    )
    logger.debug(
        f"{len(records)} computation records returned from server in {time.time() - t0:.3f}s"
    )
    if name is not None:
        records = [record for record in records if record["name"] == name]
    if attached_data_asset_id is not None:
        records = [
            record
            for record in records
            if any(
                input_data_asset["id"] == attached_data_asset_id
                for input_data_asset in record.get("data_assets", [])
            )
        ]
    if has_results is not None:
        records = [record for record in records if record["has_results"]]
    if in_progress is not None:
        records = [
            record
            for record in records
            if (
                record["state"]
                in (
                    codeocean.computation.ComputationState.Completed,
                    codeocean.computation.ComputationState.Failed,
                )
                and in_progress is False
            )
            or (
                record["state"]
                in (
                    codeocean.computation.ComputationState.Running,
                    codeocean.computation.ComputationState.Initializing,
                    codeocean.computation.ComputationState.Finalizing,
                )
                and in_progress is True
            )
        ]
    if computation_state is not None:
        records = [record for record in records if record["state"] == computation_state]
    t0 = time.time()
    computations = tuple(
        sorted(
            [codeocean.computation.Computation.from_dict(record) for record in records],
            key=lambda c: c.created,
        )
    )
    logger.debug(
        f"{len(computations)} computation models created in {time.time() - t0:.3f}s"
    )
    return computations


@functools.cache
def get_subject_data_assets(
    subject_id: str | int,
    ttl_hash: int | None = None,
    **search_params,
) -> tuple[codeocean.data_asset.DataAsset, ...]:
    """
    Get all assets associated with a subject ID.

    - uses the `subject` field in asset metadata
    - `subject_id` will be cast to a string for searching
    - subject ID is not required to be a labtracks MID
    - assets are sorted by ascending creation date
    - provide additional search parameters to filter results, as schematized in `codeocean.data_asset.DataAssetSearchParams`:
    https://github.com/codeocean/codeocean-sdk-python/blob/4d9cf7342360820f3d9bd59470234be3e477883e/src/codeocean/data_asset.py#L199

    - `ttl_hash` is used to cache the result for a given number of seconds (time-to-live)
        - default None means cache indefinitely
        - use `aind_utils.get_ttl_hash(seconds)` to generate a new ttl_hash periodically

    Examples
    --------

    Search with a subject ID as str or int (will be cast as str):
    >>> assets = get_subject_data_assets(668759)
    >>> type(assets[0])
    <class 'codeocean.data_asset.DataAsset'>
    >>> assets[0].created
    1673996872
    >>> assets[0].name
    'Example T1 and T2 MRI Images'
    >>> assets[0].tags
    ['T1', 'T2', 'MRI', 'demo']

    Additional search parameters can be supplied as kwargs:
    >>> filtered_assets = get_subject_data_assets(668759, type='dataset')
    """
    del ttl_hash  # only used for functools.cache

    if "query" in search_params:
        raise ValueError(
            "Cannot provide 'query' as a search parameter: a new query will be created using 'subject id' field to search for assets"
        )
    search_params["query"] = get_data_asset_search_query(subject_id=subject_id)
    search_params["sort_field"] = codeocean.data_asset.DataAssetSortBy.Created
    search_params["sort_order"] = codeocean.components.SortOrder.Ascending
    assets = search_data_assets(search_params)
    if not assets and not npc_session.extract_subject(str(subject_id)):
        logger.warning(
            f"No assets were found for {subject_id=}, which does not appear to be a Labtracks MID"
        )
    return assets


@functools.cache
def get_session_data_assets(
    session_id: str | npc_session.AINDSessionRecord,
    ttl_hash: int | None = None,
    **search_params,
) -> tuple[codeocean.data_asset.DataAsset, ...]:
    """
    Get all data assets whose names start with the search term.

    - assets are sorted by ascending creation date
    - searching with a partial session ID is not reliable:
      - use `aind_session.get_sessions()` to search for sessions instead, which
      can filter on subject ID, platform, and date range
      - then examine the `assets` attribute on each returned object
    - provide additional search parameters to filter results, as schematized in `codeocean.data_asset.DataAssetSearchParams`:
    https://github.com/codeocean/codeocean-sdk-python/blob/4d9cf7342360820f3d9bd59470234be3e477883e/src/codeocean/data_asset.py#L199

    - `ttl_hash` is used to cache the result for a given number of seconds (time-to-live)
        - default None means cache indefinitely
        - use `aind_utils.get_ttl_hash(seconds)` to generate a new ttl_hash periodically

    Examples
    --------
    Use a full session ID:
    >>> assets = get_session_data_assets('ecephys_676909_2023-12-13_13-43-40')
    >>> type(assets[0])
    <class 'codeocean.data_asset.DataAsset'>
    >>> assets[0].created
    1702620828
    >>> assets[0].name
    'ecephys_676909_2023-12-13_13-43-40'
    >>> assets[0].tags                    # doctest: +SKIP
    ['ecephys', 'raw', '676909']

    Additional search parameters can be supplied as kwargs:
    >>> filtered_assets = get_session_data_assets('ecephys_676909_2023-12-13_13-43-40', type='dataset')
    >>> assert len(filtered_assets) > 0
    """
    del ttl_hash  # only used for functools.cache
    try:
        session_id = npc_session.AINDSessionRecord(session_id)
    except ValueError as exc:
        raise ValueError(
            "Querying the CodeOcean API with a partial session ID is not reliable: use `aind_session.get_sessions()` to search, then examine the `assets` attribute on each returned object"
        ) from exc
    if "query" in search_params:
        raise ValueError(
            "Cannot provide 'query' as a search parameter: a new query will be created using the 'name' field to search for assets"
        )
    search_params["query"] = get_data_asset_search_query(name=session_id)
    search_params["sort_field"] = codeocean.data_asset.DataAssetSortBy.Created
    search_params["sort_order"] = codeocean.components.SortOrder.Ascending
    assets = search_data_assets(search_params)
    return assets


def is_raw_data_asset(
    asset_id_or_model: str | uuid.UUID | codeocean.data_asset.DataAsset,
) -> bool:
    """
    Determine if a data asset is raw data based on custom metadata or tags or
    name.

    In order of precedence:
    - custom metadata with "data level": "raw data" is considered raw data
    - tags containing "raw" are considered raw data
    - if no custom metadata or tags are present, the asset name is checked: if it
    is a session ID alone, with no suffixes, it is considered raw data

    Examples
    --------
    >>> is_raw_data_asset('83636983-f80d-42d6-a075-09b60c6abd5e')
    True
    >>> is_raw_data_asset('173e2fdc-0ca3-4a4e-9886-b74207a91a9a')
    False
    """
    asset = get_data_asset_model(asset_id_or_model)
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
    else:
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


def get_output_text(
    asset_or_computation_id: (
        str
        | uuid.UUID
        | codeocean.data_asset.DataAsset
        | codeocean.computation.Computation
    ),
) -> str:
    """Get the contents of the "output" file from a data asset or computation.

    - raises `FileNotFoundError` if the output file is not found
    - getting the path itself is complicated for computations, so we just return
      the text

    Examples
    --------
    Get the output file for a data asset:
    >>> text = get_output_text('153419c7-09c4-43ce-9776-45bd63c50f72')
    """
    model = get_codeocean_model(asset_or_computation_id)
    if isinstance(asset_or_computation_id, codeocean.computation.Computation):
        computation = model
        if not computation.has_results:
            raise FileNotFoundError(
                f"Computation {computation.id} has no results: cannot fetch output file"
            )
        output_file = next(
            (
                item
                for item in get_codeocean_client()
                .computations.list_computation_results(computation_id=computation.id)
                .items
                if item.name == "output"
            ),
            None,
        )
        if output_file is None:
            raise FileNotFoundError(
                f"Output file not found for computation {computation.id}"
            )
        return requests.get(
            get_codeocean_client()
            .computations.get_result_file_download_url(computation.id, "output")
            .url
        ).text
    else:
        asset = get_data_asset_model(asset_or_computation_id)
        return (get_data_asset_source_dir(asset.id) / "output").read_text()


def is_data_asset_error(
    asset_id_or_model: str | uuid.UUID | codeocean.data_asset.DataAsset,
) -> bool:
    """Make a best-effort determination of whether a data asset is created from a
    computation that errored, based on the contents of the output file.

    - if no output file is found, returns True
    - if the asset is from the spike-sorting pipeline and the results do not contain an
      NWB, returns True
    - checks whether the output file contains certain text:
        - "Essential container in task exited",
        - "Out of memory.",
        - "Task failed to start - DockerTimeoutError",
        - "The CUDA error was:",
        - "Traceback (most recent call last):",
        - "Command error:",
        - "WARN: Killing running tasks",

    Examples
    --------

    >>> aind_session.is_data_asset_error('9eb51aaf-9b45-4bd9-8b43-85d7c2781ac7')
    True
    >>> aind_session.is_data_asset_error('153419c7-09c4-43ce-9776-45bd63c50f72')
    False
    """
    asset = get_data_asset_model(asset_id_or_model)
    try:
        output = get_output_text(asset)
    except FileNotFoundError:
        return True
    if is_output_error(output):
        return True
    source_dir = get_data_asset_source_dir(asset.id)
    if (
        is_output_file_from_sorting_pipeline(output)
        and next((source_dir / "nwb").glob("*.nwb*"), None) is None
    ):
        logger.debug(
            f"{asset.name} {asset.id} considered errored: results do not contain NWB file"
        )
        return True
    return False


def is_computation_error(
    computation_id_or_model: codeocean.computation.Computation,
) -> bool:
    """Make a best-effort determination of whether a computation errored. Should
    not be used with with runs that produce no output. Migrated from npc_lims.

    Computation `end_status` can give false-positives and return "succeeded", even
    though the pipeline errored. At least, this is true for the
    spike sorting pipeline.

    Initial checks are based on the computation metadata (if the state reports failed
    then it is considered errored):
        - if the computation `state` is not "completed" a `ValueError` is raised
        - if the computation `end_status` is not "succeeded", it is considered
          errored (we assume there aren't false-negatives)

    If `end_status` is "succeeded", then the output folder is checked for indications of error:
    - no files (or only nextflow and output files for pipeline runs)
    - the output file contains certain text:
        - "Essential container in task exited",
        - "Out of memory.",
        - "Task failed to start - DockerTimeoutError",
        - "The CUDA error was:",
        - "Traceback (most recent call last):",
        - "Command error:",
        - "WARN: Killing running tasks",

    >>> aind_session.is_computation_error("7646f92f-d225-464c-b7aa-87a87f34f408")
    True
    """
    computation = get_codeocean_model(computation_id_or_model, is_computation=True)

    def desc(computation: codeocean.computation.Computation) -> str:
        return f"Computation {computation.id} ({computation.name})"

    if computation.state != codeocean.computation.ComputationState.Completed:
        raise ValueError(
            f"{desc(computation)} is {computation.state}: cannot determine if errored"
        )
    if computation.state == codeocean.computation.ComputationState.Failed:
        logger.debug(
            f"{desc(computation)} considered errored: state is {computation.state}"
        )
        return True
    if computation.end_status != codeocean.computation.ComputationEndStatus.Succeeded:
        logger.debug(
            f"{desc(computation)} considered errored: end_status is {computation.end_status}"
        )
        return True
    if not computation.has_results:
        logger.debug(
            f"{desc(computation)} considered errored: has_results is {computation.has_results}"
        )
        return True

    # check if errored based on files in result
    computation_results = get_codeocean_client().computations.list_computation_results(
        computation_id=computation.id
    )
    result_item_names = sorted(item.name for item in computation_results.items)
    is_no_files = len(result_item_names) == 0
    is_pipeline_error = len(result_item_names) == 2 and result_item_names == [
        "nextflow",
        "output",
    ]
    is_capsule_error = len(result_item_names) == 1 and result_item_names == ["output"]
    if is_no_files or is_pipeline_error or is_capsule_error:
        logger.debug(
            f"{desc(computation)} suspected errored based on number of items in result: {result_item_names}"
        )
        return True

    try:
        output = get_output_text(computation)
    except FileNotFoundError:
        output = None
    if output:
        if is_output_error(output):
            return True
        if (
            is_output_file_from_sorting_pipeline(output)
            and "nwb" not in result_item_names
        ):
            logger.debug(
                f"{desc(computation)} considered errored: results do not contain NWB file"
            )
            return True
    return False


def is_output_file_from_sorting_pipeline(output: str) -> bool:
    return all(
        text in output.lower()
        for text in ("sorting", "kilosort", "N E X T F L O W".lower())
    )


def is_output_error(output_text: str) -> bool:
    """Check if an output file contains text that indicates an error occurred
    during capsule/pipeline run.

    Examples
    --------
    >>> aind_session.is_output_error(aind_session.get_output_text('5116b590-c240-4413-8a0f-1686659d13cc')) # DockerTimeoutError
    True
    >>> aind_session.is_output_error(aind_session.get_output_text('03b8a999-d1fb-4a27-b28f-7b880fbdef4b'))
    False
    """
    for error_text in (
        "Essential container in task exited",
        "Out of memory.",
        "Task failed to start - DockerTimeoutError",
        "The CUDA error was:",
        "Traceback (most recent call last):",
        "Command error:",
        "WARN: Killing running tasks",
    ):
        if error_text in output_text:
            if "CUDA" in error_text and is_output_file_from_sorting_pipeline(
                output_text
            ):
                logger.warning(
                    "output file has at least one CUDA error message, but some probes may still be usable"
                )
                continue
            else:
                logger.debug(
                    f"output file text indicates capsule/pipeline error: contains {error_text!r}"
                )
                return True
    return False


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
