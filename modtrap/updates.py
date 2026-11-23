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
PUBLIC = "https://api.nexusmods.com/v2/graphql"   # Nexus's newer service: answers what is public without any key (TL01§29)
MODS_PER_QUESTION = 50               # mods named in one question of that service (it gives at most 80 in one answer)
FILES_PER_QUESTION = 5               # mods whose files are asked for in one question
PUBLIC_QUESTIONS = 800               # questions of that service in one scan, at most
PUBLIC_PAUSE = 0.2                   # seconds between two of them: no hurry, and no burden on the service
ARCHIVE_TIME = re.compile(r"-(\d{9,11})\.(?:zip|7z|rar)$", re.IGNORECASE)   # the upload's time in a Nexus file's name
ACCOUNT = "users/validate"           # under NEXUS: what kind of account a key is of (MO01§15)
KEY_PAGE = "https://next.nexusmods.com/settings/api-keys"   # where an account's keys are, for the owner to open (WHY§107)
HOSTS = ("api.nexusmods.com", "api.github.com")
# A mod's file is fetched from these and no others (MT40): GitHub's own store of release files, and the hosts Nexus
# names in the download address it gives. The owner's key is never sent to any of them.
DOWNLOAD_SUFFIXES = (".githubusercontent.com", ".nexus-cdn.com", ".nexusmods.com")
GITHUB_FILE = re.compile(r"^/[^/]+/[^/]+/releases/download/")
# A mod's one picture, for its pop-up (MT62, TL01§32): from Nexus's two picture hosts and GitHub's preview host, and
# no others; no key is sent to any of them.
PICTURE_HOSTS = ("staticdelivery.nexusmods.com", "images.nexusmods.com", "opengraph.githubassets.com")
PICTURE_MAX = 6 * 1024 * 1024
PICTURE_KINDS = ((b"\x89PNG\r\n\x1a\n", "image/png"), (b"\xff\xd8\xff", "image/jpeg"), (b"GIF87a", "image/gif"), (b"GIF89a", "image/gif"))
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


    def ask(self, url: str, query: str, headers: dict[str, str]) -> tuple[int, dict[str, str], object]:
        """A question in the form Nexus's newer service takes (TL01§29): the question's text, sent as a body. The
        answer as `get` gives it."""
        m = re.match(r"^https://([^/:]+)/", url)
        if not m or m.group(1).lower() not in HOSTS:
            raise Refused("ModTrap asks only %s" % " and ".join(HOSTS))
        body = json.dumps({"query": query}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST", headers={"User-Agent": self.agent, "Accept": "application/json",
                                                                             "Content-Type": "application/json", **headers})
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

    def picture(self, url: str) -> tuple[bytes, str]:
        """One picture, as its bytes and its kind ("image/png", "image/jpeg", "image/webp", "image/gif"), read from
        its first bytes and not from what the host calls it. Only from the picture hosts; nothing is followed
        elsewhere. Raises Refused, with the reason in words."""
        try:
            parts = urllib.parse.urlsplit(url)
            plain = parts.scheme == "https" and not parts.username and not parts.password and parts.port in (None, 443)
        except ValueError:
            plain = False
        if not plain or (parts.hostname or "").lower() not in PICTURE_HOSTS:
            raise Refused("the picture's address is not one ModTrap fetches a picture from")
        req = urllib.request.Request(url, headers={"User-Agent": self.agent, "Accept": "image/webp,image/png,image/jpeg,image/gif"})
        try:
            with self._opener.open(req, timeout=TIMEOUT) as r:
                data = r.read(PICTURE_MAX + 1)
        except urllib.error.HTTPError as e:
            raise Refused("the picture's host answered %d" % e.code) from None
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise Refused("the picture's host could not be reached (%s)" % logbook.why(getattr(e, "reason", e) if isinstance(getattr(e, "reason", None), BaseException) else e)) from None
        if len(data) > PICTURE_MAX:
            raise Refused("the picture is larger than ModTrap takes")
        kind = next((k for magic, k in PICTURE_KINDS if data.startswith(magic)), "image/webp" if data[:4] == b"RIFF" and data[8:12] == b"WEBP" else "")
        if not kind:
            raise Refused("what the host sent is not a picture")
        return data, kind

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


ARCHIVE_DAY = re.compile(r" (\d{4})-(\d\d)-(\d\d)T(\d\d)-(\d\d)Z [0-9A-Za-z]{6,16}(?: ?\(\d+\))?\.(?:zip|7z|rar)$", re.IGNORECASE)


def archive_time(name: str) -> int:
    """The time of upload that Nexus writes into a file's name, or 0: the seconds in its older names
    ("Name-12604-6-0-1774355307.zip"), the day and minute in its newer ones ("Name 12604 6.0 2026-11-14T12-13Z
    code.zip", TL01§31), for which the end of that minute is given, so that the file never counts as older than it is."""
    m = ARCHIVE_TIME.search(name or "")
    if m:
        return int(m.group(1))
    m = ARCHIVE_DAY.search(name or "")
    if m:
        import calendar
        try:
            return calendar.timegm((int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), 59))
        except (ValueError, OverflowError):
            return 0
    return 0


def _iso_time(text: str) -> int:
    try:
        import calendar
        return calendar.timegm(time.strptime(text[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError):
        return 0


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
    if not kept.get("files") and kept.get("updated"):
        # Only the mod's own date is kept (TL01§29): it is the time of its newest file. The installed archive's
        # name carries the time of its own upload; where the two are the same, the installed file is that newest one.
        mine = archive_time(row.get("archive") or "")
        if mine and mine == kept["updated"]:
            return {"state": "current", "text": "the installed file is the mod's newest: nothing was uploaded after it", "newest": "", "file": "", "when": "", "asked": asked}
        return {"state": "not asked", "text": "Nexus has not been asked for this mod's files yet", "newest": "", "file": "", "when": "", "asked": ""}
    # "name" is what the file is downloaded as, where the service gives that; for newer uploads it gives a storage
    # code instead (WHY§110), so "label", the file's name on its page, is what is shown.
    files = {f[0]: {"id": f[0], "name": f[1], "version": f[2], "state": f[3], "time": f[4], "group": f[5] if len(f) > 5 else 0, "size": f[7] if len(f) > 7 else 0, "code": f[8] if len(f) > 8 else "",
                    "label": (f[6] if len(f) > 6 and f[6] else f[1] if ARCHIVE.search(f[1]) else "the mod's newer file")} for f in kept.get("files", [])}
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
                    "newest": mains[0]["version"], "file": mains[0]["label"], "when": _day(mains[0]["time"]), "asked": asked}
        return {"state": "maybe", "text": "the installed file could not be told among the mod's files; its main file is version %s, of %s, and "
                                          "the installed version reads %s" % (mains[0]["version"] or "(none given)", _day(mains[0]["time"]), row.get("version") or "(none given)"),
                "newest": mains[0]["version"], "file": mains[0]["label"], "when": _day(mains[0]["time"]), "asked": asked}
    best = None
    unsure = None
    for i in installed:
        seen, at, successors = set(), i, []
        while at in chain and chain[at][1] not in seen:
            at = chain[at][1]
            seen.add(at)
            successors.append(at)
        own = files.get(i)
        if not successors and own is not None and own["group"]:
            # No word of what replaced what, but the files of one line of versions share a group (TL01§29): the
            # newest current file of the installed file's group, uploaded after it, is its newer version.
            later = [f for f in files.values() if f["group"] == own["group"] and f["state"] in active and f["time"] > own["time"]]
            if later:
                newest = max(later, key=lambda f: f["time"])
                if best is None or newest["time"] > best["time"]:
                    best = newest
                continue
            if own["state"] in active:
                continue                                    # the newest of its line, and current
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
            how, best["label"], best["version"] or "(none given)", _day(best["time"])),
                "newest": best["version"], "file": best["label"], "when": _day(best["time"]), "asked": asked, "file_id": best["id"],
                "file_name": best["name"] if ARCHIVE.search(best["name"]) else "", "time": best["time"], "size": best["size"], "code": best["code"]}
    if unsure is not None:
        return {"state": "maybe", "text": "the installed file is marked old or is no longer listed, with no word of what replaced it; a later "
                                          "main file is there: %s, version %s, of %s" % (unsure["label"], unsure["version"] or "(none given)", _day(unsure["time"])),
                "newest": unsure["version"], "file": unsure["label"], "when": _day(unsure["time"]), "asked": asked}
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
    # Only where both versions are plain numbers and MO2's is the higher: a version MO2 made up from a file's date,
    # or one written in another way, says nothing by comparison (WHY§107).
    mine, theirs = _parts(row.get("version") or ""), _parts(row.get("mo2_newest") or "")
    if mine is not None and theirs is not None and theirs > mine and v["state"] in ("not asked", "maybe"):
        v["text"] += "; MO2's own last check saw version %s as the newest" % row["mo2_newest"]
        if v["state"] == "not asked":
            v["mo2"] = True
    return v


# --- the scan --------------------------------------------------------------------------------------------------------

# What is asked of each file of a mod (TL01§29, TL01§30): its number, its name on the mod's page, the name or the
# storage code of the file itself, version, category, time of upload, the line of versions it belongs to, and its size.
FILE_FIELDS = "fileId name uri version categoryId date groupId sizeInBytes sqid"


def _public_files(got: list) -> list:
    """The public service's files of one mod as ModTrap keeps them: [number, name or storage code, version,
    category, time, group, name on the page, size in bytes, the file's own short code]."""
    files = []
    for f in got:
        try:
            size = f.get("sizeInBytes")
            files.append([int(f["fileId"]), str(f.get("uri") or ""), str(f.get("version") or ""), int(f.get("categoryId") or 0),
                          int(f.get("date") or 0), int(f.get("groupId") or 0), str(f.get("name") or ""),
                          int(size) if isinstance(size, (int, str)) and str(size).isdigit() else 0,
                          str(f.get("sqid") or "") if re.fullmatch(r"[0-9A-Za-z]{6,16}", str(f.get("sqid") or "")) else ""])
        except (KeyError, TypeError, ValueError):
            continue
    return files


def ask_files(row: dict, net: Net, store: dict, now: float | None = None) -> str:
    """Asks Nexus's public service for the files of one mod, now, and keeps them: at the press of the update button,
    so that what ModTrap waits for is what the page offers at that moment. "" when kept, else why not."""
    if row.get("host") != "nexus" or not row.get("mod_id") or not re.fullmatch(r"[a-z0-9]+", row.get("game") or ""):
        return "not a mod of Nexus"
    headers = {"Application-Name": "ModTrap", "Application-Version": net.agent.split("/", 1)[-1]}
    answers = []
    for query in ('{ game(domainName: "%s") { id } }' % row["game"], None):
        if query is None:
            game = answers[0].get("game")
            if not isinstance(game, dict) or not isinstance(game.get("id"), int):
                return "Nexus's public service does not know the game"
            query = '{ m0: modFiles(modId: "%d", gameId: "%d") { %s } }' % (row["mod_id"], game["id"], FILE_FIELDS)
        status, h, body = net.ask(PUBLIC, query, headers)
        if status != 200 or not isinstance(body, dict) or not isinstance(body.get("data"), dict):
            return "Nexus's public service could not be reached (%s)" % h.get("why", "no answer") if status == 0 else "Nexus's public service did not answer the question (%d)" % status
        answers.append(body["data"])
    got = answers[1].get("m0")
    if not isinstance(got, list):
        return "Nexus's public service gave no files"
    name = "%s/%d" % (row["game"], row["mod_id"])
    rec = store.setdefault("nexus", {}).get(name) or {"asked": 0, "updated": 0, "via": "public"}
    rec.update(files=_public_files(got), chain=[], asked=int(now if now is not None else time.time()), via="public")
    store["nexus"][name] = rec
    save(store)
    return ""

def _scan_public(rows: list[dict], wanted: dict, net: Net, store: dict, now: float, say, halted, nx: dict, force: bool, pause: float) -> bool:
    """Asks Nexus's public service, without any key (MT44, TL01§29). First, in questions of fifty mods each, when
    each mod last had a file uploaded. Then, only for mods where that is later than the installed file or cannot be
    compared, the mod's files. False when the service does not answer as expected at the outset: nothing is kept
    then, and the caller may go the other way. Otherwise True, with the account in `nx`."""
    headers = {"Application-Name": "ModTrap", "Application-Version": net.agent.split("/", 1)[-1]}
    asked = 0

    def ask(query: str):
        nonlocal asked
        if asked and pause:
            time.sleep(pause)
        asked += 1
        status, h, body = net.ask(PUBLIC, query, headers)
        if status != 200 or not isinstance(body, dict) or not isinstance(body.get("data"), dict):
            errors = body.get("errors") if isinstance(body, dict) else None
            why = ("Nexus's public service could not be reached (%s)" % h.get("why", "no answer") if status == 0 else
                   "Nexus's public service asks ModTrap to wait (%d)" % status if status in (429, 503) else
                   "Nexus's public service refused the question" if errors else "Nexus's public service answered with an error (%d)" % status)
            return None, why
        return body["data"], ""

    games: dict[str, int] = {}
    for game in sorted({g for g, _i in wanted}):
        if not re.fullmatch(r"[a-z0-9]+", game):
            continue
        data, why = ask('{ game(domainName: "%s") { id } }' % game)
        if data is None or not isinstance(data.get("game"), dict) or not isinstance(data["game"].get("id"), int):
            nx["public_why"] = why or "Nexus's public service does not know the game"
            return False
        games[game] = data["game"]["id"]

    # What each row has installed, by mod: the time in its archive's name, where there is one.
    times: dict[tuple[str, int], list[int]] = {}
    for r in rows:
        if r["host"] == "nexus":
            times.setdefault((r["game"], r["mod_id"]), []).append(archive_time(r.get("archive") or ""))
    order = sorted((k for k in wanted if k[0] in games), key=lambda k: (0 if wanted[k] else 1, k))
    need: list[tuple[str, int]] = []
    for at in range(0, len(order), MODS_PER_QUESTION):
        if halted():
            nx["why_stopped"] = "stopped"
            nx["left"] = len(order) - at
            return True
        part = order[at:at + MODS_PER_QUESTION]
        say("asking Nexus when %d of %d mods last had a new file" % (min(at + len(part), len(order)), len(order)))
        ids = ", ".join('{ gameDomain: "%s", modId: %d }' % k for k in part)
        data, why = ask("{ legacyModsByDomain(ids: [%s], count: %d) { nodes { modId gameId status updatedAt } } }" % (ids, len(part)))
        page = (data or {}).get("legacyModsByDomain") if data is not None else None
        if not isinstance(page, dict) or not isinstance(page.get("nodes"), list):
            if at == 0:
                nx["public_why"] = why or "Nexus's public service answered in a form ModTrap does not know"
                return False
            nx["why_stopped"] = why or "Nexus's public service answered in a form ModTrap does not know"
            nx["left"] = len(order) - at
            return True
        by_game = {v: k for k, v in games.items()}
        seen: dict[tuple[str, int], dict] = {}
        for n in page["nodes"]:
            try:
                seen[(by_game[int(n["gameId"])], int(n["modId"]))] = n
            except (KeyError, TypeError, ValueError):
                continue
        for k in part:
            name = "%s/%d" % k
            n = seen.get(k)
            if n is None or str(n.get("status") or "published") != "published":
                store["nexus"][name] = {"asked": int(now), "gone": "hidden or removed" if n is None else "its page is %s" % str(n.get("status")).replace("_", " "), "via": "public"}
                continue
            updated = _iso_time(str(n.get("updatedAt") or ""))
            prev = store["nexus"].get(name)
            if not force and updated and all(t and t == updated for t in times.get(k, [0])):
                # Every installed file of this mod carries the time of the mod's newest upload: it is that file,
                # and the mod's files need not be asked for.
                store["nexus"][name] = {"asked": int(now), "updated": updated, "files": [], "chain": [], "via": "public"}
            elif not force and prev is not None and prev.get("files") and prev.get("updated") == updated:
                prev["asked"] = int(now)                    # nothing was uploaded since: what is kept still stands
            else:
                store["nexus"][name] = {"asked": int(now), "updated": updated, "files": [], "chain": [], "via": "public"}
                need.append(k)
    nx["month_list"] = len(order)
    # The files of the mods that need them, a few mods to a question.
    for at in range(0, len(need), FILES_PER_QUESTION):
        if halted():
            nx["why_stopped"] = "stopped"
        elif asked >= PUBLIC_QUESTIONS:
            nx["why_stopped"] = "%d questions were asked in this scan; the rest follow at the next" % asked
        if nx["why_stopped"]:
            nx["left"] = len(need) - at
            break
        part = need[at:at + FILES_PER_QUESTION]
        say("asking Nexus for the files of mod %d of %d" % (min(at + len(part), len(need)), len(need)))

        def files_of(some):
            return "{ %s }" % " ".join('m%d: modFiles(modId: "%d", gameId: "%d") { %s }' % (i, k[1], games[k[0]], FILE_FIELDS)
                                       for i, k in enumerate(some))
        data, why = ask(files_of(part))
        answers: dict[tuple[str, int], object] = {}
        if data is not None:
            answers = {k: data.get("m%d" % i) for i, k in enumerate(part)}
        elif len(part) > 1:
            for k in part:                                  # one of them upset the question: each alone
                one, _w = ask(files_of([k]))
                answers[k] = one.get("m0") if one is not None else None
        else:
            answers = {part[0]: None}
        if all(v is None for v in answers.values()) and why and "wait" in why:
            nx["why_stopped"] = why
            nx["left"] = len(need) - at
            break
        for k, got in answers.items():
            name = "%s/%d" % k
            rec = store["nexus"].get(name) or {"asked": int(now), "updated": 0, "via": "public"}
            if not isinstance(got, list):
                rec["updated"] = 0                          # not answered: asked again at the next scan
                store["nexus"][name] = rec
                continue
            rec.update(files=_public_files(got), chain=[], asked=int(now), via="public")
            store["nexus"][name] = rec
            nx["asked"] += 1
        if nx["asked"] % 100 < FILES_PER_QUESTION:
            save(store)
    nx["questions"] = asked
    return True


def scan(rows: list[dict], key: str, net: Net, store: dict | None = None, now: float | None = None, progress=None,
         stopped=None, per_scan: int = NEXUS_PER_SCAN, force: bool = False, pause: float = PUBLIC_PAUSE) -> dict:
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

    # Nexus's newer service first: it needs no key (MT44). The older one, with the owner's key, only where the newer
    # one does not answer as expected.
    public = _scan_public(rows, wanted, net, store, now, say, halted, nx, force, pause) if wanted else True
    nx["way"] = "public" if public else "key"
    if wanted and not public and not key:
        nx["why_stopped"] = (nx.get("public_why") or "Nexus's public service did not answer as expected") + \
            "; the older service answers only with an account's key, and none is kept"
        nx["left"] = len(wanted)
    elif wanted and not public:
        nx["why_stopped"] = ""
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
    if nx.get("way") == "public":
        log.info("scan for updates: Nexus, by its public service, without a key: %d mod(s) with a number, %s asked when they last had a new file, "
                 "the files of %d asked for, %d left for later, in %d question(s)%s", nx["mods"], format(nx["month_list"], ","), nx["asked"], nx["left"],
                 nx.get("questions", 0), ": " + nx["why_stopped"] if nx["why_stopped"] else "")
    else:
      log.info("scan for updates: Nexus, by its older service, with the key%s: %d mod(s) with a number, the month's list named %s, %d asked about now, %d left for later%s%s",
             " (the public service: %s)" % nx["public_why"] if nx.get("public_why") else "",
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
            return {"open": page, "why": "no Nexus key is kept, so the download goes through Nexus's page, in your browser"}
        if premium is False:
            return {"open": page, "why": "Nexus lets a program start a download only for a Premium account, so it goes through Nexus's page, in your browser"}
        return {"fetch": "nexus", "file_id": v["file_id"], "name": v.get("file_name") or v.get("file") or "", "version": v.get("newest") or "", "page": page}
    if row["host"] == "github" and row.get("repo"):
        kept = store["github"].get(row["repo"].lower())
        got = github_asset(row, kept)
        if got is None:
            return {"open": page, "why": "the newest release has no file, or several, and ModTrap cannot tell which is this mod's"}
        return {"fetch": "github", "url": got[1], "name": got[0], "version": (kept or {}).get("tag", ""), "page": page}
    if row["host"] == "loverslab":
        return {"open": page, "why": "LoversLab gives files only to your logged-in browser; download it there, then use “Manual update” in the mod's menu"}
    return {"open": page, "why": "ModTrap cannot fetch from there; download it in your browser, then use “Manual update” in the mod's menu"}


def fetch(how: dict, row: dict, key: str, net: Net, folder: Path, progress=None, stopped=None) -> dict:
    """Fetches the file `how_to_get` named into `folder`: {"path", "name", "version"} or {"open", "why"} when the
    host would not give it after all. Raises Refused when the fetching itself fails."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", how.get("name") or "the newer file")[:200]
    if how["fetch"] == "nexus":
        url, why = nexus_link(key, net, row["game"], row["mod_id"], how["file_id"])
        if not url:
            if "Premium" in why:
                return {"open": how["page"], "why": why + ", so it goes through Nexus's page, in your browser"}
            raise Refused(why)
    else:
        url = how["url"]
    folder.mkdir(parents=True, exist_ok=True)
    size = net.download(url, folder / name, progress, stopped)
    log.info("fetched “%s” for “%s” from %s: %.1f MB", name, row["mod"], "Nexus" if how["fetch"] == "nexus" else "GitHub", size / (1024 * 1024))
    return {"path": folder / name, "name": name, "version": how.get("version", "")}


def get_of(row: dict, v: dict) -> str:
    """Where the owner gets the newer file a verdict speaks of: for Nexus the file's own page, opened the way
    Nexus's "manual download" button opens it, so that the browser itself saves the file (WHY§112: the "mod manager
    download" hands it to a program set up for such links, which need not be there); for GitHub the newest release."""
    if v["state"] not in ("update", "maybe"):
        return ""
    if row["host"] == "nexus":
        if v.get("file_id"):
            return "https://www.nexusmods.com/%s/mods/%d?tab=files&file_id=%d" % (row["game"], row["mod_id"], v["file_id"])
        return "https://www.nexusmods.com/%s/mods/%d?tab=files" % (row["game"], row["mod_id"])
    if row["host"] == "github" and row.get("repo"):
        return "https://github.com/%s/releases/latest" % row["repo"]
    return ""


def picture_address(row: dict, net: Net) -> str:
    """Where a mod's one picture is (the picture its page opens with), or "" where none is known. For a mod of
    Nexus, the public service is asked, without any key (TL01§32); for a repository at GitHub it is the preview
    picture GitHub draws for it. Other sites give none without an account."""
    if row.get("host") == "github" and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", row.get("repo") or ""):
        return "https://opengraph.githubassets.com/1/%s" % row["repo"]
    if row.get("host") != "nexus" or not row.get("mod_id") or not re.fullmatch(r"[a-z0-9]+", row.get("game") or ""):
        return ""
    headers = {"Application-Name": "ModTrap", "Application-Version": net.agent.split("/", 1)[-1]}
    status, _h, body = net.ask(PUBLIC, '{ game(domainName: "%s") { id } }' % row["game"], headers)
    game = body.get("data", {}).get("game") if status == 200 and isinstance(body, dict) and isinstance(body.get("data"), dict) else None
    if not isinstance(game, dict) or not isinstance(game.get("id"), int):
        return ""
    status, _h, body = net.ask(PUBLIC, '{ mod(modId: "%d", gameId: "%d") { thumbnailLargeUrl pictureUrl } }' % (row["mod_id"], game["id"]), headers)
    mod = body.get("data", {}).get("mod") if status == 200 and isinstance(body, dict) and isinstance(body.get("data"), dict) else None
    if not isinstance(mod, dict):
        return ""
    for key in ("thumbnailLargeUrl", "pictureUrl"):
        url = mod.get(key)
        if isinstance(url, str) and (urllib.parse.urlsplit(url).hostname or "").lower() in PICTURE_HOSTS:
            return url
    return ""


def home_of(row: dict) -> str:
    """The mod's own page as a visitor opens it (its first page, not its files), for the pop-up's link."""
    if row.get("host") == "nexus" and row.get("mod_id") and row.get("game"):
        return "https://www.nexusmods.com/%s/mods/%d" % (row["game"], row["mod_id"])
    if row.get("host") == "github" and row.get("repo"):
        return "https://github.com/%s" % row["repo"]
    url = row.get("url", "") if row.get("host") in ("url", "loverslab") else ""
    return url if url.lower().startswith(("https://", "http://")) else ""


def page_of(row: dict) -> str:
    """The mod's own page, for the owner to open."""
    if row["host"] == "nexus":
        return "https://www.nexusmods.com/%s/mods/%d?tab=files" % (row["game"], row["mod_id"])
    if row["host"] == "github" and row.get("repo"):
        return "https://github.com/%s/releases" % row["repo"]
    return row.get("url", "") if row["host"] in ("url", "loverslab") else ""


__all__ = ["Net", "Refused", "fetch", "home_of", "picture_address", "get_of", "github_asset", "github_verdict", "how_to_get", "nexus_account", "nexus_link", "load", "nexus_verdict", "page_of", "same_version", "save", "scan", "verdict"]
