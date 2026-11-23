# GeoNode base image (multi-stage, Ubuntu LTS)

Slim base images for building [GeoNode](https://geonode.org) and GeoNode projects, for **linux/amd64 and
linux/arm64**. They are built from one multi-stage Dockerfile: the virtualenv is compiled in a build stage,
and the final image keeps only the virtualenv, the runtime libraries it links to and the tools GeoNode uses.
**No compilers, headers or packaging tools.**

They are a drop-in alternative to `geonode/geonode-base`: same paths (`/usr/src/venv` on the `PATH`,
`/usr/local/bin/invoke`, `/usr/src/geonode`), so the GeoNode and geonode-project Dockerfiles work unchanged.

> Unofficial images, maintained by NDS/CPRM (Geological Survey of Brazil). Source:
> [nds-cprm/geonode, `docker/base/ubuntu/multi-stage`](https://github.com/nds-cprm/geonode/tree/geonode-base-multistage/docker/base/ubuntu/multi-stage).

## Tags

| Tag | Ubuntu | Python | GDAL | For GeoNode | PostgreSQL client |
|---|---|---|---|---|---|
| `ubuntu-26.04-pg18` | 26.04 | 3.14 | 3.12.2 | master | 18 |
| `ubuntu-26.04-pg18-devel` | 26.04 | 3.14 | 3.12.2 | master | 18 |
| `ubuntu-24.04-pg15` | 24.04 | 3.12 | 3.8.4 | 5.0.x | 15 |
| `ubuntu-24.04-pg15-devel` | 24.04 | 3.12 | 3.8.4 | 5.0.x | 15 |

Every tag is a multi-arch manifest list (amd64 + arm64); `docker pull` picks the architecture of the host.
All four were published on 23 November 2026, and every image passed the smoke test on both architectures.
`libpq5` 19.0 comes from PGDG on every tag (see "PostgreSQL client" below); `pg_dump` is 18.6 on the 26.04
tags and 15.20 on the 24.04 tags.

- **`ubuntu-<release>-pg<client>`** (`release`): for production.
- **`…-devel`**: the same image plus the compilers and `-dev` packages, for projects that must compile
  Python packages without a wheel (for example `python-ldap`). Do not use it in production.

The tag scheme is `ubuntu-<ubuntu tag>-pg<PostgreSQL client major>`, because each Ubuntu release pairs with one
GeoNode line (the GDAL bindings pinned by GeoNode must match the system `libgdal`), and GeoNode backup and
restore (`geonode.br`) needs a `pg_dump`/`pg_restore` of the **same major version as the database**.

## Usage

```dockerfile
# GeoNode 5.0.x
FROM ndscprm/geonode-base:ubuntu-24.04-pg15

# GeoNode master
FROM ndscprm/geonode-base:ubuntu-26.04-pg18
```

Check an image (also works in derived images):

```bash
docker run --rm ndscprm/geonode-base:ubuntu-26.04-pg18 geonode-base-smoke-test
```

## What is inside

- **Virtualenv `/usr/src/venv`** with the packages GeoNode pins that have no wheel for the Python of the
  release, already compiled: GDAL bindings (with `gdal_array`, at the version of the system `libgdal`), numpy,
  psycopg2, uWSGI, plus pylibmc and psutil on 24.04, and invoke and sherlock. The GeoNode build does not
  need a compiler.
- **Runtime libraries** detected from the virtualenv binaries (`ldd` + `dpkg -S`), not picked by hand.
- **Tools GeoNode uses**: `gdal-bin` (`ogr2ogr`, `gdal_translate`…), `postgresql-client-<NN>` (`psql`,
  `pg_dump`, `pg_restore`), `gettext`, `cron`, `git`, `zip`/`unzip`, `curl`, `wget`, `libmagic`.
- **No system Python GDAL bindings**: GeoNode only uses the virtualenv, whose GDAL Python utilities
  (`gdal_calc.py`, `gdal2tiles.py`…) come first in the `PATH`.
- **`apt-get upgrade`** at build time and `--no-install-recommends` everywhere.
- **Smoke test** run at the end of the build, so every published image has passed it, and kept as
  `geonode-base-smoke-test`.

### PostgreSQL client

The client comes from the PostgreSQL apt repository (PGDG) of the Ubuntu release itself, pinned at low
priority so it never replaces the GDAL, PROJ or GEOS of Ubuntu. `libpq5` and `libpq-dev` always come from
PGDG, which ships the `libpq` of the latest stable PostgreSQL. The soname is still `libpq.so.5`, and
"libpq5 is compatible with older versions"
([PGDG FAQ](https://wiki.postgresql.org/wiki/Apt/FAQ)).

Need another client version? Build the image yourself with `--build-arg POSTGRESQL_CLIENT_VERSION=<NN>`
(see the source link above).

## Size and vulnerabilities

Compared with `geonode/geonode-base:latest-ubuntu-24.04` / `latest-ubuntu-26.04` (amd64 only). Trivy 0.76.2,
OS and language packages, each CVE counted once at its highest severity.

| | Official 24.04 | `ubuntu-24.04-pg15` | Official 26.04 | `ubuntu-26.04-pg18` |
|---|---|---|---|---|
| Size (amd64 / arm64) | 1.44 GB / — | 546 MB / 570 MB | 1.66 GB / — | 659 MB / 666 MB |
| Compilers | yes | **no** | yes | **no** |
| CVEs (critical / high) | 3,475 (42 / 760) | **111 (0 / 2)** | 3,772 (43 / 794) | **97 (0 / 2)** |
| OS packages with a pending fix | 22 | **0** | 27 | **0** |

Figures from November 2026; they change as new CVEs are published. The two remaining high CVEs are in Python
packages (the GDAL bindings, fixed in GDAL 3.13, and the `setuptools` copy vendored in pip), none in OS
packages.

## Tested with

The GeoNode CI test groups were run on GeoNode images built on top of these bases (arm64):

- GeoNode 5.0.x on `ubuntu-24.04-pg15`: 1,527 tests, all 7 groups passed;
- GeoNode master on `ubuntu-26.04-pg18`: 2,046 tests, all groups passed except one environment-related
  error (`test_map_default_thumb`).

## Build arguments

| Argument | Default | Description |
|---|---|---|
| `UBUNTU_RELEASE` | `26` | Ubuntu LTS release (`24` or `26`) |
| `UBUNTU_IMAGE_TAG` | `<UBUNTU_RELEASE>.04` | `ubuntu` image tag, to pin a dated build (e.g. `noble-20260101`) |
| `EXTRA_BUILD_PACKAGES` | `libopenblas-dev libcrypt-dev` | extra build packages of the release; `libmemcached-dev` for 24 |
| `POSTGRESQL_CLIENT_VERSION` | `18` | major version of the PostgreSQL client; `15` for 24 |

```bash
docker buildx build --platform linux/amd64,linux/arm64 --target release \
  --build-arg UBUNTU_RELEASE=24 --build-arg EXTRA_BUILD_PACKAGES=libmemcached-dev \
  --build-arg POSTGRESQL_CLIENT_VERSION=17 \
  -t <your-repo>/geonode-base:ubuntu-24.04-pg17 docker/base/ubuntu/multi-stage
```

## License

GeoNode is licensed under the [GNU GPL v3](https://github.com/GeoNode/geonode/blob/master/LICENSE.txt). The
images also contain Ubuntu and third-party software under their own licenses.
