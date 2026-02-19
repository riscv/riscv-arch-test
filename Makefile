# Jordan Carlin jcarlin@hmc.edu
# Sept 10, 2025
# SPDX-License-Identifier: Apache-2.0

# Directories and files
# CONFIG_FILES is used as the default input configs when running `make` and will produce elfs in the `work/<config-name>/elfs` directory.
# COVERAGE_CONFIG_FILES is used as the default input configs when running `make coverage` and will generate coverage reports in addition to the elfs.
CONFIG_FILES ?= config/qemu/qemu-rv64-max/test_config.yaml config/qemu/qemu-rv32-max/test_config.yaml
COVERAGE_CONFIG_FILES ?= config/sail/sail-rv64-max/test_config.yaml config/sail/sail-rv32-max/test_config.yaml

WORKDIR     ?= work
EXTENSIONS  ?= I,M # Extensions to generate tests for. Leave blank to generate for all tests.
EXCLUDE_EXTENSIONS ?= # Extensions to exclude from test generation. Applies as a negative filter after EXTENSIONS.
DEBUG       ?= # Set to True to generate debug output (signature objdump and trace files). Leave blank for no debug output.

TESTDIR        := tests
SRCDIR64       := $(TESTDIR)/rv64i
SRCDIR64E      := $(TESTDIR)/rv64e
SRCDIR32       := $(TESTDIR)/rv32i
SRCDIR32E      := $(TESTDIR)/rv32e
PRIVDIR        := $(TESTDIR)/priv
PRIVHEADERSDIR := $(PRIVDIR)/headers

TEMPLATEDIR := templates
TESTGEN_SRC_DIR := generators/testgen
COVERGROUPGEN_SRC_DIR := generators/coverage
TESTGEN_DEPS := $(shell find $(TESTGEN_SRC_DIR) -type f)
COVERGROUPGEN_DEPS := $(shell find $(COVERGROUPGEN_SRC_DIR) -type f)
TESTPLANS_DIR := testplans
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


##### Spike test targets #####
.PHONY: spike spike-rv32 spike-rv64

spike: CONFIG_FILES = config/spike/spike-rv32-max/test_config.yaml config/spike/spike-rv64-max/test_config.yaml
SPIKE_ISA := imafdcbv_zicbom_zicboz_zicbop_zicfilp_zicond_zicsr_zicclsm_zifencei_zihintntl_zihintpause_zihpm_zimop_zabha_zacas_zawrs_zfa_zfbfmin_zfh_zcb_zcmop_zbc_zkn_zks_zkr_zvfbfmin_zvfbfwma_zvfh_zvbb_zvbc_zvkg_zvkned_zvknha_zvknhb_zvksed_zvksh_zvkt_sscofpmf_smcntrpmf_sstc_svinval
spike: elfs
	@exit_code=0; \
	./run_tests.py "spike --isa=rv64$(SPIKE_ISA)" $(WORKDIR)/spike-rv64-max/elfs || exit_code=1; \
	./run_tests.py "spike --isa=rv32$(SPIKE_ISA)" $(WORKDIR)/spike-rv32-max/elfs || exit_code=1; \
	exit $$exit_code

spike-rv32: CONFIG_FILES = config/spike/spike-rv32-max/test_config.yaml
spike-rv32: elfs
	./run_tests.py "spike --isa=rv32$(SPIKE_ISA)" $(WORKDIR)/spike-rv32-max/elfs

spike-rv64: CONFIG_FILES = config/spike/spike-rv64-max/test_config.yaml
spike-rv64: elfs
	./run_tests.py "spike --isa=rv64$(SPIKE_ISA)" $(WORKDIR)/spike-rv64-max/elfs


##### QEMU test targets #####
.PHONY: qemu qemu-rv32 qemu-rv64

# -semihosting is needed for test termination
# -icount shift=1 ensures accurate values for instret
# pmu-mask sets the number of hpmcounters
QEMU_RV64_CMD := qemu-system-riscv64 -nographic -semihosting -icount shift=1 -machine virt -cpu max,pmu-mask=0xfffffff8 -bios
QEMU_RV32_CMD := qemu-system-riscv32 -nographic -semihosting -icount shift=1 -machine virt -cpu max,pmu-mask=0xfffffff8 -bios

qemu: CONFIG_FILES = config/qemu/qemu-rv32-max/test_config.yaml config/qemu/qemu-rv64-max/test_config.yaml
qemu: elfs
	@exit_code=0; \
	./run_tests.py "$(QEMU_RV64_CMD)" $(WORKDIR)/qemu-rv64-max/elfs || exit_code=1; \
	./run_tests.py "$(QEMU_RV32_CMD)" $(WORKDIR)/qemu-rv32-max/elfs || exit_code=1; \
	exit $$exit_code

qemu-rv32: CONFIG_FILES = config/qemu/qemu-rv32-max/test_config.yaml
qemu-rv32: elfs
	./run_tests.py "$(QEMU_RV32_CMD)" $(WORKDIR)/qemu-rv32-max/elfs

qemu-rv64: CONFIG_FILES = config/qemu/qemu-rv64-max/test_config.yaml
qemu-rv64: elfs
	./run_tests.py "$(QEMU_RV64_CMD)" $(WORKDIR)/qemu-rv64-max/elfs


###### Test compilation targets ######
.PHONY: elfs
elfs: generate-makefiles Makefile
	$(MAKE) -C $(WORKDIR) compile

.PHONY: generate-makefiles
generate-makefiles: # too many dependencies to track; always regenerate Makefile
	$(MAKE) tests
	$(UV_RUN) act $(CONFIG_FILES) \
		--workdir $(WORKDIR) \
		--test-dir $(TESTDIR) \
		$(if $(EXTENSIONS),--extensions $(EXTENSIONS)) \
		$(if $(EXCLUDE_EXTENSIONS),--exclude $(EXCLUDE_EXTENSIONS)) \
		$(if $(DEBUG),--debug) \
		$(if $(COVERAGE),--coverage)

.PHONY: clean
clean: clean-tests
	@if [ -d $(WORKDIR) ]; then \
		find $(WORKDIR) \( -type f -o -type l \) ! -name 'extensions.txt' -delete; \
		find $(WORKDIR) -type d -empty -delete; \
	fi

###### Test generation targets ######
.PHONY: covergroupgen
covergroupgen: $(STAMP_DIR)/covergroupgen.stamp
$(STAMP_DIR)/covergroupgen.stamp: $(COVERGROUPGEN_DEPS) $(TESTPLANS) Makefile | $(STAMP_DIR)
	$(UV_RUN) generators/coverage/covergroupgen.py
	@touch $@

.PHONY: testgen
testgen: $(STAMP_DIR)/testgen.stamp
$(STAMP_DIR)/testgen.stamp: $(TESTGEN_DEPS) $(TESTPLANS) Makefile | $(STAMP_DIR)
	$(UV_RUN) testgen testplans -o tests $(if $(EXTENSIONS),--extensions $(EXTENSIONS)) $(if $(EXCLUDE_EXTENSIONS),--exclude $(EXCLUDE_EXTENSIONS))
	@touch $@

.PHONY: vector-testgen
vector-testgen: $(STAMP_DIR)/vector-testgen-unpriv.stamp
$(STAMP_DIR)/vector-testgen-unpriv.stamp: generators/testgen/scripts/vector-testgen-unpriv.py generators/testgen/scripts/vector_testgen_common.py Makefile | $(STAMP_DIR)
	$(UV_RUN) generators/testgen/scripts/vector-testgen-unpriv.py
	touch $@

.PHONY: privheaders
privheaders: $(STAMP_DIR)/csrtests.stamp $(STAMP_DIR)/illegalinstrtests.stamp

$(STAMP_DIR)/csrtests.stamp: generators/testgen/scripts/csrtests.py Makefile | $(PRIVHEADERSDIR) $(STAMP_DIR)
	$(UV_RUN) generators/testgen/scripts/csrtests.py
	@touch $@

$(STAMP_DIR)/illegalinstrtests.stamp: generators/testgen/scripts/illegalinstrtests.py Makefile | $(PRIVHEADERSDIR) $(STAMP_DIR)
	$(UV_RUN) generators/testgen/scripts/illegalinstrtests.py
	@touch $@

.PHONY: tests
tests: covergroupgen testgen privheaders

.PHONY: clean-tests
clean-tests:
	rm -rf $(SRCDIR64) $(SRCDIR32) $(SRCDIR64E) $(SRCDIR32E) $(PRIVHEADERSDIR)
	rm -rf fcov/unpriv/*
	rm -rf $(STAMP_DIR)

$(PRIVHEADERSDIR) $(STAMP_DIR):
	mkdir -p $@

###### Coverage targets ######
.PHONY: coverage
coverage: COVERAGE := True
coverage: CONFIG_FILES := $(COVERAGE_CONFIG_FILES)
coverage: generate-makefiles Makefile
	$(MAKE) -C $(WORKDIR) coverage

##### Dev targets #####
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

###### Vector coverage targets ######
.PHONY: vector-tests
vector-tests: covergroupgen vector-testgen
