# Makefile for CRDs
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
# the documentation for RVCP documentation. It supports multiple build targets
# for generating documentation in various formats (PDF, HTML).
#
# Building with a preinstalled docker container is recommended.
# Install by running:
#		make docker-pull-latest

REPO_ROOT := $(shell git rev-parse --show-toplevel)

SRC_DIR := src
BUILD_DIR := build
GENERATED_DIR := $(BUILD_DIR)/generated

DOCS := rvi20_crd mc100_crd
DOCS_PDF := $(addprefix $(BUILD_DIR)/, $(addsuffix .pdf, $(DOCS)))
DOCS_HTML := $(addprefix $(BUILD_DIR)/, $(addsuffix .html, $(DOCS)))

NORM_RULES_JSON := norm-rules.json

PARAMS_JSON_OUTPUT_FNAME := params.json
PARAMS_HTML_OUTPUT_FNAME := params.html

PARAMS_JSON := $(BUILD_DIR)/$(PARAMS_JSON_OUTPUT_FNAME)
PARAMS_HTML := $(BUILD_DIR)/$(PARAMS_HTML_OUTPUT_FNAME)

PARAM_DEF_DIR := param_defs

# All parameter definition input YAML files.
PARAM_DEF_FILES := $(wildcard $(PARAM_DEF_DIR)/*.yaml)

# Add --param-def to each parameter definition filename
PARAM_DEF_ARGS := $(foreach relative_pname,$(PARAM_DEF_FILES),--param-def $(relative_pname))

CREATE_PARAMS_TOOL := docs-resources/tools/create_params.py
CREATE_PARAMS_PYTHON := python3 $(CREATE_PARAMS_TOOL)

ENV := LANG=C.utf8
XTRA_ADOC_OPTS :=

ASCIIDOCTOR_PDF := $(ENV) asciidoctor-pdf
ASCIIDOCTOR_HTML := $(ENV) asciidoctor

OPTIONS := --trace \
           -a compress \
           -a mathematical-format=svg \
           -a pdf-fontsdir=docs-resources/fonts \
           -a pdf-theme=docs-resources/themes/riscv-pdf.yml \
           -a docinfo=shared \
           $(XTRA_ADOC_OPTS) \
           -D build \
           --failure-level=WARN
REQUIRES :=

DOCKER_BIN ?= docker
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
            -v ${PWD}/$@.workdir:/build${DOCKER_VOL_SUFFIX} \
            -v ${PWD}/src:/src:ro${DOCKER_EXTRA_VOL_SUFFIX} \
            -v ${PWD}/param_defs:/param_defs:ro${DOCKER_EXTRA_VOL_SUFFIX} \
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

WORKDIR_SETUP = \
    rm -rf $@.workdir && \
    mkdir -p $@.workdir $@.workdir/build $(GENERATED_DIR) && \
    ln -sfn ../../src ../../../common ../../../docs-resources ../../param_defs $@.workdir/

WORKDIR_TEARDOWN = \
    mv $@.workdir/$@ $@ && \
    rm -rf $@.workdir

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

ALL_SRCS := $(wildcard src/*.adoc) $(wildcard src/ext_defs/*.adoc) $(wildcard src/param_defs/*.adoc)

$(BUILD_DIR)/%.pdf: $(SRC_DIR)/%.adoc $(ALL_SRCS)
	$(WORKDIR_SETUP)
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_PDF) $(OPTIONS) $(REQUIRES) $< $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)
	@echo -e '\n  Built \e]8;;file://$(abspath $@)\e\\$@\e]8;;\e\\\n'

$(BUILD_DIR)/%.html: $(SRC_DIR)/%.adoc $(ALL_SRCS)
	$(WORKDIR_SETUP)
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(ASCIIDOCTOR_HTML) $(OPTIONS) $(REQUIRES) $< $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)
	@echo -e '\n  Built \e]8;;file://$(abspath $@)\e\\$@\e]8;;\e\\\n'

impldefs:
	@echo "Generating implementation-defined behavior tables...."
	mkdir -p $(GENERATED_DIR)
	$(REPO_ROOT)/generators/crd/generate_impl_def_table.py --norm-rules-path $(NORM_RULES_JSON) --out $(GENERATED_DIR)/all_impldefs.adoc

.PHONY: params
params: $(PARAMS_JSON) $(PARAMS_HTML)

# Build params JSON output from generated normative rules JSON and parameter definitions.
$(PARAMS_JSON): $(NORM_RULES_JSON) $(PARAM_DEF_FILES)
	$(WORKDIR_SETUP)
	cp -f $(NORM_RULES_JSON) $@.workdir
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(CREATE_PARAMS_PYTHON) --norm-rules $(NORM_RULES_JSON) $(PARAM_DEF_ARGS) --output $@ $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Build params HTML output from generated normative rules JSON and parameter definitions.
$(PARAMS_HTML): $(NORM_RULES_JSON) $(PARAM_DEF_FILES)
	$(WORKDIR_SETUP)
	cp -f $(NORM_RULES_JSON) $@.workdir
	$(DOCKER_CMD) $(DOCKER_QUOTE) $(CREATE_PARAMS_PYTHON) --html --norm-rules $(NORM_RULES_JSON) $(PARAM_DEF_ARGS) --output $@ $(DOCKER_QUOTE)
	$(WORKDIR_TEARDOWN)

# Update docker image to latest
docker-pull-latest:
	${DOCKER_BIN} pull ${DOCKER_IMG}

clean:
	@echo "Cleaning up generated files..."
	rm -rf $(BUILD_DIR)
	@echo "Cleanup completed."
