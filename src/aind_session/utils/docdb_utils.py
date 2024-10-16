from __future__ import annotations

import functools
import logging
import uuid
from typing import Any

import aind_data_access_api.document_db

import aind_session.utils.codeocean_utils

logger = logging.getLogger(__name__)


@functools.cache
def get_docdb_api_client(**kwargs) -> aind_data_access_api.document_db.MetadataDbClient:
    """
    Return a MetadataDbClient instance, passing any kwargs supplied.

    If not supplied, the following defaults are used:
        host: "api.allenneuraldynamics.org"
        database: "metadata_index"
        collection: "data_assets"
    """
    kwargs.setdefault("host", "api.allenneuraldynamics.org")
    kwargs.setdefault("database", "metadata_index")
    kwargs.setdefault("collection", "data_assets")
    return aind_data_access_api.document_db.MetadataDbClient(**kwargs)


@functools.cache
def get_subject_docdb_records(
    subject_id: str | int,
    ttl_hash: int | None = None,
) -> tuple[dict[str, Any], ...]:
    """
    Retrieve all records from the DocumentDB "data_assets" collection that are
    associated with a given subject_id. Records are sorted by ascending creation time.

    Examples
    --------
    >>> records = get_subject_docdb_records(676909)
    >>> records[0].keys()       # doctest: +SKIP
    dict_keys(['_id', 'acquisition', 'created', 'data_description', 'describedBy', 'external_links', 'instrument', 'last_modified', 'location', 'metadata_status', 'name', 'procedures', 'processing', 'rig', 'schema_version', 'session', 'subject'])
    """
    del ttl_hash
    records = get_docdb_api_client().retrieve_docdb_records(
        filter_query={
            "subject.subject_id": str(subject_id),
        },
        sort={"created": 1},
    )
    logger.debug(
        f"Retrieved {len(records)} records for subject {subject_id} from DocumentDB"
    )
    return tuple(records)


@functools.cache
def get_docdb_record(
    data_asset_name_or_id: str | uuid.UUID,
    ttl_hash: int | None = None,
) -> dict[str, Any]:
    """
    Retrieve a single record from the DocumentDB "data_assets" collection that has the
    given data asset name or, if a UUID is supplied, corresponds to the given data asset ID.

    **note: assets are currently (2024/08) incomplete in DocumentDB:** if none
    are found, a workaround using the CodeOcean API is used

    - if multiple records are found, the most-recently created record is returned
    - if no record is found, an empty dict is returned

    Examples
    --------

    Get a record by data asset name (typically a session ID):
    >>> record = get_docdb_record("ecephys_676909_2023-12-13_13-43-40")
    >>> assert record
    >>> record.keys()       # doctest: +SKIP
    dict_keys(['_id', 'acquisition', 'created', 'data_description', 'describedBy', 'external_links', 'instrument', 'last_modified', 'location', 'metadata_status', 'name', 'procedures', 'processing', 'rig', 'schema_version', 'session', 'subject'])

    Get a record by data asset ID:
    >>> assert get_docdb_record('16d46411-540a-4122-b47f-8cb2a15d593a')
    >>> assert get_docdb_record('7c45df9f-7c52-469f-9574-0b337ea838f4') # one external_links
    >>> assert get_docdb_record('282063a7-943e-4590-bbb6-507da5df9ef8') # multiple external_links
    >>> assert get_docdb_record('47308d52-98dc-42fd-995e-1ac58a686fd1') # legacy external_links format
    """
    del ttl_hash
    asset_id = asset_name = None
    try:
        asset_id = aind_session.utils.codeocean_utils.get_normalized_uuid(
            data_asset_name_or_id
        )
    except ValueError:
        asset_name = str(data_asset_name_or_id)
    if asset_id:
        # retrieve records by asset ID
        records = get_docdb_api_client().retrieve_docdb_records(
            filter_query={"external_links.Code Ocean": asset_id},
            sort={"created": 1},
        )
        if len(records) > 0:
            if len(records) > 1:
                logger.info(
                    f"Multiple records found for {asset_id} in DocumentDB: returning most-recently created"
                )
                assert (
                    records[-1]["created"] > records[0]["created"]
                ), "records are not sorted by creation time"
            return records[-1]

        if len(records) == 0:
            logger.debug(
                f"No records found matching {asset_id} in DocumentDB, however records are currently incomplete (2024-08)."
                " Getting asset name from CodeOcean API, then looking up DocumentDB record by name instead."
            )
            try:
                asset_name = aind_session.get_data_asset_model(asset_id).name
            except Exception:
                logger.info(f"{asset_id} does not exist in CodeOcean")
                return {}

    # retrieve records by name
    assert asset_name is not None
    records = get_docdb_api_client().retrieve_docdb_records(
        filter_query={
            "name": asset_name,
        },
        sort={"created": 1},
    )
    if len(records) == 0:
        logger.info(f"No records found for {asset_name!r} in DocumentDB")
        return {}
    if len(records) > 1:
        logger.info(
            f"Multiple records found for {asset_name!r} in DocumentDB: returning most-recently created"
        )
        assert (
            records[-1]["created"] > records[0]["created"]
        ), "records are not sorted by creation time"
    return records[-1]


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
