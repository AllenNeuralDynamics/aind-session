# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## Unreleased

<small>[Compare with latest](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.16...HEAD)</small>

### Fixed

- Fix compatibility with older versions of codeocean sdk ([bd6c91a](https://github.com/allenneuraldynamics/aind-session/commit/bd6c91a8cf38693bd55b8aba5ee5770e4340cc6b) by bjhardcastle).
- Fix missing required sub-dependency ([2f15f53](https://github.com/allenneuraldynamics/aind-session/commit/2f15f53d8d6aac90a20b302168bd80e9b7b06cbb) by bjhardcastle).
- Fix comment ([6ef53d7](https://github.com/allenneuraldynamics/aind-session/commit/6ef53d7b8624415885cc79aede2b355cbd90c552) by bjhardcastle).

### Removed

- Remove pdm from Actions ([159f25c](https://github.com/allenneuraldynamics/aind-session/commit/159f25ca634770fcac5aa4fe1bd69286ef7a0895) by bjhardcastle).

<!-- insertion marker -->
## [v0.3.16](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.16) - 2025-03-11

<small>[Compare with v0.3.15](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.15...v0.3.16)</small>

## [v0.3.15](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.15) - 2025-01-17

<small>[Compare with v0.3.14](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.14...v0.3.15)</small>

### Added

- Add title search to subject assets ([5dcda7c](https://github.com/allenneuraldynamics/aind-session/commit/5dcda7c310e9aafdb71adccc84bff155afba5f8d) by bjhardcastle).
- Add subject metadata to smartspim IBL converter assets ([1a2d26e](https://github.com/allenneuraldynamics/aind-session/commit/1a2d26e3fe9e0dd4d82f9f1cf82946e924777eae) by bjhardcastle).

## [v0.3.14](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.14) - 2025-01-03

<small>[Compare with v0.3.13](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.13...v0.3.14)</small>

### Fixed

- Fix test ([562ce3a](https://github.com/allenneuraldynamics/aind-session/commit/562ce3a9895118253f2215f22cbf87745ef58653) by bjhardcastle).
- Fix type ([d288801](https://github.com/allenneuraldynamics/aind-session/commit/d2888010edf63d29b84e607127813703fb6df67d) by bjhardcastle).

## [v0.3.13](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.13) - 2024-12-11

<small>[Compare with v0.3.12](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.12...v0.3.13)</small>

## [v0.3.12](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.12) - 2024-12-10

<small>[Compare with v0.3.11](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.11...v0.3.12)</small>

### Added

- Add timing for debugging connection issue ([214841e](https://github.com/allenneuraldynamics/aind-session/commit/214841e9e212368834d64ac3011d68e202c4454c) by bjhardcastle).
- Add bucket and prefix util ([9bf2ec6](https://github.com/allenneuraldynamics/aind-session/commit/9bf2ec6bb27270ff0a2dc8003c6b7561b0f088de) by bjhardcastle).

### Fixed

- Fix 503 error wrapper to correctly raise after max retries exceeded ([c8d7d8a](https://github.com/allenneuraldynamics/aind-session/commit/c8d7d8a095df2f54c3b084dbf3ff8744cc6aa15a) by bjhardcastle).
- Fix waiting for files in created asset ([580ea57](https://github.com/allenneuraldynamics/aind-session/commit/580ea57e143f64b208757e4a3740b4bd3dfb24d6) by bjhardcastle).
- Fix tests ([6730881](https://github.com/allenneuraldynamics/aind-session/commit/673088190aaede834a6df55ebfd4a8a55671f72a) by bjhardcastle).
- Fix paths ([fa878da](https://github.com/allenneuraldynamics/aind-session/commit/fa878da7eed87b2916ff01ac081416a00b670287) by bjhardcastle).
- Fix variable name ([0583a48](https://github.com/allenneuraldynamics/aind-session/commit/0583a4844166fb138028217d729ca098e40c8c93) by bjhardcastle).

## [v0.3.11](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.11) - 2024-12-07

<small>[Compare with v0.3.10](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.10...v0.3.11)</small>

### Added

- Add temporary retry wrapper to docdb functions ([4e98ffc](https://github.com/allenneuraldynamics/aind-session/commit/4e98ffc07cd75bc0f2904a1c3bec4f7c1eea68f3) by bjhardcastle).
- Add `POST` to retry methods - `run_capsule()` was failing often ([d69fb1a](https://github.com/allenneuraldynamics/aind-session/commit/d69fb1aeea7937c7a17e36bcb6cf1d63125f0e34) by bjhardcastle).
- Add Smartspim Neuropixels extension ([ff91ef8](https://github.com/allenneuraldynamics/aind-session/commit/ff91ef8f7bdf316bd67e5af31e20944fb7e57ad1) by bjhardcastle).
- Add date arguments to `search_computations()` ([56e4f19](https://github.com/allenneuraldynamics/aind-session/commit/56e4f19f3a86aec767c3187db33b57cb6ce1a80d) by bjhardcastle).

### Fixed

- Fix temporary retry wrapper to docdb functions ([4beacc5](https://github.com/allenneuraldynamics/aind-session/commit/4beacc5c9dd6490169b0c64cf320ed406769f672) by bjhardcastle).
- Fix csv line endings ([0451b68](https://github.com/allenneuraldynamics/aind-session/commit/0451b68805c2608582fb91649f58b2f6eab4f6c5) by bjhardcastle).
- Fix imports ([4ffef26](https://github.com/allenneuraldynamics/aind-session/commit/4ffef26633318db805283202c55cc8886281eddd) by bjhardcastle).
- Fix sorting `Subject.sessions` ([adaf006](https://github.com/allenneuraldynamics/aind-session/commit/adaf006f41b0d43d3db6baadbfe5e52bc1ea334f) by bjhardcastle).
- Fix `Subject` repr to show ID as string ([32d8eb7](https://github.com/allenneuraldynamics/aind-session/commit/32d8eb7e9137f2df7f7e5964a86acac3f63ba530) by bjhardcastle).

## [v0.3.10](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.10) - 2024-11-08

<small>[Compare with v0.3.9](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.9...v0.3.10)</small>

### Fixed

- Fix test ([213a8fc](https://github.com/allenneuraldynamics/aind-session/commit/213a8fc4521d6aa061b14ede313bd661f71401dd) by bjhardcastle).

### Removed

- Remove confusing readme example ([6a28478](https://github.com/allenneuraldynamics/aind-session/commit/6a2847803b68a3799c116eea75bb93898dcc4c1f) by bjhardcastle).
- Remove retry on unauthorized status ([374211a](https://github.com/allenneuraldynamics/aind-session/commit/374211a43a0fb8b14ed3066dd0db886b25d28459) by bjhardcastle).

## [v0.3.9](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.9) - 2024-10-24

<small>[Compare with v0.3.8](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.8...v0.3.9)</small>

### Added

- Add `Retry` object to CodeOcean client ([b413827](https://github.com/allenneuraldynamics/aind-session/commit/b413827cb3ce47a7189d993814706440966e227a) by bjhardcastle).
- Add annotations for `Session` properties ([8e64780](https://github.com/allenneuraldynamics/aind-session/commit/8e647807bd3ccf1b6e9672a130f179d63e40590b) by bjhardcastle).

### Fixed

- Fix mypy `name-defined` error [skip CI] ([5ba0519](https://github.com/allenneuraldynamics/aind-session/commit/5ba05194ad641f95dd85fdb4f51255c7a3af9ee3) by bjhardcastle).

## [v0.3.8](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.8) - 2024-10-21

<small>[Compare with v0.3.7](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.7...v0.3.8)</small>

### Fixed

- Fix overload signature ([87fb4ca](https://github.com/allenneuraldynamics/aind-session/commit/87fb4ca342cf4aa24e98f227b14291f50538ab76) by bjhardcastle).

## [v0.3.7](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.7) - 2024-10-19

<small>[Compare with v0.3.6](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.6...v0.3.7)</small>

### Added

- Add function to get CO asset IDs from DocDB ([5259d18](https://github.com/allenneuraldynamics/aind-session/commit/5259d188dd13f6353407b1e349b83ac926ed6d63) by bjhardcastle).

## [v0.3.6](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.6) - 2024-10-17

<small>[Compare with v0.3.5](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.5...v0.3.6)</small>

### Fixed

- Fix docstring [skip CI] ([7c06c43](https://github.com/allenneuraldynamics/aind-session/commit/7c06c43bf5c2f2a8ac120c77f6d458e91d6c9ba7) by bjhardcastle).

## [v0.3.5](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.5) - 2024-10-17

<small>[Compare with v0.3.4](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.4...v0.3.5)</small>

### Fixed

- Fix modalities ([1613560](https://github.com/allenneuraldynamics/aind-session/commit/1613560123b3ced6b132f35b76b1bdab862e07e9) by bjhardcastle).

## [v0.3.4](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.4) - 2024-10-17

<small>[Compare with v0.3.3](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.3...v0.3.4)</small>

### Added

- Add `is_sorting_analyzer` property to sorted data asset ([f5df77f](https://github.com/allenneuraldynamics/aind-session/commit/f5df77f04576edc9ac57b0632205865bf796041d) by bjhardcastle).

### Fixed

- Fix readme example ([c8eea5c](https://github.com/allenneuraldynamics/aind-session/commit/c8eea5c7c37a06c6c5afff7b8c126d1600418c29) by bjhardcastle).
- Fix `sorter.names` ([8941342](https://github.com/allenneuraldynamics/aind-session/commit/894134288446e5f5ed5277063e2ffd8d25e0aead) by bjhardcastle).

## [v0.3.3](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.3) - 2024-10-16

<small>[Compare with v0.3.2](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.2...v0.3.3)</small>

### Added

- Add `Subject` ([43a0ead](https://github.com/allenneuraldynamics/aind-session/commit/43a0eadf9960319a5a261a3952a42b34587bec78) by bjhardcastle).

## [v0.3.2](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.2) - 2024-10-16

<small>[Compare with v0.3.1](https://github.com/allenneuraldynamics/aind-session/compare/v0.3.1...v0.3.2)</small>

### Added

- Add git checkout to workflow ([f8f6bf9](https://github.com/allenneuraldynamics/aind-session/commit/f8f6bf9110e662340d999fe0e21bfc5731b7736c) by bjhardcastle).

### Fixed

- Fix pytest in workflow ([79399c8](https://github.com/allenneuraldynamics/aind-session/commit/79399c8f0d85b159eb15a29bd8125a0add2f1f9a) by bjhardcastle).
- Fix editable install in workflow ([3a175ce](https://github.com/allenneuraldynamics/aind-session/commit/3a175ce20e10511393da815f1117e42a65b36a10) by bjhardcastle).

## [v0.3.1](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.3.1) - 2024-10-14

<small>[Compare with v0.2.5](https://github.com/allenneuraldynamics/aind-session/compare/v0.2.5...v0.3.1)</small>

### Added

- Add scheduled test workflow ([ea3e5e9](https://github.com/allenneuraldynamics/aind-session/commit/ea3e5e90cf1514924adc9d72e528570bcbdadc62) by bjhardcastle).
- Add doctest option flag ([854aec6](https://github.com/allenneuraldynamics/aind-session/commit/854aec6e61d326b142bdb4e9bcd87da8649dd983) by bjhardcastle).
- Add `has_results` filter for searching computations ([acb9283](https://github.com/allenneuraldynamics/aind-session/commit/acb92834a775f6671e789b27748a393f14036d5f) by bjhardcastle).

### Fixed

- Fix staticmethod cache ([59b3aa8](https://github.com/allenneuraldynamics/aind-session/commit/59b3aa807005a1763e0dd26daea402f4e7c12475) by bjhardcastle).

## [v0.2.5](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.2.5) - 2024-09-20

<small>[Compare with v0.2.4](https://github.com/allenneuraldynamics/aind-session/compare/v0.2.4...v0.2.5)</small>

### Added

- Add method for getting latest asset for particular sorter_name ([2f8df66](https://github.com/allenneuraldynamics/aind-session/commit/2f8df66a2a41c8cfea64a92d3ac9321a5a21b7c5) by bjhardcastle).

### Removed

- Remove `ecephys.sorted_data_asset` and add `ecephys.latest_ks25_sorted_data_asset` ([27ce5e1](https://github.com/allenneuraldynamics/aind-session/commit/27ce5e1e969cfd31ed21afab72fd81bf1fce3271) by bjhardcastle).

## [v0.2.4](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.2.4) - 2024-09-16

<small>[Compare with v0.2.3](https://github.com/allenneuraldynamics/aind-session/compare/v0.2.3...v0.2.4)</small>

### Added

- Add `ecephys.get_sorter_name()` Closes #9 ([4c9bc0f](https://github.com/allenneuraldynamics/aind-session/commit/4c9bc0f0cb1eec897c018e469dd83f4134f267f8) by Ben Hardcastle).

## [v0.2.3](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.2.3) - 2024-09-12

<small>[Compare with v0.2.2](https://github.com/allenneuraldynamics/aind-session/compare/v0.2.2...v0.2.3)</small>

### Added

- Add a lims namespace extension for legacy sessions ([4c32e9b](https://github.com/allenneuraldynamics/aind-session/commit/4c32e9b81830cd599f197a891ee1e77109b08e48) by bjhardcastle).

## [v0.2.2](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.2.2) - 2024-09-12

<small>[Compare with v0.2.1](https://github.com/allenneuraldynamics/aind-session/compare/v0.2.1...v0.2.2)</small>

### Added

- Add link to extensions documentation [skip CI] ([da7d217](https://github.com/allenneuraldynamics/aind-session/commit/da7d217dbf980ac983aea44f7eb7ef9f0300fb0a) by bjhardcastle).

### Fixed

- Fix TypeVar ([3eb4327](https://github.com/allenneuraldynamics/aind-session/commit/3eb4327c6c340ecf81f1cb4295a63c9680f253f7) by Ben Hardcastle).
- Fix explicit export of extension components (for type checking) ([cee71d9](https://github.com/allenneuraldynamics/aind-session/commit/cee71d93152ff0542de455da15b580df2c397a08) by bjhardcastle).

## [v0.2.1](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.2.1) - 2024-09-10

<small>[Compare with v0.1.22](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.22...v0.2.1)</small>

### Added

- Add documentation on using custom namespace extensions ([439e17b](https://github.com/allenneuraldynamics/aind-session/commit/439e17b085de9d4078c36de1e8e64ad6cca3d1ed) by bjhardcastle).

### Fixed

- Fix typing for core extensions ([adeebae](https://github.com/allenneuraldynamics/aind-session/commit/adeebae91e1c37d23f9136b46cc5aa06f873b082) by bjhardcastle).
- Fix type hint and docstring ([21dc76c](https://github.com/allenneuraldynamics/aind-session/commit/21dc76c0a92e535855ee85e3be42bf4aaa414270) by bjhardcastle).

### Removed

- Remove redundant `metadata` extension: closes #7 ([13618dd](https://github.com/allenneuraldynamics/aind-session/commit/13618dd8617663cf092f6e37e6daa6254de66a90) by bjhardcastle).

## [v0.1.22](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.22) - 2024-09-09

<small>[Compare with v0.1.21](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.21...v0.1.22)</small>

### Removed

- Remove upper bound on Python version: fixes #6 ([0b5e6d3](https://github.com/allenneuraldynamics/aind-session/commit/0b5e6d37552d108075b3df8cfb54836bdbdb724f) by bjhardcastle).

## [v0.1.21](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.21) - 2024-09-07

<small>[Compare with v0.1.20](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.20...v0.1.21)</small>

### Added

- Add better error handling from CodeOcean API ([4ed56c9](https://github.com/allenneuraldynamics/aind-session/commit/4ed56c9c19fea3073f378e5fa49f56babd0964db) by bjhardcastle).
- Add function for getting computation or asset model by ID ([c99e724](https://github.com/allenneuraldynamics/aind-session/commit/c99e724dbc5b13298b1fc847f12db75e98a4805c) by bjhardcastle).
- Add check for asset error, parallel of computation error: closes #4 ([41f92dd](https://github.com/allenneuraldynamics/aind-session/commit/41f92dd75d08e48fcb425a1f0a1514ccb7c2ef1f) by bjhardcastle).

### Fixed

- Fix function name ([03fdf97](https://github.com/allenneuraldynamics/aind-session/commit/03fdf970d4b9998e4043e1b3e1e3dc6362cece11) by bjhardcastle).
- Fix error message ([293f0cd](https://github.com/allenneuraldynamics/aind-session/commit/293f0cd3b78a5a4192843752baab029aa35ff4e6) by bjhardcastle).

## [v0.1.20](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.20) - 2024-09-03

<small>[Compare with v0.1.19](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.19...v0.1.20)</small>

### Fixed

- Fix missing key bug in some docdb entries ([732b863](https://github.com/allenneuraldynamics/aind-session/commit/732b863287d699857989f62ae7a00f51344b2ee8) by bjhardcastle).

## [v0.1.19](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.19) - 2024-08-28

<small>[Compare with v0.1.18](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.18...v0.1.19)</small>

### Added

- Add docdb utils and property on Session object ([77812b5](https://github.com/allenneuraldynamics/aind-session/commit/77812b5c41220303f063546f1b683fd87ddf6100) by bjhardcastle).

### Fixed

- Fix doctest [skip CI] ([ffd87ae](https://github.com/allenneuraldynamics/aind-session/commit/ffd87ae9ebf343b2769fc5b4b4d9534b8ded9be3) by Ben Hardcastle).

## [v0.1.18](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.18) - 2024-08-26

<small>[Compare with v0.1.17](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.17...v0.1.18)</small>

## [v0.1.17](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.17) - 2024-08-26

<small>[Compare with v0.1.16](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.16...v0.1.17)</small>

## [v0.1.16](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.16) - 2024-08-26

<small>[Compare with v0.1.15](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.15...v0.1.16)</small>

### Fixed

- Fix search capsule computations ([5ab0f46](https://github.com/allenneuraldynamics/aind-session/commit/5ab0f46efced34e7b370d42209d5fcc6c70b084a) by bjhardcastle).

## [v0.1.15](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.15) - 2024-08-26

<small>[Compare with v0.1.14](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.14...v0.1.15)</small>

### Added

- Add and use faster function for searching computations ([bd111b6](https://github.com/allenneuraldynamics/aind-session/commit/bd111b66a52cbd0c640877ab9efbe7e4bb51fe96) by bjhardcastle).

## [v0.1.14](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.14) - 2024-08-26

<small>[Compare with v0.1.13](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.13...v0.1.14)</small>

### Fixed

- Fix already running check on run_sorting ([147bbd3](https://github.com/allenneuraldynamics/aind-session/commit/147bbd39611b5ec9a17d60b80260f4e26c09b739) by bjhardcastle).

## [v0.1.13](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.13) - 2024-08-26

<small>[Compare with v0.1.12](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.12...v0.1.13)</small>

### Added

- Add ecephys `is_sorting` property ([6f967b6](https://github.com/allenneuraldynamics/aind-session/commit/6f967b6833fa903fd77e17db49bb8d7bb8e060a8) by bjhardcastle).

## [v0.1.12](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.12) - 2024-08-26

<small>[Compare with v0.1.11](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.11...v0.1.12)</small>

### Added

- Add output file error message ([3e4f391](https://github.com/allenneuraldynamics/aind-session/commit/3e4f391ab210897c5ebd98018890d04f000f1b32) by bjhardcastle).

## [v0.1.11](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.11) - 2024-08-26

<small>[Compare with v0.1.10](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.10...v0.1.11)</small>

### Added

- Add note about user secrets on ecephys trigger capsule ([13cf268](https://github.com/allenneuraldynamics/aind-session/commit/13cf2683466c791ee73fb22896deae616b547643) by bjhardcastle).

## [v0.1.10](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.10) - 2024-08-24

<small>[Compare with v0.1.9](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.9...v0.1.10)</small>

### Added

- Add ecephys session sorting fail bool ([54692aa](https://github.com/allenneuraldynamics/aind-session/commit/54692aa9b0bdde52d48f56f07391e37247738060) by bjhardcastle).

### Fixed

- Fix test ([e2537fa](https://github.com/allenneuraldynamics/aind-session/commit/e2537fac9820e8259b8c7dc7cbb13a6799a139c8) by bjhardcastle).

## [v0.1.9](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.9) - 2024-08-24

<small>[Compare with v0.1.8](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.8...v0.1.9)</small>

### Added

- Add ecephys run sorting pipline method ([9101678](https://github.com/allenneuraldynamics/aind-session/commit/910167874eda3c27bb576239419f5b4f04e67f9e) by bjhardcastle).
- Add ecephys `is_sorted_data_asset_error` ([5da3ac1](https://github.com/allenneuraldynamics/aind-session/commit/5da3ac17555f5dc3b744d79f3eb953c88b902dd0) by bjhardcastle).
- Add id-normalizing function ([c9eac12](https://github.com/allenneuraldynamics/aind-session/commit/c9eac1207ef8a6e329adbced99b11fb92c8c666e) by bjhardcastle).
- Add `is_computation_errored` ([a46d5d2](https://github.com/allenneuraldynamics/aind-session/commit/a46d5d2bb5f2aa7d56b120d466d6ad4ba2f9a49f) by bjhardcastle).
- Add action workflow [skip ci] ([3e7b349](https://github.com/allenneuraldynamics/aind-session/commit/3e7b34994cdf654b44fb9344de3ef7c9d8c75245) by bjhardcastle).

### Fixed

- Fix sorted probe names ([1b06f69](https://github.com/allenneuraldynamics/aind-session/commit/1b06f69f1757303e583a2b1ee7d48d52986aebed) by bjhardcastle).
- Fix unused-ignore with types-request workaround ([a73d637](https://github.com/allenneuraldynamics/aind-session/commit/a73d637a85cce303d6b313805d063479fb035edf) by bjhardcastle).
- Fix types-requests bug ([3e06a5d](https://github.com/allenneuraldynamics/aind-session/commit/3e06a5d6f179a4b41c157e82c98f2575d1db292c) by bjhardcastle).

## [v0.1.8](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.8) - 2024-08-19

<small>[Compare with v0.1.7](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.7...v0.1.8)</small>

### Added

- Add ttl_hash description ([7c5704d](https://github.com/allenneuraldynamics/aind-session/commit/7c5704d60a76a6e6f9dfed2a62097924781afcce) by bjhardcastle).
- Add readme to coverage report ([393e8d3](https://github.com/allenneuraldynamics/aind-session/commit/393e8d35e59d30cfbf8558726b6ff07e0a9daa8e) by bjhardcastle).
- Add `get_sessions()` example to readme [skip ci] ([5750544](https://github.com/allenneuraldynamics/aind-session/commit/575054412d285bdc172d0f2b6906151eca743c77) by bjhardcastle).

### Fixed

- Fix test ([89a7c6f](https://github.com/allenneuraldynamics/aind-session/commit/89a7c6f5a89737f2e0419d8ac7f2d0a7b07f7018) by bjhardcastle).
- Fix function description ([c836cea](https://github.com/allenneuraldynamics/aind-session/commit/c836ceae73b40276026d91ce96f4a7d9057c3bbe) by bjhardcastle).

### Removed

- Remove use of model as input to cached function ([96e73d0](https://github.com/allenneuraldynamics/aind-session/commit/96e73d08f651830702f621db884bc8f4f4ebbe78) by bjhardcastle).

## [v0.1.7](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.7) - 2024-08-18

<small>[Compare with v0.1.6](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.6...v0.1.7)</small>

### Added

- Add sorted_data_assets to ecephys ([bebd9ba](https://github.com/allenneuraldynamics/aind-session/commit/bebd9baaafa380ad3eac5a4c1b0012d28463a0c1) by bjhardcastle).
- Add doctests ([db626f3](https://github.com/allenneuraldynamics/aind-session/commit/db626f320d9104105bd103f34e51e52e72a60e48) by bjhardcastle).

### Removed

- Remove unused function ([3240a95](https://github.com/allenneuraldynamics/aind-session/commit/3240a95537b95fcadfd5b8b9aa567bfb903edf5c) by bjhardcastle).

## [v0.1.6](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.6) - 2024-08-17

<small>[Compare with v0.1.5](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.5...v0.1.6)</small>

### Added

- Add datetime property and comments on types ([b89baec](https://github.com/allenneuraldynamics/aind-session/commit/b89baec33ada300262bc6c884723825dd5c3dec7) by bjhardcastle).
- Add get_sessions function ([24284dc](https://github.com/allenneuraldynamics/aind-session/commit/24284dcd558b62172449828282a80d48baca5e32) by bjhardcastle).

## [v0.1.5](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.5) - 2024-08-17

<small>[Compare with v0.1.4](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.4...v0.1.5)</small>

### Added

- Add support for retrieving sorted probes in ecephys extension ([dec6ed7](https://github.com/allenneuraldynamics/aind-session/commit/dec6ed73ac4e4d4e8bf34cd43c5980b4768bb4eb) by bjhardcastle).

## [v0.1.4](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.4) - 2024-08-17

<small>[Compare with v0.1.3](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.3...v0.1.4)</small>

### Added

- Add folders ([2b9d6cd](https://github.com/allenneuraldynamics/aind-session/commit/2b9d6cd442a78d679915948aac1fbd0274dde92e) by bjhardcastle).
- Add clipped  and compressed dirs to ecephys modality ([eeadea9](https://github.com/allenneuraldynamics/aind-session/commit/eeadea9dfac7bc6adf2f156749a140230d05b11e) by bjhardcastle).
- Add list of modality names ([d526597](https://github.com/allenneuraldynamics/aind-session/commit/d5265975773638d28fdab08f5edd55217b72cdd8) by bjhardcastle).
- Add credentials check when getting codeocean client ([8761766](https://github.com/allenneuraldynamics/aind-session/commit/87617665c7a09e8d8e684396620400ca2c465ea7) by bjhardcastle).
- Add example of attaching asset ([b6f5a80](https://github.com/allenneuraldynamics/aind-session/commit/b6f5a804590ebe9128588ae7e3b6314148c4524f) by bjhardcastle).
- Add test resources ([0399005](https://github.com/allenneuraldynamics/aind-session/commit/039900523c0ae8b89baf16bb412ceef1a47b01d0) by bjhardcastle).
- Add sorting, equality, hashing + examples ([b035a69](https://github.com/allenneuraldynamics/aind-session/commit/b035a695d502278f9a4bc575284b7c4bdc5ab8bd) by bjhardcastle).

### Fixed

- Fix type ([85d21cc](https://github.com/allenneuraldynamics/aind-session/commit/85d21cc55b0c24c57edc03994d6b6083a333d1f7) by bjhardcastle).

## [v0.1.3](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.3) - 2024-08-15

<small>[Compare with v0.1.2](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.2...v0.1.3)</small>

## [v0.1.2](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.2) - 2024-08-15

<small>[Compare with v0.1.1](https://github.com/allenneuraldynamics/aind-session/compare/v0.1.1...v0.1.2)</small>

### Added

- Add metadata json parent path property ([ad49871](https://github.com/allenneuraldynamics/aind-session/commit/ad498710f33584611455b16b563971a54842e704) by Ben Hardcastle).

### Removed

- Remove typo ([2142214](https://github.com/allenneuraldynamics/aind-session/commit/214221461191e9f8a14f97cf366c1145583c3103) by Ben Hardcastle).

## [v0.1.1](https://github.com/allenneuraldynamics/aind-session/releases/tag/v0.1.1) - 2024-08-15

<small>[Compare with first commit](https://github.com/allenneuraldynamics/aind-session/compare/8087285e01582e65777de967a8cc4730d0fe9156...v0.1.1)</small>

### Added

- Add doctests to readme ([5124af0](https://github.com/allenneuraldynamics/aind-session/commit/5124af0147f292af1b4825560ad2125c1d67ef81) by bjhardcastle).
- Add ecephys and metadata extension ([8c159ef](https://github.com/allenneuraldynamics/aind-session/commit/8c159ef6df01f457f06208db59e61e904ad98662) by bjhardcastle).
- Add core Session object functionality and extension framework ([fcaae72](https://github.com/allenneuraldynamics/aind-session/commit/fcaae72ce0ceade810cec51aa368c7a0370f2c41) by bjhardcastle).

### Fixed

- Fix imports for <3.10 ([8c0a5ec](https://github.com/allenneuraldynamics/aind-session/commit/8c0a5ec511fda39ff35e8d2018ba5b4f7be0ef90) by bjhardcastle).

### Removed

- Remove 3.12 from test matrix ([2462017](https://github.com/allenneuraldynamics/aind-session/commit/2462017aff7267a77d9df4ba700b0f7581f58aa4) by Ben Hardcastle).
- Remove unused secrets ([3765b26](https://github.com/allenneuraldynamics/aind-session/commit/3765b2649460bc8f97ec2b9b45c92256d15f2001) by Ben Hardcastle).

