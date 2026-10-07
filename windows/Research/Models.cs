using System.Text.Json.Serialization;

namespace Notaeo;

public sealed record UserPublic(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("email")] string Email);

public sealed record AuthResponse(
    [property: JsonPropertyName("user")] UserPublic User,
    [property: JsonPropertyName("token")] string Token);

public abstract record RegisterOutcome
{
    public sealed record Authed(AuthResponse Response) : RegisterOutcome;
    public sealed record Duplicate(string Detail) : RegisterOutcome;
}

public sealed record Notebook(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("created_at")] string CreatedAt);

public sealed record SourcePage(
    [property: JsonPropertyName("number")] int Number,
    [property: JsonPropertyName("text")] string Text);

public sealed record SourceChunk(
    [property: JsonPropertyName("seq")] int Seq,
    [property: JsonPropertyName("pages")] List<int> Pages,
    [property: JsonPropertyName("text")] string Text);

public sealed record ImportantPassage(
    [property: JsonPropertyName("text")] string Text,
    [property: JsonPropertyName("score")] double Score,
    [property: JsonPropertyName("chunk_seq")] int ChunkSeq,
    [property: JsonPropertyName("pages")] List<int> Pages);

public sealed record SourceSummary(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("notebook_id")] string NotebookId,
    [property: JsonPropertyName("kind")] string Kind,
    [property: JsonPropertyName("title")] string Title,
    [property: JsonPropertyName("tags")] List<string> Tags,
    [property: JsonPropertyName("created_at")] string CreatedAt,
    [property: JsonPropertyName("chunk_count")] int ChunkCount);

public sealed record SourceDetail(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("notebook_id")] string NotebookId,
    [property: JsonPropertyName("kind")] string Kind,
    [property: JsonPropertyName("title")] string Title,
    [property: JsonPropertyName("tags")] List<string> Tags,
    [property: JsonPropertyName("created_at")] string CreatedAt,
    [property: JsonPropertyName("pages")] List<SourcePage> Pages,
    [property: JsonPropertyName("chunks")] List<SourceChunk> Chunks,
    [property: JsonPropertyName("canonical_url")] string? CanonicalUrl,
    [property: JsonPropertyName("site_name")] string? SiteName,
    [property: JsonPropertyName("byline")] string? Byline,
    [property: JsonPropertyName("published")] string? Published,
    [property: JsonPropertyName("important_passages")] List<ImportantPassage>? ImportantPassages)
{
    public string FullText()
    {
        if (Pages.Count > 0)
        {
            return string.Join("\n\n", Pages.Select(p => p.Text));
        }

        return string.Join("\n\n", Chunks.Select(c => c.Text));
    }
}

public sealed record SourceChunksPage(
    [property: JsonPropertyName("total")] int Total,
    [property: JsonPropertyName("chunks")] List<SourceChunk> Chunks);

public sealed record DuplicateRef(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("title")] string Title);

public sealed record PasteResult(bool Saved, DuplicateRef? DuplicateOf, SourceSummary? Summary);

public sealed record UploadResult(
    [property: JsonPropertyName("sources")] List<SourceSummary> Sources,
    [property: JsonPropertyName("errors")] List<Dictionary<string, string>> Errors);

public sealed record ExamGoal(
    [property: JsonPropertyName("title")] string Title,
    [property: JsonPropertyName("exam_date")] string ExamDate,
    [property: JsonPropertyName("daily_minutes")] int DailyMinutes,
    [property: JsonPropertyName("focus_topics")] List<string> FocusTopics);

public sealed record CoachCitation(
    [property: JsonPropertyName("source_id")] string SourceId,
    [property: JsonPropertyName("source_title")] string SourceTitle,
    [property: JsonPropertyName("pages")] List<int> Pages);

public sealed record CoachTask(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("topic")] string Topic,
    [property: JsonPropertyName("prompt")] string Prompt,
    [property: JsonPropertyName("answer")] string Answer,
    [property: JsonPropertyName("minutes")] int Minutes,
    [property: JsonPropertyName("reason")] string Reason,
    [property: JsonPropertyName("source_id")] string? SourceId,
    [property: JsonPropertyName("source_title")] string? SourceTitle,
    [property: JsonPropertyName("pages")] List<int> Pages,
    [property: JsonPropertyName("chunk_seq")] int? ChunkSeq,
    [property: JsonPropertyName("card_id")] string? CardId);

public sealed record CoachAttempt(
    [property: JsonPropertyName("task_id")] string TaskId,
    [property: JsonPropertyName("rating")] string Rating,
    [property: JsonPropertyName("response")] string Response,
    [property: JsonPropertyName("created_at")] string CreatedAt);

public sealed record CoachSession(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("notebook_id")] string NotebookId,
    [property: JsonPropertyName("goal")] ExamGoal Goal,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("generated_by")] string GeneratedBy,
    [property: JsonPropertyName("notice")] string? Notice,
    [property: JsonPropertyName("tasks")] List<CoachTask> Tasks,
    [property: JsonPropertyName("attempts")] List<CoachAttempt> Attempts,
    [property: JsonPropertyName("created_at")] string CreatedAt,
    [property: JsonPropertyName("completed_at")] string? CompletedAt);

public sealed record CoachState(
    [property: JsonPropertyName("goal")] ExamGoal? Goal,
    [property: JsonPropertyName("sessions")] List<CoachSession> Sessions);

public sealed record CoachExplanation(
    [property: JsonPropertyName("answer")] string Answer,
    [property: JsonPropertyName("citations")] List<CoachCitation> Citations,
    [property: JsonPropertyName("model")] string? Model,
    [property: JsonPropertyName("generated_by")] string GeneratedBy,
    [property: JsonPropertyName("notice")] string? Notice);

public sealed record AISettings(
    [property: JsonPropertyName("configured")] bool Configured,
    [property: JsonPropertyName("provider")] string? Provider,
    [property: JsonPropertyName("model")] string? Model);

public sealed record SearchRequest(
    string Query,
    string? Kind = null,
    bool Related = true,
    int Offset = 0,
    int Limit = 10);

public sealed record SearchHit(
    [property: JsonPropertyName("source_id")] string SourceId,
    [property: JsonPropertyName("source_title")] string SourceTitle,
    [property: JsonPropertyName("pages")] List<int> Pages,
    [property: JsonPropertyName("score")] double Score,
    [property: JsonPropertyName("snippet")] string Snippet,
    [property: JsonPropertyName("matched_terms")] List<string> MatchedTerms);

public sealed record SearchPage(
    [property: JsonPropertyName("query")] string Query,
    [property: JsonPropertyName("hits")] List<SearchHit> Hits,
    [property: JsonPropertyName("total")] int Total,
    [property: JsonPropertyName("limit")] int Limit,
    [property: JsonPropertyName("offset")] int Offset,
    [property: JsonPropertyName("has_more")] bool HasMore,
    [property: JsonPropertyName("took_ms")] int TookMs,
    [property: JsonPropertyName("related")] bool Related);

public sealed record MindMapNode(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("children")] List<MindMapNode> Children,
    [property: JsonPropertyName("source_id")] string? SourceId,
    [property: JsonPropertyName("pages")] List<int> Pages);

public sealed record MindMapExport(byte[] Data, string Filename);

public sealed record WebDiscoveryRequest(
    string Query,
    int Limit = 20,
    string Engine = "auto",
    string? Domain = null,
    string FileType = "all",
    bool Academic = false,
    string Recency = "any",
    string? Region = "us-en");

public sealed record WebDiscoveryResult(
    [property: JsonPropertyName("title")] string Title,
    [property: JsonPropertyName("url")] string Url,
    [property: JsonPropertyName("snippet")] string Snippet,
    [property: JsonPropertyName("domain")] string Domain,
    [property: JsonPropertyName("file_type")] string FileType,
    [property: JsonPropertyName("score")] double Score)
{
    [System.Text.Json.Serialization.JsonIgnore]
    public string TypeLabel => string.Equals(FileType, "pdf", StringComparison.OrdinalIgnoreCase)
        ? "PDF link"
        : "Web page";
}

public sealed record WebDiscoveryFilters(
    [property: JsonPropertyName("domain")] string? Domain,
    [property: JsonPropertyName("file_type")] string FileType,
    [property: JsonPropertyName("academic")] bool Academic,
    [property: JsonPropertyName("recency")] string Recency,
    [property: JsonPropertyName("region")] string? Region);

public sealed record WebDiscoveryPage(
    [property: JsonPropertyName("query")] string Query,
    [property: JsonPropertyName("effective_query")] string EffectiveQuery,
    [property: JsonPropertyName("engine")] string Engine,
    [property: JsonPropertyName("results")] List<WebDiscoveryResult> Results,
    [property: JsonPropertyName("took_ms")] int TookMs,
    [property: JsonPropertyName("filters")] WebDiscoveryFilters Filters);

public sealed record SiteIndexSite(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("url")] string Url,
    [property: JsonPropertyName("created_at")] string CreatedAt,
    [property: JsonPropertyName("indexed_at")] string? IndexedAt,
    [property: JsonPropertyName("page_count")] int PageCount,
    [property: JsonPropertyName("notice")] string Notice,
    [property: JsonPropertyName("revision")] int Revision);
