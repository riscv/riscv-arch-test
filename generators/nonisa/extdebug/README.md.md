## External Debug Test Generator

External Debug is different than other riscv-arch-test suites.  It cannot be tested by running instructions on a DUT; instead, it must manipulate a Debug Transfer Module (DTM) via JTAG or a platform-specific protocol. Moreover, the External Debug features consist of the Sdext extension, Debug Module (DM), and DTM all working together.  There is no way to exercise Sdext features without a DM, and the DTM is the standard way to access the DM. Therefore, these three parts of External Debug are tested as a whole, with a platform-specific External Debug Abstraction Layer (EDAL) defining how DM accesses reach the device-under-test (DUT).

The DM is tested in two ways:
* Register reads and writes
* Abstract commands (composed from multiple reads & writes)

Much of the External Debug spec describes optional features.  The External Debug test suite queries the DUT to identify its capabilities.  It reports the features available and only tests those features.

Plans:
* Create DM tests implemented in terms of register reads and writes
* Create reporting infrastructure
* Implement EDAL for Spike, Whisper, ImperasDV, CVW debug branch
* Run and fix DM tests
* Create Abstract Command Test Plan for each set of mostly optional commands
* Create another abstraction to specify Abstract Commands
* Run and test abstract commands
* Create Sdext test plan
* Run
