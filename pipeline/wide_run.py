import os
import sys
import traceback
import run as legacy
from wide_discovery import wider_evidence

original_collect = legacy.collect

def expanded_collect(sources, cutoff):
    base, diagnostics = original_collect(sources, cutoff)
    config = legacy.read_json(legacy.ROOT / "pipeline" / "discovery-config.json", {})
    try:
        wide, extra_diagnostics = wider_evidence(config, cutoff, legacy.NOW)
    except Exception as error:
        legacy.write_json(legacy.REPORT / "discovery-error.json", {"error":str(error)})
        print("Wide discovery failed; continuing existing feeds:", str(error))
        return base, diagnostics
    by_url = {legacy.normalized_url(c["url"]): c for c in base}
    for candidate in wide:
        url = legacy.normalized_url(candidate["url"])
        if url and url not in by_url: by_url[url] = candidate
    return list(by_url.values()), diagnostics + extra_diagnostics

legacy.collect = expanded_collect

if __name__ == "__main__":
    try:
        legacy.main()
    except Exception as error:
        key = os.environ.get("GEMINI_API_KEY", "")
        message = str(error); trace = traceback.format_exc()
        if key:
            message = message.replace(key,"[REDACTED]")
            trace = trace.replace(key,"[REDACTED]")
        legacy.write_json(legacy.REPORT / "error.json", {"error":message,"traceback":trace})
        print("Pipeline stopped:",message,file=sys.stderr)
        sys.exit(1)
