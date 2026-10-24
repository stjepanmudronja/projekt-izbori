// Dump a PDF's text layer, page by page, using macOS's built-in PDFKit — no
// poppler or Python PDF library needed. Used for the 2009 lokalni report,
// whose PDFs (unlike the scanned 1990s Sabor reports) carry real text.
//
//   swiftc -O tools/pdf_text.swift -o tools/pdf_text   (first build is slow)
//   tools/pdf_text in.pdf > out.txt
import PDFKit

let args = CommandLine.arguments
guard args.count == 2, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write("usage: pdf_text <file.pdf>\n".data(using: .utf8)!)
    exit(1)
}
for i in 0..<doc.pageCount {
    print("=====PAGE \(i + 1)")
    print(doc.page(at: i)?.string ?? "")
}
