# aind-session

User-friendly tools for accessing paths, metadata and assets related to AIND sessions.

[![PyPI](https://img.shields.io/pypi/v/aind-session.svg?label=PyPI&color=blue)](https://pypi.org/project/aind-session/)
[![Python version](https://img.shields.io/pypi/pyversions/aind-session)](https://pypi.org/project/aind-session/)

[![Coverage](https://img.shields.io/codecov/c/github/AllenNeuralDynamics/aind-session?logo=codecov)](https://app.codecov.io/github/AllenNeuralDynamics/aind-session)
[![CI/CD](https://img.shields.io/github/actions/workflow/status/AllenNeuralDynamics/aind-session/publish.yml?label=CI/CD&logo=github)](https://github.com/AllenNeuralDynamics/aind-session/actions/workflows/publish.yml)
[![GitHub issues](https://img.shields.io/github/issues/AllenNeuralDynamics/aind-session?logo=github)](https://github.com/AllenNeuralDynamics/aind-session/issues)

## *Under development!*
Please check this out and make feature requests, but don't rely on the API to remain stable just yet..


# Aim
This package is meant to provide easy access to session-related stuff required for common tasks in CodeOcean and beyond. 

- when interacting with the CodeOcean API, it uses and returns objects from the [official Python library](https://github.com/codeocean/codeocean-sdk-python) - we will avoid duplicating functionality provided by that package, except to make convenience functions with assumptions baked-in (for example, getting a client with environment variables and a default domain; finding all the assets for a particular session)
- the core `Session` class should have a minimal set of methods and attributes that are common to sessions from all platforms - it should be fast to initialize and not do unnecessary work
- extensions provide additional functionality (e.g. for specific modalities, metadata, databases) - at the moment, this is implemented via registration of namespaces ([like Pandas](https://pandas.pydata.org/docs/development/extending.html)), which allows for extending without subclassing
- when searching for session data or information, methods should be exhaustive: for example, as naming conventions change, this package should support current and previous versions of names
- when searching is unsuccessful, as much information as possible should be provided to the user via logging messages and exceptions, so they can understand the reasons for failure

# Usage

## User secrets
Credentials are required for:
  - S3
    - using the "assumable role" in CodeOcean should suffice
    - alternatively, access keys as environment variables or in a config file will be found by `boto3` (see [docs](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html))
  - CodeOcean API
    - an access token is required with at least "Datasets - Read" scope:
      - see CodeOcean's [docs](https://docs.codeocean.com/user-guide/code-ocean-api/authentication) on how to create a token
      - `CODE_OCEAN_API_TOKEN` is the preferred environment variable name 
      - if not found, the first environment variable with a value starting `COP_` is used (case-insensitive)
    - domain name defaults to `https://codeocean.allenneuraldynamics.org`, but can be overridden by setting `CODE_OCEAN_DOMAIN`

For development, environment variables can be provided in a `.env` file in the project root directory or the user's home directory.

## Install
```bash
pip install aind_session
```

## Python
```python
>>> from aind_session import Session

# Common attributes available for all sessions:
>>> session = Session('ecephys_676909_2023-12-13_13-43-40')
>>> session.platform
'ecephys'
>>> session.subject_id
'676909'
>>> session.dt
datetime.datetime(2023, 12, 13, 13, 43, 40)
>>> session.raw_data_asset.id
'16d46411-540a-4122-b47f-8cb2a15d593a'
>>> session.raw_data_dir.as_posix()
's3://aind-ephys-data/ecephys_676909_2023-12-13_13-43-40'

# Additional functionality in namespace extensions:
>>> session.metadata.subject['genotype']
'Pvalb-IRES-Cre/wt;Ai32(RCL-ChR2(H134R)_EYFP)/wt'
>>> session.ecephys.sorted_data_asset.name
'ecephys_676909_2023-12-13_13-43-40_sorted_2024-03-01_16-02-45'


```

# Development
See instructions in [CONTRIBUTING.md](https://github.com/AllenNeuralDynamics/aind-session/blob/main/CONTRIBUTING.md) and the [original template](https://github.com/AllenInstitute/copier-pdm-npc/blob/main/README.md)
