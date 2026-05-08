#define CONFORMING_SM_SUPPORTED
//#define ACCESS_FAULT_ADDRESS 0x80000000
#define RVMODEL_PMP_GRAIN 0
// PMP_NUM_REGIONS=16, PMP_GRANULARITY=0 (G=0, byte granularity)
#define RVMODEL_NUM_PMPS 16
// cv32e40s mtvec BASE = bits[31:7] → 128-byte alignment required
#define RVMODEL_MTVEC_ALIGN 7
