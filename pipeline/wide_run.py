import concurrent.futures as cf
from collections import Counter
import os
import sys
import traceback
import urllib.parse
from threading import Lock
import run as legacy
import wide_discovery as wide
from strict_gemini import make_generator

# Use the working core, but replace its API client with schema-enforced JSON.
legacy.gemini = make_generator(legacy)
original_collect = legacy.collect

PRIORITY_DOMAINS = [
    "reuters.com", "apnews.com", "defensenews.com", "breakingdefense.com", "aviationweek.com",
    "flightglobal.com", "ft.com", "wsj.com", "bloomberg.com", "cnbc.com", "payloadspace.com",
    "defensescoop.com", "navalnews.com", "usni.org", "airandspaceforces.com", "nasa.gov",
    "gao.gov", "faa.gov", "boeing.com", "boeing.mediaroom.com", "airbus.com", "rtx.com",
    "lockheedmartin.com", "northropgrumman.com", "anduril.com", "shield.ai", "saronic.com",
    "thedrum.com", "campaignlive.co.uk", "adage.com", "adweek.com", "marketingweek.com",
    "marketingdive.com", "lbbonline.com", "b2bmarketing.net", "demandgenreport.com",
    "dandad.org", "canneslions.com", "businesswire.com", "prnewswire.com"
]
PRIMARY_DOMAINS = ["boeing.com", "boeing.mediaroom.com", "airbus.com", "rtx.com",
    "lockheedmartin.com", "northropgrumman.com", "anduril.com", "shield.ai", "saronic.com"]


def publisher_host(item):
    return (urllib.parse.urlsplit(item.get("publisher_home", "")).hostname or "").lower()

def priority(item):
    host = publisher_host(item)
    return wide.rank(item) + (20 if wide.belongs(host, PRIORITY_DOMAINS) else 0)

def expanded_evidence(config, cutoff, now):
    items = wide.discover(config, cutoff, now)
    blocked = config.get("blocked_text_domains", ["spacenews.com", "defenceiq.com"])
    domains = sorted({publisher_host(item) for item in items if publisher_host(item)
                      and not wide.belongs(publisher_host(item), blocked)})
    # User requested all publishers eligible; known text restrictions remain exclusions.
    config = dict(config)
    config["approved_text_domains"] = domains
    config["max_extraction_attempts"] = max(100, int(config.get("max_extraction_attempts",100)))
    eligible = []; excluded = []
    for item in items:
        host = publisher_host(item)
        if not host or wide.belongs(host, blocked):
            excluded.append({"title":item["title"],"publisher":item["publisher"],"domain":host,
                             "status":"known_source_restriction_or_missing_domain"})
        else: eligible.append(item)
    eligible.sort(key=lambda item:(priority(item),item["published_at"]),reverse=True)
    # Reserve up to 30% of attempts for marketing; no mandatory publication quota.
    maximum = config["max_extraction_attempts"]
    selected = []; counts = Counter(); keys = set()
    def add(item):
        host = publisher_host(item)
        key = (wide.headline_key(item["title"]), item["publisher"].lower())
        if key in keys or counts[host] >= 5: return False
        selected.append(item); keys.add(key); counts[host] += 1; return True
    for item in eligible:
        if item["category"] == "marketing": add(item)
        if len(selected) >= min(30,maximum): break
    for item in eligible:
        if len(selected) >= maximum: break
        add(item)
    locks = {publisher_host(item): Lock() for item in selected}
    def acquire_one(item):
        # Only one acquisition at a time per publisher host.
        with locks[publisher_host(item)]:
            candidate, report = wide.acquire(item,config)
            if candidate:
                host = urllib.parse.urlsplit(candidate["url"]).hostname or ""
                if host.endswith(".gov") or host.endswith(".mil"):
                    candidate["kind"] = "government announcement"
                elif wide.belongs(host,PRIMARY_DOMAINS):
                    candidate["kind"] = "company announcement"
                elif wide.belongs(host,["businesswire.com","prnewswire.com"]):
                    candidate["kind"] = "distributed press release"
            return candidate,report
    evidence = []; reports = []
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(acquire_one,item) for item in selected]
        for future in cf.as_completed(futures):
            candidate, report = future.result(); reports.append(report)
            if candidate: evidence.append(candidate)
    wide.write("acquisition-report.json", {"source_mode":"all_discovered_publishers_eligible",
        "eligible_domains":len(domains),"attempted":len(selected),"evidence_acquired":len(evidence),
        "not_attempted_due_to_budget_or_diversity":len(eligible)-len(selected),
        "known_restriction_exclusions":excluded,"status_counts":dict(Counter(r["status"] for r in reports)),
        "results":reports})
    diagnostics = []
    for publisher,category in sorted({(item["publisher"],item["category"]) for item in evidence}):
        diagnostics.append({"publisher":publisher,"category":category,"status":"ok",
            "usable_in_window":sum(item["publisher"]==publisher and item["category"]==category for item in evidence),
            "method":"Google News discovery + accessible article text"})
    print("Google eligible publisher domains:",len(domains))
    print("Google article acquisition attempts:",len(selected))
    print("Google discoveries with acquired article evidence:",len(evidence))
    print("Acquisition status counts:",dict(Counter(r["status"] for r in reports)))
    return evidence,diagnostics

def expanded_collect(sources,cutoff):
    base, diagnostics = original_collect(sources,cutoff)
    config = legacy.read_json(legacy.ROOT / "pipeline" / "discovery-config.json",{})
    if not isinstance(config,dict): raise ValueError("discovery-config.json must be an object")
    # Do not silently fall back to narrow feeds if wide discovery crashes.
    extra,extra_diagnostics = expanded_evidence(config,cutoff,legacy.NOW)
    by_url = {legacy.normalized_url(item["url"]):item for item in base}
    for item in extra:
        url = legacy.normalized_url(item["url"])
        if url and url not in by_url: by_url[url] = item
    return list(by_url.values()),diagnostics+extra_diagnostics

legacy.collect = expanded_collect

from restricted_links import install as install_restricted_links
install_restricted_links(legacy, wide)

from robust_editor import install as install_robust_editor
install_robust_editor(legacy)

if __name__ == "__main__":
    try:
        legacy.main()
    except Exception as error:
        key = os.environ.get("GEMINI_API_KEY","")
        message = str(error); trace = traceback.format_exc()
        if key:
            message = message.replace(key,"[REDACTED]")
            trace = trace.replace(key,"[REDACTED]")
        legacy.write_json(legacy.REPORT / "error.json",{"error":message,"traceback":trace})
        print("Pipeline stopped:",message,file=sys.stderr)
        sys.exit(1)
