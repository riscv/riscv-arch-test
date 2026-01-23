## Plugins: __init__.py
import pluggy

decoderHookImpl = pluggy.HookimplMarker("decoder")
parserHookImpl = pluggy.HookimplMarker("parser")
