# aind-session

User-friendly tools for accessing paths, metadata and assets related to AIND sessions.

[![PyPI](https://img.shields.io/pypi/v/aind-session.svg?label=PyPI&color=blue)](https://pypi.org/project/aind-session/)
[![Python version](https://img.shields.io/pypi/pyversions/aind-session)](https://pypi.org/project/aind-session/)

[![Coverage](https://img.shields.io/codecov/c/github/AllenNeuralDynamics/aind-session?logo=codecov)](https://app.codecov.io/github/AllenNeuralDynamics/aind-session)
[![CI/CD](https://img.shields.io/github/actions/workflow/status/AllenNeuralDynamics/aind-session/publish.yml?label=CI/CD&logo=github)](https://github.com/AllenNeuralDynamics/aind-session/actions/workflows/publish.yml)
[![GitHub issues](https://img.shields.io/github/issues/AllenNeuralDynamics/aind-session?logo=github)](https://github.com/AllenNeuralDynamics/aind-session/issues)

# Overview
This package is meant to provide easy access to session information needed for common tasks, in CodeOcean and beyond. It joins the CodeOcean API (metadata about data assets, capsules, pipelines) with DocDB (metadata about session, subject, rig) and provides data at the level of a single experiment session, or a single subject (with zero or more sessions).

- when interacting with the CodeOcean API, it uses and returns objects from the [official Python library](https://github.com/codeocean/codeocean-sdk-python) - we will avoid duplicating functionality provided by that package, except to make convenience functions with assumptions baked-in (for example, getting a client with environment variables and a default domain; finding all the assets for a particular session)
- the core `Session` class should have a minimal set of methods and attributes that are common to sessions from all platforms - it should be fast to initialize and not do unnecessary work
- extensions provide additional functionality (e.g. for specific modalities,
  metadata, databases) - at the moment, this is implemented via registration of
  namespaces ([like
  Pandas](https://pandas.pydata.org/docs/development/extending.html)), which
  allows for extending without subclassing (for examples, see [extensions](https://github.com/AllenNeuralDynamics/aind-session/blob/main/src/aind_session/extensions))
- when searching for session data or information, methods should be exhaustive: for example, as naming conventions change, this package should support current and previous versions of names
- when searching is unsuccessful, as much information as possible should be provided to the user via logging messages and exceptions, so they can understand the reasons for failure

# Usage

## User secrets
Credentials are required for:
  - AWS
    - in a capsule, use the `AWS Assumable Role - aind-codeocean-user` secret
    - alternatively, environment variables or a config file will
      be found automatically (see [boto3 docs](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html))
  - CodeOcean API
    - an access token is required with at least `Datasets: Read` scope (see
      [CodeOcean
      docs](https://docs.codeocean.com/user-guide/code-ocean-api/authentication)
      on how to create one)
    - in a capsule, this can be found under the `API credentials` secret
    - alternatively, `CODE_OCEAN_API_TOKEN` is the preferred environment variable name 
        - if not found, the first environment variable with a value starting with `COP_` is used (case-insensitive)
      - the domain name defaults to `https://codeocean.allenneuraldynamics.org`, but can be overridden with a `CODE_OCEAN_DOMAIN` environment variable

For development, environment variables can be provided in a `.env` file in the project root directory or the user's home directory.

## Install
```bash
pip install aind_session
```

## Python
```python
>>> import aind_session

# Common attributes available for all sessions:
>>> session = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
>>> session.platform
'ecephys'
>>> session.subject_id
'676909'
>>> session.dt
datetime.datetime(2023, 12, 13, 13, 43, 40)
>>> len(session.data_assets)            # doctest: +SKIP
42
>>> session.is_uploaded
True
>>> session.raw_data_asset.id
'16d46411-540a-4122-b47f-8cb2a15d593a'
>>> session.raw_data_dir.as_posix()
's3://aind-ephys-data/ecephys_676909_2023-12-13_13-43-40'
>>> session.modalities
('behavior', 'behavior_videos', 'ecephys')
>>> session.docdb.keys()
dict_keys(['_id', 'acquisition', 'created', 'data_description', 'describedBy', 'external_links', 'instrument', 'last_modified', 'location', 'metadata_status', 'name', 'procedures', 'processing', 'rig', 'schema_version', 'session', 'subject'])
>>> session.docdb['subject']['genotype']
'Pvalb-IRES-Cre/wt;Ai32(RCL-ChR2(H134R)_EYFP)/wt'

# Additional functionality in namespace extensions:
>>> session.ecephys.is_sorted
True
>>> latest_asset = session.ecephys.sorter.kilosort2_5.sorted_data_assets[-1]
>>> latest_asset.name                  # doctest: +SKIP
'ecephys_676909_2023-12-13_13-43-40_sorted_2024-03-01_16-02-45'

# Objects refer to the original session, regardless of how they were created:
>>> a = aind_session.Session('ecephys_676909_2023-12-13_13-43-40')
>>> b = aind_session.Session('ecephys_676909_2023-12-13_13-43-40_sorted_2024-03-01_16-02-45')
>>> assert a == b, "Objects are equal if they refer to the same session ID"

# Objects are also hashable and sortable (by their ID)
```

Search for session objects by subject ID, platform, date:
```python
>>> import aind_session

>>> sessions: tuple[aind_session.Session, ...] = aind_session.get_sessions(subject_id=676909)
>>> sessions[0].platform
'behavior'
>>> sessions[0].date
'2023-10-24'

# Filter sessions by platform:
>>> aind_session.get_sessions(subject_id=676909, platform='ecephys')[0].platform
'ecephys'

# Filter sessions by date (most common formats accepted):
>>> a = aind_session.get_sessions(subject_id=676909, date='2023-12-13')
>>> b = aind_session.get_sessions(subject_id=676909, date='2023-12-13_13-43-40')
>>> c = aind_session.get_sessions(subject_id=676909, date='2023-12-13 13:43:40')
>>> d = aind_session.get_sessions(subject_id=676909, date='20231213')
>>> e = aind_session.get_sessions(subject_id=676909, date='20231213_134340')
>>> a == b == c == d == e
True

# Filter sessions by start or end date (can be open on either side):
>>> aind_session.get_sessions(subject_id=676909, start_date='2023-12-13')
(Session('ecephys_676909_2023-12-13_13-43-40'), Session('ecephys_676909_2023-12-14_12-43-11'))
>>> aind_session.get_sessions(subject_id=676909, start_date='2023-12-13', end_date='2023-12-14_10-00-00')
(Session('ecephys_676909_2023-12-13_13-43-40'),)

```

# Development
See instructions in [CONTRIBUTING.md](https://github.com/AllenNeuralDynamics/aind-session/blob/main/CONTRIBUTING.md) and the [original template](https://github.com/AllenInstitute/copier-pdm-npc/blob/main/README.md)
