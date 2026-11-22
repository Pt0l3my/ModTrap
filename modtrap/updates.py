"""Whether a mod has a newer file where it came from (MT37, WHY§101): asked of Nexus and of GitHub, nothing else.

This is the only part of ModTrap that goes out to the network. It asks two services, by their public interfaces
for programs, and reads the answers; it downloads no mod, changes nothing in the modlist, and sends nothing of
the owner's but the key Nexus gave them, to Nexus alone.

Nexus (MO01§13, as MO2 itself asks):
- one question gives every mod of the game that had a file added in the last month;
- one question per mod gives its files, and which file replaced which. From the file that is installed, the chain
  of replacements is followed: a newer file that is current means an update.
A mod is asked about again only when that month's list shows a newer file than at the last asking, or the last
asking is over four weeks old. Nexus allows an account a number of questions a day and an hour; ModTrap stops well
short of both, and takes up the rest at the next scan.

GitHub: the newest release of a repository, compared with the release the installed archive came from.

Every answer is kept in ModTrap's own folder, so that the page can show the last known state without asking.
"""

from __future__ import annotations

import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import logbook, paths, sources

log = logbook.get("updates")

NEXUS = "https://api.nexusmods.com/v1"
GITHUB = "https://api.github.com"
ACCOUNT = "users/validate"           # under NEXUS: what kind of account a key is of (MO01§15)
HOSTS = ("api.nexusmods.com", "api.github.com")
# A mod's file is fetched from these and no others (MT40): GitHub's own store of release files, and the hosts Nexus
# names in the download address it gives. The owner's key is never sent to any of them.
DOWNLOAD_SUFFIXES = (".githubusercontent.com", ".nexus-cdn.com", ".nexusmods.com")
GITHUB_FILE = re.compile(r"^/[^/]+/[^/]+/releases/download/")
DOWNLOAD_MAX = 30 * 1024 ** 3
HOPS = 6
ARCHIVE = re.compile(r"\.(zip|7z|rar)$", re.IGNORECASE)
TIMEOUT = 40
BODY_MAX = 96 * 1024 * 1024
NEXUS_PER_SCAN = 400                 # questions about single mods in one scan, at most
NEXUS_DAY_RESERVE = 300              # of the day's allowance this many are left alone
NEXUS_HOUR_RESERVE = 20
GITHUB_PER_SCAN = 40
GITHUB_RESERVE = 5
ASK_AGAIN = 28 * 86400               # a mod not in the month's list is asked about again after this long
GITHUB_AGAIN = 12 * 3600
STORE = "updates.json"


class Refused(Exception):
    """An address ModTrap does not go to."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None                                      # an answer that points elsewhere is not followed


class Net:
    """HTTPS questions to the two services, and to nothing else."""

    def __init__(self, version: str = ""):
        self.agent = "ModTrap/%s" % (version or "0")
        self._opener = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=ssl.create_default_context()))

    def get(self, url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], object]:
        """(status, the answer's headers in lower case, the answer read as JSON or None). Status 0: no answer."""
        m = re.match(r"^https://([^/:]+)/", url)
        if not m or m.group(1).lower() not in HOSTS:
            raise Refused("ModTrap asks only %s" % " and ".join(HOSTS))
        req = urllib.request.Request(url, headers={"User-Agent": self.agent, "Accept": "application/json", **headers})
        try:
            with self._opener.open(req, timeout=TIMEOUT) as r:
                status, got, raw = r.status, {k.lower(): v for k, v in r.headers.items()}, r.read(BODY_MAX)
        except urllib.error.HTTPError as e:
            return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, None
        except (urllib.error.URLError, OSError, ValueError) as e:
            return 0, {"why": logbook.why(getattr(e, "reason", e) if isinstance(getattr(e, "reason", None), BaseException) else e)}, None
        try:
            return status, got, json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return status, got, None


    def download(self, url: str, dest: Path, progress=None, stopped=None) -> int:
        """Fetches one file to `dest` (written beside it first, then swapped in). Only from the hosts mod files are
        kept on; an answer that points on is followed only to such a host, a few times at most. Returns its size.
        Raises Refused, with the reason in words."""
        for _hop in range(HOPS):
            parts = urllib.parse.urlsplit(url)
            host = (parts.hostname or "").lower()
            ok = parts.scheme == "https" and not parts.username and (
                (host == "github.com" and GITHUB_FILE.match(parts.path or "")) or any(host.endswith(x) for x in DOWNLOAD_SUFFIXES))
            if not ok:
                raise Refused("the download's address is not one ModTrap fetches a mod's file from")
            req = urllib.request.Request(url, headers={"User-Agent": self.agent, "Accept": "application/octet-stream"})
            try:
                with self._opener.open(req, timeout=TIMEOUT) as r:
                    total = int(r.headers.get("Content-Length") or 0)
                    if total > DOWNLOAD_MAX:
                        raise Refused("the file is larger than ModTrap fetches")
                    tmp = dest.with_name(dest.name + ".part")
                    done = 0
                    try:
                        with open(tmp, "wb") as f:
                            while True:
                                if stopped is not None and stopped():
                                    raise Refused("stopped")
                                block = r.read(1024 * 1024)
                                if not block:
                                    break
                                done += len(block)
                                if done > DOWNLOAD_MAX:
                                    raise Refused("the file is larger than ModTrap fetches")
                                f.write(block)
                                if progress is not None:
                                    progress(done, total)
                        if total and done != total:
                            raise Refused("the file did not arrive whole")
                        tmp.replace(dest)
                    finally:
                        tmp.unlink(missing_ok=True)
                    return done
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                    url = urllib.parse.urljoin(url, e.headers["Location"])
                    continue
                raise Refused("the file's host answered with an error (%d)" % e.code) from None
            except (urllib.error.URLError, OSError, ValueError) as e:
                raise Refused("the file could not be fetched (%s)" % logbook.why(getattr(e, "reason", e) if isinstance(getattr(e, "reason", None), BaseException) else e)) from None
        raise Refused("the download was passed on too many times")


# --- what is kept between scans ------------------------------------------------------------------------------------

def load() -> dict:
    try:
        with open(paths.home() / STORE, "rb") as f:
            got = json.loads(f.read().decode("utf-8"))
        if got.get("format") == "modtrap-updates/1":
            return got
    except (OSError, ValueError):
        pass
    return {"format": "modtrap-updates/1", "nexus": {}, "github": {}, "last": {}}


def save(store: dict) -> None:
    paths.write_atomic(paths.home() / STORE, json.dumps(store, separators=(",", ":")).encode("utf-8"))


# --- the verdict, from what is kept ---------------------------------------------------------------------------------

def _parts(version: str) -> tuple | None:
    v = version.strip().lower().lstrip("v")
    if not v or not re.fullmatch(r"\d+(\.\d+)*", v):
        return None
    t = tuple(int(x) for x in v.split("."))
    while len(t) > 1 and t[-1] == 0:
        t = t[:-1]
    return t


def same_version(a: str, b: str) -> bool:
    pa, pb = _parts(a), _parts(b)
    return pa == pb if pa is not None and pb is not None else a.strip().lower().lstrip("v") == b.strip().lower().lstrip("v")


def _day(seconds) -> str:
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(int(seconds)))
    except (ValueError, OverflowError, OSError, TypeError):
        return ""


def nexus_verdict(row: dict, kept: dict | None) -> dict:
    """What Nexus's files for the mod say of the files installed (MO01§13). {"state": "update", "current", "maybe",
    "gone" or "not asked", "text", "newest", "file", "when", "asked"}."""
    if kept is None:
        return {"state": "not asked", "text": "Nexus has not been asked about this mod yet", "newest": "", "file": "", "when": "", "asked": ""}
    asked = _day(kept.get("asked", 0))
    if kept.get("gone"):
        return {"state": "gone", "text": "Nexus no longer shows this mod (%s)" % kept["gone"], "newest": "", "file": "", "when": "", "asked": asked}
    d = sources.data()
    active, gone = set(d["active_states"]), set(d["gone_states"])
    files = {f[0]: {"id": f[0], "name": f[1], "version": f[2], "state": f[3], "time": f[4]} for f in kept.get("files", [])}
    chain = {c[0]: c for c in kept.get("chain", [])}
    installed = [i for i in row.get("files", []) if i in files or i in chain or any(c[1] == i for c in chain.values())]
    how = "by the file's number"
    if not installed and row.get("archive"):
        low = row["archive"].lower()
        installed = [f["id"] for f in files.values() if f["name"].lower() == low] or \
                    [c[0] for c in chain.values() if c[2].lower() == low] or [c[1] for c in chain.values() if c[3].lower() == low]
        how = "by the archive's name"
    mains = sorted((f for f in files.values() if f["state"] == 1), key=lambda f: -f["time"])
    if not installed:
        if not mains:
            return {"state": "maybe", "text": "the installed file could not be told among the mod's files, and the mod has no main file now",
                    "newest": "", "file": "", "when": "", "asked": asked}
        if row.get("version") and any(same_version(row["version"], f["version"]) for f in mains):
            return {"state": "current", "text": "the installed version is that of a main file (the file itself could not be told)",
                    "newest": mains[0]["version"], "file": mains[0]["name"], "when": _day(mains[0]["time"]), "asked": asked}
        return {"state": "maybe", "text": "the installed file could not be told among the mod's files; its main file is version %s, of %s, and "
                                          "the installed version reads %s" % (mains[0]["version"] or "(none given)", _day(mains[0]["time"]), row.get("version") or "(none given)"),
                "newest": mains[0]["version"], "file": mains[0]["name"], "when": _day(mains[0]["time"]), "asked": asked}
    best = None
    unsure = None
    for i in installed:
        seen, at, successors = set(), i, []
        while at in chain and chain[at][1] not in seen:
            at = chain[at][1]
            seen.add(at)
            successors.append(at)
        own = files.get(i)
        current = next((files[s] for s in reversed(successors) if s in files and files[s]["state"] in active), None)
        downloadable = next((files[s] for s in reversed(successors) if s in files and files[s]["state"] not in gone), None)
        newer = current or (downloadable if own is None or own["state"] not in active else None)
        if newer is not None:
            if best is None or newer["time"] > best["time"]:
                best = newer
        elif own is None or own["state"] not in active:
            later = next((f for f in mains if own is None or f["time"] > own["time"]), None)
            if later is not None:
                unsure = later
    if best is not None:
        return {"state": "update", "text": "a newer file replaced the installed one (%s): %s, version %s, of %s" % (
            how, best["name"], best["version"] or "(none given)", _day(best["time"])),
                "newest": best["version"], "file": best["name"], "when": _day(best["time"]), "asked": asked, "file_id": best["id"]}
    if unsure is not None:
        return {"state": "maybe", "text": "the installed file is marked old or is no longer listed, with no word of what replaced it; a later "
                                          "main file is there: %s, version %s, of %s" % (unsure["name"], unsure["version"] or "(none given)", _day(unsure["time"])),
                "newest": unsure["version"], "file": unsure["name"], "when": _day(unsure["time"]), "asked": asked}
    return {"state": "current", "text": "no newer file replaced the installed one (%s)" % how, "newest": "", "file": "", "when": "", "asked": asked}


def github_verdict(row: dict, kept: dict | None) -> dict:
    if kept is None:
        return {"state": "not asked", "text": "GitHub has not been asked about this repository yet", "newest": "", "file": "", "when": "", "asked": ""}
    asked = _day(kept.get("asked", 0))
    if kept.get("gone"):
        return {"state": "gone", "text": "GitHub shows no release for this repository (%s)" % kept["gone"], "newest": "", "file": "", "when": "", "asked": asked}
    tag, when = kept.get("tag", ""), kept.get("published", "")[:10]
    if row.get("tag"):
        if row["tag"] == tag:
            return {"state": "current", "text": "the installed archive is of the newest release (%s)" % tag, "newest": tag, "file": "", "when": when, "asked": asked}
        return {"state": "update", "text": "the newest release is %s, of %s; the installed archive is of release %s" % (tag, when, row["tag"]),
                "newest": tag, "file": "", "when": when, "asked": asked}
    if row.get("version") and same_version(row["version"], tag):
        return {"state": "current", "text": "the installed version is the newest release (%s)" % tag, "newest": tag, "file": "", "when": when, "asked": asked}
    return {"state": "maybe", "text": "the newest release is %s, of %s; which release is installed is not recorded (the version reads %s)" % (
        tag, when, row.get("version") or "(none given)"), "newest": tag, "file": "", "when": when, "asked": asked}


def verdict(row: dict, store: dict) -> dict:
    """The last known state of one mod (`sources.gather`'s row), from what is kept."""
    if row["host"] == "nexus":
        v = nexus_verdict(row, store["nexus"].get("%s/%d" % (row["game"], row["mod_id"])))
    elif row["host"] == "github" and row.get("repo"):
        v = github_verdict(row, store["github"].get(row["repo"].lower()))
    else:
        why = {"": "no record on this PC says where this mod came from", "url": "it came from a web address that cannot be asked for versions",
               "loverslab": "it came from LoversLab, which gives a program no way to ask for versions: open its page in your browser, where you are logged in"}
        v = {"state": "none", "text": why.get(row["host"], "it came from %s, which cannot be asked for versions" % row["host"]),
             "newest": "", "file": "", "when": "", "asked": ""}
    # What MO2 itself last saw is said beside it: it is on this PC already, and costs no question.
    if row.get("mo2_newest") and row.get("version") and not same_version(row["mo2_newest"], row["version"]) and v["state"] in ("not asked", "maybe"):
        v["text"] += "; MO2's own last check saw version %s as the newest" % row["mo2_newest"]
        if v["state"] == "not asked":
            v["mo2"] = True
    return v


# --- the scan --------------------------------------------------------------------------------------------------------

def scan(rows: list[dict], key: str, net: Net, store: dict | None = None, now: float | None = None, progress=None,
         stopped=None, per_scan: int = NEXUS_PER_SCAN, force: bool = False) -> dict:
    """Asks Nexus and GitHub about the mods of `rows` that need asking, keeps the answers, and gives an account:
    {"nexus": {"mods", "asked", "left", "month_list", "why_stopped", "day_left", "hour_left"}, "github": {...},
    "seconds", "when"}. `progress(text)` is told what it is at; `stopped()` ends it early. `force`: every mod of
    `rows` is asked about now, whatever was kept (the owner asked about these mods by name)."""
    store = load() if store is None else store
    now = time.time() if now is None else now
    started = time.monotonic()
    say = progress or (lambda _t: None)
    halted = stopped or (lambda: False)
    out = {"nexus": {"mods": 0, "asked": 0, "left": 0, "month_list": 0, "why_stopped": "", "day_left": None, "hour_left": None},
           "github": {"repos": 0, "asked": 0, "left": 0, "why_stopped": "", "left_this_hour": None}, "seconds": 0.0, "when": int(now)}
    nx = out["nexus"]
    wanted: dict[tuple[str, int], bool] = {}
    for r in rows:
        if r["host"] == "nexus":
            k = (r["game"], r["mod_id"])
            wanted[k] = wanted.get(k, False) or bool(r.get("enabled"))
    nx["mods"] = len(wanted)
    headers = {"APIKEY": key, "Application-Name": "ModTrap", "Application-Version": net.agent.split("/", 1)[-1], "Protocol-Version": "1.0.0"}

    def limits(h: dict) -> None:
        for name, field in (("x-rl-daily-remaining", "day_left"), ("x-rl-hourly-remaining", "hour_left")):
            try:
                nx[field] = int(h[name])
            except (KeyError, ValueError):
                pass

    def refusal(status: int, h: dict) -> str:
        return {0: "Nexus could not be reached (%s)" % h.get("why", "no answer"), 401: "Nexus did not accept the key",
                429: "Nexus says the account's allowance of questions is used up for now"}.get(status, "Nexus answered with an error (%d)" % status)

    if wanted and not key:
        nx["why_stopped"] = "no Nexus key is kept: Nexus answers a program only with an account's key"
        nx["left"] = len(wanted)
    elif wanted:
        updated: dict[str, dict[int, int]] = {}
        for game in sorted({g for g, _i in wanted}):
            say("asking Nexus which mods of %s had a new file in the last month" % game)
            status, h, body = net.get("%s/games/%s/mods/updated?period=1m" % (NEXUS, game), headers)
            limits(h)
            if status != 200 or not isinstance(body, list):
                nx["why_stopped"] = refusal(status, h)
                break
            updated[game] = {}
            for e in body:
                try:
                    updated[game][int(e["mod_id"])] = int(e.get("latest_file_update") or 0)
                except (KeyError, TypeError, ValueError):
                    continue
            nx["month_list"] += len(updated[game])
        if not nx["why_stopped"]:
            need = []
            for (game, mod_id), enabled in wanted.items():
                prev = store["nexus"].get("%s/%d" % (game, mod_id))
                newer = updated[game].get(mod_id, 0)
                if force or prev is None or prev.get("asked", 0) < now - ASK_AGAIN or newer > prev.get("asked", 0) - 3600:
                    need.append((0 if newer else 1, 0 if enabled else 1, 0 if prev is None else 1, game, mod_id))
                else:
                    prev["seen"] = int(now)                    # the month's list shows nothing newer: the answer still stands
            need.sort()
            for n, (_a, _b, _c, game, mod_id) in enumerate(need):
                if halted():
                    nx["why_stopped"] = "stopped"
                elif nx["asked"] >= per_scan:
                    nx["why_stopped"] = "%d mods were asked about in this scan; the rest follow at the next, to spare the account's allowance" % per_scan
                elif nx["day_left"] is not None and nx["day_left"] <= NEXUS_DAY_RESERVE:
                    nx["why_stopped"] = "the account has %d question(s) left for today; ModTrap leaves those alone" % nx["day_left"]
                elif nx["hour_left"] is not None and nx["hour_left"] <= NEXUS_HOUR_RESERVE:
                    nx["why_stopped"] = "the account has %d question(s) left for this hour; ModTrap leaves those alone" % nx["hour_left"]
                if nx["why_stopped"]:
                    nx["left"] = len(need) - n
                    break
                if n % 10 == 0:
                    say("asking Nexus about mod %d of %d" % (n + 1, len(need)))
                status, h, body = net.get("%s/games/%s/mods/%d/files" % (NEXUS, game, mod_id), headers)
                limits(h)
                rec = {"asked": int(now)}
                if status in (403, 404):
                    rec["gone"] = "hidden or removed" if status == 404 else "not open to this account, or under review"
                elif status != 200 or not isinstance(body, dict):
                    nx["why_stopped"] = refusal(status, h)
                    nx["left"] = len(need) - n
                    break
                else:
                    files, chain = [], []
                    for f in body.get("files") or []:
                        try:
                            when = int(f.get("uploaded_timestamp") or 0)
                            files.append([int(f["file_id"]), str(f.get("file_name") or ""), str(f.get("version") or ""),
                                          int(f.get("category_id") or 0), when // 1000 if when > 10 ** 11 else when])
                        except (KeyError, TypeError, ValueError):
                            continue
                    for c in body.get("file_updates") or []:
                        try:
                            chain.append([int(c["old_file_id"]), int(c["new_file_id"]), str(c.get("old_file_name") or ""), str(c.get("new_file_name") or "")])
                        except (KeyError, TypeError, ValueError):
                            continue
                    rec.update(files=files, chain=chain)
                store["nexus"]["%s/%d" % (game, mod_id)] = rec
                nx["asked"] += 1
                if nx["asked"] % 50 == 0:
                    save(store)

    gh = out["github"]
    repos = sorted({r["repo"].lower() for r in rows if r["host"] == "github" and r.get("repo")})
    gh["repos"] = len(repos)
    for n, repo in enumerate(repos):
        prev = store["github"].get(repo)
        if prev is not None and prev.get("asked", 0) > now - GITHUB_AGAIN and not force:
            continue
        if halted():
            gh["why_stopped"] = "stopped"
        elif gh["asked"] >= GITHUB_PER_SCAN:
            gh["why_stopped"] = "%d repositories were asked about in this scan; the rest follow at the next" % GITHUB_PER_SCAN
        elif gh["left_this_hour"] is not None and gh["left_this_hour"] <= GITHUB_RESERVE:
            gh["why_stopped"] = "GitHub allows a program without an account few questions an hour; the rest follow later"
        if gh["why_stopped"]:
            gh["left"] = sum(1 for x in repos[n:] if store["github"].get(x) is None or store["github"][x].get("asked", 0) <= now - GITHUB_AGAIN)
            break
        say("asking GitHub about repository %d of %d" % (n + 1, len(repos)))
        h_req = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if prev and prev.get("etag"):
            h_req["If-None-Match"] = prev["etag"]
        status, h, body = net.get("%s/repos/%s/releases/latest" % (GITHUB, repo), h_req)
        try:
            gh["left_this_hour"] = int(h["x-ratelimit-remaining"])
        except (KeyError, ValueError):
            pass
        if status == 304 and prev:
            prev["asked"] = int(now)
        elif status == 404:
            store["github"][repo] = {"asked": int(now), "gone": "no release, or no such repository"}
        elif status == 200 and isinstance(body, dict) and body.get("tag_name"):
            assets = []
            for a in (body.get("assets") or [])[:60]:
                if isinstance(a, dict) and a.get("name") and a.get("browser_download_url"):
                    assets.append([str(a["name"]), str(a["browser_download_url"]), int(a.get("size") or 0)])
            store["github"][repo] = {"asked": int(now), "tag": str(body["tag_name"]), "published": str(body.get("published_at") or ""),
                                     "etag": h.get("etag", ""), "assets": assets}
        else:
            gh["why_stopped"] = ("GitHub could not be reached (%s)" % h.get("why", "no answer") if status == 0 else
                                 "GitHub's allowance of questions for this hour is used up" if status in (403, 429) else
                                 "GitHub answered with an error (%d)" % status)
            gh["left"] = len(repos) - n
            break
        gh["asked"] += 1
    out["seconds"] = round(time.monotonic() - started, 1)
    if not force:
        store["last"] = out                               # a question about single mods is not "the last scan"
    save(store)
    log.info("scan for updates: Nexus: %d mod(s) with a number, the month's list named %s, %d asked about now, %d left for later%s%s",
             nx["mods"], format(nx["month_list"], ","), nx["asked"], nx["left"], ": " + nx["why_stopped"] if nx["why_stopped"] else "",
             "; the account has %s question(s) left today, %s this hour" % (nx["day_left"], nx["hour_left"]) if nx["day_left"] is not None else "")
    log.info("scan for updates: GitHub: %d repositor(ies), %d asked about now, %d left for later%s; the scan took %.1f s",
             gh["repos"], gh["asked"], gh["left"], ": " + gh["why_stopped"] if gh["why_stopped"] else "", out["seconds"])
    return out


# --- fetching a newer file (MT40) ------------------------------------------------------------------------------------

def nexus_headers(key: str, net: Net) -> dict:
    return {"APIKEY": key, "Application-Name": "ModTrap", "Application-Version": net.agent.split("/", 1)[-1], "Protocol-Version": "1.0.0"}


def nexus_account(key: str, net: Net) -> dict:
    """What Nexus says of the key's account (MO01§15): {"ok", "premium", "why"}."""
    status, h, body = net.get("%s/%s" % (NEXUS, ACCOUNT), nexus_headers(key, net))
    if status == 200 and isinstance(body, dict) and "user_id" in body:
        return {"ok": True, "premium": bool(body.get("is_premium")), "why": ""}
    return {"ok": False, "premium": False, "why": "Nexus did not accept the key" if status == 401 else
            "Nexus could not be reached (%s)" % h.get("why", "no answer") if status == 0 else "Nexus answered with an error (%d)" % status}


def nexus_link(key: str, net: Net, game: str, mod_id: int, file_id: int) -> tuple[str, str]:
    """The address of one file, as Nexus gives it to a program (MO01§14): (address, "") or ("", why). Nexus gives
    it to a paying account only; to any other it answers that it will not."""
    status, h, body = net.get("%s/games/%s/mods/%d/files/%d/download_link" % (NEXUS, game, mod_id, file_id), nexus_headers(key, net))
    if status == 200 and isinstance(body, list):
        for server in body:
            if isinstance(server, dict) and str(server.get("URI") or "").lower().startswith("https://"):
                return str(server["URI"]), ""
        return "", "Nexus named no address for the file"
    if status == 403:
        return "", "Nexus lets a program start a download only for a Premium account"
    return "", ("Nexus did not accept the key" if status == 401 else "Nexus could not be reached (%s)" % h.get("why", "no answer") if status == 0
                else "Nexus answered with an error (%d)" % status)


def github_asset(row: dict, kept: dict | None) -> tuple[str, str] | None:
    """Which file of the newest release is the mod's: the one named as the installed archive, else the one whose
    name differs from it only in digits (a version), else the only archive there is. None when it cannot be told."""
    files = [(a[0], a[1]) for a in (kept or {}).get("assets", []) if ARCHIVE.search(a[0])]
    if not files:
        return None
    shape = lambda name: re.sub(r"[\d._\- ]+", "", name.lower())
    mine = (row.get("archive") or "").lower()
    same = [f for f in files if f[0].lower() == mine] or ([f for f in files if shape(f[0]) == shape(mine)] if mine else [])
    if len(same) == 1:
        return same[0]
    return files[0] if len(files) == 1 else None


def how_to_get(row: dict, v: dict, store: dict, key: bool, premium: bool | None) -> dict:
    """What the update button does for one mod, decided without asking anyone: {"fetch": "nexus" or "github", ...}
    when ModTrap can fetch the file itself, else {"open": the page to open, "why": why ModTrap does not fetch}."""
    page = get_of(row, v) or page_of(row)
    if row["host"] == "nexus":
        if v["state"] != "update" or not v.get("file_id"):
            return {"open": page, "why": "which file is the newer one is not known for certain"}
        if not key:
            return {"open": page, "why": "no Nexus key is kept, so the download goes through Nexus's page and MO2"}
        if premium is False:
            return {"open": page, "why": "Nexus lets a program start a download only for a Premium account, so it goes through Nexus's page and MO2"}
        return {"fetch": "nexus", "file_id": v["file_id"], "name": v.get("file") or "", "version": v.get("newest") or "", "page": page}
    if row["host"] == "github" and row.get("repo"):
        kept = store["github"].get(row["repo"].lower())
        got = github_asset(row, kept)
        if got is None:
            return {"open": page, "why": "the newest release has no file, or several, and ModTrap cannot tell which is this mod's"}
        return {"fetch": "github", "url": got[1], "name": got[0], "version": (kept or {}).get("tag", ""), "page": page}
    if row["host"] == "loverslab":
        return {"open": page, "why": "LoversLab gives files only to your logged-in browser; download it there, then use “Install a downloaded archive as its newer version” in the mod's menu"}
    return {"open": page, "why": "ModTrap cannot fetch from there; download it in your browser, then use “Install a downloaded archive as its newer version” in the mod's menu"}


def fetch(how: dict, row: dict, key: str, net: Net, folder: Path, progress=None, stopped=None) -> dict:
    """Fetches the file `how_to_get` named into `folder`: {"path", "name", "version"} or {"open", "why"} when the
    host would not give it after all. Raises Refused when the fetching itself fails."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", how.get("name") or "the newer file")[:200]
    if how["fetch"] == "nexus":
        url, why = nexus_link(key, net, row["game"], row["mod_id"], how["file_id"])
        if not url:
            if "Premium" in why:
                return {"open": how["page"], "why": why + ", so it goes through Nexus's page and MO2"}
            raise Refused(why)
    else:
        url = how["url"]
    folder.mkdir(parents=True, exist_ok=True)
    size = net.download(url, folder / name, progress, stopped)
    log.info("fetched “%s” for “%s” from %s: %.1f MB", name, row["mod"], "Nexus" if how["fetch"] == "nexus" else "GitHub", size / (1024 * 1024))
    return {"path": folder / name, "name": name, "version": how.get("version", "")}


def get_of(row: dict, v: dict) -> str:
    """Where the owner gets the newer file a verdict speaks of: for Nexus the file's own page, opened the way
    Nexus's "mod manager download" button opens it, so that MO2 takes the download; for GitHub the newest release."""
    if v["state"] not in ("update", "maybe"):
        return ""
    if row["host"] == "nexus":
        if v.get("file_id"):
            return "https://www.nexusmods.com/%s/mods/%d?tab=files&file_id=%d&nmm=1" % (row["game"], row["mod_id"], v["file_id"])
        return "https://www.nexusmods.com/%s/mods/%d?tab=files" % (row["game"], row["mod_id"])
    if row["host"] == "github" and row.get("repo"):
        return "https://github.com/%s/releases/latest" % row["repo"]
    return ""


def page_of(row: dict) -> str:
    """The mod's own page, for the owner to open."""
    if row["host"] == "nexus":
        return "https://www.nexusmods.com/%s/mods/%d?tab=files" % (row["game"], row["mod_id"])
    if row["host"] == "github" and row.get("repo"):
        return "https://github.com/%s/releases" % row["repo"]
    return row.get("url", "") if row["host"] in ("url", "loverslab") else ""


__all__ = ["Net", "Refused", "fetch", "get_of", "github_asset", "github_verdict", "how_to_get", "nexus_account", "nexus_link", "load", "nexus_verdict", "page_of", "same_version", "save", "scan", "verdict"]
