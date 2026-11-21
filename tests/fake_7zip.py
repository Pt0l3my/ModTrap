"""A stand-in for the 7-Zip program, for tests: it answers `l -slt` and `x` the way ModTrap's reader expects, from a
.zip that carries a 7z or rar signature in front (invented here; no real 7-Zip is run or contained)."""

import io
import os
import sys
import zipfile


def main(argv):
    mode = argv[0]
    src = argv[argv.index("--") + 1]
    data = open(src, "rb").read()
    z = zipfile.ZipFile(io.BytesIO(data[data.index(b"PK\x03\x04"):]))
    how = os.environ.get("FAKE_7ZIP", "")
    if how == "broken":
        return 2
    if mode == "l":
        print("7-Zip (a stand-in)\n\nListing archive: x\n\n--\nPath = x\nType = 7z\n\n----------")
        for i in z.infolist():
            print("Path = %s\nSize = %d\nAttributes = %s\nEncrypted = %s\n" % (
                i.filename.rstrip("/").replace("/", "\\"), i.file_size, "D" if i.is_dir() else "A",
                "+" if how == "encrypted" else "-"))
        if how == "link":
            print("Path = shortcut\nSize = 0\nAttributes = A\nSymbolic Link = C:\\Elsewhere\n")
        return 0
    if mode == "x":
        dest = next(a[2:] for a in argv if a.startswith("-o"))
        z.extractall(dest)
        return 0
    return 7


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
