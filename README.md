# aind-session

User-friendly tools for accessing paths, metadata and assets related to AIND sessions.

[![PyPI](https://img.shields.io/pypi/v/aind-session.svg?label=PyPI&color=blue)](https://pypi.org/project/aind-session/)
[![Python version](https://img.shields.io/pypi/pyversions/aind-session)](https://pypi.org/project/aind-session/)

[![Coverage](https://img.shields.io/codecov/c/github/AllenNeuralDynamics/aind-session?logo=codecov)](https://app.codecov.io/github/AllenNeuralDynamics/aind-session)
[![CI/CD](https://img.shields.io/github/actions/workflow/status/AllenNeuralDynamics/aind-session/publish.yml?label=CI/CD&logo=github)](https://github.com/AllenNeuralDynamics/aind-session/actions/workflows/publish.yml)
[![GitHub issues](https://img.shields.io/github/issues/AllenNeuralDynamics/aind-session?logo=github)](https://github.com/AllenNeuralDynamics/aind-session/issues)

# Usage
```bash
conda create -n aind_session python>=3.9
conda activate aind_session
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
>>> session.raw_data_folder.as_posix()
's3://aind-ephys-data/ecephys_676909_2023-12-13_13-43-40'

# Additional functionality in namespace extensions:
>>> session.metadata.subject['genotype']
'Pvalb-IRES-Cre/wt;Ai32(RCL-ChR2(H134R)_EYFP)/wt'
>>> session.ecephys.sorted_data_asset.name
'ecephys_676909_2023-12-13_13-43-40_sorted_2024-03-01_16-02-45'


```

# Development
See instructions in https://github.com/AllenNeuralDynamics/aind-session/CONTRIBUTING.md and the original template: https://github.com/AllenInstitute/copier-pdm-npc/blob/main/README.md