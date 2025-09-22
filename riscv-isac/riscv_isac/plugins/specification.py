import pluggy

decoderHookSpec = pluggy.HookspecMarker("decoder")
parserHookSpec = pluggy.HookspecMarker("parser")

class DecoderSpec(object):
    @decoderHookSpec
    def setup(self,inxFlag,arch):
        pass

    @decoderHookSpec
    def decode(self, instrObj_temp):
        pass

class ParserSpec(object):
    @parserHookSpec
    def setup(self,trace,arch):
        pass

    @parserHookSpec
    def __iter__(self):
        pass
