# SPDX-License-Identifier: BSD-3-Clause
# place to build compiled files ref.elf (etc, eventually, when someone tells me what they should be!)
WORKDIR   := /tmp/tests/
             
# SRCDIR = /usr/local/src/cvw-main/tests/, used as anchor in recursion
SRCDIR    := $(CURDIR)
# this Makefile's pathname to tests/Makefile, used as anchor in recursion
MAKEFILE  := $(SRCDIR)/$(lastword $(MAKEFILE_LIST))
             
# subdirectories of source anchor directory for compiling from
SUBDIRS   :=  riscv-test-suite
# calculation of where the source .S is in the source hierarchy during recursion
# (also overwritten by recursive calls but should be right anyway)
SOURCE    := $(SRCDIR)/$(subst x$(strip $(WORKDIR)),,x$(CURDIR))
# defines needed for cpp macro expansion, will be 32 or 64 as rv32 or rv64 part of path
XLEN      := $(if $(findstring rv32,$(SOURCE)),32,64)
FLEN      := $(XLEN)
             
# for cpp, .h files for macro expansions
INCDIRS   := $(SRCDIR)/riscv-arch-test/riscv-test-suite/env/ \
             $(SRCDIR)/riscof/sail_cSim/env
CPP       := cpp
CPPFLAGS  := -DXLEN=$(XLEN) -DFLEN=$(XLEN) $(foreach d,$(INCDIRS),-I $d )
     
# for the linker
EMULATION := elf$(intcmp $(XLEN),32,16,32,64)briscv_$(intcmp $(XLEN),32,ilp16,ilp32,lp64)
LD        := riscv64-linux-gnu-ld
LDFLAGS   := -m $(EMULATION) \
             -T $(SRCDIR)/riscof/sail_cSim/env/link.ld
                               
# for the assembler
ARCH     := rv$(intcmp $(XLEN),32,16gb,32gb,64gbq)_zicbom_zicboz_zfh
ABI      := $(intcmp $(XLEN),32,ilp16,ilp32,lp64)
AS       := riscv64-linux-gnu-as
ASFLAGS  := -mbig-endian -march=$(ARCH) -mabi=$(ABI)
                               
all: tests
         
# Build the elf files (and so on? Eventually!) for testing in WORKDIR:
#  This rule launches this Makefile anew in each leaf subdir of WORKDIR;
#  INCDIRS, SRCDIR, MAKEFILE are preserved all the way down in the recursion;
#  VPATH is not used, SOURCE=SRCDIR/{} explicitly locates assembler .S file;
tests: root 
	cd $(SRCDIR) && find $(SUBDIRS) -name \*.S -type f -exec \
	$(MAKE) -f $(MAKEFILE)            \
	     -C $(strip $(WORKDIR))/{}    \
	     ref.elf                      \
	     MAKEFILE=$(MAKEFILE)         \
	     SOURCE=$(SRCDIR)/{}          \
	     INCDIRS="$(INCDIRS)"         \
	     SRCDIR="$(SRCDIR)"           \
	      \;

# Build WORKDIR directory hierarchy, mirroring SRCDIR
root:
	mkdir -p $(WORKDIR)
	cd $(SRCDIR) && find $(SUBDIRS) -name \*.S -exec mkdir -p $(strip $(WORKDIR))/{} \;

ref.elf: ref.o
	$(LD) $(LDFLAGS) -o $@  $<

ref.o : ref.s
	$(AS) $(ASFLAGS) -o $@ $<

ref.s : $(SOURCE)
	$(CPP) $(CPPFLAGS) -o $@ $<

.PRECIOUS: .s .S .elf
.PHONY : tests all clean distclean root

clean:
	find $(WORKDIR) -type f \
			-name '*.elf' \
			-exec rm -f {} \; \
		     -o -type f \
			-name '*.[soS]' \
			-exec rm -f {} \;

distclean: clean
