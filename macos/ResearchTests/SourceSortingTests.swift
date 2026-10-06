import XCTest
@testable import Notaeo

final class SourceSortingTests: XCTestCase {
    private func source(_ id: String, title: String, date: String, kind: String = "paste") -> SourceSummary {
        SourceSummary(id: id, notebookId: "course", kind: kind, title: title, tags: [], createdAt: date, chunkCount: 1)
    }

    func testDateOrderingUsesInstantsAndKeepsMissingDatesLast() {
        let sources = [
            source("unknown", title: "Unknown", date: "invalid"),
            source("older", title: "Older", date: "2026-10-06T10:30:00Z"),
            source("newer", title: "Newer", date: "2026-10-06T07:00:00.123-04:00"),
            source("same", title: "Same instant", date: "2026-10-06T11:00:00.123+00:00"),
        ]
        XCTAssertEqual(SourceSortOrder.newest.sorted(sources).map(\.id), ["newer", "same", "older", "unknown"])
        XCTAssertEqual(SourceSortOrder.oldest.sorted(sources).map(\.id), ["older", "newer", "same", "unknown"])
        XCTAssertNil(SourceSortOrder.creationDate(of: sources[0]))
    }

    func testNameAndKindChoicesHaveStableNaturalOrdering() {
        let sources = [
            source("b", title: "Lecture 10", date: "", kind: "pdf"),
            source("c", title: "lecture 2", date: "", kind: "paste"),
            source("a", title: "Lecture 10", date: "", kind: "pdf"),
        ]
        XCTAssertEqual(SourceSortOrder.name.sorted(sources).map(\.id), ["c", "a", "b"])
        XCTAssertEqual(SourceSortOrder.kind.sorted(sources).map(\.id), ["c", "a", "b"])
        XCTAssertEqual(SourceSortOrder.newest.sorted(sources).map(\.id), ["a", "b", "c"])
    }
}
