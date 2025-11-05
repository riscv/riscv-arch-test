# Jordan Carlin jcarlin@hmc.edu
# Sept 10, 2025
# SPDX-License-Identifier: Apache-2.0

# Directories and files
CONFIG_FILE ?= configs/duts/cvw/cvw-rv32gc/test_config.yaml
REF_CONFIG_FILES ?= configs/ref/sail-rv32gc/test_config.yaml
WORKDIR     ?= work
WORKDIR_REF ?= work-ref

TESTDIR        := tests
SRCDIR64       := $(TESTDIR)/rv64
SRCDIR32       := $(TESTDIR)/rv32
PRIVDIR        := $(TESTDIR)/priv
PRIVHEADERSDIR := $(PRIVDIR)/headers
PRIVDIR64      := $(PRIVDIR)/rv64
PRIVDIR32      := $(PRIVDIR)/rv32

TEMPLATEDIR := templates
TESTGEN_SRC_DIR := generators/tests/testgen/src/testgen
COVERGROUPGEN_SRC_DIR := generators/coverage/templates
TESTGEN_DEPS := $(wildcard $(TESTGEN_SRC_DIR)/* $(TESTGEN_SRC_DIR)/**/*)
COVERGROUPGEN_DEPS := $(wildcard $(COVERGROUPGEN_SRC_DIR)/* $(COVERGROUPGEN_SRC_DIR)/**)
TESTPLANS_DIR	:= testplans
TESTPLANS := $(wildcard $(TESTPLANS_DIR)/*.csv $(TESTPLANS_DIR)/**/*.csv)

STAMP_DIR := $(WORKDIR)/stamps

# Check if UV is installed and set UV variable
UV := $(shell command -v uv 2> /dev/null)
ifneq ($(UV),)
		UV_RUN := $(UV) run
else
		UV_RUN :=
		$(warning "Warning: 'uv' command not found. Running scripts without UV, but there may be dependency issues.")
endif

.DEFAULT_GOAL := elfs

###### Test compilation targets ######
.PHONY: elfs
elfs: generate-makefiles-dut Makefile
	$(MAKE) -C $(WORKDIR) compile

.PHONY: generate-makefiles-dut
generate-makefiles-dut: # too many dependencies to track; always regenerate Makefile
	$(MAKE) tests
	$(UV_RUN) act $(CONFIG_FILE) --workdir $(WORKDIR) --test-dir $(TESTDIR)

.PHONY: clean
clean: clean-tests clean-ref
	rm -rf $(WORKDIR)

###### Test generation targets ######
.PHONY: covergroupgen
covergroupgen: $(STAMP_DIR)/covergroupgen.stamp
$(STAMP_DIR)/covergroupgen.stamp: generators/coverage/covergroupgen.py $(COVERGROUPGEN_DEPS) $(TESTPLANS) Makefile | $(STAMP_DIR)
	$(UV_RUN) generators/coverage/covergroupgen.py
	touch $@

.PHONY: testgen
testgen:  $(STAMP_DIR)/testgen.stamp
$(STAMP_DIR)/testgen.stamp: $(TESTGEN_DEPS) Makefile | $(STAMP_DIR)
	$(UV_RUN) testgen testplans -o tests -e M
	rm -rf $(SRCDIR64)/E $(SRCDIR32)/E
	touch $@

.PHONY: privheaders
privheaders: $(STAMP_DIR)/csrtests.stamp $(STAMP_DIR)/illegalinstrtests.stamp

$(STAMP_DIR)/csrtests.stamp: generators/tests/scripts/csrtests.py Makefile | $(PRIVHEADERSDIR) $(STAMP_DIR)
	$(UV_RUN) generators/tests/scripts/csrtests.py
	touch $@

$(STAMP_DIR)/illegalinstrtests.stamp: generators/tests/scripts/illegalinstrtests.py Makefile | $(PRIVHEADERSDIR) $(STAMP_DIR)
	$(UV_RUN) generators/tests/scripts/illegalinstrtests.py
	touch $@

.PHONY: tests
tests: covergroupgen testgen privheaders

.PHONY: clean-tests
clean-tests:
	rm -rf $(SRCDIR64) $(SRCDIR32) $(PRIVHEADERSDIR) $(PRIVDIR64) $(PRIVDIR32)
	rm -rf fcov/unpriv/*
	rm -rf $(STAMP_DIR)

$(PRIVHEADERSDIR) $(STAMP_DIR):
	mkdir -p $@

###### Coverage targets ######
.PHONY: generate-makefiles-ref
generate-makefiles-ref: # too many dependencies to track; always regenerate Makefile
	$(MAKE) tests
	$(UV_RUN) act $(REF_CONFIG_FILES) --workdir $(WORKDIR_REF) --test-dir $(TESTDIR) --coverage
.PHONY: coverage

coverage: generate-makefiles-ref Makefile
	$(MAKE) -C $(WORKDIR_REF) coverage

.PHONY: clean-ref
clean-ref:
	rm -rf $(WORKDIR_REF)

# Dev targets
.PHONY: lint
lint:
	$(UV_RUN) ruff check
	$(UV_RUN) pyright

.PHONY: format
format:
	$(UV_RUN) ruff format
