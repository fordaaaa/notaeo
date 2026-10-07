import XCTest
@testable import Notaeo

// MARK: - Educational site index: model + engine

final class SiteIndexModelTests: XCTestCase {
    func testIndexEngineRawValueAndLabel() {
        XCTAssertEqual(WebDiscoveryEngine.index.rawValue, "index")
        XCTAssertEqual(WebDiscoveryEngine.index.label, "Indexed sites")
        XCTAssertTrue(WebDiscoveryEngine.allCases.contains(.index))
    }

    func testSiteDecodesSnakeCaseAndRoundTrips() throws {
        let json = """
        {"id":"abcdef123456","url":"https://example.edu/books","created_at":"2026-10-07T00:00:00Z","indexed_at":"2026-10-07T01:00:00Z","page_count":5,"notice":"complete","revision":2}
        """.data(using: .utf8)!
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let site = try decoder.decode(SiteIndexSite.self, from: json)
        XCTAssertEqual(site.id, "abcdef123456")
        XCTAssertEqual(site.url, "https://example.edu/books")
        XCTAssertEqual(site.createdAt, "2026-10-07T00:00:00Z")
        XCTAssertEqual(site.indexedAt, "2026-10-07T01:00:00Z")
        XCTAssertEqual(site.pageCount, 5)
        XCTAssertEqual(site.notice, "complete")
        XCTAssertEqual(site.revision, 2)
        // Identifiable + Equatable + Sendable conformance is compile-checked.
        XCTAssertEqual(site, site)
        let same: any Identifiable = site
        XCTAssertEqual(same.id as? String, "abcdef123456")
    }

    func testSiteDecodesNullIndexedAt() throws {
        let json = """
        {"id":"bbbbbbbbbbbb","url":"https://example.edu/new","created_at":"2026-10-07T00:00:00Z","indexed_at":null,"page_count":0,"notice":"complete","revision":1}
        """.data(using: .utf8)!
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let site = try decoder.decode(SiteIndexSite.self, from: json)
        XCTAssertNil(site.indexedAt)
        XCTAssertEqual(site.pageCount, 0)
    }
}

// MARK: - Educational site index: transport (real URLSession pipeline)

private func siteIndexSession() -> URLSession {
    let config = URLSessionConfiguration.ephemeral
    config.protocolClasses = [StubURLProtocol.self]
    return URLSession(configuration: config)
}

private func siteIndexAPI(token: String? = "acct-1") -> NotaeoAPI {
    let t = token
    return NotaeoAPI(
        baseURL: URL(string: "http://127.0.0.1:9")!,
        desktopToken: "desk-per-launch",
        session: siteIndexSession(),
        accountToken: { t }
    )
}

private func siteIndexHTTP(_ url: URL, status: Int) -> HTTPURLResponse {
    HTTPURLResponse(url: url, statusCode: status, httpVersion: nil, headerFields: nil)!
}

private func siteIndexBody(_ request: URLRequest) -> Data {
    if let body = request.httpBody, !body.isEmpty { return body }
    if let stream = request.httpBodyStream {
        stream.open()
        defer { stream.close() }
        var data = Data()
        var buffer = [UInt8](repeating: 0, count: 8192)
        while stream.hasBytesAvailable {
            let count = stream.read(&buffer, maxLength: buffer.count)
            if count <= 0 { break }
            data.append(buffer, count: count)
        }
        return data
    }
    return Data()
}

private let siteIndexJSON = """
{"id":"abcdef123456","url":"https://example.edu/books","created_at":"2026-10-07T00:00:00Z","indexed_at":"2026-10-07T01:00:00Z","page_count":5,"notice":"complete","revision":2}
"""

final class SiteIndexAPITests: XCTestCase {
    override func tearDown() {
        StubURLProtocol.handler = nil
        super.tearDown()
    }

    func testListSendsAuthHeadersAndDecodesSites() async throws {
        StubURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/web/index/sites")
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer acct-1")
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-Notaeo-Desktop-Token"), "desk-per-launch")
            let json = "[\(siteIndexJSON)]"
            return (siteIndexHTTP(request.url!, status: 200), Data(json.utf8))
        }
        let sites = try await siteIndexAPI().listIndexSites()
        XCTAssertEqual(sites.count, 1)
        XCTAssertEqual(sites.first?.url, "https://example.edu/books")
        XCTAssertEqual(sites.first?.pageCount, 5)
        XCTAssertEqual(sites.first?.revision, 2)
    }

    func testAddPostsURLAndDecodesSite() async throws {
        StubURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/web/index/sites")
            XCTAssertEqual(request.httpMethod, "POST")
            let body = try! JSONSerialization.jsonObject(with: siteIndexBody(request)) as! [String: Any]
            XCTAssertEqual(body["url"] as? String, "https://example.edu/books")
            return (siteIndexHTTP(request.url!, status: 201), Data(siteIndexJSON.utf8))
        }
        let site = try await siteIndexAPI().addIndexSite(url: "https://example.edu/books")
        XCTAssertEqual(site.id, "abcdef123456")
        XCTAssertEqual(site.notice, "complete")
    }

    func testRefreshPostsToSiteRefreshAndDecodesSite() async throws {
        StubURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/web/index/sites/abcdef123456/refresh")
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer acct-1")
            return (siteIndexHTTP(request.url!, status: 200), Data(siteIndexJSON.utf8))
        }
        let site = try await siteIndexAPI().refreshIndexSite(id: "abcdef123456")
        XCTAssertEqual(site.pageCount, 5)
        XCTAssertEqual(site.indexedAt, "2026-10-07T01:00:00Z")
    }

    func testDeleteSendsDeleteAndAccepts204() async throws {
        StubURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/web/index/sites/abcdef123456")
            XCTAssertEqual(request.httpMethod, "DELETE")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer acct-1")
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-Notaeo-Desktop-Token"), "desk-per-launch")
            return (siteIndexHTTP(request.url!, status: 204), Data())
        }
        try await siteIndexAPI().deleteIndexSite(id: "abcdef123456")
    }

    func testForeignSiteMapsToNotFound() async {
        StubURLProtocol.handler = { req in
            (siteIndexHTTP(req.url!, status: 404), Data(#"{"detail":"indexed site not found"}"#.utf8))
        }
        do {
            _ = try await siteIndexAPI().refreshIndexSite(id: "ffffffffffff")
            XCTFail("expected 404")
        } catch let error as APIError {
            XCTAssertEqual(error, .notFound("indexed site not found"))
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func testValidationMapsToValidationError() async {
        StubURLProtocol.handler = { req in
            (siteIndexHTTP(req.url!, status: 422), Data(#"{"detail":"url must be an https address on an educational site"}"#.utf8))
        }
        do {
            _ = try await siteIndexAPI().addIndexSite(url: "http://example.com/evil")
            XCTFail("expected 422")
        } catch let error as APIError {
            if case .validation(let message) = error {
                XCTAssertTrue(message.contains("https"))
            } else {
                XCTFail("wrong error \(error)")
            }
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func testCrawlFailureMapsToServer502() async {
        StubURLProtocol.handler = { req in
            (siteIndexHTTP(req.url!, status: 502), Data(#"{"detail":"could not refresh the site right now"}"#.utf8))
        }
        do {
            _ = try await siteIndexAPI().refreshIndexSite(id: "abcdef123456")
            XCTFail("expected 502")
        } catch let error as APIError {
            XCTAssertEqual(error, .server(status: 502, message: "could not refresh the site right now"))
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func testStaleRevisionMapsToValidation409() async {
        StubURLProtocol.handler = { req in
            (siteIndexHTTP(req.url!, status: 409), Data(#"{"detail":"the site changed while refreshing"}"#.utf8))
        }
        do {
            _ = try await siteIndexAPI().refreshIndexSite(id: "abcdef123456")
            XCTFail("expected 409")
        } catch let error as APIError {
            if case .validation(let message) = error {
                XCTAssertTrue(message.contains("changed"))
            } else {
                XCTFail("wrong error \(error)")
            }
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func testMissingAuthMapsToUnauthorized() async {
        StubURLProtocol.handler = { req in
            (siteIndexHTTP(req.url!, status: 401), Data(#"{"detail":"login required"}"#.utf8))
        }
        do {
            _ = try await siteIndexAPI().listIndexSites()
            XCTFail("expected 401")
        } catch let error as APIError {
            XCTAssertEqual(error, .unauthorized("login required"))
        } catch {
            XCTFail("wrong error \(error)")
        }
    }
}

// MARK: - Educational site index: controller staleness

private actor DelayedSiteIndexService: SiteIndexManaging {
    private var listPending: [Int: CheckedContinuation<[SiteIndexSite], any Error>] = [:]
    private var listNext = 0
    private var addPending: [String: CheckedContinuation<SiteIndexSite, any Error>] = [:]
    private var refreshPending: [Int: (id: String, cont: CheckedContinuation<SiteIndexSite, any Error>)] = [:]
    private var refreshNext = 0
    private var deletePending: [String: CheckedContinuation<Void, any Error>] = [:]

    private func site(id: String = "abcdef123456", url: String = "https://example.edu/books") -> SiteIndexSite {
        SiteIndexSite(id: id, url: url, createdAt: "2026-10-07T00:00:00Z", indexedAt: "2026-10-07T01:00:00Z", pageCount: 5, notice: "complete", revision: 2)
    }

    func listIndexSites() async throws -> [SiteIndexSite] {
        let token: Int = listNext
        listNext += 1
        return try await withCheckedThrowingContinuation { listPending[token] = $0 }
    }

    func addIndexSite(url: String) async throws -> SiteIndexSite {
        try await withCheckedThrowingContinuation { addPending[url] = $0 }
    }

    func refreshIndexSite(id: String) async throws -> SiteIndexSite {
        let token: Int = refreshNext
        refreshNext += 1
        let captured = id
        return try await withCheckedThrowingContinuation { refreshPending[token] = (captured, $0) }
    }

    func deleteIndexSite(id: String) async throws {
        try await withCheckedThrowingContinuation { deletePending[id] = $0 }
    }

    func listCount() -> Int { listPending.count }
    func refreshCount() -> Int { refreshPending.count }
    func hasList() -> Bool { !listPending.isEmpty }
    func hasAdd(_ url: String) -> Bool { addPending[url] != nil }
    func hasRefresh() -> Bool { !refreshPending.isEmpty }
    func hasDelete(_ id: String) -> Bool { deletePending[id] != nil }

    func resolveListToken(_ token: Int, _ sites: [SiteIndexSite]) {
        listPending.removeValue(forKey: token)?.resume(returning: sites)
    }

    func resolveList(_ sites: [SiteIndexSite]) {
        let pending = listPending
        listPending = [:]
        for c in pending.values { c.resume(returning: sites) }
    }

    func resolveAdd(_ url: String) {
        addPending.removeValue(forKey: url)?.resume(returning: site())
    }

    func resolveRefreshToken(_ token: Int, notice: String = "complete") {
        guard let entry = refreshPending.removeValue(forKey: token) else { return }
        var s = site(id: entry.id)
        s.notice = notice
        entry.cont.resume(returning: s)
    }

    func resolveDelete(_ id: String) {
        deletePending.removeValue(forKey: id)?.resume(returning: ())
    }
}

final class SiteIndexControllerTests: XCTestCase {
    @MainActor
    private func waitUntil(_ message: String, _ check: @escaping () async -> Bool) async throws {
        let deadline = Date().addingTimeInterval(3)
        while !(await check()) {
            guard Date() < deadline else { throw NSError(domain: "site-index-test-timeout-\(message)", code: 1) }
            try await Task.sleep(for: .milliseconds(1))
        }
    }

    @MainActor
    func testLateListCannotReplaceNewerResults() async throws {
        let service = DelayedSiteIndexService()
        let controller = SiteIndexController()
        let first = Task { await controller.list(using: service) }
        try await waitUntil("first-list") { await service.listCount() == 1 }
        let second = Task { await controller.list(using: service) }
        try await waitUntil("second-list") { await service.listCount() == 2 }
        // Resolve the stale first list with one URL; the newer list wins.
        await service.resolveListToken(0, [SiteIndexSite(id: "aaaaaaaaaaaaaaaa", url: "https://example.edu/old", createdAt: "2026-10-07T00:00:00Z", indexedAt: nil, pageCount: 0, notice: "complete", revision: 1)])
        await first.value
        XCTAssertTrue(controller.isLoading)
        XCTAssertTrue(controller.sites.isEmpty)
        await service.resolveListToken(1, [SiteIndexSite(id: "bbbbbbbbbbbb", url: "https://example.edu/new", createdAt: "2026-10-07T00:00:00Z", indexedAt: nil, pageCount: 1, notice: "complete", revision: 1)])
        await second.value
        XCTAssertFalse(controller.isLoading)
        XCTAssertEqual(controller.sites.map(\.id), ["bbbbbbbbbbbb"])
    }

    @MainActor
    func testClearingPendingListPreventsItsResponse() async throws {
        let service = DelayedSiteIndexService()
        let controller = SiteIndexController()
        let task = Task { await controller.list(using: service) }
        try await waitUntil("pending-list") { await service.hasList() }
        controller.clear()
        await service.resolveList([SiteIndexSite(id: "aaaaaaaaaaaaaaaa", url: "https://example.edu/old", createdAt: "2026-10-07T00:00:00Z", indexedAt: nil, pageCount: 0, notice: "complete", revision: 1)])
        await task.value
        XCTAssertFalse(controller.isLoading)
        XCTAssertTrue(controller.sites.isEmpty)
        XCTAssertNil(controller.error)
    }

    @MainActor
    func testCancelledListTaskCannotPublish() async throws {
        let service = DelayedSiteIndexService()
        let controller = SiteIndexController()
        let task = Task { await controller.list(using: service) }
        try await waitUntil("leaving-list") { await service.hasList() }
        task.cancel()
        await service.resolveList([SiteIndexSite(id: "aaaaaaaaaaaaaaaa", url: "https://example.edu/old", createdAt: "2026-10-07T00:00:00Z", indexedAt: nil, pageCount: 0, notice: "complete", revision: 1)])
        await task.value
        XCTAssertFalse(controller.isLoading)
        XCTAssertTrue(controller.sites.isEmpty)
    }

    @MainActor
    func testLateRefreshCannotOverwriteNewerRefresh() async throws {
        let service = DelayedSiteIndexService()
        let controller = SiteIndexController()
        let first = Task { await controller.refresh(id: "abcdef123456", using: service) }
        try await waitUntil("first-refresh") { await service.refreshCount() == 1 }
        // Second refresh supersedes the first; resolve stale first with partial.
        let second = Task { await controller.refresh(id: "abcdef123456", using: service) }
        try await waitUntil("second-refresh") { await service.refreshCount() == 2 }
        await service.resolveRefreshToken(0, notice: "partial")
        await first.value
        // Stale refresh must not publish or clear the working state.
        XCTAssertNotEqual(controller.sites.first?.notice, "partial")
        XCTAssertEqual(controller.workingId, "abcdef123456")
        await service.resolveRefreshToken(1, notice: "complete")
        await second.value
        XCTAssertEqual(controller.sites.first?.notice, "complete")
        XCTAssertNil(controller.workingId)
    }

    @MainActor
    func testCancelPreventsLateAddNotice() async throws {
        let service = DelayedSiteIndexService()
        let controller = SiteIndexController()
        let task = Task { await controller.add(url: "https://example.edu/books", using: service) }
        try await waitUntil("pending-add") { await service.hasAdd("https://example.edu/books") }
        controller.cancel()
        await service.resolveAdd("https://example.edu/books")
        await task.value
        XCTAssertTrue(controller.sites.isEmpty)
        XCTAssertNil(controller.error)
        XCTAssertFalse(controller.isAdding)
    }

    @MainActor
    func testCancelPreventsLateDeleteFromClearingWorkingState() async throws {
        let service = DelayedSiteIndexService()
        let controller = SiteIndexController()
        let task = Task { await controller.delete(id: "abcdef123456", using: service) }
        try await waitUntil("pending-delete") { await service.hasDelete("abcdef123456") }
        controller.cancel()
        await service.resolveDelete("abcdef123456")
        await task.value
        XCTAssertNil(controller.workingId)
        XCTAssertNil(controller.error)
    }
}
