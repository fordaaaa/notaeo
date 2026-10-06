import Foundation

enum SourceSortOrder: String, CaseIterable, Identifiable {
    case newest, oldest, name, kind

    var id: String { rawValue }
    var label: String {
        switch self {
        case .newest: "Newest first"
        case .oldest: "Oldest first"
        case .name: "Name"
        case .kind: "File type"
        }
    }

    static func creationDate(of source: SourceSummary) -> Date? {
        let parser = ISO8601DateFormatter()
        parser.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = parser.date(from: source.createdAt) { return date }
        parser.formatOptions = [.withInternetDateTime]
        return parser.date(from: source.createdAt)
    }

    func sorted(_ sources: [SourceSummary]) -> [SourceSummary] {
        // Parse once per item, rather than for every comparison in the sort.
        let dated = sources.map { (source: $0, date: self == .newest || self == .oldest ? Self.creationDate(of: $0) : nil) }
        return dated.sorted { lhs, rhs in
            switch self {
            case .newest, .oldest:
                switch (lhs.date, rhs.date) {
                case let (a?, b?) where a != b: return self == .newest ? a > b : a < b
                case (_?, nil): return true
                case (nil, _?): return false
                default: break
                }
            case .kind:
                if lhs.source.kind != rhs.source.kind { return lhs.source.kind < rhs.source.kind }
                fallthrough
            case .name:
                let order = lhs.source.title.localizedStandardCompare(rhs.source.title)
                if order != .orderedSame { return order == .orderedAscending }
            }
            return lhs.source.id < rhs.source.id
        }.map(\.source)
    }
}
