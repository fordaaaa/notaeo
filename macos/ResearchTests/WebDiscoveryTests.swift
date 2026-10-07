import XCTest
@testable import Notaeo

// MARK: - Web discovery transport (real URLSession pipeline)

final class WebDiscoveryAPITests: XCTestCase {
    private func discoverySession() -> URLSession {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [StubURLProtocol.self]
        return URLSession(configuration: config)
    }

    private func discoveryAPI(token: String? = "acct-1") -> NotaeoAPI {
        let t = token
        return NotaeoAPI(
            baseURL: URL(string: "http://127.0.0.1:9")!,
            desktopToken: "desk-per-launch",
            session: discoverySession(),
            accountToken: { t }
        )
    }

    private func discoveryHTTP(_ url: URL, status: Int) -> HTTPURLResponse {
        HTTPURLResponse(url: url, statusCode: status, httpVersion: nil, headerFields: nil)!
    }

    override func tearDown() {
        StubURLProtocol.handler = nil
        super.tearDown()
    }

    func testDiscoverSendsAuthHeadersAndAllFilterParams() async throws {
        StubURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/web/discover")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer acct-1")
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-Notaeo-Desktop-Token"), "desk-per-launch")
            let items = URLComponents(url: request.url!, resolvingAgainstBaseURL: false)!.queryItems!
            let query = Dictionary(uniqueKeysWithValues: items.map { ($0.name, $0.value ?? "") })
            XCTAssertEqual(query["q"], "ATP & \"Calvin cycle\"")
            XCTAssertEqual(query["limit"], "20")
            XCTAssertEqual(query["engine"], "duckduckgo")
            XCTAssertEqual(query["domain"], "example.edu")
            XCTAssertEqual(query["file_type"], "pdf")
            XCTAssertEqual(query["academic"], "true")
            XCTAssertEqual(query["recency"], "month")
            XCTAssertEqual(query["region"], "us-en")
            let json = #"{"query":"ATP","effective_query":"ATP site:example.edu","engine":"duckduckgo","results":[],"took_ms":3,"filters":{"domain":"example.edu","file_type":"pdf","academic":true,"recency":"month","region":"us-en"}}"#
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, Data(json.utf8))
        }
        let request = WebDiscoveryRequest(
            query: "ATP & \"Calvin cycle\"",
            limit: 20,
            engine: .duckduckgo,
            domain: "example.edu",
            fileType: .pdf,
            academic: true,
            recency: .month,
            region: .usEN
        )
        let page = try await discoveryAPI().discoverWeb(request: request)
        XCTAssertEqual(page.engine, "duckduckgo")
        XCTAssertEqual(page.tookMs, 3)
    }

    func testDiscoverOmitsEmptyDomainAndDecodesSnakeCaseWithFullSnippet() async throws {
        StubURLProtocol.handler = { request in
            let items = URLComponents(url: request.url!, resolvingAgainstBaseURL: false)!.queryItems!
            let names = Set(items.map { $0.name })
            XCTAssertFalse(names.contains("domain"))
            let json = #"{"query":"mitosis","effective_query":"mitosis","engine":"auto","results":[{"title":"Cell division","url":"https://example.edu/mitosis","snippet":"Mitosis & meiosis: full \"detail\" preserved.","domain":"example.edu","file_type":"html","score":9.5}],"took_ms":7,"filters":{"domain":null,"file_type":"all","academic":false,"recency":"any","region":"us-en"}}"#
            return (HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!, Data(json.utf8))
        }
        let request = WebDiscoveryRequest(query: "mitosis", engine: .auto, fileType: .all, academic: false, recency: .any, region: .usEN)
        let page = try await discoveryAPI().discoverWeb(request: request)
        XCTAssertEqual(page.effectiveQuery, "mitosis")
        XCTAssertEqual(page.results.count, 1)
        XCTAssertEqual(page.results.first?.domain, "example.edu")
        XCTAssertEqual(page.results.first?.fileType, "html")
        XCTAssertEqual(page.results.first?.snippet, "Mitosis & meiosis: full \"detail\" preserved.")
        XCTAssertEqual(page.filters.domain, nil)
    }

    func testDiscoverUnavailableMapsToSafe503() async throws {
        StubURLProtocol.handler = { req in
            (self.discoveryHTTP(req.url!, status: 503), Data(#"{"detail":"web search is temporarily unavailable"}"#.utf8))
        }
        do {
            _ = try await discoveryAPI().discoverWeb(request: WebDiscoveryRequest(query: "cells"))
            XCTFail("expected 503")
        } catch let error as APIError {
            XCTAssertEqual(error, .server(status: 503, message: "web search is temporarily unavailable"))
        }
    }

    func testDiscoverValidationMapsToValidationError() async throws {
        StubURLProtocol.handler = { req in
            (self.discoveryHTTP(req.url!, status: 422), Data(#"{"detail":"q must not be blank"}"#.utf8))
        }
        do {
            _ = try await discoveryAPI().discoverWeb(request: WebDiscoveryRequest(query: "   "))
            XCTFail("expected 422")
        } catch let error as APIError {
            if case .validation(let message) = error {
                XCTAssertTrue(message.contains("blank"))
            } else {
                XCTFail("wrong error \(error)")
            }
        }
    }

    private func discoveryBody(_ request: URLRequest) -> Data {
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

    func testImportWebSourceWrapsURLIngestWithoutForce() async throws {
        StubURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/api/notebooks/course/sources/url")
            XCTAssertEqual(request.httpMethod, "POST")
            let body = try! JSONSerialization.jsonObject(with: self.discoveryBody(request)) as! [String: Any]
            XCTAssertEqual(body["url"] as? String, "https://example.edu/article")
            XCTAssertEqual(body["force"] as? Bool, false)
            let json = #"{"id":"abcdef123457","notebook_id":"course","kind":"url","title":"Article","tags":[],"created_at":"2026-10-01T00:00:00Z","chunk_count":3}"#
            return (HTTPURLResponse(url: request.url!, statusCode: 201, httpVersion: nil, headerFields: nil)!, Data(json.utf8))
        }
        let result = try await discoveryAPI().importWebSource(notebookId: "course", url: "https://example.edu/article")
        XCTAssertTrue(result.saved)
        XCTAssertEqual(result.summary?.id, "abcdef123457")
    }
}

// MARK: - Controller staleness

private actor DelayedDiscoveryService: WebDiscovering {
    private var searchPending: [String: CheckedContinuation<WebDiscoveryPage, any Error>] = [:]
    private var importPending: [String: CheckedContinuation<PasteResult, any Error>] = [:]
    nonisolated(unsafe) var seenNotebookIds: [String] = []
    nonisolated(unsafe) var seenImportURLs: [String] = []

    private func discoveryPage(query: String) -> WebDiscoveryPage {
        WebDiscoveryPage(
            query: query,
            effectiveQuery: query,
            engine: "auto",
            results: [],
            tookMs: 1,
            filters: WebDiscoveryFilters(domain: nil, fileType: "all", academic: false, recency: "any", region: "us-en")
        )
    }

    func discoverWeb(request: WebDiscoveryRequest) async throws -> WebDiscoveryPage {
        try await withCheckedThrowingContinuation { searchPending[request.query] = $0 }
    }

    func importWebSource(notebookId: String, url: String) async throws -> PasteResult {
        seenNotebookIds.append(notebookId)
        seenImportURLs.append(url)
        return try await withCheckedThrowingContinuation { importPending[url] = $0 }
    }

    func hasSearch(_ query: String) -> Bool { searchPending[query] != nil }
    func hasImport(_ url: String) -> Bool { importPending[url] != nil }

    func resolveSearch(_ query: String) {
        searchPending.removeValue(forKey: query)?.resume(returning: discoveryPage(query: query))
    }

    func resolveImportSaved(_ url: String, sourceId: String) {
        let summary = SourceSummary(
            id: sourceId, notebookId: "course", kind: "url", title: "Article",
            tags: [], createdAt: "2026-10-01T00:00:00Z", chunkCount: 2
        )
        importPending.removeValue(forKey: url)?.resume(returning: PasteResult(saved: true, duplicateOf: nil, summary: summary))
    }
}

final class NativeDiscoveryStateTests: XCTestCase {
    @MainActor
    private func waitForSearch(_ query: String, service: DelayedDiscoveryService) async throws {
        let deadline = Date().addingTimeInterval(3)
        while !(await service.hasSearch(query)) {
            guard Date() < deadline else { throw NSError(domain: "discovery-test-timeout", code: 1) }
            try await Task.sleep(for: .milliseconds(1))
        }
    }

    @MainActor
    private func waitForImport(_ url: String, service: DelayedDiscoveryService) async throws {
        let deadline = Date().addingTimeInterval(3)
        while !(await service.hasImport(url)) {
            guard Date() < deadline else { throw NSError(domain: "discovery-test-timeout", code: 2) }
            try await Task.sleep(for: .milliseconds(1))
        }
    }

    @MainActor
    func testLateSearchCannotReplaceNewerResultsOrStopItsLoadingState() async throws {
        let service = DelayedDiscoveryService()
        let controller = NativeDiscoveryController()
        let first = Task { await controller.search(notebookId: "course", request: WebDiscoveryRequest(query: "first"), using: service) }
        try await waitForSearch("first", service: service)
        let second = Task { await controller.search(notebookId: "course", request: WebDiscoveryRequest(query: "second"), using: service) }
        try await waitForSearch("second", service: service)
        await service.resolveSearch("first")
        await first.value
        XCTAssertTrue(controller.isLoading)
        XCTAssertNil(controller.page)
        await service.resolveSearch("second")
        await second.value
        XCTAssertFalse(controller.isLoading)
        XCTAssertEqual(controller.page?.query, "second")
        XCTAssertEqual(controller.notebookId, "course")
        XCTAssertEqual(controller.lastRequest?.query, "second")
    }

    @MainActor
    func testFailedSearchRetainsGoogleFallbackForSubmittedFilters() async throws {
        let controller = NativeDiscoveryController()
        await controller.search(notebookId: "course", request: WebDiscoveryRequest(query: "ATP & cells", domain: "example.edu", fileType: .pdf), using: UnavailableDiscoveryService())
        XCTAssertNil(controller.page)
        XCTAssertNotNil(controller.error)
        let url = try XCTUnwrap(controller.googleURL)
        let query = try XCTUnwrap(URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.first?.value)
        XCTAssertEqual(query, "ATP & cells site:example.edu filetype:pdf")
    }

    @MainActor
    func testAccountChangeDropsPriorQueryAndLateCachedResult() async throws {
        let service = DelayedDiscoveryService()
        let controller = NativeDiscoveryController()
        controller.bindAccount("account-a")
        let task = Task { await controller.search(notebookId: "same-course", request: WebDiscoveryRequest(query: "private-query", engine: .auto), using: service) }
        try await waitForSearch("private-query", service: service)
        controller.bindAccount("account-b")
        await service.resolveSearch("private-query")
        await task.value
        XCTAssertNil(controller.page)
        XCTAssertNil(controller.lastRequest)
        XCTAssertNil(controller.googleURL)
        XCTAssertFalse(controller.isLoading)
    }

    @MainActor
    func testClearingPendingSearchPreventsItsResponseFromReappearing() async throws {
        let service = DelayedDiscoveryService()
        let controller = NativeDiscoveryController()
        let task = Task { await controller.search(notebookId: "course", request: WebDiscoveryRequest(query: "cancelled"), using: service) }
        try await waitForSearch("cancelled", service: service)
        controller.clear()
        await service.resolveSearch("cancelled")
        await task.value
        XCTAssertFalse(controller.isLoading)
        XCTAssertNil(controller.page)
        XCTAssertNil(controller.error)
        XCTAssertNil(controller.lastRequest)
    }

    @MainActor
    func testCancelledViewTaskCannotPublishALateResult() async throws {
        let service = DelayedDiscoveryService()
        let controller = NativeDiscoveryController()
        let task = Task { await controller.search(notebookId: "course", request: WebDiscoveryRequest(query: "leaving"), using: service) }
        try await waitForSearch("leaving", service: service)
        task.cancel()
        await service.resolveSearch("leaving")
        await task.value
        XCTAssertFalse(controller.isLoading)
        XCTAssertNil(controller.page)
        XCTAssertNil(controller.error)
    }

    @MainActor
    func testCancelStopsSpinnerWithoutClearingCurrentResults() async throws {
        let service = DelayedDiscoveryService()
        let controller = NativeDiscoveryController()
        let first = Task { await controller.search(notebookId: "course", request: WebDiscoveryRequest(query: "settled"), using: service) }
        try await waitForSearch("settled", service: service)
        await service.resolveSearch("settled")
        await first.value
        XCTAssertEqual(controller.page?.query, "settled")
        let pending = Task { await controller.search(notebookId: "course", request: WebDiscoveryRequest(query: "next"), using: service) }
        try await waitForSearch("next", service: service)
        controller.cancel()
        await service.resolveSearch("next")
        await pending.value
        XCTAssertFalse(controller.isLoading)
        XCTAssertNil(controller.page?.query == "next" ? controller.page : nil)
    }

    @MainActor
    func testLateImportCannotOverwriteNewerImportNotice() async throws {
        let service = DelayedDiscoveryService()
        let controller = NativeDiscoveryController()
        let first = Task { await controller.importSource(notebookId: "course", url: "https://example.edu/first", using: service) }
        try await waitForImport("https://example.edu/first", service: service)
        let second = Task { await controller.importSource(notebookId: "course", url: "https://example.edu/second", using: service) }
        try await waitForImport("https://example.edu/second", service: service)
        await service.resolveImportSaved("https://example.edu/first", sourceId: "aaaaaaaaaaaa")
        await first.value
        XCTAssertNil(controller.lastImportedSourceId)
        XCTAssertNil(controller.importNotice)
        await service.resolveImportSaved("https://example.edu/second", sourceId: "bbbbbbbbbbbb")
        await second.value
        XCTAssertEqual(controller.lastImportedSourceId, "bbbbbbbbbbbb")
        XCTAssertNotNil(controller.importNotice)
        XCTAssertNil(controller.importingURL)
    }

    @MainActor
    func testCancelPreventsLateImportNotice() async throws {
        let service = DelayedDiscoveryService()
        let controller = NativeDiscoveryController()
        let task = Task { await controller.importSource(notebookId: "course", url: "https://example.edu/late", using: service) }
        try await waitForImport("https://example.edu/late", service: service)
        controller.cancel()
        await service.resolveImportSaved("https://example.edu/late", sourceId: "aaaaaaaaaaaa")
        await task.value
        XCTAssertNil(controller.importingURL)
        XCTAssertNil(controller.importNotice)
        XCTAssertNil(controller.lastImportedSourceId)
    }

    @MainActor
    func testImportPassesCurrentNotebookId() async throws {
        let service = DelayedDiscoveryService()
        let controller = NativeDiscoveryController()
        let task = Task { await controller.importSource(notebookId: "course-2", url: "https://example.edu/x", using: service) }
        try await waitForImport("https://example.edu/x", service: service)
        controller.clear()
        await service.resolveImportSaved("https://example.edu/x", sourceId: "aaaaaaaaaaaa")
        await task.value
        XCTAssertEqual(service.seenNotebookIds, ["course-2"])
    }
}

// MARK: - Google link + browser safety

final class GoogleDiscoveryLinkTests: XCTestCase {
    func testIDNADomainFilterMatchesBackendAndGoogleEncoding() throws {
        XCTAssertTrue(GoogleDiscoveryLink.isValidDomain("bücher.de"))
        let url = try XCTUnwrap(GoogleDiscoveryLink.url(query: "cells", domain: "bücher.de", fileType: .all))
        let query = try XCTUnwrap(URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.first?.value)
        XCTAssertEqual(query, "cells site:xn--bcher-kva.de")
    }

    func testValidBareHostsAreAccepted() {
        XCTAssertTrue(GoogleDiscoveryLink.isValidDomain("example.edu"))
        XCTAssertTrue(GoogleDiscoveryLink.isValidDomain("arxiv.org"))
        XCTAssertTrue(GoogleDiscoveryLink.isValidDomain("sub.example.edu"))
        XCTAssertTrue(GoogleDiscoveryLink.isValidDomain("EXAMPLE.EDU"))
        XCTAssertTrue(GoogleDiscoveryLink.isValidDomain("example.edu."))
    }

    func testSchemePathCredentialsPortsAndOperatorsAreRejected() {
        for bad in ["", "  ", "https://example.edu", "http://example.edu/path", "example.edu/path",
                    "user:secret@example.edu", "user@example.edu", "example.edu:8080",
                    "example edu", "site:example.edu", "example.edu filetype:pdf",
                    "evil-example.edu query", "localhost", "127.0.0.1", "example..edu", "-bad.com", "bad-.com"] {
            XCTAssertFalse(GoogleDiscoveryLink.isValidDomain(bad), "should reject: \(bad)")
        }
    }

    func testGoogleURLIncludesOnlyQuerySiteAndType() throws {
        let url = GoogleDiscoveryLink.url(query: "ATP & Calvin", domain: "example.edu", fileType: .pdf)!
        XCTAssertEqual(url.scheme, "https")
        XCTAssertEqual(url.host, "www.google.com")
        XCTAssertEqual(url.path, "/search")
        let items = URLComponents(url: url, resolvingAgainstBaseURL: false)!.queryItems!
        let q = items.first(where: { $0.name == "q" })!.value!
        XCTAssertTrue(q.contains("ATP & Calvin"))
        XCTAssertTrue(q.contains("site:example.edu"))
        XCTAssertTrue(q.contains("filetype:pdf"))
        XCTAssertFalse(q.contains("academic"))
        // No tokens or account material in the link.
        XCTAssertFalse(url.absoluteString.contains("acct"))
        XCTAssertFalse(url.absoluteString.contains("desk"))
    }

    func testGoogleURLEncodesSpecialQueryAndOmitsInvalidDomain() {
        let url = GoogleDiscoveryLink.url(query: "a&b \"c\"", domain: "https://example.edu/path", fileType: .html)!
        let q = URLComponents(url: url, resolvingAgainstBaseURL: false)!.queryItems!.first(where: { $0.name == "q" })!.value!
        XCTAssertTrue(q.contains("a&b \"c\""))
        XCTAssertFalse(q.contains("site:"))
        XCTAssertTrue(q.contains("-filetype:pdf"))
    }

    func testGoogleURLForAllTypeOmitsFiletypeOperator() {
        let url = GoogleDiscoveryLink.url(query: "cells", domain: nil, fileType: .all)!
        let q = URLComponents(url: url, resolvingAgainstBaseURL: false)!.queryItems!.first(where: { $0.name == "q" })!.value!
        XCTAssertEqual(q, "cells")
    }

    func testBrowserSafetyAllowsOnlyCredentialFreeHTTPS() {
        XCTAssertTrue(GoogleDiscoveryLink.canOpenWebsite(URL(string: "https://example.edu/article")!))
        XCTAssertTrue(GoogleDiscoveryLink.canOpenWebsite(URL(string: "http://example.edu/article")!))
        XCTAssertFalse(GoogleDiscoveryLink.canOpenWebsite(URL(string: "https://user:secret@example.edu/")!))
        XCTAssertFalse(GoogleDiscoveryLink.canOpenWebsite(URL(string: "file:///etc/passwd")!))
        XCTAssertFalse(GoogleDiscoveryLink.canOpenWebsite(URL(string: "https://")!))
    }

    func testResultTypeLabelDistinguishesPDFLinkFromWebPage() {
        XCTAssertEqual(WebDiscoveryResult(title: "t", url: "https://x/y.pdf", snippet: "s", domain: "x", fileType: "pdf", score: 1).typeLabel, "PDF link")
        XCTAssertEqual(WebDiscoveryResult(title: "t", url: "https://x/y", snippet: "s", domain: "x", fileType: "html", score: 1).typeLabel, "Web page")
    }
}

private struct UnavailableDiscoveryService: WebDiscovering {
    func discoverWeb(request: WebDiscoveryRequest) async throws -> WebDiscoveryPage {
        throw APIError.server(status: 503, message: "Search unavailable")
    }
    func importWebSource(notebookId: String, url: String) async throws -> PasteResult {
        throw APIError.server(status: 503, message: "Import unavailable")
    }
}
