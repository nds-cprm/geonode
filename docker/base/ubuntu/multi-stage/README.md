# GeoNode base images — multi-stage, one Dockerfile for every Ubuntu release

A multi-stage alternative to the single-stage `docker/base/ubuntu/<release>/Dockerfile`. One `Dockerfile`
builds the base image of every supported Ubuntu LTS release, and a directory per release holds what
changes from one release to the other. The final image has no compilers, headers or packaging tools. It
keeps the same paths as the single-stage images and checks itself with a smoke test at the end of the
build.

| `UBUNTU_RELEASE` (directory) | Ubuntu | Python | GDAL | GeoNode | `EXTRA_BUILD_PACKAGES` | `POSTGRESQL_CLIENT_VERSION` |
|---|---|---|---|---|---|---|
| `26` (default) | 26.04 | 3.14 | 3.12.2 | master | `libopenblas-dev libcrypt-dev` (default): numpy 1.26 has no wheel for Python 3.14; `crypt.h` for uWSGI | 18 (default) |
| `24` | 24.04 | 3.12 | 3.8.4 | 5.0.x | `libmemcached-dev`: pylibmc | 15 |

The GDAL Python bindings pinned by GeoNode must match the `libgdal` of the Ubuntu release, so each release
pairs with one GeoNode line.

## At a glance

Figures of the linux/arm64 builds, compared with the published single-stage images (linux/amd64).
Vulnerabilities come from Trivy 0.76.2, with each CVE counted once per image at its highest severity.

| | 24.04 single-stage | 24.04 `release` | 24.04 `devel` | 26.04 single-stage | 26.04 `release` | 26.04 `devel` |
|---|---|---|---|---|---|---|
| Size | 1.44 GB | **570 MB** | 1.23 GB | 1.66 GB | **666 MB** | 1.43 GB |
| Debian packages | 697 | 241 | 393 | 749 | 246 | 432 |
| Compilers / `-dev` packages | yes / 86 | **no / 1** | yes / 79 | yes / 116 | **no / 0** | yes / 107 |
| Vulnerabilities (critical / high) | 3,475 (42 / 760) | **111 (0 / 2)** | 538 (3 / 91) | 3,772 (43 / 794) | **97 (0 / 2)** | 241 (3 / 29) |
| ...in OS packages | 3,468 | 108 (0 / 0) | 536 | 3,750 | 93 (0 / 0) | 238 |
| OS packages with a pending fix | 22 | 0 | 0 | 27 | 0 | 0 |
| setuid/setgid binaries | 15 | 13 | 13 | 14 | 12 | 12 |
| GDAL bindings with `gdal_array` | no | yes | yes | no | yes | yes |
| GDAL bindings for the system Python | yes | no | no | yes | no | no |

The `devel` images are `release` plus the compilers and `-dev` packages of the `build` stage. Their extra
vulnerabilities come from those packages (mostly `linux-libc-dev`), so production should use `release`.

**Test suite.** A GeoNode image built on top of the linux/arm64 `release` images of this directory, from
the root `Dockerfile` with only its `FROM` changed, ran the GeoNode CI test groups on 22/11/2026 (see [RELATORIO_TESTES_GEONODE.md](RELATORIO_TESTES_GEONODE.md),
in Portuguese):

| Base | GeoNode | Tests | Result |
|---|---|---|---|
| `ubuntu-24.04-pg15` | 5.0.x | 1,527 | all 7 groups pass |
| `ubuntu-26.04-pg18` | master | 2,046 | 1 error, caused by the test environment (`test_map_default_thumb`, see "Known points") |

On 26.04 the `security` group passed on the second attempt: on the first one the stack did not start,
because Django connected while the emulated `geonode/postgis` container was restarting after initializing
the database. The results match the earlier runs, made with per-release Dockerfiles that still installed
the system Python GDAL bindings, so removing them changed no test result.

**Unified build.** Images built from this directory for linux/amd64 and linux/arm64, both targets, both
releases, on 22/11/2026 (Podman 6.1.4 on an arm64 Mac, amd64 under QEMU). All four tags were built
as manifest lists, and the smoke test passed on all eight images: at the end of each build stage, and
again on each architecture pulled from the manifest list (19 checks on 24.04, 17 on 26.04). The arm64
images have the same package counts and the same vulnerabilities as the figures above.

| Tag | amd64 | arm64 | Smoke test |
|---|---|---|---|
| `ubuntu-24.04-pg15` | 546 MB | 570 MB | ✅ both |
| `ubuntu-24.04-pg15-devel` | 1.25 GB | 1.23 GB | ✅ both |
| `ubuntu-26.04-pg18` | 659 MB | 666 MB | ✅ both |
| `ubuntu-26.04-pg18-devel` | 1.47 GB | 1.43 GB | ✅ both |

Sizes are the image sizes Podman reports for each architecture of the manifest list
(`podman image inspect --format '{{.Size}}'`, decimal units as in `podman images`); the manifest list
itself shows as 1.1 kB. The 24.04 figures are those of the images rebuilt with `get-runtime-packages`.

## Layout

| Path | Purpose |
|---|---|
| `Dockerfile` | The multi-stage build, shared by every release |
| `smoke-test` | Checks a built image. The image has it as `/usr/local/bin/geonode-base-smoke-test`, and the `runtime` and `devel` stages run it at the end |
| `get-runtime-packages` | Lists the Ubuntu packages that provide the shared libraries of the virtualenv binaries (found with `ldd` and `dpkg -S`). The `build` stage runs it, and `runtime` installs the list; `--help` shows the usage |
| `<release>/requirements.txt` | Python packages compiled into the virtualenv: the packages pinned by the matching GeoNode line that have no wheel for the Python of that release, plus `invoke` and `sherlock` |
| `geonode-tests` | Runs the GeoNode CI test suite on a GeoNode image built on top of a base image (see "Testing a base image") |
| `RELATORIO_TESTES_GEONODE.md` | Test report (in Portuguese) |

GDAL is not listed in `requirements.txt`. The bindings must match the system `libgdal`, so the Dockerfile
installs `GDAL==$(gdal-config --version)`. It installs `numpy` first, so the bindings get `gdal_array`.

The other per-release settings are build arguments (see "Build arguments"). Their defaults are those of
Ubuntu 26.04. An empty `EXTRA_BUILD_PACKAGES` only prints a warning; an empty or non-numeric
`POSTGRESQL_CLIENT_VERSION` fails the build.

The image keeps `requirements.txt` and a `build-info` file in `/etc/geonode-base/`. `build-info` records
the Ubuntu release, the `ubuntu` image tag and the PostgreSQL client of the build.

## Stages and targets

```
build ──(virtualenv + list of runtime libraries)──► runtime ──► devel   = runtime + compilers and -dev packages
                                                       └──────► release = runtime  (last stage: default target)
```

| Stage | Content |
|---|---|
| `build` | Checks that the `ubuntu` image is of release `UBUNTU_RELEASE`. Installs the compilers and `-dev` packages and builds `/usr/src/venv` from `<release>/requirements.txt` and the GDAL bindings. Then lists, with `ldd` and `dpkg -S`, the Ubuntu packages that provide the shared libraries the virtualenv uses |
| `runtime` | The virtualenv, only those runtime libraries, and the tools GeoNode uses: `gdal-bin`, `postgresql-client`, `gettext`, `cron`, `git`, `curl`, `wget`, `zip`/`unzip`, `libmagic1`. No GDAL bindings for the system Python. Ends with the smoke test |
| `devel` | `runtime` plus the compilers and `-dev` packages of `build`, for debugging and for projects that compile packages without wheels. Ends with the smoke test |
| `release` | `runtime`. It is the last stage, so a plain `docker build` produces it |

The paths are the same as in the single-stage images: `/usr/src/venv` on the `PATH`,
`/usr/local/bin/invoke` and `/usr/src/geonode`. The GeoNode and geonode-project Dockerfiles therefore
work unchanged. The image keeps the root user and defines no `ENTRYPOINT`.

## Building

Run these from the root of the repository. Docker and Podman take the same commands, and BuildKit is not
required. The defaults build Ubuntu 26.04; for 24.04, pass its three values. `--target` picks the stage.

Suggested tags put both versions in the name: `ubuntu-<UBUNTU_IMAGE_TAG>-pg<POSTGRESQL_CLIENT_VERSION>` for
`release`, with `-devel` appended for `devel`.

```bash
# Ubuntu 26.04 (GeoNode master), PostgreSQL client 18: the defaults
docker build --target release -t geonode/geonode-base:ubuntu-26.04-pg18 docker/base/ubuntu/multi-stage
docker build --target devel -t geonode/geonode-base:ubuntu-26.04-pg18-devel docker/base/ubuntu/multi-stage

# Ubuntu 24.04 (GeoNode 5.0.x), PostgreSQL client 15
docker build --target release --build-arg UBUNTU_RELEASE=24 \
  --build-arg EXTRA_BUILD_PACKAGES="libmemcached-dev" --build-arg POSTGRESQL_CLIENT_VERSION=15 \
  -t geonode/geonode-base:ubuntu-24.04-pg15 docker/base/ubuntu/multi-stage
docker build --target devel --build-arg UBUNTU_RELEASE=24 \
  --build-arg EXTRA_BUILD_PACKAGES="libmemcached-dev" --build-arg POSTGRESQL_CLIENT_VERSION=15 \
  -t geonode/geonode-base:ubuntu-24.04-pg15-devel docker/base/ubuntu/multi-stage

# Ubuntu 24.04 for a PostgreSQL 17 database, on a dated ubuntu image, with Podman
podman build --target release --build-arg UBUNTU_RELEASE=24 --build-arg UBUNTU_IMAGE_TAG=noble-20260101 \
  --build-arg EXTRA_BUILD_PACKAGES="libmemcached-dev" --build-arg POSTGRESQL_CLIENT_VERSION=17 \
  -t geonode/geonode-base:ubuntunoble-20260101-pg17 docker/base/ubuntu/multi-stage
```

To build both architectures under one tag (a manifest list):

```bash
# Podman: local manifest list; push it with "podman manifest push"
podman build --platform linux/amd64,linux/arm64 --manifest geonode/geonode-base:ubuntu-26.04-pg18 \
  --target release docker/base/ubuntu/multi-stage

# Docker: buildx, pushed to the registry
docker buildx build --platform linux/amd64,linux/arm64 --target release \
  -t geonode/geonode-base:ubuntu-26.04-pg18 --push docker/base/ubuntu/multi-stage
```

A build host of another architecture builds the foreign one under QEMU emulation. It works, but it is
several times slower, especially on 26.04, which compiles numpy.

### Build arguments

| Argument | Default | Effect |
|---|---|---|
| `UBUNTU_RELEASE` | `26` | Release directory whose `requirements.txt` is used |
| `UBUNTU_IMAGE_TAG` | `<UBUNTU_RELEASE>.04` | Tag of the `ubuntu` image of every stage, to pin a dated build or another tag of the same release (e.g. `noble-20260101`). The first `RUN` of `build` reads `/etc/os-release` and fails if the image is not Ubuntu `<UBUNTU_RELEASE>.x`, so the files of one release never go into an image of another |
| `EXTRA_BUILD_PACKAGES` | `libopenblas-dev libcrypt-dev` (26) | Build packages the release needs for its `requirements.txt`, installed in `build` and `devel` together with `BUILD_PACKAGES`. Pass `libmemcached-dev` for 24. If empty, the build prints a warning and goes on |
| `POSTGRESQL_CLIENT_VERSION` | `18` | Major version of `postgresql-client` (`psql`, `pg_dump`, `pg_restore`). It must match the database (see below); pass `15` for 24. The build fails if it is empty or not a number |
| `BUILD_PACKAGES` | compilers and `-dev` packages common to every release | Installed in `build` and `devel` |

### PostgreSQL client version and tags

GeoNode's backup and restore tool (`geonode.br`) uses the `pg_dump` and `pg_restore` of the image, so the
client must have the **same major version as the database**. `pg_dump` refuses to dump a newer server,
and a dump made by a newer `pg_dump` may not restore into an older server: `pg_dump` 17, for example,
already emits `SET transaction_timeout`, which PostgreSQL 15 rejects. Build one image per client version,
with the version in the tag, so each deployment picks the image of its database.

The client comes from the PostgreSQL apt repository (PGDG) of the Ubuntu release itself (`noble-pgdg`,
`resolute-pgdg`), configured with **priority 100**, so it only provides what Ubuntu lacks
(`postgresql-client-NN`). When Ubuntu ships the requested client (18 on 26.04), the Ubuntu package is
used. The pin matters because PGDG also ships newer GDAL, PROJ, GEOS and `libpq` builds (GDAL 3.13 at the
time of writing). Without it, an `apt-get install` or `upgrade` in a derived image would replace the
`libgdal` the bindings were built against.

One exception: `libpq5` and `libpq-dev` always come from PGDG, at priority 600. `postgresql-client-NN`
depends on `libpq5 (>= NN)`, which the Ubuntu `libpq5` may not satisfy (16 on 24.04 with client 17 or 18:
apt cannot install the client). PGDG ships a single `libpq5`, built from the latest stable
PostgreSQL (19 at the time of writing), whatever the client version. The soname is still `libpq.so.5`, and
the PGDG FAQ states that "libpq5 is compatible with older versions"
([Apt/FAQ](https://wiki.postgresql.org/wiki/Apt/FAQ), "I want libpq5 for version X, but there is only
version Y in the repository"); the Ubuntu packages linked to it (`libgdal34t64`) depend on an unversioned
`libpq5`, and the smoke test checks `psycopg2` and GDAL against it. `libpq-dev` goes along because the
Ubuntu one depends on its exact `libpq5` version (`devel` stage).

## Smoke test

`smoke-test` runs at the end of the `runtime` and `devel` stages, so every tagged image has passed it. It
also stays in the image as `geonode-base-smoke-test`:

```bash
docker run --rm geonode/geonode-base:ubuntu-26.04-pg18 geonode-base-smoke-test
```

It prints one `ok` or `FAIL` line per check, and exits with 1 if any check fails:

- every package of `/etc/geonode-base/requirements.txt` is installed at a version that matches its pin,
  and its modules import. The module names come from the package metadata. uWSGI is the exception: its
  module only imports inside uWSGI, so the test runs the `uwsgi` binary and compares the version it
  reports;
- the GDAL bindings have the version of `libgdal` (`gdalinfo --version`), `gdal_array` round-trips a numpy
  array, the PROJ database answers `EPSG:4326`, and `ogr2ogr` and `gdal_translate` run;
- `psycopg2` is linked to `libpq`, and `pg_dump` has the major version the image was built with;
- `libmagic` is present (`python-magic` loads it with `ctypes`; GeoNode uses it to validate uploads),
  `/usr/local/bin/invoke` runs, and `pip check` is clean;
- the system Python has no GDAL bindings, `/usr/bin` has no `*.py` file, and the `gdal_calc.py` on the
  `PATH` is the virtualenv one. `--no-system` skips this group, for derived images that install
  `python3-gdal` on purpose.

The test reads `requirements.txt` from the image, so the same script works for every release, and adding
a package to `requirements.txt` adds it to the test.

## System Python GDAL bindings

`gdal-bin` (`ogr2ogr`, `gdal_translate`…) depends on `python3-gdal`, the GDAL bindings for the system
Python, which pulls the system numpy (on 26.04 also `python3-numpy-dev`). GeoNode runs in the virtualenv.
It has its own bindings and its own copies of the 18 GDAL Python utilities (`gdal_calc.py`,
`gdal2tiles.py`, `ogrmerge.py`…), first in the `PATH`. Installing `python3-gdal` would only duplicate
them, and on 26.04 it would add a second numpy (2.3) next to the virtualenv's 1.26. So the `runtime`
stage installs `gdal-bin` without it.

### Why a placeholder package

`gdal-bin` declares `python3-gdal` as a hard dependency (`Depends`), not a recommendation, at an exact
version:

```
gdal-bin 3.8.4+dfsg-3ubuntu3 (24.04)
  Depends: ..., python3-gdal (= 3.8.4+dfsg-3ubuntu3), python3-numpy (= 1:1.26.4+ds-6ubuntu1), python3-numpy-abi9
gdal-bin 3.12.2+dfsg-1build2 (26.04)
  Depends: ..., python3-gdal (= 3.12.2+dfsg-1build2)
```

`--no-install-recommends` does not help, since it only drops `Recommends`. The build therefore creates,
with `dpkg-deb`, an empty package (`geonode-base-no-system-python-gdal`) that `Provides` those
`python3-*` packages at the exact versions `gdal-bin` requires. It reads the versions from `apt-cache`
during the build, and the build log shows a `Placeholder provides: ...` line.

| Alternative | Why it was ruled out |
|---|---|
| Install everything, then `dpkg --force-depends -r python3-gdal` | Leaves the apt database **broken**: `apt-get check` reports an unmet dependency, and in a derived image any `apt-get install` fails ("Unmet dependencies… try apt --fix-broken install") or reinstalls `python3-gdal` by itself |
| Skip `gdal-bin` and copy the binaries from `build` | The binaries live outside dpkg and get no security updates, and their libraries must be tracked by hand |
| `equivs` | Same result as the placeholder, but it needs `equivs` and its dependencies installed; `dpkg-deb` is already in the `ubuntu` image |
| `path-exclude` on the files of `python3-gdal` and numpy | dpkg records the packages as installed without their files, and `python3-numpy` still pulls its own dependencies |

The placeholder has no `Conflicts` or `Replaces`, so `apt-get install python3-gdal` still works in a
derived image. `apt-get check` passes, and a simulated install of `gdal-bin` proposes nothing.

### `/etc/dpkg/dpkg.cfg.d/geonode-no-system-gdal-scripts`

The 18 utilities in `/usr/bin` belong to `gdal-bin` (`dpkg -S /usr/bin/gdal_calc.py` answers `gdal-bin`),
not to `python3-gdal`. They start with `#!/usr/bin/python3` and import `osgeo_utils`. Without
`python3-gdal` they would stay in the image broken: `ModuleNotFoundError: No module named 'osgeo'`. A
plain `gdal_calc.py` runs the virtualenv copy. The broken copy would run when the script is called by
its full path, from cron (`PATH=/usr/bin:/bin`), from a subprocess with a cleared environment, or through
`sudo`'s `secure_path`.

The file holds dpkg `path-exclude` rules and is written before `gdal-bin` is installed:

```
path-exclude=/usr/bin/gdal*.py
path-exclude=/usr/bin/ogr*.py
path-exclude=/usr/bin/pct2rgb.py
path-exclude=/usr/bin/rgb2pct.py
```

dpkg never writes those files, in this build or in any later install or upgrade of `gdal-bin`; a plain
`rm` would be undone by the next upgrade. The `ubuntu` image itself uses the same mechanism
(`/etc/dpkg/dpkg.cfg.d/excludes`) to leave out man pages. The patterns end in `.py`, so the binaries
(`gdalinfo`, `ogr2ogr`…) are untouched. The smoke test fails if any `*.py` shows up in `/usr/bin`. That
catches a future GDAL script whose name falls outside the patterns.

| Call | With the system copies | With the exclusion |
|---|---|---|
| `gdal_calc.py` (image `PATH`) | virtualenv copy, works | virtualenv copy, works |
| `/usr/bin/gdal_calc.py`, or cron with the default `PATH` | `ModuleNotFoundError: No module named 'osgeo'` | `command not found` |

Scheduled jobs should call `/usr/src/venv/bin/gdal_calc.py` or set `PATH` in the crontab.

### Consequences for derived images, and how to revert

- **GDAL updates from Ubuntu** (expected apt behavior; not tested yet, since no newer `gdal-bin` has been
  published since the build). `apt-get upgrade` keeps a newer `gdal-bin` back, because it requires a newer
  `python3-gdal` than the placeholder provides. `apt-get install gdal-bin` or `dist-upgrade` upgrade it and
  install the real `python3-gdal` with it. apt never ends up broken. The fix is to rebuild the base, which
  the virtualenv bindings need anyway to follow `libgdal`.
- **Reverting both**, in a derived image that needs the system bindings and utilities:

```dockerfile
RUN rm /etc/dpkg/dpkg.cfg.d/geonode-no-system-gdal-scripts && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends --reinstall gdal-bin python3-gdal && \
    rm -rf /var/lib/apt/lists/*
# geonode-base-smoke-test --no-system still checks the rest of the image
```

The virtualenv copies stay first in the `PATH`.

## Using it

As the base of the GeoNode image, replace the `FROM` of the root `Dockerfile` with the image of the
matching release, for instance `FROM geonode/geonode-base:ubuntu-26.04-pg18` for GeoNode master.

The final image has no compiler. Every Python package installed on top of it must therefore have a wheel
for the Python of the release on the target architecture, or be pure Python. Once the packages of
`requirements.txt` are in place, this holds for every dependency of the matching GeoNode line. A project
that needs another package without a wheel (for instance `python-ldap`, used by the geonode-contribs LDAP
app) can build on `devel`, or compile the wheel in a stage of its own and copy it.

To run the GeoNode test suite on a GeoNode image built on top of it, see "Testing a base image" below.

## Testing a base image: `geonode-tests`

`geonode-tests` runs the GeoNode test suite, group by group, exactly as the GeoNode CI does, against a
GeoNode image built from this repository on top of a chosen base image. No downstream project is involved,
so a failure points to the base image or to the GeoNode code, not to customizations.

```bash
# GeoNode master on the Ubuntu 26.04 base
docker build --target release -t geonode/geonode-base:ubuntu-26.04-pg18 docker/base/ubuntu/multi-stage
./docker/base/ubuntu/multi-stage/geonode-tests --ref master --base geonode/geonode-base:ubuntu-26.04-pg18

# GeoNode 5.0.x on the Ubuntu 24.04 base
docker build --target release --build-arg UBUNTU_RELEASE=24 \
  --build-arg EXTRA_BUILD_PACKAGES="libmemcached-dev" --build-arg POSTGRESQL_CLIENT_VERSION=15 \
  -t geonode/geonode-base:ubuntu-24.04-pg15 docker/base/ubuntu/multi-stage
./docker/base/ubuntu/multi-stage/geonode-tests --ref 5.0.x --base geonode/geonode-base:ubuntu-24.04-pg15
```

What it does, following `.github/workflows/tests.yml` and `run-test-suite.yml` of the tested ref:

1. exports the source of the ref with `git archive` (the working tree is not touched);
2. builds the GeoNode image from the root `Dockerfile` of that source, with its `FROM` replaced by the base
   under test;
3. reads the test groups and their commands from `tests.yml`, and how the stack is started (compose file,
   env file, `up` arguments) from `run-test-suite.yml`, so each ref runs with its own CI definition;
4. for each group, like a CI job: starts a fresh stack, creates the test databases, runs the test command
   inside the `django` container, saves the logs and removes the stack with its volumes.

On purpose, it differs from the CI in four points:
- `--failfast` is removed, so every group runs to the end (`-f` keeps it);
- published ports are dropped, so the test stack does not clash with other stacks on the host;
- the Codecov upload is not run;
- service images that do not exist for the host architecture (e.g. the amd64-only GeoServer and PostGIS
  images on arm64) run emulated; `--service-image SERVICE=IMAGE` replaces one of them.

Options (see `./docker/base/ubuntu/multi-stage/geonode-tests --help`):

| Option | Effect |
|---|---|
| `-b, --base IMAGE` | Base image under test (default `docker.io/ndscprm/geonode-base:ubuntu-26.04-pg18`) |
| `-r, --ref REF` | Git ref of the GeoNode source to build and test (default `HEAD`). It must match the base, since GeoNode pins GDAL to the `libgdal` of the base: `5.0.x` with 24.04, `master` with 26.04 |
| `--platform PLATFORM` | Platform of the GeoNode image (default: the host's) |
| `--service-image S=IMG` | Use `IMG` for the compose service `S`, e.g. a native arm64 PostGIS; repeatable |
| `--no-build` | Reuse the GeoNode image built by a previous run (same ref and base) |
| `-f, --failfast` | Keep the `--failfast` of the CI test commands |
| `-k, --keep` / `--down` | Keep the stack of the last group for inspection / remove it with its volumes |
| `-l, --list` | List the groups of the ref. It builds the GeoNode image first (or reuses it with `--no-build`), because the CI YAML is read with the PyYAML of that image |
| `group...` | Run only these groups (default: all, in the order of `tests.yml`) |

Environment variables:

| Variable | Effect |
|---|---|
| `CONTAINER_ENGINE=docker\|podman` | Force the engine (default: Docker if its daemon answers, otherwise Podman) |
| `BOOT_TIMEOUT` | Maximum wait, in seconds, for `django` and `geoserver` to become healthy (default 3600) |
| `MAX_FAILED_LIST` | Failed tests listed per group in the summary (default 30) |
| `GEONODE_TESTS_DIR` | Work directory (default `~/.cache/geonode-base-tests`) |

Logs go to `~/.cache/geonode-base-tests/logs/<date-time>/`: `build.log`, `plan.json`, `override.yml`,
`summary.txt` (also printed at the end) and, per group, the test log, the stack start log and the services
log. The services log is saved even when the stack fails to start. The exit status is 0 only if every
group passes.

Notes from running it:

- **Duration.** Each group starts a fresh stack (about 3 minutes with emulated services) and loads the
  gisdata sample layers (about 10 minutes) before its tests, as the CI's `test.sh` does. A full run took
  about 2 h 45 min per GeoNode line on the machine described in the report.
- **Emulation.** The CI service images (`geonode/postgis`, `geonode/geoserver`, `geonode/nginx` and, on
  5.0.x, `geonode/geoserver_data`) only exist for amd64. On arm64 they run under QEMU, which slows the boot
  and can expose races that do not happen natively: on master, a group's stack sometimes fails to
  start because Django connects while the emulated PostgreSQL restarts after initializing the database
  (`csw` once, `security` once); the group passed on a second run. `--service-image` can swap in native images, at the cost of diverging from the CI.
- **Environment-dependent test.** On master, `test_map_default_thumb` needs the Wikimedia tiles (which
  answered 403 in the test environment) and downloads the thumbnail through `SITEURL`, which uWSGI does
  not serve with `DEBUG=False`. It fails for reasons that do not involve the base image.
- **Compose details.** The master compose file reads `env_file: ${COMPOSE_ENV_FILES:-.env}`; the script
  exports `COMPOSE_ENV_FILES` with the CI env file, as the workflow does. Containers are named
  `<service>4<project>`, following the `container_name` of the compose files.
- **Podman.** `podman pull --platform linux/arm64` succeeds even when only an amd64 image exists, so the
  script reads the platform from the pulled image before writing the compose override.

Requirements: bash 4.3 or newer (on macOS, the Homebrew bash), git, and Docker or Podman with compose.

## Problems of the single-stage images fixed by this build

Problems of the base images published from `docker/base/ubuntu/24/Dockerfile` and
`docker/base/ubuntu/26/Dockerfile` (`geonode/geonode-base:latest-ubuntu-24.04` and `latest-ubuntu-26.04`)
that this Dockerfile fixes. They come from reading those Dockerfiles and from the figures in "At a glance".
Most serious first:

1. **Build and packaging tools in the production image.** The single-stage images keep:
   - `gcc`, `build-essential`, `python3-all-dev`, `python3-dev` and the `-dev` libraries (86 on 24.04, 116 on
     26.04);
   - `devscripts`, `debhelper`, `pkg-kde-tools` and `sharutils`, only used by a PROJ build that is commented
     out in the Dockerfile;
   - tools with no runtime use: `vim`, `zip`, `unzip`, `curl`, `wget`, `gnupg2`, `lsb-release`, and `git` on
     26.04.

   Hence 1.44 / 1.66 GB and most of the CVEs: `linux-libc-dev`, pulled in with the compilers, carries the
   42 / 43 critical ones. **Fix:** everything is compiled in `build`, and `runtime` gets only the virtualenv
   and the libraries it needs. `release` has no compiler and at most one `-dev` package (`systemd-dev` on
   24.04, with no C headers). It is 570 / 666 MB, with no critical or high CVE in OS packages. `devel`
   covers the need to compile.
2. **No `apt-get upgrade`.** 22 (24.04) and 27 (26.04) OS packages have a published fix that is not
   applied. **Fix:** `apt-get upgrade` in every stage, so none is pending.
3. **Recommended packages installed.** Some `apt-get install` calls lack `--no-install-recommends`. That
   brings packages such as `openssh-client`, with the setuid `ssh-agent` and `ssh-keysign` (15 / 14
   setuid/setgid binaries). **Fix:** `--no-install-recommends` everywhere: 13 / 12 binaries.
4. **GDAL bindings without `gdal_array`.** `pip install GDAL` runs before numpy is in the virtualenv, so
   raster I/O as numpy arrays (`ReadAsArray`, `OpenArray`) does not work. **Fix:** numpy first, then GDAL
   with `--no-build-isolation`. The smoke test checks a `gdal_array` round trip.
5. **System Python stacks duplicating the virtualenv.** apt installs `python3-gdal`, `python3-psycopg2`,
   `python3-ldap`, `python3-lxml`, `uwsgi` and `uwsgi-plugin-python3`, which the virtualenv does not see.
   On 26.04, `python3-gdal` adds numpy 2.3 next to the virtualenv's 1.26. **Fix:** virtualenv only.
   `gdal-bin` comes without `python3-gdal`, thanks to the placeholder package, and the dpkg `path-exclude`
   leaves out its broken Python utilities in `/usr/bin` (see "System Python GDAL bindings").
6. **GeoNode packages not prebuilt.** The images lack `psycopg2`, `pylibmc` and `psutil` (24.04) and numpy
   (26.04), and they ship uWSGI 2.0.31 instead of GeoNode's pinned 2.0.30. The GeoNode build compiles them
   again and depends on the compilers of the base. **Fix:** they are compiled in the virtualenv, at
   GeoNode's pins, from each release's `requirements.txt`, so the GeoNode build needs no compiler.
7. **Fixed PostgreSQL client, from another Ubuntu release on 26.04.** Both images hard-code
   `postgresql-client-15`, while `geonode.br` needs the same major version as the database. On 26.04 the
   repository is `noble-pgdg` (24.04), which mixes packages of two releases. **Fix:** the mandatory
   `POSTGRESQL_CLIENT_VERSION` build argument (default 18) picks the client. It comes from the release's
   own PGDG (`${VERSION_CODENAME}-pgdg`) at priority 100. The major version goes into the tag
   (`-pg<client>`), and the smoke test checks `pg_dump`.
8. **PGDG key added with `apt-key` (24.04).** It is deprecated and trusts the key for every repository.
   **Fix:** `signed-by`, so the key applies to PGDG only.
9. **Cleanup that does not shrink the image.** `rm -rf /var/lib/apt/lists/*` runs in its own `RUN`, so the
   lists stay in earlier layers, and the pip cache stays in the image. **Fix:** the lists are removed in the
   same `RUN` as each install, and pip runs with `--no-cache-dir`.
10. **amd64 only.** On Apple Silicon, AWS Graviton or Ampere hosts the official images run emulated.
    **Fix:** the same Dockerfile builds amd64 and arm64 unchanged; all four tags were built as manifest
    lists of both. Publishing them is still up to the GeoNode maintainers.
11. **No self-check.** Nothing tests the image after the build. **Fix:** the smoke test runs at the end of
    `runtime` and `devel` and fails the build. It stays in the image as `geonode-base-smoke-test` for
    derived images.
12. **Two Dockerfiles drifting apart.** The differences between them do not come from the Ubuntu release:
    - only 26.04 sets `DEBIAN_FRONTEND`, creates `/usr/src/geonode` and installs `git`;
    - only 24.04 installs `libmemcached-dev`;
    - only 24.04 has a no-op `RUN . /usr/src/venv/bin/activate` and a stale "will install python3.10"
      comment.

    **Fix:** one Dockerfile. What changes per release lives in the directory's `requirements.txt` and in two
    build arguments (`EXTRA_BUILD_PACKAGES`, `POSTGRESQL_CLIENT_VERSION`).

## Advantages and improvements

### Compared with the single-stage images

| Aspect | Single-stage | Multi-stage `release` | Advantage |
|---|---|---|---|
| Size | 1.44 GB (24.04), 1.66 GB (26.04) | 570 MB, 666 MB | less than half: faster pulls and pushes, less storage |
| Compilers and `-dev` packages | gcc, g++, make, 86 / 116 `-dev`, `linux-libc-dev` | no compiler; at most `systemd-dev` (24.04), which ships no C headers | smaller attack surface; nothing can be compiled inside a compromised container |
| OS vulnerabilities | 3,468 / 3,750, with 42 / 43 critical | 108 / 93, no critical or high | most single-stage CVEs come from `linux-libc-dev` and the `-dev` packages |
| Ubuntu security fixes | 22 / 27 packages with a pending fix | `apt-get upgrade` in every stage: none pending | every rebuild picks up the fixes |
| apt recommends | some packages installed with recommends (e.g. `openssh-client` on 24.04) | `--no-install-recommends` everywhere | fewer packages and fewer setuid/setgid binaries |
| Runtime libraries | chosen by hand | found by `ldd` on the virtualenv modules | nothing unused, nothing missing |
| GDAL bindings | without `gdal_array` | with `gdal_array` | raster I/O as numpy arrays works |
| System Python bindings | `python3-gdal` and the system numpy next to the virtualenv | virtualenv only | a single numpy and one copy of each GDAL utility |
| Build of GeoNode on top | compiles `psycopg2` (and `pylibmc`, `psutil` on 24.04 arm64, numpy on 26.04), and replaces uWSGI 2.0.31 with the pinned 2.0.30 | those packages are already built, at the versions GeoNode pins | no compiler needed in the GeoNode image, faster builds |
| PGDG and PostgreSQL client | PGDG blocked except `postgresql-client-15`, hard-coded; on 26.04 from `noble-pgdg` | PGDG of the release itself at priority 100; client chosen at build time | the client follows the database, as `geonode.br` requires, and no packages of another Ubuntu release are mixed in |
| One Dockerfile | one Dockerfile per release | one Dockerfile; a directory per release with only `requirements.txt` | a fix applies to every release at once |
| Self-check | none | smoke test in the build and in the image | a broken image cannot be tagged, and derived images can check themselves |
| Image for compiling | — | `devel` (`release` + compilers) | packages without wheels still build, without weighing on the production image |
| Compatibility | — | same paths | GeoNode and geonode-project Dockerfiles work unchanged |

### Proposed improvements, not applied yet

- **Drop the setuid/setgid bits** at the end of `runtime` (see "Known points"), leaving no binary with
  those bits. The test suite must be run again before adopting it.
- **Run the test suite on amd64.** The unified images build and pass the smoke test on amd64 (see "At a
  glance"), but the GeoNode test suite ran only on arm64.
- **Ask the GeoNode maintainers to publish arm64 images too.** Today the official images are amd64 only:
  the base (`geonode/geonode-base`), `geonode/geonode`, and the stack and CI services
  (`geonode/postgis`, `geonode/geoserver`, `geonode/geoserver_data`, `geonode/nginx`). On arm64 hosts
  (Apple Silicon Macs, AWS Graviton, Ampere…) they only run emulated, which is slower and prone to
  failures that do not happen natively. This Dockerfile builds both architectures unchanged. With
  `docker buildx build --platform linux/amd64,linux/arm64` in the GitHub Actions workflows (with QEMU or
  GitHub's arm64 runners), the same tags would serve both architectures.
- **numpy 2.x, in GeoNode rather than in the base.** GeoNode master pins `numpy==1.26.*` in
  `pyproject.toml`. GeoNode uses numpy directly only in `geonode/upload/handlers/tiles3d/utils.py`, and
  that file uses `np.NaN`, which numpy 2.0 removed (`np.nan` works in both). shapely 2.1 and GDAL 3.12
  already support numpy 2. Moving to numpy 2.x would bring:
  - Python 3.14 wheels: the 26.04 base would no longer compile numpy nor need `libopenblas-dev`;
  - a maintained release line: 1.26.4 is the last 1.26 release and has no official Python 3.14 support.

  The performance gain for GeoNode itself is negligible.
- **In GeoNode, not in the base:**
  - install with `pip install --no-cache-dir` in the root `Dockerfile`, which would remove 147–195 MB of
    pip cache from GeoNode 5.0.x images;
  - update Pillow 12.1.1 and PyJWT 2.8.0, which account for every critical CVE of a GeoNode 5.0.x image.
- **In deployments:** `no-new-privileges` and `cap_drop: [ALL]` neutralize the setuid/setgid binaries
  even before the base drops the bits.

## Known points

- **setuid/setgid binaries.** The `release` images have 13 (24.04) and 12 (26.04). All of them except
  `crontab` come from the `ubuntu` image itself (`su`, `passwd`, `mount`…); `crontab` comes from `cron`,
  which GeoNode's `entrypoint.sh` restarts. GeoNode uses none of them inside the container. Removing the
  bits (`find / -xdev -perm /6000 -type f -exec chmod a-s {} +` at the end of `runtime`) is a possible
  hardening step, not applied yet.
- **Remaining vulnerabilities.** The OS packages have no critical or high CVEs and none with a pending
  fix. The fixable ones are in Python: the GDAL bindings (fixed in 3.13) and the `setuptools` copy bundled
  with pip. On 26.04, Trivy also reports one medium CVE in the Go standard library of `/usr/bin/pebble`,
  Canonical's service manager that `ubuntu:26.04` ships outside `dpkg`.
- **numpy 1.26 on Python 3.14.** GeoNode master pins a numpy series without Python 3.14 wheels or official
  support. It compiles and the test suite passes, but it is worth following upstream.
- **`test_map_default_thumb` (GeoNode master).** The only error of the 26.04 suite does not depend on the
  image. The test fetches background tiles from `maps.wikimedia.org`, which answered 403 in the test
  environment. It then downloads the generated thumbnail through `SITEURL`
  (`http://localhost:8000/uploaded/...`), which uWSGI does not serve with `DEBUG=False`.

## Adding or updating a release

- **New GeoNode pins:** update `<release>/requirements.txt` when GeoNode changes them (`setup.cfg` on
  5.0.x, `pyproject.toml` on master). List the pinned packages that have no wheel for the Python of the
  release on linux/amd64 and linux/arm64 (check PyPI), and keep `numpy` first for `gdal_array`.
- **New Ubuntu LTS release:**
  - add a directory named after its year (`28/` for 28.04) with its `requirements.txt`;
  - add a row to the first table with its `EXTRA_BUILD_PACKAGES` and PostgreSQL client;
  - build it with `--build-arg UBUNTU_RELEASE=28`;
  - if a common build package changed name, adjust `BUILD_PACKAGES`.

  If `gdal-bin` ships Python utilities whose names fall outside the `path-exclude` patterns, the smoke test
  fails and names them.
- **Runtime libraries:** `ldd` finds them automatically. Libraries loaded with `ctypes` are invisible to
  `ldd` and must be added by hand to `runtime`; today that is only `libmagic1`.
- **Security updates:** every stage runs `apt-get upgrade`, so a rebuild picks up the Ubuntu fixes.
