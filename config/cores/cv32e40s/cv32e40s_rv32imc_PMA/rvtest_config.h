#define CONFORMING_SM_SUPPORTED
//#define ACCESS_FAULT_ADDRESS 0x80000000
#define RVMODEL_PMP_GRAIN 0
// PMP_NUM_REGIONS=0 by default in cv32e40s_core.sv — no PMP hardware instantiated
#define RVMODEL_NUM_PMPS 0
// cv32e40s mtvec BASE = bits[31:7] → 128-byte alignment required
#define RVMODEL_MTVEC_ALIGN 7
