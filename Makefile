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
EXCLUDE_EXTENSIONS ?= Sm,S,InterruptsSm,ExceptionsZalrsc,ExceptionsZaamo,PMPSm,PMPZca,PMPmisaligned,Sv,Svade,Svadu,SvaduPMP,SvPMP,SvZicbo

# DEBUG and FAST are runtime options for controlling build output. They are mutually exclusive. Set to True to enable either option.
# DEBUG enables debug output (signature objdump and trace files). This will slow down ELF generation significantly.
# FAST disables objdump generation for faster builds. This speeds up ELF generation significantly, but makes debugging mismatches harder.
DEBUG       ?=
FAST        ?=

# COVERAGE_SIMULATOR is only used when collecting coverage (make coverage)
COVERAGE_SIMULATOR ?= questa # Coverage simulator backend: questa or vcs

# Number of parallel build jobs for test compilation.
# Automatically derived from make's -j or --jobs flag (e.g., make -j4). Can be overridden with JOBS=N.
# 0 (default) = auto-detect CPU count.
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
# Check if UV is installed and set UV variable
UV := $(shell command -v uv 2> /dev/null)
ifneq ($(UV),)
  UV_RUN := $(UV) run
else
  UV_RUN :=
  $(warning "Warning: 'uv' command not found. Running scripts without UV, but there may be dependency issues.")
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
		$(if $(COVERAGE),--coverage) \
		$(if $(COVERAGE),--coverage-simulator $(COVERAGE_SIMULATOR))

.PHONY: clean
clean: clean-tests
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
# Run all tests
.PHONY: regression
regression:
	$(MAKE) clean
	@exit_code=0; \
	$(MAKE) coverage || exit_code=1; \
	$(foreach sim,$(SIMULATORS),$(MAKE) $(sim) || exit_code=1; ) \
	exit $$exit_code



########### Simulators ###########
# Run commands are driven from config files:
#   config/<simulator>/<config>/run_cmd.txt  — the shell command to run ELFs
#
# Targets are auto-generated from the discovered run_cmd.txt files:
#   make spike-rv64-max        — build ELFs and run tests for a single config
#   make spike                 — build and run all configs for a simulator
#   make regression            — run all simulators
#
# Note on escaping in the define blocks below:
#   $$ is needed to defer expansion to recipe execution time (standard Make escaping).
#   $$$$ produces a literal $$ in the shell, which is needed for command substitution
#   inside shell commands that are themselves inside Make $(foreach) expansions.

# Find all configs that provide a run command
RUN_CMD_FILES := $(shell find config -name run_cmd.txt)

# Extract unique simulator names from the second path component
# e.g., config/spike/spike-rv64-max/run_cmd.txt -> spike
SIMULATORS := $(sort $(foreach f,$(RUN_CMD_FILES),$(word 2,$(subst /, ,$(f)))))

# Extract unique config names from the leaf directory of each run_cmd.txt path
# e.g., config/spike/spike-rv64-max/run_cmd.txt -> spike-rv64-max
ALL_CONFIGS := $(sort $(foreach f,$(RUN_CMD_FILES),$(notdir $(patsubst %/run_cmd.txt,%,$(f)))))

# --- Helper functions ---

# Look up the full config directory path for a config name
# e.g., $(call config-dir,spike-rv64-max) -> config/spike/spike-rv64-max
config-dir = $(patsubst %/run_cmd.txt,%,$(filter %/$1/run_cmd.txt,$(RUN_CMD_FILES)))

# Get all run_cmd.txt paths for a given simulator
# e.g., $(call sim-run-cmds,spike) -> config/spike/spike-rv32-max/run_cmd.txt config/spike/spike-rv64-max/run_cmd.txt
sim-run-cmds = $(filter config/$1/%,$(RUN_CMD_FILES))

# Get all test_config.yaml paths for a given simulator (replacing run_cmd.txt with test_config.yaml)
sim-test-configs = $(patsubst %/run_cmd.txt,%/test_config.yaml,$(call sim-run-cmds,$1))

# Get all config names (leaf directories) for a given simulator
# e.g., $(call sim-config-names,spike) -> spike-rv32-max spike-rv64-max
sim-config-names = $(foreach f,$(call sim-run-cmds,$1),$(notdir $(patsubst %/run_cmd.txt,%,$(f))))

# --- Per-config targets (make <config-name>) ---
# Generates tests, builds ELFs for a single config, and runs them.
.PHONY: $(ALL_CONFIGS)

define config-target
$(1): EXTENSIONS =
$(1): tests
	$$(eval _DIR := $$(call config-dir,$(1)))
	@EXTENSIONS="" \
	CONFIG_FILES="$$(_DIR)/test_config.yaml" \
	$$(MAKE) elfs
	./run_tests.py "$$$$(cat $$(_DIR)/run_cmd.txt)" $$(WORKDIR)/$(1)/elfs
endef

$(foreach cfg,$(ALL_CONFIGS),$(eval $(call config-target,$(cfg))))

# --- Per-simulator targets (make <simulator>) ---
# Generates tests, builds ELFs for all of a simulator's configs, then runs each one.
# Continues through failures and reports a non-zero exit code if any run failed.
define sim-target
.PHONY: $(1)
$(1): tests
	CONFIG_FILES="$(call sim-test-configs,$(1))" \
	$$(MAKE) elfs
	@exit_code=0; \
	$(foreach cfg,$(call sim-config-names,$(1)),\
	  ./run_tests.py "$$$$(cat $$(call config-dir,$(cfg))/run_cmd.txt)" $$(WORKDIR)/$(cfg)/elfs || exit_code=1; ) \
	exit $$$$exit_code
endef

$(foreach sim,$(SIMULATORS),$(eval $(call sim-target,$(sim))))



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
