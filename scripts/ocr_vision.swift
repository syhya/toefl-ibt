import Foundation
import Vision
import ImageIO

// Optional, local-only multilingual OCR for the Chinese reference scans on macOS.
guard CommandLine.arguments.count == 2 else { exit(2) }
let url = URL(fileURLWithPath: CommandLine.arguments[1])
guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
      let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else { exit(3) }
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = true
try VNImageRequestHandler(cgImage: image).perform([request])
let rows: [[String: Any]] = (request.results ?? []).compactMap { observation in
    guard let candidate = observation.topCandidates(1).first else { return nil }
    let bounds = observation.boundingBox
    return ["text": candidate.string,
            "x": Int(bounds.minX * Double(image.width)),
            "y": Int((1 - bounds.maxY) * Double(image.height)),
            "w": Int(bounds.width * Double(image.width)),
            "h": Int(bounds.height * Double(image.height)),
            "confidence": Double(candidate.confidence) * 100]
}.sorted { ($0["y"] as! Int) < ($1["y"] as! Int) }
let data = try JSONSerialization.data(withJSONObject: rows, options: [.sortedKeys])
FileHandle.standardOutput.write(data)
