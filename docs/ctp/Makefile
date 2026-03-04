# Makefile for RISC-V Doc Template
#
# This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
# International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to
# Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.
#
# SPDX-License-Identifier: CC-BY-SA-4.0
#
# Description:
#
# This Makefile is designed to automate the process of building and packaging
# the Doc Template for RISC-V Extensions.

REPO_ROOT := $(shell git rev-parse --show-toplevel)
DOCS := ctp

DATE ?= $(shell date +%Y-%m-%d)
VERSION ?= v0.0.0
REVMARK ?= Draft
DOCKER_IMG := docker.io/riscvintl/riscv-docs-base-container-image:latest
DOCKER_BIN ?= docker
ifneq ($(SKIP_DOCKER),true)
    DOCKER_IS_PODMAN = \
      $(shell ! ${DOCKER_BIN}  -v | grep podman >/dev/null ; echo $$?)
    ifeq "$(DOCKER_IS_PODMAN)" "1"
        # Modify the SELinux label for the host directory to indicate
        # that it can be shared with multiple containers. This is apparently
        # only required for Podman, though it is also supported by Docker.
        DOCKER_VOL_SUFFIX = :z
        DOCKER_EXTRA_VOL_SUFFIX = ,z
    else
        DOCKER_IS_ROOTLESS = \
            $(shell ! ${DOCKER_BIN} info -f '{{println .SecurityOptions}}' | grep rootless >/dev/null ; echo $$?)
        ifneq "$(DOCKER_IS_ROOTLESS)" "1"
            # Rooted Docker requires this flag so that the files it creates are
            # owned by the current user instead of root. Rootless docker does not
            # require it, and Podman doesn't either since it is always rootless.
            DOCKER_USER_ARG := --user $(shell id -u)
        endif
    endif

    DOCKER_CMD := \
        ${DOCKER_BIN} run --rm \
            -v ${PWD}/build:/build${DOCKER_VOL_SUFFIX} \
            -v ${PWD}/src:/build/src:ro${DOCKER_EXTRA_VOL_SUFFIX} \
            -v ${PWD}/../docs-resources:/build/docs-resources:ro${DOCKER_EXTRA_VOL_SUFFIX} \
            -w /build \
						${DOCKER_USER_ARG} \
            ${DOCKER_IMG} \
            /bin/sh -c
    DOCKER_QUOTE := "
else
    DOCKER_CMD = \
        cd build &&
endif

ARTIFACT_CLEANUP = mv build/$@ $@

SRC_DIR := src
BUILD_DIR := build

DOCS_PDF := $(addprefix $(BUILD_DIR)/, $(addsuffix .pdf, $(DOCS)))
DOCS_HTML := $(addprefix $(BUILD_DIR)/, $(addsuffix .html, $(DOCS)))

XTRA_ADOC_OPTS :=
ASCIIDOCTOR_PDF := asciidoctor-pdf
ASCIIDOCTOR_HTML := asciidoctor
OPTIONS := --trace \
           -a compress \
           -a mathematical-format=svg \
           -a revnumber=${VERSION} \
           -a revremark=${REVMARK} \
           -a revdate=${DATE} \
           -a pdf-fontsdir=docs-resources/fonts \
           -a pdf-theme=docs-resources/themes/riscv-pdf.yml \
           $(XTRA_ADOC_OPTS) \
		   		 -D build \
           --failure-level=ERROR
REQUIRES := --require=asciidoctor-diagram \
						--require=asciidoctor-lists \
            --require=asciidoctor-mathematical

.PHONY: all build clean build-container build-no-container build-docs

all: build

# Check if the docs-resources/global-config.adoc file exists. If not, the user forgot to check out submodules.
ifeq ("$(wildcard ../docs-resources/global-config.adoc)","")
  $(warning You must clone with --recurse-submodules to automatically populate the submodule 'docs-resources'.")
  $(warning Checking out submodules for you via 'git submodule update --init --recurse'...)
  $(shell git submodule update --init --recursive)
endif

build-pdf: $(DOCS_PDF)
build-html: $(DOCS_HTML)

build: build-pdf build-html
	rm -rf build/build build/docs-resources build/src

ALL_SRCS := $(shell git ls-files $(SRC_DIR))

$(BUILD_DIR)/%.pdf: $(SRC_DIR)/%.adoc $(ALL_SRCS) testplans normrules
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_PDF) $(OPTIONS) $(REQUIRES) $< $(DOCKER_QUOTE)
	$(ARTIFACT_CLEANUP)

$(BUILD_DIR)/%.html: $(SRC_DIR)/%.adoc $(ALL_SRCS) testplans normrules
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_HTML) $(OPTIONS) $(REQUIRES) $< $(DOCKER_QUOTE)
	$(ARTIFACT_CLEANUP)

# Make CSV testplans into more readable asciidoc tables by
# transposing them to one instruction per column, separating
# into at most 10 instructions per page, and trimming unused
# coverpoints
TESTPLANS := $(wildcard $(REPO_ROOT)/testplans/*)
testplans: $(TESTPLANS)
	@echo "Copying test plans..."
	@if [ -d $(REPO_ROOT)/testplans ]; then \
		rm -rf src/testplans; \
        mkdir -p build; \
		$(REPO_ROOT)/generators/ctp/transpose_csv.py $(REPO_ROOT)/testplans src/testplans 10; \
	else \
		echo "No test plans directory found in source."; \
	fi
	@echo "Test plans copied to build directory."

normrules:
	@echo "Generating normative rule tables...."
	$(REPO_ROOT)/generators/ctp/generate_norm_table.py --yaml $(REPO_ROOT)/coverpoints/norm/ --out $(SRC_DIR)/norm --report mismatch_report.txt
	@echo "Generating parameter rule tables...."
	$(REPO_ROOT)/generators/ctp/generate_param_table.py --yaml $(REPO_ROOT)/coverpoints/param --udb $(REPO_ROOT)/external/riscv-unified-db/spec/std/isa/param --out $(SRC_DIR)/param/

# Update docker image to latest
docker-pull-latest:
	${DOCKER_BIN} pull ${DOCKER_IMG}

clean:
	@echo "Cleaning up generated files..."
	rm -rf $(BUILD_DIR)
	@echo "Cleanup completed."
