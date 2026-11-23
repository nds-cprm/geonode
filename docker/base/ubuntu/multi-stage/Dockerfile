# GeoNode base image, multi-stage, for every supported Ubuntu LTS release: a slimmer alternative to the
# single-stage docker/base/ubuntu/<release>/Dockerfile. See README.md next to this file.
#
#   docker build --target release --build-arg UBUNTU_RELEASE=24 --build-arg EXTRA_BUILD_PACKAGES="libmemcached-dev" \
#     --build-arg POSTGRESQL_CLIENT_VERSION=15 -t geonode-base:ubuntu-24.04-pg15 docker/base/ubuntu/multi-stage
#   docker build --target devel -t geonode-base:ubuntu-26.04-pg18-devel docker/base/ubuntu/multi-stage
#
# (podman build takes the same arguments)
#
# What changes from one Ubuntu release to the other:
# - <release>/requirements.txt, next to this file: the Python packages compiled into the virtualenv (the
#   packages pinned by the matching GeoNode line that have no wheel for the Python of that Ubuntu release),
#   plus invoke and sherlock;
# - the build arguments EXTRA_BUILD_PACKAGES (the extra build packages those need) and
#   POSTGRESQL_CLIENT_VERSION. The defaults of every build argument are those of Ubuntu 26.04; the 24
#   build passes its own values (README.md lists them).
# The GDAL bindings take the version of the system libgdal (gdal-config --version).
#
# Stages:
# - "build" has the compilers and the -dev packages, builds the virtualenv and lists the Ubuntu packages
#   that provide the shared libraries its binaries link to.
# - "runtime" copies the virtualenv and installs only those runtime libraries and the tools GeoNode uses
#   (gdal-bin, postgresql-client, gettext, cron, git...): no compilers, headers or packaging tools.
# - "devel" is "runtime" plus the compilers and the -dev packages of "build": a GeoNode project builds
#   on it the same way it builds on "release", and can also compile packages that have no wheel.
# - "release" is "runtime" (the last stage, so it is also the default target).
#
# "build" and "runtime" use the same Ubuntu image and Python (/usr/bin/python3), so the virtualenv built
# in "build" runs unchanged in "runtime". The paths are the same as in the single-stage images
# (/usr/src/venv, /usr/local/bin/invoke, /usr/src/geonode), so the GeoNode and geonode-project
# Dockerfiles work as before.
#
# Packages that need a compiler and are not listed in requirements.txt (for example python-ldap, used by
# the geonode-contribs LDAP app) do not install on "release": build them on "devel" or in a stage of your
# own.

# Ubuntu LTS release: the name of one of the directories next to this file (24 = Ubuntu 24.04 for
# GeoNode 5.0.x, 26 = Ubuntu 26.04 for GeoNode master)
ARG UBUNTU_RELEASE=26

# Tag of the ubuntu image used by every stage. The default is the plain release (24.04, 26.04); set it to
# pin a dated build or another tag of the same release (e.g. noble-20260101). The "build" stage fails
# if the image is not of the major release given by UBUNTU_RELEASE, whose files it uses.
ARG UBUNTU_IMAGE_TAG=${UBUNTU_RELEASE}.04

# Compilers and headers common to every release, installed in "build" and in "devel" together with the
# extra build packages of the release
ARG BUILD_PACKAGES="python3-dev python3-venv gcc g++ make pkg-config libgdal-dev libpq-dev \
zlib1g-dev libxml2-dev libssl-dev libpcre2-dev libcap-dev"

# Extra build packages of the release, for the packages of its requirements.txt (empty: a warning).
# - 26 (default): "libopenblas-dev libcrypt-dev" (numpy 1.26 has no wheel for Python 3.14; crypt.h for uWSGI)
# - 24: "libmemcached-dev" (pylibmc)
ARG EXTRA_BUILD_PACKAGES="libopenblas-dev libcrypt-dev"

# Major version of the PostgreSQL client (pg_dump, pg_restore, psql); it must not be empty. Keep it equal
# to the major version of the database: pg_dump refuses to dump a newer server, and a dump made by a newer
# pg_dump may not restore into an older server (GeoNode backup/restore, geonode.br). Put it in the image
# tag (see README.md). The default, 18, is the client Ubuntu 26.04 ships; build 24 with
# --build-arg POSTGRESQL_CLIENT_VERSION=15 (the PostgreSQL of the GeoNode 5.0.x compose files). Versions
# Ubuntu does not ship come from PGDG.
ARG POSTGRESQL_CLIENT_VERSION=18

FROM ubuntu:${UBUNTU_IMAGE_TAG} AS build

ARG UBUNTU_RELEASE
ARG UBUNTU_IMAGE_TAG
ARG BUILD_PACKAGES
ARG EXTRA_BUILD_PACKAGES

ENV DEBIAN_FRONTEND=noninteractive

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY ${UBUNTU_RELEASE}/requirements.txt /etc/geonode-base/requirements.txt

# The image must be of the major release whose requirements.txt is used. An empty EXTRA_BUILD_PACKAGES only
# prints a warning: a release may need none
RUN . /etc/os-release && \
    if [ "${ID}" != ubuntu ] || [ "${VERSION_ID%%.*}" != "${UBUNTU_RELEASE}" ]; then \
        echo "ubuntu:${UBUNTU_IMAGE_TAG} is ${PRETTY_NAME}, not Ubuntu ${UBUNTU_RELEASE}.x (UBUNTU_RELEASE=${UBUNTU_RELEASE})" >&2; \
        exit 1; \
    fi && \
    echo "Base image: ubuntu:${UBUNTU_IMAGE_TAG} (${PRETTY_NAME})" && \
    if [ -z "${EXTRA_BUILD_PACKAGES}" ]; then \
        echo "WARNING: EXTRA_BUILD_PACKAGES is empty; the packages of requirements.txt may not build without the extra build packages of the release (README.md lists them)" >&2; \
    else \
        echo "Extra build packages: ${EXTRA_BUILD_PACKAGES}"; \
    fi && \
    apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends ca-certificates python3 ${BUILD_PACKAGES} ${EXTRA_BUILD_PACKAGES} && \
    rm -rf /var/lib/apt/lists/*

# GDAL bindings with the version of the system libgdal (gdal-config), built against the numpy installed
# from requirements.txt (gdal_array), hence --no-build-isolation
RUN python3 -m venv /usr/src/venv && \
    . /usr/src/venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /etc/geonode-base/requirements.txt && \
    GDAL_VERSION="$(gdal-config --version)" && \
    pip install --no-cache-dir --no-build-isolation "GDAL==${GDAL_VERSION}" && \
    python -c "from osgeo import gdal, gdal_array; assert gdal.__version__ == '${GDAL_VERSION}', gdal.__version__"

# Ubuntu packages that provide the shared libraries used by the binaries of the virtualenv, installed by
# "runtime" (see get-runtime-packages --help). It fails if a system library belongs to no package
COPY get-runtime-packages /usr/local/bin/geonode-base-get-runtime-packages
RUN geonode-base-get-runtime-packages /usr/src/venv > /runtime-packages.txt


FROM ubuntu:${UBUNTU_IMAGE_TAG} AS runtime

ARG UBUNTU_RELEASE
ARG UBUNTU_IMAGE_TAG
ARG POSTGRESQL_CLIENT_VERSION

ENV DEBIAN_FRONTEND=noninteractive

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY --from=build /runtime-packages.txt /tmp/runtime-packages.txt
COPY --from=build /etc/geonode-base/ /etc/geonode-base/

# gdal-bin (ogr2ogr, gdal_translate... used by GeoNode) depends on python3-gdal, the GDAL bindings for the
# *system* Python, which pull the system numpy. GeoNode only uses /usr/src/venv, which has its own bindings
# and the GDAL Python utilities (gdal_calc.py, gdal2tiles.py...) first in the PATH. So:
# - a local placeholder package provides the Python packages that gdal-bin requires, at the versions it
#   requires, so apt installs gdal-bin without them and stays consistent. A derived image can still
#   install the real python3-gdal: the placeholder does not conflict with it. A newer gdal-bin from
#   Ubuntu is kept back by "apt-get upgrade" (and "apt-get install gdal-bin" brings the real python3-gdal
#   with it) until the image is rebuilt, which also refreshes the placeholder versions;
# - dpkg skips the copies of the Python utilities that gdal-bin ships in /usr/bin: they run with the system
#   Python, which has no bindings, and would fail when called by their full path or with a minimal PATH
#   (cron). The rule also holds when gdal-bin is upgraded in a derived image. To get them back:
#   rm /etc/dpkg/dpkg.cfg.d/geonode-no-system-gdal-scripts && apt-get install --reinstall gdal-bin python3-gdal
RUN printf '%s\n' 'path-exclude=/usr/bin/gdal*.py' 'path-exclude=/usr/bin/ogr*.py' \
        'path-exclude=/usr/bin/pct2rgb.py' 'path-exclude=/usr/bin/rgb2pct.py' \
        > /etc/dpkg/dpkg.cfg.d/geonode-no-system-gdal-scripts && \
    apt-get update -y && \
    provides="$(apt-cache show --no-all-versions gdal-bin | sed -n 's/^Depends: //p' | tr ',' '\n' \
        | sed -e 's/^ *//' -e 's/ |.*//' | grep '^python3-' | while read -r name rest; do \
            version="$(apt-cache policy "$name" | awk '/Candidate:/ { print $2 }')"; \
            if [ -n "$version" ] && [ "$version" != "(none)" ]; then echo "$name (= $version)"; else echo "$name"; fi; \
          done | paste -sd, - | sed 's/,/, /g')" && \
    echo "Placeholder provides: $provides" && \
    mkdir -p /tmp/placeholder/DEBIAN && \
    printf '%s\n' \
        'Package: geonode-base-no-system-python-gdal' \
        'Version: 1.0' \
        'Architecture: all' \
        'Maintainer: GeoNode <dev@geonode.org>' \
        "Provides: $provides" \
        'Description: placeholder for the system Python GDAL bindings' \
        ' GeoNode uses the GDAL bindings and utilities of its virtualenv (/usr/src/venv).' \
        > /tmp/placeholder/DEBIAN/control && \
    dpkg-deb --build /tmp/placeholder /tmp/placeholder.deb && \
    dpkg -i /tmp/placeholder.deb && \
    rm -rf /tmp/placeholder /tmp/placeholder.deb /var/lib/apt/lists/*

RUN pg_client="${POSTGRESQL_CLIENT_VERSION}" && \
    if ! [[ "${pg_client}" =~ ^[0-9]+$ ]]; then \
        echo "POSTGRESQL_CLIENT_VERSION is '${pg_client}': it must be the major version of the database (e.g. 15 or 18)" >&2; \
        exit 1; \
    fi && \
    echo "PostgreSQL client: ${pg_client}" && \
    apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates curl wget gnupg2 \
        python3 python-is-python3 \
        gdal-bin \
        gettext cron git zip unzip \
        libmagic1 && \
    xargs -a /tmp/runtime-packages.txt apt-get install -y --no-install-recommends && \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg && \
    . /etc/os-release && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] https://apt.postgresql.org/pub/repos/apt/ ${VERSION_CODENAME}-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list && \
    # Low priority for PGDG: it only provides what Ubuntu lacks (postgresql-client-NN). PGDG also ships
    # newer GDAL, PROJ, GEOS and libpq builds; without this pin an "apt-get install" or "upgrade" in a
    # derived image would replace the libgdal the GDAL bindings were built against.
    printf 'Package: *\nPin: origin apt.postgresql.org\nPin-Priority: 100\n' > /etc/apt/preferences.d/pgdg && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends "postgresql-client-${pg_client}" && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/runtime-packages.txt && \
    # What this image was built with, read by geonode-base-smoke-test
    printf '%s\n' \
        "UBUNTU_RELEASE=${UBUNTU_RELEASE}" \
        "UBUNTU_IMAGE_TAG=${UBUNTU_IMAGE_TAG}" \
        "POSTGRESQL_CLIENT_VERSION=${pg_client}" \
        > /etc/geonode-base/build-info

COPY --from=build /usr/src/venv /usr/src/venv

ENV PATH="/usr/src/venv/bin:$PATH"

COPY smoke-test /usr/local/bin/geonode-base-smoke-test

# "invoke" on the path used by the entrypoint.sh of existing GeoNode projects. The smoke test checks the
# packages of requirements.txt, the GDAL bindings, the PostgreSQL client and the absence of the system
# Python GDAL bindings; it also runs in derived images (geonode-base-smoke-test).
RUN ln -s /usr/src/venv/bin/invoke /usr/local/bin/invoke && \
    mkdir -p /usr/src/geonode && \
    geonode-base-smoke-test


FROM runtime AS devel

ARG BUILD_PACKAGES
ARG EXTRA_BUILD_PACKAGES

# The same build packages as "build". The -dev packages come from Ubuntu (PGDG has low priority), so
# libgdal-dev matches the libgdal the GDAL bindings were built against.
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends ${BUILD_PACKAGES} ${EXTRA_BUILD_PACKAGES} && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    gcc --version | head -n 1 && \
    [ "$(gdal-config --version)" = "$(python -c 'from osgeo import gdal; print(gdal.__version__)')" ] && \
    geonode-base-smoke-test


# This line below is necessary to define the release stage as the default image
FROM runtime AS release
