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
#   # Create work directory for outputs first, otherwise it will not be owned by the current user
#   mkdir work
#   # Start container if the user is typical 1000:1000
#   docker run -it --rm -v ./<vendor>:/act4/config/cores/<vendor>:ro -v ./work:/act4/work riscv-act4
#   # Or if your user does not have ID 1000
#   docker run -it --rm -u $(id -u):$(id -g) -v ./<vendor>:/act4/config/cores/<vendor>:ro -v ./work:/act4/work riscv-act4
#
#   Inside the container with the pre-cloned and ready to use repo root is at /act4; run:
#     CONFIG_FILES=config/cores/<vendor>/<dut>/test_config.yaml make

# Global ARGs - declared before any FROM so they are overridable across all stages.
# Each stage that uses them must redeclare them with a bare ARG (no default) to bring them into scope.
ARG RISCV_TOOLCHAIN_PREFIX=/opt/riscv
ARG SAIL_VERSION=0.11
ARG RISCV_TOOLCHAIN_VERSION=2026.04.26

# Stage 1: build riscv-gnu-toolchain
#
# LDFLAGS=-static ensures no shared-lib dependencies survive into the final image.
FROM ubuntu:24.04@sha256:c4a8d5503dfb2a3eb8ab5f807da5bc69a85730fb49b5cfca2330194ebcc41c7b AS toolchain-builder

ARG DEBIAN_FRONTEND=noninteractive
ARG RISCV_TOOLCHAIN_PREFIX
ARG RISCV_TOOLCHAIN_VERSION

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

RUN git clone --depth 1 --branch "${RISCV_TOOLCHAIN_VERSION}" https://github.com/riscv/riscv-gnu-toolchain /tmp/riscv-gnu-toolchain \
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

# Stage 2: install mise, then use it to install uv (Python) and Ruby, and pre-install the riscv-unified-db Bundler gem,
# and pre-download all Python dependencies via uv sync.
#
# mise reads .mise.toml from the repo to pin exact tool versions.
# We pre-warm both the gem cache and the uv virtualenv here so the first `make` inside the container doesn't need
# network access for Ruby or Python deps.
#
# HOME=/home/shared is used so all caches (mise, uv, udb, etc.) land in a single directory that is copied to the final
# image.
FROM ubuntu:24.04@sha256:c4a8d5503dfb2a3eb8ab5f807da5bc69a85730fb49b5cfca2330194ebcc41c7b AS mise-fetcher

ARG DEBIAN_FRONTEND=noninteractive

# mise needs curl + ca-certificates to download tools, build-essential is needed for installation of Ruby gems.
RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  build-essential \
  && rm -rf /var/lib/apt/lists/*

ENV MISE_YES=1 \
  HOME=/home/shared \
  PATH="/home/shared/.local/bin:${PATH}"

RUN mkdir -p /home/shared

# Install mise itself into ~/.local/bin
RUN curl -fsSL https://mise.jdx.dev/install.sh | sh

# Copy the full repo from the build context.
# mise and bundler need .mise.toml and the Gemfile(s); uv needs pyproject.toml / uv.lock.
COPY . /act4/

# Install uv and Ruby at the versions pinned in .mise.toml
# Pre-install the riscv-unified-db gem into the mise-managed Ruby's gem dir so `bundle install` is a no-op at runtime.
# Pre-download all Python dependencies so `uv sync` is a no-op at runtime.
RUN cd /act4 \
  && mise install \
  && mise exec -- bundle install --gemfile=framework/src/act/data/Gemfile \
  && mise exec -- uv sync

# Stage 3: final runtime image
FROM ubuntu:24.04@sha256:c4a8d5503dfb2a3eb8ab5f807da5bc69a85730fb49b5cfca2330194ebcc41c7b

LABEL description="RISC-V Architectural Certification Tests (ACT4) build env"
LABEL org.opencontainers.image.source="https://github.com/riscv/riscv-arch-test"

ARG DEBIAN_FRONTEND=noninteractive
ARG TZ=UTC
ARG RISCV_TOOLCHAIN_PREFIX
ARG SAIL_VERSION

ENV TZ="${TZ}" \
  SAIL_PREFIX=/opt/sail \
  MISE_YES=1 \
  HOME=/home/shared
ENV PATH="${RISCV_TOOLCHAIN_PREFIX}/bin:${SAIL_PREFIX}/bin:/home/shared/.local/bin:${PATH}"

# Runtime-only packages:
#   - make, ca-certificates: drive the ACT4 Makefile
#   - curl: required to fetch the sail-riscv release archive
RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  make \
  && rm -rf /var/lib/apt/lists/*

# Fetch and install sail-riscv directly into the final image
RUN SAIL_OS="$(uname -s)" \
  && SAIL_ARCH="$(uname -m)" \
  && mkdir -p "${SAIL_PREFIX}" \
  && curl --location --fail \
  "https://github.com/riscv/sail-riscv/releases/download/${SAIL_VERSION}/sail-riscv-${SAIL_OS}-${SAIL_ARCH}.tar.gz" \
  | tar xz --directory="${SAIL_PREFIX}" --strip-components=1

COPY --from=toolchain-builder "${RISCV_TOOLCHAIN_PREFIX}" "${RISCV_TOOLCHAIN_PREFIX}"
COPY --from=mise-fetcher      /act4                       /act4
COPY --from=mise-fetcher      /home/shared                /home/shared

# Fix home ownership so that any user can use it
RUN chmod -R 777 /act4 /home/shared

# Smoke-test: verify all the binaries landed correctly (runs as root during build, before USER switch)
RUN riscv64-unknown-elf-gcc --version \
  && sail_riscv_sim --version \
  && mise --version

# Default user with ID 1000 matching typical desktop installation
USER ubuntu

WORKDIR /act4

CMD ["/bin/bash"]
