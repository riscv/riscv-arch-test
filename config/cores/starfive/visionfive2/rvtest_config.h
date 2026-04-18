// SPDX-License-Identifier: Apache-2.0
// rvtest_config.h — Supported extensions for StarFive VisionFive 2 (JH7110)
//
// JH7110 ISA: RV64GC (I, M, A, F, D, C extensions)
// Running under OpenSBI: S-mode and U-mode tests only.
// M-mode tests excluded (include_priv_tests: false in test_config.yaml).

// PMP: OpenSBI configures PMP entries at boot. Not directly controllable.
// Set grain and count to match JH7110 hardware (8 PMP entries, grain=0).
#define RVMODEL_PMP_GRAIN 0
#define RVMODEL_NUM_PMPS  8

// Base ISA extensions supported by JH7110
#define F_SUPPORTED
#define D_SUPPORTED

// Bit-manipulation (B extension = Zba + Zbb + Zbs on JH7110)
#define ZBA_SUPPORTED
#define ZBB_SUPPORTED
#define ZBS_SUPPORTED

// Atomics
#define ZAAMO_SUPPORTED
#define ZALRSC_SUPPORTED

// Compressed instructions
#define ZCA_SUPPORTED
#define ZCB_SUPPORTED
#define ZCD_SUPPORTED

// Counters (time CSR available via OpenSBI)
#define TIME_CSR_IMPLEMENTED 1

// Virtual memory: JH7110 supports Sv39 and Sv48
#define SV39_SUPPORTED
#define SV48_SUPPORTED

// Supervisor mode supported (OpenSBI delegates S-mode to the OS)
#define S_SUPPORTED
