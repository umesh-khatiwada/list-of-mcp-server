import re
from typing import Any, Dict

def substitute_manifest_vars(data: Any, runtime_map: Dict[str, str]) -> Any:
    """
    Recursively substitute $VARNAME in any string field of a dict/list structure with values from runtime_map.
    """
    def substitute(val):
        if isinstance(val, str):
            def repl(match):
                var = match.group(1)
                return runtime_map.get(var, match.group(0))
            return re.sub(r'\$(\w+)', repl, val)
        elif isinstance(val, dict):
            return {k: substitute(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [substitute(v) for v in val]
        return val
    return substitute(data)
