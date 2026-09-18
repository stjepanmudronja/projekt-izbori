"""Render a scanned PDF's pages to PNG without poppler, OCR or a PDF library.

Written for `files/rezultati_sabor_2024/1997/1997_3_Rezultati_Sabor_zupanijski_dom.pdf`,
the DIP report on the 1997 Županijski dom election, which is the only source
for that year. The file has **no text layer at all** — 43 pages, each a single
1-bit CCITTFaxDecode (Group 4 fax) image at 2480x3507 — and this machine has
neither poppler, nor tesseract, nor pypdf/pdfplumber/fitz.

Nothing needs decoding, though: TIFF supports Group 4 natively, so each image's
raw stream can be wrapped in a minimal single-strip TIFF header and handed to
macOS's built-in `sips` for conversion to PNG. That turns an unreadable scan
into pages legible enough to transcribe by eye.

    python tools/extract_scanned_pdf.py <file.pdf> <out-dir>
"""
import os
import re
import struct
import subprocess
import sys

# Tag, type, count, value. StripOffsets (273) is patched once the header size
# is known; PhotometricInterpretation 0 is WhiteIsZero, which matches PDF's
# CCITTFaxDecode default of BlackIs1=false.
def tiff_g4(data, width, height):
    tags = [(256, 4, 1, width), (257, 4, 1, height), (258, 3, 1, 1),
            (259, 3, 1, 4), (262, 3, 1, 0), (273, 4, 1, 0), (277, 3, 1, 1),
            (278, 4, 1, height), (279, 4, 1, len(data))]
    data_off = 8 + 2 + len(tags) * 12 + 4
    out = bytearray(b'II*\x00' + struct.pack('<I', 8) + struct.pack('<H', len(tags)))
    for tag, typ, count, value in tags:
        out += struct.pack('<HHI', tag, typ, count)
        out += struct.pack('<I', data_off if tag == 273 else value)
    out += struct.pack('<I', 0)
    return bytes(out) + data


def main(pdf_path, out_dir):
    """Find every CCITT image object and write it out as a PNG.

    The dictionary's keys come in no fixed order — Ghostscript leads with
    /Subtype, iText with /DecodeParms, whose own nested `>>` defeats any
    attempt to match the dictionary as a whole. So each image is located by
    its /Subtype/Image, bracketed by the enclosing `obj` and its `stream`, and
    the fields read out of that span.
    """
    os.makedirs(out_dir, exist_ok=True)
    blob = open(pdf_path, 'rb').read()
    stream_re = re.compile(rb'stream\r?\n')
    count = 0
    for match in re.finditer(rb'/Subtype\s*/Image', blob):
        start = blob.rfind(b'obj', 0, match.start())
        stream = stream_re.search(blob, match.end())
        if start < 0 or stream is None:
            continue
        header = blob[start:stream.start()]
        if b'CCITTFaxDecode' not in header:
            continue
        width = int(re.search(rb'/Width\s+(\d+)', header).group(1))
        height = int(re.search(rb'/Height\s+(\d+)', header).group(1))
        length = int(re.search(rb'/Length\s+(\d+)', header).group(1))
        count += 1
        tif = os.path.join(out_dir, f'page{count:02d}.tif')
        png = os.path.join(out_dir, f'page{count:02d}.png')
        with open(tif, 'wb') as fh:
            fh.write(tiff_g4(blob[stream.end():stream.end() + length], width, height))
        subprocess.run(['sips', '-s', 'format', 'png', tif, '--out', png],
                       check=True, capture_output=True)
        os.remove(tif)
    print(f'{count} page(s) written to {out_dir}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
