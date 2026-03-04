# Makefile for RISC-V Conformance Test Plan (CTP)
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
# the documentation for the RISC-V Certification Test Plan. It supports multiple
# build targets for generating documentation in various formats (PDF, HTML).

REPO_ROOT := $(shell git rev-parse --show-toplevel)
DOCS := ctp

DATE ?= $(shell date +%Y-%m-%d)
VERSION ?= v0.0.0
REVMARK ?= Draft
DOCKER_BIN ?= docker
DOCKER_INTERACTIVE=$(shell [ -t 0 ] && echo "-it --init")
SKIP_DOCKER ?= $(shell if command -v ${DOCKER_BIN}  >/dev/null 2>&1 ; then echo false; else echo true; fi)
DOCKER_IMG := ghcr.io/riscv/riscv-docs-base-container-image:latest
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

    DOCKER_CMD = \
        ${DOCKER_BIN} run --rm \
            ${DOCKER_INTERACTIVE} \
            -v ${PWD}/$@.workdir:/build${DOCKER_VOL_SUFFIX} \
            -v ${PWD}/src:/src:ro${DOCKER_EXTRA_VOL_SUFFIX} \
            -v ${PWD}/$(GENERATED_DIR):/build/generated:ro${DOCKER_EXTRA_VOL_SUFFIX} \
            -v ${PWD}/../common:/common:ro${DOCKER_EXTRA_VOL_SUFFIX} \
            -v ${PWD}/../docs-resources:/docs-resources:ro${DOCKER_EXTRA_VOL_SUFFIX} \
            -w /build \
            $(DOCKER_USER_ARG) \
            ${DOCKER_IMG} \
            /bin/sh -c
    DOCKER_QUOTE := "
else
    DOCKER_CMD = \
        cd $@.workdir &&
endif

ifdef UNRELIABLE_BUT_FASTER_INCREMENTAL_BUILDS
WORKDIR_SETUP = \
    mkdir -p $@.workdir/src && \
    ln -sfn $(patsubst %,../../../%,$(wildcard src/*.adoc)) $@.workdir/src/ && \
    ln -sfn ../../../$(GENERATED_DIR)/testplans ../../../$(GENERATED_DIR)/norm ../../../$(GENERATED_DIR)/param $@.workdir/src/ && \
    ln -sfn ../../common ../../docs-resources $@.workdir/
WORKDIR_TEARDOWN = mv $@.workdir/$@ $@
else
WORKDIR_SETUP = \
    rm -rf $@.workdir && \
    mkdir -p $@.workdir/src && \
    ln -sfn $(patsubst %,../../../%,$(wildcard src/*.adoc)) $@.workdir/src/ && \
    ln -sfn ../../../$(GENERATED_DIR)/testplans ../../../$(GENERATED_DIR)/norm ../../../$(GENERATED_DIR)/param $@.workdir/src/ && \
    ln -sfn ../../common ../../docs-resources $@.workdir/

WORKDIR_TEARDOWN = \
    mv $@.workdir/$@ $@ && \
    rm -rf $@.workdir
endif

SRC_DIR := src
BUILD_DIR := build
GENERATED_DIR := $(BUILD_DIR)/generated

DOCS_PDF := $(addprefix $(BUILD_DIR)/, $(addsuffix .pdf, $(DOCS)))
DOCS_HTML := $(addprefix $(BUILD_DIR)/, $(addsuffix .html, $(DOCS)))

ENV := LANG=C.utf8
XTRA_ADOC_OPTS :=

ASCIIDOCTOR_PDF := $(ENV) asciidoctor-pdf
ASCIIDOCTOR_HTML := $(ENV) asciidoctor

OPTIONS := --trace \
           -a compress \
           -a pdf-fontsdir=docs-resources/fonts \
           -a pdf-theme=docs-resources/themes/riscv-pdf.yml \
           $(XTRA_ADOC_OPTS) \
           -a revnumber=${VERSION} \
           -a revremark=${REVMARK} \
           -a revdate=${DATE} \
           -a docinfo=shared \
           -D build \
           --failure-level=WARN
REQUIRES := --require=asciidoctor-diagram \
            --require=asciidoctor-lists

.PHONY: all build clean build-container build-no-container build-docs build-pdf build-html docker-pull-latest submodule-check

all: build

# Check if the docs-resources/global-config.adoc file exists. If not, the user forgot to check out submodules.
ifeq ("$(wildcard ../docs-resources/global-config.adoc)","")
  $(warning You must clone with --recurse-submodules to automatically populate the submodule 'docs-resources'.")
  $(warning Checking out submodules for you via 'git submodule update --init --recursive'...)
  $(shell git submodule update --init --recursive)
endif

build-pdf: $(DOCS_PDF)
build-html: $(DOCS_HTML)
build: build-pdf build-html

ALL_SRCS := $(shell git ls-files $(SRC_DIR))

$(BUILD_DIR)/%.pdf: $(SRC_DIR)/%.adoc $(ALL_SRCS) testplans normrules
	$(WORKDIR_SETUP)
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_PDF) $(OPTIONS) $(REQUIRES) $< $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)
	@echo -e '\n  Built \e]8;;file://$(abspath $@)\e\\$@\e]8;;\e\\\n'

$(BUILD_DIR)/%.html: $(SRC_DIR)/%.adoc $(ALL_SRCS) testplans normrules
	$(WORKDIR_SETUP)
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_HTML) $(OPTIONS) $(REQUIRES) $< $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)
	@echo -e '\n  Built \e]8;;file://$(abspath $@)\e\\$@\e]8;;\e\\\n'

# Make CSV testplans into more readable asciidoc tables by
# transposing them to one instruction per column, separating
# into at most 10 instructions per page, and trimming unused
# coverpoints
TESTPLANS := $(wildcard $(REPO_ROOT)/testplans/*)
testplans: $(TESTPLANS)
	@echo "Generating test plan tables..."
	@if [ -d $(REPO_ROOT)/testplans ]; then \
		rm -rf $(GENERATED_DIR)/testplans; \
		$(REPO_ROOT)/generators/ctp/transpose_csv.py $(REPO_ROOT)/testplans $(GENERATED_DIR)/testplans 10; \
	else \
		echo "No test plans directory found in source."; \
	fi
	@echo "Test plan tables generated."

normrules:
	@echo "Generating normative rule tables...."
	$(REPO_ROOT)/generators/ctp/generate_norm_table.py --yaml $(REPO_ROOT)/coverpoints/norm/ --out $(GENERATED_DIR)/norm --report mismatch_report.txt
	@echo "Generating parameter rule tables...."
	$(REPO_ROOT)/generators/ctp/generate_param_table.py --yaml $(REPO_ROOT)/coverpoints/param --udb $(REPO_ROOT)/external/riscv-unified-db/spec/std/isa/param --norm-dir $(GENERATED_DIR)/norm --out $(GENERATED_DIR)/param/

# Update docker image to latest
docker-pull-latest:
	${DOCKER_BIN} pull ${DOCKER_IMG}

clean:
	@echo "Cleaning up generated files..."
	rm -rf $(BUILD_DIR)
	@echo "Cleanup completed."
