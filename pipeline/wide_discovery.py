import concurrent.futures as cf
import datetime as dt
import hashlib
import html
import ipaddress
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from pathlib import Path
from email.utils import parsedate_to_datetime
from threading import Lock

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "run-output"
UA = "Reduction/0.2 (+https://reduction.nyc/rtx; news briefing)"
LIMIT = 2_500_000
_ROBOTS = {}; _LOCK = Lock()

def write(name, value):
    REPORT.mkdir(exist_ok=True)
    (REPORT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")

def public_url(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
        raise ValueError("Unsafe URL")
    if p.port not in (None, 80, 443): raise ValueError("Unsupported URL port")
    for address in socket.getaddrinfo(p.hostname, p.port or 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(address[4][0]).is_global:
            raise ValueError("Non-public destination rejected")
    return p

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        old = urllib.parse.urlsplit(req.full_url).hostname
        new = urllib.parse.urlsplit(newurl).hostname
        if old != new:
            raise ValueError("Cross-host redirect requires separate access review")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def get(url):
    public_url(url)
    opener = urllib.request.build_opener(SafeRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with opener.open(request, timeout=12) as response:
        data = response.read(LIMIT + 1)
        if len(data) > LIMIT: raise ValueError("Response exceeds size limit")
        return data, response.headers.get("Content-Type", "")

def belongs(host, domains):
    return any(host == domain or host.endswith("." + domain) for domain in domains)

def robots_allowed(url):
    parts = urllib.parse.urlsplit(url)
    origin = parts.scheme + "://" + parts.netloc
    with _LOCK:
        cached = _ROBOTS.get(origin)
    if cached is None:
        try:
            data, _ = get(origin + "/robots.txt")
            parser = urllib.robotparser.RobotFileParser()
            parser.parse(data.decode("utf-8", errors="replace").splitlines())
            cached = parser
        except urllib.error.HTTPError as e:
            cached = True if e.code == 404 else False
        except Exception:
            cached = False
        with _LOCK: _ROBOTS[origin] = cached
    if isinstance(cached, bool): return cached
    delay = cached.crawl_delay(UA) or cached.crawl_delay("*")
    # Do not attempt domains with a requested crawl delay; report them for review.
    if delay: return False
    return cached.can_fetch(UA, url)

def parse_date(value):
    try:
        date = parsedate_to_datetime(value)
        return date.replace(tzinfo=dt.timezone.utc) if date.tzinfo is None else date.astimezone(dt.timezone.utc)
    except (ValueError, TypeError): return None

def clean_title(title, publisher):
    suffix = " - " + publisher
    if title.endswith(suffix): title = title[:-len(suffix)]
    return " ".join(html.unescape(title).split())

def headline_key(title):
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()

def search_track(track, country, days, cutoff, now):
    params = {"q": track["query"] + " when:" + str(days) + "d",
              "hl": "en-US" if country == "US" else "en-GB",
              "gl": country, "ceid": country + ":en"}
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)
    info = {"track": track["name"], "edition": country, "category": track["category"], "search_url": url}
    try:
        raw, _ = get(url)
        root = ET.fromstring(raw); items = []; total = 0
        for node in root.findall("./channel/item"):
            total += 1; date = parse_date(node.findtext("pubDate", ""))
            if not date or not cutoff <= date <= now + dt.timedelta(minutes=5): continue
            source = node.find("source")
            publisher = source.text if source is not None and source.text else "Unknown publisher"
            source_home = source.attrib.get("url", "") if source is not None else ""
            link = node.findtext("link", ""); title = clean_title(node.findtext("title", ""), publisher)
            if not title or not link: continue
            items.append({"title": title, "publisher": publisher, "publisher_home": source_home,
                "google_url": link, "published_at": date.isoformat(), "category": track["category"],
                "tracks": [track["name"]], "editions": [country]})
        info.update({"status": "ok", "returned": total, "in_window": len(items)})
        return items, info
    except Exception as e:
        info.update({"status": "failed", "error": str(e)[:250]})
        return [], info

def rank(item):
    title = item["title"].lower()
    value = min(len(item["tracks"]), 5) * 2
    for word in ("first", "breakthrough", "production", "prototype", "contract", "acquisition", "campaign", "activation", "rebrand", "demonstration", "procurement", "autonomous"):
        if word in title: value += 2
    if item["category"] == "marketing": value += 2
    return value

def discover(config, cutoff, now):
    days = min(15, max(config.get("lookback_days", 7), (now - cutoff).days + 2))
    jobs = [(track, edition) for track in config["queries"] for edition in track["editions"]]
    all_items = []; reports = []
    with cf.ThreadPoolExecutor(max_workers=config.get("discovery_workers", 3)) as pool:
        futures = [pool.submit(search_track, t, e, days, cutoff, now) for t,e in jobs]
        for future in cf.as_completed(futures):
            items, report = future.result(); all_items.extend(items); reports.append(report)
    unique = {}
    for item in all_items:
        key = (headline_key(item["title"]), item["publisher"].lower())
        if key not in unique: unique[key] = item
        else:
            original = unique[key]
            original["tracks"] = sorted(set(original["tracks"] + item["tracks"]))
            original["editions"] = sorted(set(original["editions"] + item["editions"]))
            if item["category"] == "marketing": original["category"] = "marketing"
    items = sorted(unique.values(), key=lambda x: (rank(x), x["published_at"]), reverse=True)
    items = items[:config.get("max_discovered", 1800)]
    write("discovery.json", items)
    write("discovery-report.json", {"track_count": len(config["queries"]), "search_count": len(jobs),
        "successful_searches": sum(r["status"] == "ok" for r in reports),
        "raw_in_window": len(all_items), "unique_retained": len(items),
        "publishers": sorted({i["publisher"] for i in items}),
        "cutoff": cutoff.isoformat(), "end": now.isoformat(),
        "searches": sorted(reports, key=lambda r: (r["track"], r["edition"]))})
    print("Google News unique discoveries:", len(items), "Publishers:", len({i['publisher'] for i in items}))
    return items

def acquire(item, config):
    info = {"title": item["title"], "publisher": item["publisher"], "category": item["category"]}
    try:
        home_host = (urllib.parse.urlsplit(item["publisher_home"]).hostname or "").lower()
        approved = config["approved_text_domains"]; blocked = config.get("blocked_text_domains", [])
        if not belongs(home_host, approved) or belongs(home_host, blocked):
            info["status"] = "discovery_only_unapproved_domain"; return None, info
        from googlenewsdecoder import gnewsdecoder
        from trafilatura import extract
        decoded = gnewsdecoder(item["google_url"], interval=0.2, timeout=10)
        if not isinstance(decoded, dict) or not decoded.get("success"):
            info["status"] = "link_resolution_failed"; return None, info
        url = decoded.get("decoded_url", ""); parts = public_url(url)
        if not belongs(parts.hostname.lower(), approved) or belongs(parts.hostname.lower(), blocked):
            info["status"] = "resolved_domain_unapproved"; return None, info
        if not robots_allowed(url):
            info["status"] = "robots_denied_or_unavailable"; return None, info
        raw, content_type = get(url)
        if "html" not in content_type:
            info["status"] = "not_html"; return None, info
        page = raw.decode("utf-8", errors="replace")
        # Conservative exclusion of pages explicitly labeled subscription-only.
        if re.search(r'"isAccessibleForFree"\s*:\s*(?:false|"false")', page, re.I):
            info["status"] = "paywall_detected"; return None, info
        text = extract(page, url=url, include_comments=False, include_tables=False, favor_precision=True)
        text = " ".join((text or "").split())
        if len(text) < 900:
            info["status"] = "insufficient_article_text"; return None, info
        lowered = text[:1800].lower()
        if any(x in lowered for x in ("subscribe to continue reading", "sign in to continue reading", "verify you are human", "enable javascript and cookies", "access denied")):
            info["status"] = "access_gate_detected"; return None, info
        info.update({"status": "evidence_acquired", "url": url, "characters": len(text)})
        uid = hashlib.sha256(url.encode()).hexdigest()[:20]
        government = belongs(parts.hostname, ["nasa.gov"])
        return {"id": uid, "title": item["title"], "url": url, "publisher": item["publisher"],
            "category": item["category"], "kind": "government announcement" if government else "reporting",
            "published_at": item["published_at"], "evidence": text[:5500], "access": "free"}, info
    except Exception as e:
        info.update({"status": "acquisition_failed", "error": str(e)[:250]}); return None, info

def wider_evidence(config, cutoff, now):
    items = discover(config, cutoff, now)
    approved = []; excluded = []
    for item in items:
        host = (urllib.parse.urlsplit(item["publisher_home"]).hostname or "").lower()
        if belongs(host, config["approved_text_domains"]) and not belongs(host, config.get("blocked_text_domains", [])):
            approved.append(item)
        else: excluded.append({"title":item["title"],"publisher":item["publisher"],"status":"discovery_only_unapproved_domain","domain":host})
    # Interleave categories and cap a single publisher's acquisition attempts.
    buckets = {}
    for item in approved: buckets.setdefault((item["category"],item["publisher"]), []).append(item)
    selected = []
    for round_index in range(20):
        for key in sorted(buckets, key=lambda k: (k[0] != "marketing", k[1])):
            if round_index < len(buckets[key]): selected.append(buckets[key][round_index])
            if len(selected) >= config.get("max_extraction_attempts",100): break
        if len(selected) >= config.get("max_extraction_attempts",100): break
    evidence = []; reports = []
    with cf.ThreadPoolExecutor(max_workers=config.get("evidence_workers",3)) as pool:
        futures = [pool.submit(acquire,item,config) for item in selected]
        for future in cf.as_completed(futures):
            candidate, report = future.result(); reports.append(report)
            if candidate: evidence.append(candidate)
    write("acquisition-report.json", {"attempted": len(selected), "evidence_acquired": len(evidence),
        "discovery_only_unapproved": len(excluded), "results": reports, "unapproved_discoveries": excluded})
    diagnostics = []
    for key in sorted({(c["publisher"],c["category"]) for c in evidence}):
        count = sum(c["publisher"]==key[0] and c["category"]==key[1] for c in evidence)
        diagnostics.append({"publisher":key[0],"category":key[1],"status":"ok","usable_in_window":count,"method":"Google News discovery + accessible article text"})
    print("Google discoveries with acquired article evidence:",len(evidence))
    return evidence, diagnostics
