import XCTest
@testable import Notaeo

final class MindMapAPITests: XCTestCase {
    private func client() -> NotaeoAPI {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [StubURLProtocol.self]
        return NotaeoAPI(baseURL: URL(string: "http://127.0.0.1:8765")!, desktopToken: "desktop-session",
                         session: URLSession(configuration: config), accountToken: { "owner-token" })
    }

    override func tearDown() { StubURLProtocol.handler = nil; super.tearDown() }

    func testMindMapDecodesRecursiveSourceCitationsAndUsesBothCredentials() async throws {
        StubURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/notebooks/course/mindmap")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer owner-token")
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-Notaeo-Desktop-Token"), "desktop-session")
            let json = #"{"id":"root","name":"Biology","source_id":null,"pages":[],"children":[{"id":"source","name":"Notes","source_id":"notes","pages":[2,4],"children":[{"id":"concept","name":"Mitosis","source_id":"notes","pages":[4],"children":[]}]}]}"#
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, Data(json.utf8))
        }
        let tree = try await client().getMindmap(notebookId: "course")
        XCTAssertNil(tree.sourceId)
        XCTAssertEqual(tree.children.first?.children.first?.sourceId, "notes")
        XCTAssertEqual(tree.children.first?.children.first?.pages, [4])
    }

    func testMindMapExportPreservesMarkdownAndSanitizesFilename() async throws {
        StubURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/notebooks/course/mindmap/export")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer owner-token")
            let headers = ["Content-Disposition": #"attachment; filename="../../Biology-mindmap.md""#]
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: headers)!, Data("# Biology\n- Notes (page 4)\n".utf8))
        }
        let export = try await client().exportMindmap(notebookId: "course")
        XCTAssertEqual(export.filename, "Biology-mindmap.md")
        XCTAssertEqual(String(data: export.data, encoding: .utf8), "# Biology\n- Notes (page 4)\n")
    }

    func testForeignMapRemainsNotFound() async throws {
        StubURLProtocol.handler = { request in
            (HTTPURLResponse(url: request.url!, statusCode: 404, httpVersion: nil, headerFields: nil)!, Data(#"{"detail":"not found"}"#.utf8))
        }
        do {
            _ = try await client().getMindmap(notebookId: "foreign")
            XCTFail("Expected 404")
        } catch let error as APIError {
            XCTAssertEqual(error, .notFound("not found"))
        }
    }
}
