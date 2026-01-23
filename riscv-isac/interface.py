import importlib
import pluggy
from riscv_isac.plugins.specification import *
import riscv_isac.plugins as plugins


def interface (trace, arch, mode):

    '''
    Arguments:
    Trace - Log_file_path
    Arch -  Architecture
    Mode - Execution trace format

    '''
    parser_pm = pluggy.PluginManager("parser")
    decoder_pm = pluggy.PluginManager("decoder")
    parser_pm.add_hookspecs(ParserSpec)
    decoder_pm.add_hookspecs(DecoderSpec)

    parserfile = importlib.import_module("riscv_isac.plugins."+mode) 
    parserclass = getattr(parserfile, "mode_"+mode) 
    parser_pm.register(parserclass())
    parser = parser_pm.hook
    parser.setup(trace=trace,arch=arch)

    instructionObjectfile = importlib.import_module("riscv_isac.plugins.internalDecoder")
    decoderclass = getattr(instructionObjectfile, "disassembler") 
    decoder_pm.register(decoderclass())
    decoder = decoder_pm.hook
    decoder.setup(arch=arch)
   
    
    iterator = iter(parser.__iter__()[0])

    for instr, mnemonic, addr, commitvalue in iterator: 
        if instr is not None:
            instrObj = decoder.decode(instr=instr, addr=addr)