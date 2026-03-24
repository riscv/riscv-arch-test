#define RVMODEL_ACCESS_FAULT_ADDRESS 0x00000000
#define RVMODEL_PMP_GRAIN 0
#define RVMODEL_NUM_PMPS 16
#define D_SUPPORTED
#define ZFA_SUPPORTED
#define F_SUPPORTED
#define ZFH_SUPPORTED
#define ZBB_SUPPORTED
#define ZBA_SUPPORTED
#define ZBS_SUPPORTED
#define ZAAMO_SUPPORTED
#define ZALRSC_SUPPORTED
#define ZICBOM_SUPPORTED
#define ZICBOZ_SUPPORTED
#define ZICBOP_SUPPORTED
#define ZIHPM_SUPPORTED
#define ZCA_SUPPORTED
#define ZCB_SUPPORTED
#define ZCD_SUPPORTED

#define TIME_CSR_IMPLEMENTED 1

// Vector configuration
#define SEWMIN 8
#define ELEN 64
#define MAXINDEXEEW 64

// Supported fractional LMULs for vector
// all supported now should be generated based on config
#define LMULf8_SUPPORTED
#define LMULf4_SUPPORTED
#define LMULf2_SUPPORTED
