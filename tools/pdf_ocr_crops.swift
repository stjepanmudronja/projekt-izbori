// OCR many small regions of PDF pages, each on its own: a second, sharper
// reading of cells the full-page pass got wrong (1997 ward candidates'
// names). A cell rendered alone and large reads far better than the same
// text on a whole page ("Nan Saraster" there, "Stjepan Fišter" here).
//
//   swiftc -O tools/pdf_ocr_crops.swift -o tools/pdf_ocr_crops
//   tools/pdf_ocr_crops < crops.tsv > readings.tsv
//
// Input lines:  id <TAB> pdf <TAB> page <TAB> x <TAB> y <TAB> w <TAB> h
// (page points, origin top-left), optionally <TAB> degrees: the page's `skew`
// line from `pdf_ocr` under OCR_DESKEW=1, so a crop is cut from the same
// straightened page its coordinates came from. Output lines: id <TAB> confidence <TAB> text,
// the crop's recognised lines joined with spaces, left to right — or, with
// CROP_LINES=1, one line per recognised line: id <TAB> confidence <TAB> y <TAB>
// text <TAB> x, y and x being the line's top and left edge in page points
// (for a column of counts).
import Foundation
import PDFKit
import Vision

let scale: CGFloat = 6
var docs: [String: PDFDocument] = [:]
while let line = readLine() {
    let f = line.split(separator: "\t", omittingEmptySubsequences: false).map(String.init)
    guard f.count >= 7, let pageNo = Int(f[2]),
          let x = Double(f[3]), let y = Double(f[4]), let w = Double(f[5]), let h = Double(f[6]) else { continue }
    let doc = docs[f[1]] ?? PDFDocument(url: URL(fileURLWithPath: f[1]))
    guard let d = doc, let page = d.page(at: pageNo - 1) else { continue }
    docs[f[1]] = d
    let box = page.bounds(for: .mediaBox)
    let (cx, cy, cw, ch) = (CGFloat(x), CGFloat(y), CGFloat(w), CGFloat(h))
    // A white margin around the cell helps the detector.
    let pad: CGFloat = 6
    let W = Int((cw + 2 * pad) * scale), H = Int((ch + 2 * pad) * scale)
    guard let ctx = CGContext(data: nil, width: W, height: H, bitsPerComponent: 8, bytesPerRow: 0,
                              space: CGColorSpaceCreateDeviceGray(), bitmapInfo: 0) else { continue }
    ctx.setFillColor(gray: 1, alpha: 1)
    ctx.fill(CGRect(x: 0, y: 0, width: W, height: H))
    ctx.saveGState()
    ctx.clip(to: CGRect(x: pad * scale, y: pad * scale, width: cw * scale, height: ch * scale))
    ctx.scaleBy(x: scale, y: scale)
    ctx.translateBy(x: pad - cx, y: pad - (box.height - cy - ch))
    if f.count >= 8, let degrees = Double(f[7]), degrees != 0 {
        ctx.translateBy(x: box.width / 2, y: box.height / 2)
        ctx.rotate(by: CGFloat(-degrees * .pi / 180))
        ctx.translateBy(x: -box.width / 2 - box.minX, y: -box.height / 2 - box.minY)
    }
    page.draw(with: .mediaBox, to: ctx)
    ctx.restoreGState()
    guard let image = ctx.makeImage() else { continue }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false
    request.recognitionLanguages = ["cs-CZ", "pl-PL"]
    // Revision 3 guesses each line's orientation, and on a crop with little
    // text reads some upside down ("HNS 414" as "SNH DIT"); revision 2
    // reads the crop as rendered.
    request.revision = VNRecognizeTextRequestRevision2
    try? VNImageRequestHandler(cgImage: image, options: [:]).perform([request])
    if ProcessInfo.processInfo.environment["CROP_LINES"] == "1" {
        for o in request.results ?? [] {
            guard let t = o.topCandidates(1).first else { continue }
            // Normalised box -> page points: undo the padding and the scale.
            let top = cy - pad + (1 - o.boundingBox.maxY) * (ch + 2 * pad)
            let left = cx - pad + o.boundingBox.minX * (cw + 2 * pad)
            print("\(f[0])\t\(String(format: "%.2f", t.confidence))\t\(String(format: "%.1f", top))\t\(t.string.replacingOccurrences(of: "\t", with: " "))\t\(String(format: "%.1f", left))")
        }
        fflush(stdout)
        continue
    }
    let obs = (request.results ?? []).sorted { $0.boundingBox.minX < $1.boundingBox.minX }
    let text = obs.compactMap { $0.topCandidates(1).first?.string }.joined(separator: " ")
    let conf = obs.compactMap { $0.topCandidates(1).first?.confidence }.min() ?? 0
    print("\(f[0])\t\(String(format: "%.2f", conf))\t\(text.replacingOccurrences(of: "\t", with: " "))")
    fflush(stdout)
}
