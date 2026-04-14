# Jordan Carlin jcarlin@hmc.edu
# Created Sept 10, 2025
# Modified April 5, 2026
# SPDX-License-Identifier: Apache-2.0



########## Runtime Options ##########
# CONFIG_FILES is used as the default input configs when running `make` and will produce elfs in the `work/<config-name>/elfs` directory.
# COVERAGE_CONFIG_FILES is used as the default input configs when running `make coverage` and will generate coverage reports in addition to the elfs.
CONFIG_FILES ?= config/spike/spike-rv32-max/test_config.yaml config/spike/spike-rv64-max/test_config.yaml
COVERAGE_CONFIG_FILES ?= config/sail/sail-rv64-max/test_config.yaml config/sail/sail-rv32-max/test_config.yaml

# WORKDIR is where all of the generated files are created
WORKDIR     ?= work

# EXTENSIONS is a comma-separated list of extensions to generate tests for. Leave blank to generate for all tests.
# EXCLUDE_EXTENSIONS overrides EXTENSIONS to exclude particular extensions from test generation. Applies as a negative filter after EXTENSIONS.
# Default exclusion reasons:
#  - Sm, S: Insufficient WARL configuration options.
#  - Sv,Svade,Svadu,SvaduPMP,SvPMP,SvZicbo: sail-riscv missing support for Svade/Svadu causes mismatches. Resolved in upcoming sail-riscv release.
#  - ExceptionsZalrsc: See sail-riscv issue 1574. Resolved in upcoming sail-riscv release.
#  - ExceptionsZaamo: Configuration needed between access and misaligned faults
#  - InterruptsSm,PMPSm,PMPZca,PMPmisaligned: Additional testing needed on a wider range of configs. Some missing config options to match ref model.
EXTENSIONS  ?=
EXCLUDE_EXTENSIONS ?= Sm,S,InterruptsSm,InterruptsS,ExceptionsZalrsc,ExceptionsZaamo,PMPSm,PMPZca,PMPmisaligned,Sv,Svade,Svadu,SvaduPMP,SvPMP,SvZicbo,SvPMPZicbo

# Strip spaces from comma-separated lists so shell word-splitting doesn't break CLI arguments
empty :=
space := $(empty) $(empty)
override EXTENSIONS := $(subst $(space),$(empty),$(EXTENSIONS))
override EXCLUDE_EXTENSIONS := $(subst $(space),$(empty),$(EXCLUDE_EXTENSIONS))

# DEBUG, FAST, and VERBOSE are runtime options for controlling build output. DEBUG and FAST are mutually exclusive.
# DEBUG enables debug output (signature objdump, trace files, and trap report). This will slow down ELF generation significantly.
# FAST disables objdump generation for faster builds. This speeds up ELF generation significantly, but makes debugging mismatches harder.
# VERBOSE implies DEBUG, serializes all commands (JOBS=1), and prints each command as it is issued.
DEBUG       ?=
FAST        ?=
VERBOSE     ?=

# VERBOSE implies DEBUG and serializes the build
ifneq ($(VERBOSE),)
  DEBUG := True
	JOBS  := 1
endif

# COVERAGE_SIMULATOR is only used when collecting coverage (make coverage)
COVERAGE_SIMULATOR ?= questa # Coverage simulator backend: questa or vcs

# Number of parallel build jobs for test compilation.
# Automatically derived from make's -j or --jobs flag (e.g., make -j4). Can be overridden with JOBS=N.
# 0 (default) = auto-detect CPU count.
# Setting to 1 is helpful for debugging test hangs so that only a single test runs at a time.
JOBS ?= $(or $(patsubst -j%,%,$(filter -j%,$(MAKEFLAGS))),0)



########## Directories ##########
TESTDIR        := tests
SRCDIR64       := $(TESTDIR)/rv64i
SRCDIR64E      := $(TESTDIR)/rv64e
SRCDIR32       := $(TESTDIR)/rv32i
SRCDIR32E      := $(TESTDIR)/rv32e
PRIVDIR        := $(TESTDIR)/priv

COVERPOINT_DIR         := coverpoints
UNPRIV_COVERPOINTS_DIR := $(COVERPOINT_DIR)/unpriv
COVERAGE_HELPERS_DIR   := $(COVERPOINT_DIR)/coverage

TEMPLATEDIR := templates
TESTGEN_SRC_DIR := generators/testgen
COVERGROUPGEN_SRC_DIR := generators/coverage
TESTGEN_DEPS := $(shell find $(TESTGEN_SRC_DIR) -type f)
COVERGROUPGEN_DEPS := $(shell find $(COVERGROUPGEN_SRC_DIR) -type f)
TESTPLANS_DIR := testplans
TESTPLANS := $(wildcard $(TESTPLANS_DIR)/*.csv $(TESTPLANS_DIR)/**/*.csv)

STAMP_DIR := $(WORKDIR)/stamps
$(STAMP_DIR):
	@mkdir -p $@



########## Installation Check ##########
# Tool management — prefer mise, then uv, then an activated venv with the
# CLIs already installed. uv/mise always wins over VIRTUAL_ENV.
MISE := $(shell command -v mise 2> /dev/null)
UV   := $(shell command -v uv 2> /dev/null)

ifneq ($(MISE),)
  UV_RUN := $(MISE) exec -- uv run
else ifneq ($(UV),)
  UV_RUN := $(UV) run
else ifneq ($(VIRTUAL_ENV),)
  # Activated venv without uv/mise: require the three CLIs on PATH.
  MISSING_CLIS := $(strip $(foreach c,act testgen covergroupgen,\
                    $(if $(shell command -v $(c) 2> /dev/null),,$(c))))
  ifneq ($(MISSING_CLIS),)
    $(error Activated venv ($(VIRTUAL_ENV)) is missing required CLIs: $(MISSING_CLIS). Install with: pip install -e ./framework -e ./generators/testgen -e ./generators/coverage or use mise/uv)
  endif
  UV_RUN :=
else
  $(error Neither uv nor mise found, and no venv is activated. See the README (Prerequisites) for install options.)
endif

# Ruby/Bundler is required for the UDB gem whenever we are not going through mise.
ifeq ($(MISE),)
  BUNDLE := $(shell command -v bundle 2> /dev/null)
  ifeq ($(BUNDLE),)
    $(error Bundle not found. Ruby and Bundler are required for UDB. See the README for more information.)
  endif
endif



########## Test compilation ##########
.DEFAULT_GOAL := elfs
.PHONY: elfs
elfs: tests
	@$(UV_RUN) act $(CONFIG_FILES) \
		--workdir $(WORKDIR) \
		--test-dir $(TESTDIR) \
		--jobs $(JOBS) \
		$(if $(EXTENSIONS),--extensions $(EXTENSIONS)) \
		$(if $(EXCLUDE_EXTENSIONS),--exclude $(EXCLUDE_EXTENSIONS)) \
		$(if $(DEBUG),--debug) \
		$(if $(FAST),--fast) \
		$(if $(VERBOSE),--verbose) \
		$(if $(COVERAGE),--coverage) \
		$(if $(COVERAGE),--coverage-simulator $(COVERAGE_SIMULATOR))

.PHONY: clean
clean:
	@if [ -d $(WORKDIR) ]; then \
		find $(WORKDIR) \( -type f -o -type l \) ! -name 'extensions.txt' -delete; \
		find $(WORKDIR) -type d -empty -delete; \
	fi



########## Test generation ##########
.PHONY: covergroupgen
covergroupgen: $(STAMP_DIR)/covergroupgen.stamp
$(STAMP_DIR)/covergroupgen.stamp: $(COVERGROUPGEN_DEPS) $(TESTPLANS) Makefile | $(STAMP_DIR)
	@$(UV_RUN) covergroupgen testplans $(if $(EXTENSIONS),--extensions $(EXTENSIONS)) $(if $(EXCLUDE_EXTENSIONS),--exclude $(EXCLUDE_EXTENSIONS))
	@touch $@

.PHONY: testgen
testgen: $(STAMP_DIR)/testgen.stamp
$(STAMP_DIR)/testgen.stamp: $(TESTGEN_DEPS) $(TESTPLANS) Makefile | $(STAMP_DIR)
	@$(UV_RUN) testgen testplans -o tests --jobs $(JOBS) $(if $(EXTENSIONS),--extensions $(EXTENSIONS)) $(if $(EXCLUDE_EXTENSIONS),--exclude $(EXCLUDE_EXTENSIONS))
	@touch $@

.PHONY: vector-testgen
vector-testgen: $(STAMP_DIR)/vector-testgen-unpriv.stamp
$(STAMP_DIR)/vector-testgen-unpriv.stamp: generators/testgen/scripts/vector-testgen-unpriv.py generators/testgen/scripts/vector_testgen_common.py Makefile | $(STAMP_DIR)
	$(UV_RUN) generators/testgen/scripts/vector-testgen-unpriv.py
	touch $@

.PHONY: tests
tests: covergroupgen testgen

.PHONY: vector-tests
vector-tests: covergroupgen vector-testgen

.PHONY: clean-tests
clean-tests:
	rm -rf $(SRCDIR64) $(SRCDIR32) $(SRCDIR64E) $(SRCDIR32E)
	rm -rf $(UNPRIV_COVERPOINTS_DIR) $(COVERAGE_HELPERS_DIR)
	rm -rf $(STAMP_DIR)



########### Coverage ###########
# Just sets some variables and then runs the standard elfs target
.PHONY: coverage
coverage: COVERAGE := True
coverage: CONFIG_FILES := $(COVERAGE_CONFIG_FILES)
coverage: elfs



########### Regression ###########
# Clean, run coverage, then run all configs that have a run_cmd.txt, continuing through failures.
.PHONY: regression
regression: clean
	@exit_code=0; \
	$(MAKE) coverage || exit_code=1; \
	CONFIG_FILES="$(patsubst %/run_cmd.txt,%/test_config.yaml,$(RUN_CMD_FILES))" \
	$(MAKE) elfs || exit_code=1; \
	$(foreach f,$(RUN_CMD_FILES),\
	  ./run_tests.py $(if $(DEBUG),--debug) $(if $(VERBOSE),--verbose) "$$(cat $(f))" $(WORKDIR)/$(notdir $(patsubst %/run_cmd.txt,%,$(f)))/elfs || exit_code=1; ) \
	exit $$exit_code



########### Simulators ###########
# Targets are auto-generated from discovered run_cmd.txt files. Every directory name
# in the config path becomes a Make target that runs all configs beneath it:
#   make spike-rv64-max   — single config
#   make spike            — all spike configs
#   make cvw              — all cvw configs
#   make cores            — all configs under cores/
#
# Note on escaping: $$ defers expansion past $(eval $(call ...)); $$$$ yields a literal $ in the shell.

# Find all configs that provide a run command
RUN_CMD_FILES := $(shell find config -name run_cmd.txt)

# Map each directory name in the path to its run_cmd.txt files.
# e.g., config/cores/cvw/cvw-rv64gc/run_cmd.txt populates _TARGETS_cores, _TARGETS_cvw, _TARGETS_cvw-rv64gc
$(foreach f,$(RUN_CMD_FILES),\
  $(foreach d,$(filter-out config,$(subst /, ,$(patsubst %/run_cmd.txt,%,$(f)))),\
    $(eval _TARGETS_$(d) += $(f))))

# Collect all unique target names
ALL_RUN_TARGETS := $(sort $(foreach f,$(RUN_CMD_FILES),\
  $(filter-out config,$(subst /, ,$(patsubst %/run_cmd.txt,%,$(f))))))

# Each target generates tests, builds ELFs, and runs each config (continuing through failures).
.PHONY: $(ALL_RUN_TARGETS)

define run-target
$(1): tests
	CONFIG_FILES="$(patsubst %/run_cmd.txt,%/test_config.yaml,$(_TARGETS_$(1)))" \
	$$(MAKE) elfs
	@exit_code=0; \
	$(foreach f,$(_TARGETS_$(1)),\
	  ./run_tests.py $(if $(DEBUG),--debug) $(if $(VERBOSE),--verbose) "$$$$(cat $(f))" $$(WORKDIR)/$(notdir $(patsubst %/run_cmd.txt,%,$(f)))/elfs || exit_code=1; ) \
	exit $$$$exit_code
endef

$(foreach t,$(ALL_RUN_TARGETS),$(eval $(call run-target,$(t))))



########## Linting/Formatting ##########
.PHONY: lint
lint:
	$(UV_RUN) ruff check
	$(UV_RUN) pyright

.PHONY: lint-fix
lint-fix:
	$(UV_RUN) ruff check --fix

.PHONY: format
format:
	$(UV_RUN) ruff format
