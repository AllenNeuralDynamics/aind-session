from __future__ import annotations

import functools
import logging

import upath

logger = logging.getLogger(__name__)

S3_DATA_BUCKET_NAMES = (
    "codeocean-s3datasetsbucket-1u41qdg42ur9",
    "aind-private-data-prod-o5171v",
    "aind-open-data-prod-o5171v",
    "aibs-behavior-data",
    "aind-ephys-data",
    "aind-ophys-data",
)
"""Known S3 bucket names for data associated with CodeOcean assets."""


@functools.cache
def get_source_dir_by_name(name: str, ttl_hash: int | None = None) -> upath.UPath:
    """Checks known S3 buckets for a dir with the given name.

    - raises `FileNotFoundError` if the dir is not found

    Examples
    --------
    >>> get_source_dir_by_name('ecephys_676909_2023-12-13_13-43-40').as_posix()
    's3://aind-ephys-data/ecephys_676909_2023-12-13_13-43-40'
    """
    del ttl_hash  # only used for functools.cache

    for s3_bucket in S3_DATA_BUCKET_NAMES:
        path = upath.UPath(f"s3://{s3_bucket}/{name}")
        if path.exists():
            logger.debug(f"Found dir matching {name!r} in {path.parent.as_posix()}")
            return path
    raise FileNotFoundError(f"No dir named {name!r} found in known data buckets on S3")


if __name__ == "__main__":
    from aind_session import testmod

    testmod()
