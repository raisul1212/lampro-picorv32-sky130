#!/usr/bin/env python3
"""Write the raster images embedded in a PDF as PNG files, using only the standard library.

  extract_pdf_images.py FILE.pdf OUTDIR

For every image XObject whose data is a single FlateDecode stream (8 bits per component, gray or RGB):
  * with a PNG predictor (Predictor >= 10) the compressed stream already is the zlib data of a PNG
    image, and it is copied into the PNG unchanged;
  * without a predictor the raw rows are written with PNG filter type 0 and compressed.
In both cases the decoded pixels are those stored in the PDF; nothing is resampled or converted.
Each file is named <pdf stem>_obj<N>_<width>x<height>.png. Images with other filters (DCTDecode,
ASCII85 and so on), soft masks, and images with other bit depths are listed and skipped.

This is the tool used to recover docs/src/figs/ from the v2.0.1 PDFs, whose figure files were not kept.
"""
import os
import re
import struct
import sys
import zlib


def chunk(tag, data):
    body = tag + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def png(width, height, channels, zdata):
    ctype = {1: 0, 3: 2}[channels]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, ctype, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zdata) + chunk(b"IEND", b"")


def objects(data):
    """Yield (objnum, dict bytes, stream start) for every 'N G obj << ... >> stream'."""
    for m in re.finditer(rb"(\d+)\s+(\d+)\s+obj\s*<<", data):
        start = m.end() - 2
        depth, i = 0, start
        while i < len(data) - 1:
            two = data[i:i + 2]
            if two == b"<<":
                depth += 1
                i += 2
            elif two == b">>":
                depth -= 1
                i += 2
                if depth == 0:
                    break
            else:
                i += 1
        d = data[start:i]
        rest = data[i:i + 20].lstrip()
        if rest.startswith(b"stream"):
            s = data.index(b"stream", i) + 6
            if data[s:s + 2] == b"\r\n":
                s += 2
            elif data[s:s + 1] in (b"\n", b"\r"):
                s += 1
            yield int(m[1]), d, s


def intval(d, key):
    m = re.search(rb"/" + key + rb"\s+(\d+)(?!\s+\d+\s+R)", d)
    return int(m[1]) if m else None


def main(pdf, outdir):
    data = open(pdf, "rb").read()
    os.makedirs(outdir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(pdf))[0]
    n = 0
    for num, d, s in objects(data):
        if not re.search(rb"/Subtype\s*/Image", d):
            continue
        w, h, bpc = intval(d, b"Width"), intval(d, b"Height"), intval(d, b"BitsPerComponent")
        length = intval(d, b"Length")
        fm = re.search(rb"/Filter\s*(\[[^\]]*\]|/\w+)", d)
        names = re.findall(rb"/(\w+)", fm[1]) if fm else []
        label = "obj %d (%sx%s)" % (num, w, h)
        if names != [b"FlateDecode"] or bpc != 8 or not length or b"/SMask" in d or b"/ImageMask" in d:
            print("skipped", label, "filters=%r bpc=%s" % (names, bpc))
            continue
        z = data[s:s + length]
        if len(z) != length or data[s + length:s + length + 20].lstrip()[:9] != b"endstream":
            print("skipped", label, "stream length does not match")
            continue
        pm = re.search(rb"/Predictor\s+(\d+)", d)
        predictor = int(pm[1]) if pm else 1
        raw = zlib.decompress(z)
        if predictor >= 10:
            colors = intval(d, b"Colors") or 3
            if len(raw) != h * (1 + w * colors):
                print("skipped", label, "unexpected decoded size")
                continue
            png_bytes = png(w, h, colors, z)
        else:
            if len(raw) % (w * h):
                print("skipped", label, "unexpected decoded size")
                continue
            colors = len(raw) // (w * h)
            if colors not in (1, 3):
                print("skipped", label, "%d components" % colors)
                continue
            rows = b"".join(b"\x00" + raw[y * w * colors:(y + 1) * w * colors] for y in range(h))
            png_bytes = png(w, h, colors, zlib.compress(rows, 9))
        name = "%s_obj%d_%dx%d.png" % (stem, num, w, h)
        with open(os.path.join(outdir, name), "wb") as f:
            f.write(png_bytes)
        print("wrote", name)
        n += 1
    return 0 if n else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
