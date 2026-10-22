import AppKit

let output = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)

func color(_ hex: UInt32) -> CGColor {
    CGColor(
        colorSpace: CGColorSpaceCreateDeviceRGB(),
        components: [CGFloat((hex >> 16) & 255) / 255, CGFloat((hex >> 8) & 255) / 255, CGFloat(hex & 255) / 255, 1]
    )!
}

for size in [16, 32, 64, 128, 256, 512, 1024] {
    let context = CGContext(
        data: nil,
        width: size,
        height: size,
        bitsPerComponent: 8,
        bytesPerRow: 0,
        space: CGColorSpaceCreateDeviceRGB(),
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    )!
    // Normalized, top-left coordinates match NativePresentation.NotaeoMark.
    context.scaleBy(x: CGFloat(size), y: CGFloat(size))
    context.translateBy(x: 0, y: 1)
    context.scaleBy(x: 1, y: -1)
    context.saveGState()
    context.addPath(CGPath(roundedRect: CGRect(x: 0, y: 0, width: 1, height: 1),
                           cornerWidth: 0.24, cornerHeight: 0.24, transform: nil))
    context.clip()
    let gradient = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(),
                              colors: [color(0x1F574D), color(0x0D332E)] as CFArray,
                              locations: [0, 1])!
    context.drawLinearGradient(gradient, start: .zero, end: CGPoint(x: 1, y: 1), options: [])
    context.restoreGState()

    let ribbon = CGMutablePath()
    let points: [CGPoint] = [(0.22, 0.76), (0.22, 0.24), (0.36, 0.24),
                             (0.64, 0.59), (0.64, 0.24), (0.78, 0.24),
                             (0.78, 0.76), (0.64, 0.76), (0.36, 0.41),
                             (0.36, 0.76)].map { CGPoint(x: $0.0, y: $0.1) }
    ribbon.addLines(between: points)
    ribbon.closeSubpath()
    context.setFillColor(color(0xF7F0D9))
    context.addPath(ribbon)
    context.fillPath()
    context.setStrokeColor(CGColor(red: 0, green: 0, blue: 0, alpha: 0.10))
    context.setLineWidth(0.025)
    context.move(to: CGPoint(x: 0.28, y: 0.24))
    context.addLine(to: CGPoint(x: 0.72, y: 0.76))
    context.strokePath()
    context.setFillColor(color(0xD4AD61))
    context.fillEllipse(in: CGRect(x: 0.7425, y: 0.1625, width: 0.075, height: 0.075))

    let bitmap = NSBitmapImageRep(cgImage: context.makeImage()!)
    try bitmap.representation(using: .png, properties: [:])!.write(to: output.appending(path: "icon-\(size).png"))
}
