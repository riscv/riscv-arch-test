# riscv-arch-test ACT4 build environment
# https://github.com/riscv/riscv-arch-test (branch: act4)
#
# Includes:
#   - riscv-gnu-toolchain  (GCC 15 / Binutils 2.44, built from source, statically linked)
#   - mise                 (tool manager; installs uv/Python and Ruby automatically)
#   - sail-riscv           (RISC-V reference model)
#
# Usage:
#   docker build -t riscv-act4 .
#   docker run -it --rm -v .:/mnt riscv-act4
#   Or if your user does not have ID 1000:
#   docker run -it --rm -u $(id -u):$(id -g) -v .:/mnt riscv-act4
#
#   Inside the container the repo root is at /mnt; run:
#     CONFIG_FILES=config/cores/<vendor>/<dut>/test_config.yaml make

# Global ARGs - declared before any FROM so they are overridable across all stages.
# Each stage that uses them must redeclare them with a bare ARG (no default) to bring them into scope.
ARG RISCV_TOOLCHAIN_PREFIX=/opt/riscv
ARG SAIL_PREFIX=/opt/sail
ARG SAIL_VERSION=0.10

# Stage 1: build riscv-gnu-toolchain
#
# LDFLAGS=-static ensures no shared-lib dependencies survive into the final image.
FROM ubuntu:24.04 AS toolchain-builder

ARG DEBIAN_FRONTEND=noninteractive
ARG RISCV_TOOLCHAIN_PREFIX

ENV RISCV_TOOLCHAIN_PREFIX="${RISCV_TOOLCHAIN_PREFIX}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    autoconf \
    automake \
    autotools-dev \
    bc \
    bison \
    build-essential \
    cmake \
    ca-certificates \
    curl \
    flex \
    gawk \
    gperf \
    git \
    libexpat-dev \
    libglib2.0-dev \
    libgmp-dev \
    libmpc-dev \
    libmpfr-dev \
    libncurses-dev \
    libslirp-dev \
    libtool \
    ninja-build \
    patchutils \
    python3 \
    python3-tomli \
    texinfo \
    zlib1g-dev

RUN git clone --depth 1 https://github.com/riscv/riscv-gnu-toolchain /tmp/riscv-gnu-toolchain \
 && cd /tmp/riscv-gnu-toolchain \
 && sed -i 's/c,c++/c/g' Makefile.in \
 && sed -i 's/c,c++,fortran/c/g' Makefile.in \
 && ./configure \
        --prefix="${RISCV_TOOLCHAIN_PREFIX}" \
        --disable-gdb \
        --disable-qemu \
        --disable-linux \
        --disable-nls \
        --enable-strip \
        ${CROSS_FLAGS} \
        --with-multilib-generator="\
rv32e-ilp32e--;\
rv32i-ilp32--;\
rv32im-ilp32--;\
rv32iac-ilp32--;\
rv32imac-ilp32--;\
rv32imafc-ilp32f--;\
rv32imafdc-ilp32d--;\
rv64i-lp64--;\
rv64ic-lp64--;\
rv64iac-lp64--;\
rv64imafdc-lp64d--;\
rv64im-lp64--;" \
 && GCC_EXTRA_CONFIGURE_FLAGS="\
--enable-languages=c \
--disable-gcov \
--disable-lto \
--disable-libgomp \
--disable-libssp \
--disable-libquadmath \
--disable-decimal-float \
--disable-libsanitizer \
--disable-libvtv \
--enable-static \
--disable-shared" \
    BINUTILS_TARGET_FLAGS_EXTRA="--disable-gprof --disable-gprofng" \
    LDFLAGS="-static -static-libgcc -static-libstdc++" \
    make -j"$(nproc)" \
 && rm -rf /tmp/riscv-gnu-toolchain

# Stage 2: fetch sail-riscv binary
FROM ubuntu:24.04 AS sail-fetcher

ARG DEBIAN_FRONTEND=noninteractive
ARG SAIL_VERSION
ARG SAIL_PREFIX

ENV SAIL_PREFIX="${SAIL_PREFIX}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
 && rm -rf /var/lib/apt/lists/*

RUN SAIL_OS="$(uname -s)" \
 && SAIL_ARCH="$(uname -m)" \
 && mkdir -p "${SAIL_PREFIX}" \
 && curl --location --fail \
      "https://github.com/riscv/sail-riscv/releases/download/${SAIL_VERSION}/sail-riscv-${SAIL_OS}-${SAIL_ARCH}.tar.gz" \
    | tar xz --directory="${SAIL_PREFIX}" --strip-components=1

# Stage 3: install mise, then use it to install uv (Python) and Ruby, and pre-install the riscv-unified-db Bundler gem.
#
# mise reads .mise.toml from the repo to pin exact tool versions.
# We pre-warm the gem cache here so the first `make` inside the container doesn't need network access for Ruby deps.
#
# mise installs everything under MISE_DATA_DIR (/opt/mise) so it can be cleanly COPY'd into the final image.
FROM ubuntu:24.04 AS mise-fetcher

ARG DEBIAN_FRONTEND=noninteractive

# mise needs curl + ca-certificates to download tools.
# The remaining packages are required by ruby-build to compile Ruby from source (mise uses ruby-build under the hood and
# does not use the distro Ruby package).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    build-essential \
    autoconf \
    libffi-dev \
    libgdbm-dev \
    libncurses-dev \
    libreadline-dev \
    libssl-dev \
    libyaml-dev \
    zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

ENV MISE_DATA_DIR=/opt/mise
ENV MISE_CONFIG_DIR=/opt/mise/config
ENV MISE_CACHE_DIR=/opt/mise/cache
ENV MISE_YES=1
ENV PATH="/opt/mise/shims:/opt/mise/bin:${PATH}"

# Install mise itself into /opt/mise/bin
RUN curl -fsSL https://mise.jdx.dev/install.sh | MISE_INSTALL_PATH=/opt/mise/bin/mise sh

# Copy only the files mise and bundler need from the build context.
# .mise.toml pins the uv and Ruby versions; the Gemfile(s) declare the riscv-unified-db gem. No full repo clone needed.
COPY .mise.toml /tmp/act/
COPY framework/src/act/data/Gemfile framework/src/act/data/Gemfile.lock /tmp/act/

# Install uv and Ruby at the versions pinned in .mise.toml.
# Tools land in /opt/mise/installs/, shims in /opt/mise/shims/.
RUN cd /tmp/act && mise install

# Pre-install the riscv-unified-db gem into the mise-managed Ruby's gem dir so `bundle install` is a no-op at runtime
RUN cd /tmp/act && mise exec -- bundle install --gemfile=Gemfile

# Stage 4: final runtime image
FROM ubuntu:24.04

LABEL description="RISC-V Architectural Certification Tests (ACT4) build env"
LABEL org.opencontainers.image.source="https://github.com/riscv/riscv-arch-test"

ARG DEBIAN_FRONTEND=noninteractive
ARG TZ=UTC
ARG RISCV_TOOLCHAIN_PREFIX
ARG SAIL_PREFIX

ENV TZ="${TZ}"
ENV RISCV_TOOLCHAIN_PREFIX="${RISCV_TOOLCHAIN_PREFIX}"
ENV SAIL_PREFIX="${SAIL_PREFIX}"
ENV XDG_CACHE_HOME=/opt/cache

# mise environment — must match mise-fetcher stage
ENV MISE_DATA_DIR=/opt/mise
ENV MISE_CONFIG_DIR=/opt/mise/config
ENV MISE_CACHE_DIR=/opt/mise/cache
ENV MISE_YES=1
# Writable by any user for mise and other tools to store data
ENV HOME=/tmp/home

# Full PATH: RISC-V toolchain → Sail → mise shims (uv, ruby, bundle, …) → mise itself
ENV PATH="${RISCV_TOOLCHAIN_PREFIX}/bin:${SAIL_PREFIX}/bin:/opt/mise/shims:/opt/mise/bin:${PATH}"

# Runtime-only packages:
#   - python3: uv-managed venvs need a system Python as fallback
#   - make, git, ca-certificates: drive the ACT4 Makefile
#   - lib*: Ruby runtime shared libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    make \
    python3 \
    libffi8 \
    libgdbm6t64 \
    libncurses6 \
    libreadline8t64 \
    libssl3 \
    libyaml-0-2 \
    zlib1g \
 && rm -rf /var/lib/apt/lists/* \
 && ldconfig

COPY --from=toolchain-builder "${RISCV_TOOLCHAIN_PREFIX}" "${RISCV_TOOLCHAIN_PREFIX}"
COPY --from=sail-fetcher      "${SAIL_PREFIX}"            "${SAIL_PREFIX}"
COPY --from=mise-fetcher      /opt/mise                   /opt/mise
# For some crazy reason udb isn't using normally installed libz3 and instead reaches to its cache 😞
COPY --from=mise-fetcher      /root/.cache/udb            "${XDG_CACHE_HOME}/udb"

# Fix cache ownership so that any user can use it
RUN chown -R nobody:nogroup "${XDG_CACHE_HOME}" && chmod -R 777 "${XDG_CACHE_HOME}"

# Use --system so the safe.directory setting is visible to all users, not just root
RUN git config --system --add safe.directory /mnt \
 && git config --system --add safe.directory /mnt/external/riscv-unified-db

# Smoke-test: verify all the binaries landed correctly (runs as root during build, before USER switch)
RUN riscv64-unknown-elf-gcc --version \
 && sail_riscv_sim --version \
 && mise --version

USER ubuntu

WORKDIR /mnt

CMD ["/bin/bash"]
