import json
import os
import time
import urllib.error
import urllib.parse

def schema_for(material):
    string = {"type": "STRING"}
    strings = {"type": "ARRAY", "items": string}
    if "items" in material:
        properties = {"index": {"type": "INTEGER"}, "pass": {"type": "BOOLEAN"}, "reason": string}
        item = {"type": "OBJECT", "properties": properties, "required": list(properties)}
        return "verdicts", {"type": "OBJECT", "properties": {
            "verdicts": {"type": "ARRAY", "items": item}}, "required": ["verdicts"]}
    check_properties = {"claim": string, "source_id": string, "quote": string}
    properties = {"headline": string, "summary": string, "why_it_matters": string,
        "category": {"type": "STRING", "enum": ["industry", "marketing"]},
        "companies": strings, "topics": strings, "source_ids": strings,
        "score": {"type": "INTEGER"}, "evidence_checks": {"type": "ARRAY", "items": {
            "type": "OBJECT", "properties": check_properties, "required": list(check_properties)}}}
    item = {"type": "OBJECT", "properties": properties, "required": list(properties)}
    return "stories", {"type": "OBJECT", "properties": {
        "stories": {"type": "ARRAY", "items": item}}, "required": ["stories"]}

def parse_output(text, expected_key):
    value = json.loads(text)
    if isinstance(value, list): value = {expected_key: value}
    if not isinstance(value, dict) or expected_key not in value:
        shape = list(value.keys()) if isinstance(value, dict) else type(value).__name__
        raise ValueError("Gemini response missing '" + expected_key + "'; shape: " + str(shape))
    items = value[expected_key]
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ValueError("Gemini '" + expected_key + "' must be an array of objects")
    return {expected_key: items}

def make_generator(legacy):
    def generate(system, material, max_tokens=8500):
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key: raise ValueError("Missing GEMINI_API_KEY")
        expected, schema = schema_for(material)
        payload = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": json.dumps(material, ensure_ascii=False)}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema,
                                 "maxOutputTokens": max_tokens}}
        model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
        url = "https://generativelanguage.googleapis.com/v1beta/models/" + urllib.parse.quote(model, safe="") + ":generateContent"
        for attempt in range(2):
            try:
                raw = legacy.fetch(url, json.dumps(payload).encode(), {
                    "Content-Type": "application/json", "x-goog-api-key": key})
                envelope = json.loads(raw)
                if not isinstance(envelope, dict): raise ValueError("Invalid Gemini API envelope")
                candidates = envelope.get("candidates", [])
                if not candidates or not isinstance(candidates[0], dict):
                    raise ValueError("Gemini returned no candidate; check safety or quota response")
                candidate = candidates[0]
                if candidate.get("finishReason") != "STOP":
                    raise ValueError("Gemini response incomplete: " + str(candidate.get("finishReason")))
                text = "".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", [])
                               if isinstance(part, dict) and not part.get("thought", False))
                result = parse_output(text, expected)
                legacy.write_json(legacy.REPORT / ("gemini-" + expected + "-shape.json"),
                    {"expected_key": expected, "item_count": len(result[expected]), "schema_enforced": True})
                return result
            except urllib.error.HTTPError as error:
                detail = error.read().decode(errors="replace").replace(key,"[REDACTED]")[:600]
                if error.code in (500,502,503,504) and attempt == 0:
                    time.sleep(12); continue
                raise ValueError("Gemini HTTP " + str(error.code) + ": " + detail) from None
        raise ValueError("Gemini request failed")
    return generate
