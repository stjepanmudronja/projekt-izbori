// OCR a scanned PDF with macOS's own frameworks: PDFKit renders each page,
// Vision recognises the text. No poppler or tesseract needed.
//
//   swiftc -O tools/pdf_ocr.swift -o tools/pdf_ocr
//   tools/pdf_ocr <pdf> [first-page last-page] > out.tsv
//
// Output: one line per recognised text line,
//   page <TAB> x <TAB> y <TAB> width <TAB> height <TAB> confidence <TAB> text
// with coordinates in page points, origin top-left, so a caller can rebuild
// rows and columns. Croatian is not among Vision's languages; Czech and
// Polish together carry č, ć, š and ž (đ comes out as d or đ and is fixed by
// the caller).
import Foundation
import PDFKit
import Vision

let args = CommandLine.arguments
guard args.count >= 2, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write("usage: pdf_ocr <pdf> [first last]\n".data(using: .utf8)!)
    exit(1)
}
let first = args.count >= 4 ? Int(args[2])! : 1
let last = args.count >= 4 ? Int(args[3])! : doc.pageCount
let scale: CGFloat = CGFloat(Double(ProcessInfo.processInfo.environment["OCR_SCALE"] ?? "4") ?? 4)   // 4 = ~288 dpi

for index in (first - 1)..<min(last, doc.pageCount) {
    guard let page = doc.page(at: index) else { continue }
    let box = page.bounds(for: .mediaBox)
    let w = Int(box.width * scale), h = Int(box.height * scale)
    let space = CGColorSpaceCreateDeviceGray()
    guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                              space: space, bitmapInfo: CGImageAlphaInfo.none.rawValue) else { continue }
    ctx.setFillColor(gray: 1, alpha: 1)
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
    ctx.scaleBy(x: scale, y: scale)
    ctx.translateBy(x: -box.minX, y: -box.minY)
    page.draw(with: .mediaBox, to: ctx)
    guard let image = ctx.makeImage() else { continue }

    // Pass 1: the whole page. Optional pass 2: one vertical strip (the vote
    // column), since Vision's detector skips some small isolated numbers on
    // the full page; pass-2 boxes overlapping a pass-1 box are dropped. It
    // can also invent one, so callers must check what it adds.
    var seen: [CGRect] = []
    let env = ProcessInfo.processInfo.environment
    // OCR_ROI_X / OCR_ROI_W (fractions of the page width) add the second pass.
    var rois = [CGRect(x: 0, y: 0, width: 1, height: 1)]
    if let rx = env["OCR_ROI_X"].flatMap(Double.init) {
        rois.append(CGRect(x: rx, y: 0, width: Double(env["OCR_ROI_W"] ?? "") ?? (1 - rx), height: 1))
    }
    for roi in rois {
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = false
        request.recognitionLanguages = ["cs-CZ", "pl-PL"]
        request.regionOfInterest = roi
        let handler = VNImageRequestHandler(cgImage: image, options: [:])
        try? handler.perform([request])
        for obs in request.results ?? [] {
            guard let top = obs.topCandidates(1).first else { continue }
            let b = obs.boundingBox   // normalised to the ROI, origin bottom-left
            let r = CGRect(x: roi.minX + b.minX * roi.width, y: roi.minY + b.minY * roi.height,
                           width: b.width * roi.width, height: b.height * roi.height)
            if roi.width < 1 && seen.contains(where: { $0.intersects(r) &&
                    $0.intersection(r).width * $0.intersection(r).height > 0.3 * r.width * r.height }) {
                continue
            }
            seen.append(r)
            let x = r.minX * box.width, y = (1 - r.maxY) * box.height
            let line = String(format: "%d\t%.1f\t%.1f\t%.1f\t%.1f\t%.2f\t", index + 1, x, y,
                              r.width * box.width, r.height * box.height, top.confidence)
            print(line + top.string.replacingOccurrences(of: "\t", with: " "))
        }
    }
}
