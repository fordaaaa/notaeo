import Foundation

// MARK: - Account

struct UserPublic: Codable, Equatable, Sendable {
    var id: String
    var email: String
}

struct AuthResponse: Codable, Sendable {
    var user: UserPublic
    var token: String
}

enum RegisterOutcome: Sendable {
    case authed(AuthResponse)
    case duplicate(detail: String)
}

// MARK: - Notebooks / sources

struct Notebook: Codable, Identifiable, Equatable, Sendable {
    var id: String
    var name: String
    var createdAt: String
}

struct SearchHit: Decodable, Equatable, Sendable {
    let sourceId: String
    let sourceTitle: String
    let pages: [Int]
    let score: Double
    let snippet: String
    let matchedTerms: [String]
}

struct SearchPage: Decodable, Equatable, Sendable {
    let query: String
    let hits: [SearchHit]
    let total: Int
    let limit: Int
    let offset: Int
    let hasMore: Bool
    let tookMs: Int
    let related: Bool
}

struct NativeSearchRequest: Equatable, Sendable {
    var query: String
    var kind: String? = nil
    var related: Bool = true
    var offset: Int = 0
    var limit: Int = 10
}

struct NativeMindmapNode: Decodable, Identifiable, Equatable, Sendable {
    let id: String
    let name: String
    let children: [NativeMindmapNode]
    let sourceId: String?
    let pages: [Int]
}

struct SourcePage: Codable, Equatable, Sendable {
    var number: Int
    var text: String
}

struct SourceChunk: Codable, Equatable, Sendable {
    var seq: Int
    var pages: [Int]
    var text: String
}

struct ImportantPassage: Codable, Equatable, Sendable {
    var text: String
    var score: Double
    var chunkSeq: Int
    var pages: [Int]
}

struct SourceSummary: Codable, Identifiable, Equatable, Sendable {
    var id: String
    var notebookId: String
    var kind: String
    var title: String
    var tags: [String]
    var createdAt: String
    var chunkCount: Int
}

struct SourceDetail: Codable, Identifiable, Equatable, Sendable {
    var id: String
    var notebookId: String
    var kind: String
    var title: String
    var tags: [String]
    var createdAt: String
    var pages: [SourcePage]
    var chunks: [SourceChunk]
    var canonicalUrl: String?
    var siteName: String?
    var byline: String?
    var published: String?
    var importantPassages: [ImportantPassage]?

    var fullText: String {
        if !pages.isEmpty { return pages.map { $0.text }.joined(separator: "\n\n") }
        return chunks.map { $0.text }.joined(separator: "\n\n")
    }
}

struct SourceChunksPage: Codable, Sendable {
    var total: Int
    var chunks: [SourceChunk]
}

struct DuplicateRef: Codable, Equatable, Sendable {
    var id: String
    var title: String
}

struct PasteResult: Sendable {
    var saved: Bool
    var duplicateOf: DuplicateRef?
    var summary: SourceSummary?
}

// MARK: - Coach (mirrors backend/core/models.py)

struct ExamGoal: Codable, Equatable, Sendable {
    var title: String
    var examDate: String
    var dailyMinutes: Int
    var focusTopics: [String]
}

struct CoachCitation: Codable, Equatable, Sendable {
    var sourceId: String
    var sourceTitle: String
    var pages: [Int]
}

struct CoachTask: Codable, Identifiable, Equatable, Sendable {
    var id: String
    var topic: String
    var prompt: String
    var answer: String
    var minutes: Int
    var reason: String
    var sourceId: String?
    var sourceTitle: String?
    var pages: [Int]
    var chunkSeq: Int?
    var cardId: String?
}

struct CoachAttempt: Codable, Equatable, Sendable {
    var taskId: String
    var rating: String
    var response: String
    var createdAt: String
}

struct CoachSession: Codable, Identifiable, Equatable, Sendable {
    var id: String
    var notebookId: String
    var goal: ExamGoal
    var status: String
    var generatedBy: String
    var notice: String?
    var tasks: [CoachTask]
    var attempts: [CoachAttempt]
    var createdAt: String
    var completedAt: String?
}

struct CoachState: Codable, Equatable, Sendable {
    var goal: ExamGoal?
    var sessions: [CoachSession]
}

struct CoachExplanation: Codable, Equatable, Sendable {
    var answer: String
    var citations: [CoachCitation]
    var model: String?
    var generatedBy: String
    var notice: String?
}

// MARK: - AI availability (mirrors authed GET /api/ai/status)

struct AIStatus: Codable, Equatable, Sendable {
    var enabled: Bool
    var model: String?
}

// MARK: - Web discovery (mirrors GET /api/web/discover)

enum WebDiscoveryEngine: String, Codable, CaseIterable, Equatable, Sendable {
    case auto
    case google
    case duckduckgo
    case brave
    case mojeek
    case index

    var label: String {
        switch self {
        case .auto: return "Automatic"
        case .google: return "Google"
        case .duckduckgo: return "DuckDuckGo"
        case .brave: return "Brave"
        case .mojeek: return "Mojeek"
        case .index: return "Indexed sites"
        }
    }
}

enum WebDiscoveryFileType: String, Codable, CaseIterable, Equatable, Sendable {
    case all
    case pdf
    case html

    var label: String {
        switch self {
        case .all: return "All pages"
        case .pdf: return "PDF links"
        case .html: return "Web pages"
        }
    }
}

enum WebDiscoveryRecency: String, Codable, CaseIterable, Equatable, Sendable {
    case any
    case day
    case week
    case month
    case year

    var label: String {
        switch self {
        case .any: return "Any time"
        case .day: return "Past day"
        case .week: return "Past week"
        case .month: return "Past month"
        case .year: return "Past year"
        }
    }
}

enum WebDiscoveryRegion: String, Codable, CaseIterable, Equatable, Sendable {
    case usEN = "us-en"
    case caEN = "ca-en"
    case ukEN = "uk-en"
    case auEN = "au-en"

    var label: String {
        switch self {
        case .usEN: return "US (English)"
        case .caEN: return "Canada (English)"
        case .ukEN: return "UK (English)"
        case .auEN: return "Australia (English)"
        }
    }
}

struct WebDiscoveryRequest: Equatable, Sendable {
    var query: String
    var limit: Int = 20
    var engine: WebDiscoveryEngine = .auto
    var domain: String? = nil
    var fileType: WebDiscoveryFileType = .all
    var academic: Bool = false
    var recency: WebDiscoveryRecency = .any
    var region: WebDiscoveryRegion = .usEN
}

struct WebDiscoveryResult: Decodable, Equatable, Sendable {
    var title: String
    var url: String
    var snippet: String
    var domain: String
    var fileType: String
    var score: Double

    var isPDF: Bool { fileType.lowercased() == "pdf" }

    var typeLabel: String { isPDF ? "PDF link" : "Web page" }
}

struct WebDiscoveryFilters: Decodable, Equatable, Sendable {
    var domain: String?
    var fileType: String
    var academic: Bool
    var recency: String
    var region: String
}

struct WebDiscoveryPage: Decodable, Equatable, Sendable {
    var query: String
    var effectiveQuery: String
    var engine: String
    var results: [WebDiscoveryResult]
    var tookMs: Int
    var filters: WebDiscoveryFilters
}

// MARK: - Educational site index (mirrors GET /api/web/index/sites)

struct SiteIndexSite: Codable, Identifiable, Equatable, Sendable {
    var id: String
    var url: String
    var createdAt: String
    var indexedAt: String?
    var pageCount: Int
    var notice: String
    var revision: Int
}

// MARK: - Coach helpers (resume/next-question logic shared by app + tests)

enum CoachLogic {
    /// Mirrors ExamCoachPanel: prefer the active session, else the first saved one.
    static func resumeSession(in state: CoachState) -> CoachSession? {
        state.sessions.first(where: { $0.status == "active" }) ?? state.sessions.first
    }

    /// Index of the first task without a saved attempt (-1 when all rated).
    static func nextQuestionIndex(in session: CoachSession) -> Int {
        session.tasks.firstIndex(where: { task in
            !session.attempts.contains(where: { $0.taskId == task.id })
        }) ?? -1
    }

    static func isComplete(_ session: CoachSession) -> Bool {
        !session.tasks.isEmpty && session.tasks.allSatisfy { task in
            session.attempts.contains(where: { $0.taskId == task.id })
        }
    }
}
