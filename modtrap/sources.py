"""Where each mod of the modlist came from (MT37, WHY§101): read from files on this PC only, nothing asked of anyone.

Three records say where a mod came from, and ModTrap reads all three:

- the mod's own `meta.ini`, which MO2 keeps (MO01§12): the mod's number at Nexus, the version installed, the newest
  version MO2 last saw, the archive it was installed from, the files installed by their numbers, a web address;
- the `.meta` file MO2 keeps beside each downloaded archive (MO01§12): the mod's and the file's number, a web
  address;
- the modlist's own Wabbajack file, if the owner names it (TL01§27): every archive of the list with where it is
  downloaded from, and which mod folders the list fills from which archive. It also says which mods are the
  list's own: a mod it does not name was added afterwards.

Nothing here changes a file, and nothing here goes out to the network: that is `updates.py`.
"""

from __future__ import annotations

import json
import os
import re
import time
import zipfile
from pathlib import Path

from . import logbook, paths
MOD_PREFIX = "ModTrap - "               # the name of the mod ModTrap makes for a demaster (as `demaster.MOD_PREFIX`; not
                                     # taken from there: the parts that change a modlist are loaded only with their switch)
from .instance import Instance, fold, parse_ini

log = logbook.get("sources")

META_BYTES = 512 * 1024              # a meta file is read no further than this
NOTE_MAX = 400                       # characters of a mod's comment or note that are shown
WJ_ENTRY = "modlist"                 # the list itself, inside a Wabbajack file (TL01§27)
WJ_CHUNK = 1024 * 1024
WJ_VALUE_MAX = 64 * 1024 * 1024      # one entry of the list larger than this is passed over
# A repository at GitHub, by any page of it (WHY§147): the repository itself, its releases, its code, its issues. The
# page of one release, or a file of it, also names the release that is installed. An address of GitHub's own pages
# (github.com/orgs/…, /settings/…) is not a repository.
GITHUB = re.compile(r"^https?://(?:www\.)?github\.com/([A-Za-z0-9][A-Za-z0-9-]*)/([A-Za-z0-9_.-]+)(?=[/?#]|$)", re.IGNORECASE)
GITHUB_TAG = re.compile(r"^/(?:releases/(?:download|tag|expanded_assets)/([^/?#]+)|archive/refs/tags/([^?#]+?)\.(?:zip|tar\.gz)(?:[?#]|$))", re.IGNORECASE)
GITHUB_OWN = frozenset(("orgs", "settings", "topics", "search", "marketplace", "sponsors", "features", "about", "users", "apps", "collections", "explore",
                        "notifications", "pulls", "issues", "login", "join", "enterprise", "pricing", "customer-stories", "security", "site", "trending",
                        "new", "codespaces"))
# The same repository by GitHub's other hosts: a file of its code, its packed code, the service programs ask.
GITHUB_OTHER = re.compile(r"^https?://(?:raw\.githubusercontent\.com|codeload\.github\.com|api\.github\.com/repos)/([A-Za-z0-9][A-Za-z0-9-]*)/([A-Za-z0-9_.-]+)(?=[/?#]|$)", re.IGNORECASE)


def github_repo(url: str) -> tuple[str, str] | None:
    """The repository an address at GitHub is of, and the release it names ("" where it names none): ("owner/name",
    tag). None where the address is not of a repository."""
    from urllib.parse import unquote
    hit = GITHUB.match(url)
    tag = ""
    if hit is not None:
        if hit.group(1).lower() in GITHUB_OWN:
            return None
        named = GITHUB_TAG.match(url[hit.end():])
        if named is not None:
            tag = unquote(named.group(1) or named.group(2) or "")
    else:
        hit = GITHUB_OTHER.match(url)
    if hit is None:
        return None
    repo = re.sub(r"\.git$", "", hit.group(2), flags=re.IGNORECASE)
    return ("%s/%s" % (hit.group(1), repo), tag) if repo not in ("", ".", "..") else None
LOVERSLAB = re.compile(r"^https?://(?:www\.)?loverslab\.com/", re.IGNORECASE)
_data: dict | None = None


def host_of(url: str) -> str:
    """The kind of source a web address is: "github", "loverslab", or "url" for any other."""
    return "github" if github_repo(url) else "loverslab" if LOVERSLAB.match(url) else "url"


def data() -> dict:
    """ModTrap's data on sources (`sources.json`): the name of a game at Nexus by MO2's and by Wabbajack's name
    for it, and the states of a file at Nexus."""
    global _data
    if _data is None:
        with open(Path(__file__).with_name("data") / "sources.json", "rb") as f:
            _data = json.loads(f.read().decode("utf-8"))
    return _data


def nexus_game(name: str) -> str:
    """The game's name in Nexus's addresses, for MO2's or Wabbajack's name of it; "" when ModTrap does not know."""
    return str(data()["nexus_games"].get((name or "").strip().lower(), ""))


def _ini_text(raw: bytes) -> dict[str, dict[str, str]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", "replace")
    try:
        got = parse_ini(text)
    except Exception:
        return {}
    return {sec.lower(): {k.lower(): v for k, v in keys.items()} for sec, keys in got.items()}


def _ini(path: Path) -> dict[str, dict[str, str]]:
    try:
        with open(path, "rb") as f:
            return _ini_text(f.read(META_BYTES))
    except OSError:
        return {}


def _number(text: str) -> int:
    try:
        n = int(str(text).strip())
    except ValueError:
        return 0
    return n if n > 0 else 0


def mod_meta(folder: Path) -> dict:
    """What a mod's `meta.ini` says of where it came from (MO01§12), and what the owner wrote of it in MO2:
    {"mod_id", "game", "version", "mo2_newest", "ignored", "archive", "repository", "url", "last_query", "files":
    [(mod number, file number)], "comments" (MO2's Notes column), "notes" (the longer note, as plain words)}."""
    return mod_meta_of(_ini(folder / "meta.ini"))


def mod_meta_of(ini: dict) -> dict:
    g = ini.get("general", {})
    files = []
    arr = ini.get("installedfiles", {})
    for i in range(1, _number(arr.get("size", "0")) + 1):
        pair = (_number(arr.get("%d\\modid" % i, "")), _number(arr.get("%d\\fileid" % i, "")))
        if pair[0] and pair[1] and pair not in files:
            files.append(pair)
    url = g.get("url", "") if g.get("hascustomurl", "").lower() == "true" or not _number(g.get("modid", "")) else ""
    notes = re.sub(r"\s+", " ", re.sub(r"<style\b.*?</style>|<[^>]*>", " ", g.get("notes", ""), flags=re.IGNORECASE | re.DOTALL))
    for ent, ch in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"')):
        notes = notes.replace(ent, ch)
    return {"comments": g.get("comments", "").strip()[:NOTE_MAX], "notes": notes.strip()[:NOTE_MAX],
            "mod_id": _number(g.get("modid", "")), "game": g.get("gamename", ""), "version": g.get("version", ""),
            "mo2_newest": g.get("newestversion", ""), "ignored": g.get("ignoredversion", ""),
            "archive": os.path.basename(g.get("installationfile", "").replace("\\", "/")),
            "repository": g.get("repository", ""), "url": url if url.lower().startswith(("http://", "https://")) else "",
            "last_query": g.get("lastnexusquery", ""), "files": files}


def download_meta(downloads: Path | None, archive: str) -> dict:
    """What the `.meta` file beside a downloaded archive says (MO01§12). {"mod_id", "file_id", "game", "version",
    "url"}; empty when there is none."""
    if downloads is None or not archive:
        return {}
    return download_meta_of(_ini(downloads / (archive + ".meta")))


def download_meta_of(ini: dict) -> dict:
    g = ini.get("general", {})
    if not g:
        return {}
    url = next((u for u in g.get("url", "").split(";") if u.lower().startswith(("http://", "https://"))), "")
    return {"mod_id": _number(g.get("modid", "")), "file_id": _number(g.get("fileid", "")), "game": g.get("gamename", ""),
            "version": g.get("version", ""), "url": url}


# --- the mark a browser leaves on a downloaded file (WHY§109) -----------------------------------------------------------

MARK = ":Zone.Identifier"            # Windows keeps it beside the file's own bytes, on the disks it uses for that
MARK_BYTES = 8 * 1024


def _read_mark(path: Path) -> str:
    """The text of the mark on a file, or "" where there is none: on another system, on a disk that keeps none,
    or for a file that no browser downloaded."""
    if os.name != "nt":
        return ""
    try:
        with open(str(path) + MARK, "rb") as f:
            raw = f.read(MARK_BYTES)
    except OSError:
        return ""
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return ""


def web_mark(path: Path, read=None) -> dict:
    """Where a browser says it downloaded a file from: {"url": the address of the file, "page": the page the download
    was started on}; either may be missing. `read` stands in for the reading in tests."""
    text = (read or _read_mark)(path)
    out = {}
    for line in text.splitlines():
        key, _eq, value = line.partition("=")
        value = value.strip()
        if value.lower().startswith(("http://", "https://")) and len(value) <= 2000 and not any(c.isspace() for c in value):
            if key.strip().lower() == "hosturl":
                out["url"] = value
            elif key.strip().lower() == "referrerurl":
                out["page"] = value
    return out


def source_of_mark(mark: dict) -> str:
    """The one address of a mark that says most of the source: a GitHub address before any other (the release's
    file, else the page), then a LoversLab one, then the page the download was started on, then the file's own."""
    both = [mark.get("url", ""), mark.get("page", "")]
    for test in (github_repo, LOVERSLAB.match):
        hit = next((u for u in both if u and test(u)), "")
        if hit:
            return hit
    return mark.get("page") or mark.get("url") or ""


# --- what the owner gave by hand (WHY§103) -------------------------------------------------------------------------

GIVEN = "given-sources.json"
LINK_MAX = 500
# A mod's page at Nexus, by any tab of it and with whatever follows its number (WHY§147); also as the site's newer
# addresses write it, and as a "mod manager download" link does.
NEXUS_PAGE = re.compile(r"^https?://(?:www\.|next\.)?nexusmods\.com/(?:games/)?([a-z0-9]+)/mods/(\d+)(?![0-9])", re.IGNORECASE)
NEXUS_NXM = re.compile(r"^nxm://([a-z0-9]+)/mods/(\d+)(?:/files/(\d+))?", re.IGNORECASE)
NEXUS_FILE = re.compile(r"[?&]file_id=(\d+)", re.IGNORECASE)
NAMED = re.compile(r"(?<![0-9])(?<![0-9]\.)v?(\d+(?:\.\d+){1,4}(?:[-.]?(?:rc|beta|alpha|pre|b|a)[-.]?\d*)?[a-z]?)(?![0-9A-Za-z])", re.IGNORECASE)


def name_end_version(name: str) -> str:
    """The version a name ends with, where it is written in a way `adding.version_in` does not take: after a dot
    ("Thing.Pack.1.2.0"), or with a pre-release's mark ("Thing-0.7.0-rc1"). "" where the name ends otherwise."""
    name = name.strip().rstrip(")")
    last = None
    for last in NAMED.finditer(name):
        pass
    return last.group(1) if last is not None and last.end() == len(name) and last.start() > 0 else ""


def names_version(version: str, *names: str) -> bool:
    """Whether one of the names (a mod's, its archive's) carries this version, as a whole: "1.2.0" is in
    "Thing.1.2.0" and in "Thing-v1.2.0.zip", not in "Thing 11.2.0" or "Thing 1.2.01"."""
    want = version.strip().lower().lstrip("v")
    if not re.search(r"\d", want):
        return False
    for name in names:
        name = re.sub(r"\.(zip|7z|rar)$", "", name or "", flags=re.IGNORECASE)
        if any(v.lower() == want for v in NAMED.findall(name)):
            return True
    return False


def given_load() -> dict:
    """What the owner told ModTrap of sources, kept in ModTrap's own folder and never in a mod's: {"links": {modlist:
    {mod, folded: address}}, "archives": {archive's name, folded: what its meta file said}, "mods": {modlist: {mod,
    folded: what its meta file said}}}. And what ModTrap itself notes there for a mod by its name: "favourites",
    and "choices": {modlist: {mod, folded: the answers its installer was given, by name}} (MT84)."""
    try:
        with open(paths.home() / GIVEN, "rb") as f:
            got = json.loads(f.read().decode("utf-8"))
        if got.get("format") == "modtrap-given/1":
            for k in ("links", "archives", "mods", "favourites", "choices"):
                got.setdefault(k, {})
            return got
    except (OSError, ValueError):
        pass
    return {"format": "modtrap-given/1", "links": {}, "archives": {}, "mods": {}, "favourites": {}, "choices": {}}


def given_save(given: dict) -> None:
    paths.write_atomic(paths.home() / GIVEN, json.dumps(given, separators=(",", ":")).encode("utf-8"))


def parse_link(url: str) -> dict:
    """A web address the owner gave as a mod's source, in ModTrap's words: {"host": "nexus", "game", "mod_id",
    "file_id"} for a mod's page at Nexus, {"host": "github", "repo", "tag", "url"} for a repository, {"host": "url",
    "url"} for anything else. Raises ValueError with the reason in words."""
    url = url.strip().strip("<>\"'")
    hit = NEXUS_NXM.match(url)
    if hit:
        url = "https://www.nexusmods.com/%s/mods/%s%s" % (hit.group(1).lower(), hit.group(2), "?tab=files&file_id=%s" % hit.group(3) if hit.group(3) else "")
    elif re.match(r"^(www\.|next\.)?(nexusmods\.com|github\.com)/", url, re.IGNORECASE):
        url = "https://" + url                         # copied without its beginning
    if not url.lower().startswith(("http://", "https://")) or len(url) > LINK_MAX or any(c.isspace() or ord(c) < 32 for c in url):
        raise ValueError("a source link is a web address: it starts with https:// and has no spaces")
    hit = NEXUS_PAGE.match(url)
    if hit:
        f = NEXUS_FILE.search(url)
        return {"host": "nexus", "game": hit.group(1).lower(), "mod_id": int(hit.group(2)), "file_id": int(f.group(1)) if f else 0, "url": url}
    repo = github_repo(url)
    if repo is not None:
        return {"host": "github", "repo": repo[0], "tag": repo[1], "url": url}
    return {"host": host_of(url), "url": url}


def own_record(archive: str, meta: dict | None = None) -> str:
    """The `meta.ini` ModTrap writes for a mod it adds (MO01§12): the archive it came from and, where known, its
    source, in MO2's own fields, so that MO2 and ModTrap both know afterwards where the mod came from. `meta`:
    {"game": MO2's name of the game, "mod_id", "file_id", "version", "url"}; all optional."""
    meta = meta or {}
    clean = lambda v: re.sub(r'[\r\n"]', "", str(v))
    lines = ["[General]"]
    if archive:
        lines.append("installationFile=%s" % archive.replace("\\", "/"))
    if meta.get("mod_id") and meta.get("game"):
        lines += ["gameName=%s" % clean(meta["game"]), "modid=%d" % int(meta["mod_id"]), "repository=Nexus"]
    if meta.get("version"):
        lines.append('version="%s"' % clean(meta["version"]))
    if meta.get("url") and str(meta["url"]).lower().startswith(("http://", "https://")):
        lines += ['url="%s"' % clean(meta["url"]), "hasCustomURL=true"]
    if meta.get("mod_id") and meta.get("file_id") and meta.get("game"):
        lines += ["", "[installedFiles]", "1\\modid=%d" % int(meta["mod_id"]), "1\\fileid=%d" % int(meta["file_id"]), "size=1"]
    return "\r\n".join(lines) + "\r\n"


# --- a Wabbajack file --------------------------------------------------------------------------------------------

def _values(stream, want: set[str]):
    """Walks one large JSON object piece by piece and gives (key, value) for each entry of the arrays named in
    `want` at its top, and (key, value) for its other top entries that are plain texts. The list of a large
    modlist is hundreds of megabytes: it is never held whole."""
    dec = json.JSONDecoder()
    buf = ""
    pos = 0
    done = False

    def more() -> bool:
        nonlocal buf, pos, done
        if done:
            return False
        piece = stream.read(WJ_CHUNK)
        if not piece:
            done = True
            return False
        buf = buf[pos:] + piece
        pos = 0
        return True

    def skip_space() -> bool:
        nonlocal pos
        while True:
            while pos < len(buf) and buf[pos] in " \t\r\n,":
                pos += 1
            if pos < len(buf):
                return True
            if not more():
                return False

    def value():
        """One whole JSON value at `pos`; more of the file is read until it is whole."""
        nonlocal pos
        while True:
            try:
                got, end = dec.raw_decode(buf, pos)
                if end == len(buf) and not done and not buf[pos] in '[{"':
                    raise ValueError("a number or word may go on in the next piece")
                pos = end
                return got
            except ValueError:
                if len(buf) - pos > WJ_VALUE_MAX or not more():
                    raise

    if not skip_space() or buf[pos] != "{":
        raise ValueError("not a list")
    pos += 1
    while skip_space():
        if buf[pos] == "}":
            return
        key = value()
        if not skip_space() or buf[pos] != ":":
            raise ValueError("no value")
        pos += 1
        if not skip_space():
            raise ValueError("cut short")
        if key in want and buf[pos] == "[":
            pos += 1
            while skip_space():
                if buf[pos] == "]":
                    pos += 1
                    break
                yield key, value()
        else:
            got = value()
            if isinstance(got, (str, int, float)):
                yield key, got


def _state(state: dict) -> dict:
    """Where an archive of the list is downloaded from, in ModTrap's own words (TL01§27)."""
    kind = str(state.get("$type", "")).split(",")[0].strip()
    if kind.startswith("NexusDownloader"):
        return {"host": "nexus", "game": nexus_game(str(state.get("GameName", ""))), "mod_id": _number(state.get("ModID", "")),
                "file_id": _number(state.get("FileID", "")), "version": str(state.get("Version") or "")}
    url = str(state.get("Url") or state.get("IPS4Url") or "")
    if url:
        return {"host": host_of(url), "url": url}
    if kind.startswith("LoversLab"):
        return {"host": "loverslab", "url": ""}
    return {"host": {"GameFileSourceDownloader": "game", "WabbajackCDNDownloader+State": "list's own files",
                     "ManualDownloader": "by hand", "MegaDownloader": "mega", "GoogleDriveDownloader": "google drive",
                     "MediaFireDownloader+State": "mediafire", "ModDBDownloader": "moddb"}.get(kind, kind or "unknown")}


class _Inflate:
    """The bytes of one entry of a zip archive as they lie in it (TL01§27), given back as the entry's own bytes: for
    a list the page cut out of a Wabbajack file and sent alone."""

    def __init__(self, raw, method: int):
        import zlib
        if method not in (0, 8):
            raise ValueError("the list is packed in a way ModTrap does not read (%d)" % method)
        self.raw, self.z, self.done = raw, zlib.decompressobj(-15) if method == 8 else None, False

    def readable(self):
        return True

    def writable(self):
        return False

    def seekable(self):
        return False

    @property
    def closed(self):
        return False

    def flush(self):
        pass

    def close(self):
        pass

    def read(self, n: int = -1) -> bytes:
        import zlib
        if self.z is None:
            return self.raw.read(n)
        out = b""
        while not out and not self.done:
            piece = self.raw.read(WJ_CHUNK)
            try:
                out = self.z.decompress(piece) if piece else self.z.flush()
            except zlib.error:
                raise ValueError("the list's bytes are not whole") from None
            self.done = not piece
        return out

    def readinto(self, b) -> int:
        got = self.read(len(b))
        b[:len(got)] = got
        return len(got)

    read1 = read


def _read_list(raw, progress=None) -> dict:
    """The list of a Wabbajack file, from its bytes (TL01§27). See `read_wabbajack`."""
    import io
    archives: dict[str, dict] = {}
    by_name: dict[str, str] = {}
    uses: dict[str, dict[str, int]] = {}
    top: dict[str, object] = {}
    n_dir = 0
    hosts: dict[str, int] = {}
    stream = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
    try:
        for key, v in _values(stream, {"Archives", "Directives"}):
            if key == "Archives" and isinstance(v, dict):
                h = str(v.get("Hash", ""))
                st = _state(v.get("State") or {}) if isinstance(v.get("State"), dict) else {"host": "unknown"}
                st["name"] = str(v.get("Name", ""))
                archives[h] = st
                by_name[fold(st["name"])] = h
                hosts[st["host"]] = hosts.get(st["host"], 0) + 1
            elif key == "Directives" and isinstance(v, dict):
                n_dir += 1
                to = str(v.get("To", "")).replace("/", "\\")
                parts = to.split("\\")
                if len(parts) >= 3 and parts[0].lower() == "mods":
                    mod = uses.setdefault(fold(parts[1]), {})
                    ahp = v.get("ArchiveHashPath")
                    h = str(ahp[0]) if isinstance(ahp, list) and ahp else ""
                    mod[h] = mod.get(h, 0) + 1
                if progress is not None and n_dir % 100_000 == 0:
                    progress(n_dir)
            elif key in ("Name", "Version", "WabbajackVersion", "GameType"):
                top[key] = v
    except (ValueError, RecursionError) as e:
        raise ValueError("its list could not be read to the end (%s)" % (str(e) if "bytes are not whole" in str(e) else logbook.why(e))) from None
    if not archives and not n_dir:
        raise ValueError("it holds no archives and no entries of what goes where: it is not a Wabbajack list")
    mods = {m: [h for h, _n in sorted(hs.items(), key=lambda kv: -kv[1]) if h in archives] for m, hs in uses.items()}
    return {"name": str(top.get("Name", "")), "version": str(top.get("Version", "")), "game": str(top.get("GameType", "")),
            "archives": archives, "by_name": by_name, "mods": mods,
            "counts": {"archives": len(archives), "directives": n_dir, "mods": len(mods), "hosts": hosts}}


def read_wabbajack(path: Path, progress=None) -> dict:
    """The modlist's own Wabbajack file (TL01§27): {"name", "version", "archives": {archive's hash: {"name", "host",
    ...}}, "by_name": {archive's file name, folded: hash}, "mods": {mod folder, folded: [archive hashes, most used
    first]}, "counts": {...}}. Raises ValueError with a reason in words when the file is not one."""
    try:
        zf = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as e:
        raise ValueError("it could not be opened as a Wabbajack file (%s)" % logbook.why(e)) from None
    with zf:
        if WJ_ENTRY not in zf.namelist():
            raise ValueError("it holds no list (an entry called “%s”)" % WJ_ENTRY)
        with zf.open(WJ_ENTRY) as raw:
            return _read_list(raw, progress)


def read_list_bytes(path: Path, method: int, progress=None) -> dict:
    """As `read_wabbajack`, of the list's bytes alone as they lay in the Wabbajack file: stored (0) or deflated (8)."""
    with open(path, "rb") as f:
        return _read_list(_Inflate(f, method), progress)


def said(got: dict, seconds: float) -> None:
    c = got["counts"]
    log.info("the Wabbajack list “%s” (%s) was read in %.1f s: %s archive(s) (%s), %s entr(ies) of what goes where, %s mod folder(s)",
             got["name"], got["version"], seconds, format(c["archives"], ","),
             ", ".join("%s from %s" % (format(n, ","), host) for host, n in sorted(c["hosts"].items(), key=lambda kv: -kv[1])),
             format(c["directives"], ","), format(c["mods"], ","))


def memo_name(name: str, size: int, date: int) -> str:
    return "%s-%d-%d.json" % (re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:80], size, date)


def memo_read(name: str) -> dict | None:
    try:
        with open(paths.home() / "wabbajack" / name, "rb") as f:
            got = json.loads(f.read().decode("utf-8"))
        return got["list"] if got.get("format") == "modtrap-wabbajack/1" else None
    except (OSError, ValueError, KeyError):
        return None


def memo_write(name: str, got: dict) -> None:
    try:
        paths.write_atomic(paths.home() / "wabbajack" / name, json.dumps({"format": "modtrap-wabbajack/1", "list": got}).encode("utf-8"))
    except OSError as e:
        log.warn("the reading of the Wabbajack list could not be kept for next time: %s", logbook.why(e))


def wabbajack(path: Path, progress=None) -> dict:
    """`read_wabbajack`, remembered in ModTrap's own folder by the file's size and date: a large list takes a
    while to read, and does not change."""
    st = path.stat()
    memo = memo_name(path.name, st.st_size, st.st_mtime_ns)
    got = memo_read(memo)
    if got is not None:
        return got
    started = time.monotonic()
    got = read_wabbajack(path, progress)
    said(got, time.monotonic() - started)
    memo_write(memo, got)
    return got


# --- all of it, for each mod -----------------------------------------------------------------------------------

def gather(inst: Instance, wj: dict | None = None, added_by_modtrap: set[str] | None = None, given: dict | None = None,
           mark_reader=None) -> list[dict]:
    """One row for each mod of the modlist: where it came from, by every record there is. {"mod", "enabled",
    "host": "nexus", "github", "url" or "", "game", "mod_id", "files": [file numbers at Nexus known to be installed],
    "archive", "version", "mo2_newest", "url", "repo": "owner/name", "tag", "origin": "list", "modtrap", "added" or ""
    (not known: no Wabbajack file was named), "by": which record said so, "given": the owner's own link, if any}.

    `given` is what the owner gave by hand for this modlist (`given_load`): {"links": {mod, folded: address},
    "archives": {archive's name, folded: a download's meta}, "mods": {mod, folded: a mod's meta}}. The owner's link
    is taken before every record; a meta file the owner gave fills in where the mod's own records say nothing."""
    added = {fold(n) for n in (added_by_modtrap or set())}
    given = given or {}
    links, g_archives, g_mods = given.get("links", {}), given.get("archives", {}), given.get("mods", {})
    rows = []
    for m in inst.mods:
        if m.kind != "mod" or m.folder is None:
            continue
        meta = own = mod_meta(m.folder)
        handed = g_mods.get(fold(m.name))
        by_meta = "meta.ini"
        if handed and not meta["mod_id"] and not meta["url"]:
            meta = dict(meta, **{k: handed[k] for k in ("mod_id", "game", "url", "files") if handed.get(k)},
                        archive=meta["archive"] or handed.get("archive", ""), version=meta["version"] or handed.get("version", ""))
            meta["files"] = [tuple(x) for x in meta["files"]]
            by_meta = "a meta file you gave"
        dl = download_meta(inst.downloads_dir, meta["archive"])
        by_dl = "the download's meta file"
        if not dl.get("mod_id") and not dl.get("url") and g_archives.get(fold(meta["archive"])):
            dl, by_dl = g_archives[fold(meta["archive"])], "a download's meta file you gave"
        row = {"mod": m.name, "enabled": m.enabled, "host": "", "game": "", "mod_id": 0, "files": [], "archive": meta["archive"],
               "version": meta["version"], "mo2_newest": meta["mo2_newest"], "url": "", "repo": "", "tag": "", "by": [],
               "given": links.get(fold(m.name), ""), "version_by": "", "priority": m.priority, "comments": own.get("comments", ""), "notes": own.get("notes", "")}
        from_list: list[dict] = []
        if wj is not None:
            hashes = list(wj["mods"].get(fold(m.name), []))
            if meta["archive"] and fold(meta["archive"]) in wj["by_name"]:
                h = wj["by_name"][fold(meta["archive"])]
                hashes = [h] + [x for x in hashes if x != h]          # the archive MO2 names for the mod comes first
            from_list = [wj["archives"][h] for h in hashes if h in wj["archives"]]
            in_list = fold(m.name) in wj["mods"]
            row["origin"] = "modtrap" if fold(m.name) in added or m.name.startswith(MOD_PREFIX) else "list" if in_list else "added"
        else:
            row["origin"] = "modtrap" if fold(m.name) in added or m.name.startswith(MOD_PREFIX) else ""
        # The owner's own link comes before every record: it is what the owner says the source is.
        mine = None
        if row["given"]:
            try:
                mine = parse_link(row["given"])
            except ValueError:
                mine = None
        if mine is not None and mine["host"] == "nexus":
            ids = [f for mid, f in meta["files"] if mid == mine["mod_id"]]
            if dl.get("mod_id") == mine["mod_id"] and dl.get("file_id") and dl["file_id"] not in ids:
                ids.append(dl["file_id"])
            if mine["file_id"] and mine["file_id"] not in ids:
                ids.append(mine["file_id"])
            ids += [a["file_id"] for a in from_list if a["host"] == "nexus" and a.get("mod_id") == mine["mod_id"] and a.get("file_id") and a["file_id"] not in ids]
            row.update(host="nexus", game=mine["game"], mod_id=mine["mod_id"], files=ids, by=["your link"])
            rows.append(row)
            continue
        if mine is not None:
            row.update(host=mine["host"], url=mine["url"], repo=mine.get("repo", ""), tag=mine.get("tag", ""), by=["your link"])
            rows.append(row)
            continue
        # Nexus: the mod's number by MO2's own records first, then by the list's file.
        game = nexus_game(meta["game"]) or nexus_game(dl.get("game", ""))
        mod_id = meta["mod_id"] or dl.get("mod_id", 0)
        if mod_id and game:
            row.update(host="nexus", game=game, mod_id=mod_id)
            row["by"].append(by_meta if meta["mod_id"] else by_dl)
            ids = [f for mid, f in meta["files"] if mid == mod_id]
            if dl.get("mod_id") == mod_id and dl.get("file_id") and dl["file_id"] not in ids:
                ids.append(dl["file_id"])
            for a in from_list:
                if a["host"] == "nexus" and a.get("mod_id") == mod_id and a.get("game") == game and a.get("file_id") and a["file_id"] not in ids:
                    ids.append(a["file_id"])
                    if "the Wabbajack file" not in row["by"]:
                        row["by"].append("the Wabbajack file")
            row["files"] = ids
        else:
            first = next((a for a in from_list if a["host"] == "nexus" and a.get("mod_id") and a.get("game")), None)
            if first is not None:
                row.update(host="nexus", game=first["game"], mod_id=first["mod_id"], by=["the Wabbajack file"],
                           files=[a["file_id"] for a in from_list if a["host"] == "nexus" and a.get("mod_id") == first["mod_id"] and a.get("file_id")])
                row["version"] = row["version"] or first.get("version", "")
        if not row["host"]:
            url = meta["url"] or dl.get("url", "") or next((a.get("url", "") for a in from_list if a.get("url")), "")
            if url:
                hit = github_repo(url)
                row.update(host=host_of(url), url=url)
                row["by"].append(by_meta if meta["url"] else by_dl if dl.get("url") else "the Wabbajack file")
                if hit:
                    row["repo"], row["tag"] = hit
            elif from_list:
                row["host"] = from_list[0]["host"] if from_list[0]["host"] not in ("nexus", "github", "url") else ""
                row["url"] = from_list[0].get("url", "")
                row["by"].append("the Wabbajack file")
        if not row["host"] and meta["archive"] and inst.downloads_dir is not None:
            # No record names a source: the archive itself may, by the mark the browser left on it when it was
            # downloaded (WHY§109). Only where the archive still lies in MO2's downloads folder.
            url = source_of_mark(web_mark(inst.downloads_dir / meta["archive"], mark_reader))
            if url:
                hit = github_repo(url)
                row.update(host=host_of(url), url=url)
                row["by"].append("the mark your browser left on the downloaded archive")
                if hit:
                    row["repo"], row["tag"] = hit
        rows.append(row)
    from . import adding
    for row in rows:
        if not row["version"]:
            # No record states a version: the mod's own name may end with one (ModTrap names a mod by its title
            # and its version, MT67), and so may the name of its archive.
            row["version"] = adding.version_in(row["mod"]) or name_end_version(row["mod"]) or \
                (adding.from_archive_name(row["archive"])["version"] if row["archive"] else "")
            row["version_by"] = "name" if row["version"] else ""
    return rows


__all__ = ["data", "download_meta", "download_meta_of", "gather", "given_load", "given_save", "memo_name", "memo_read", "memo_write",
           "github_repo", "mod_meta", "mod_meta_of", "name_end_version", "names_version", "nexus_game", "parse_link", "source_of_mark", "web_mark", "own_record", "read_list_bytes", "read_wabbajack", "said", "wabbajack"]
