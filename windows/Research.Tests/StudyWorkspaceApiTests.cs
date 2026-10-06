using System.Net;
using System.Net.Http.Headers;
using System.Text;
using Notaeo;
using Xunit;

namespace Notaeo.Tests;

// Transport + DTO regressions for the Windows study workspace:
// GET /api/notebooks/{id}/search/page, /mindmap, /mindmap/export.
public sealed class StudyWorkspaceApiTests
{
    private static Dictionary<string, string> ParseQuery(string query)
    {
        var map = new Dictionary<string, string>();
        var trimmed = query.TrimStart('?');
        if (string.IsNullOrEmpty(trimmed))
        {
            return map;
        }

        foreach (var part in trimmed.Split('&', StringSplitOptions.RemoveEmptyEntries))
        {
            var idx = part.IndexOf('=');
            if (idx < 0)
            {
                map[Uri.UnescapeDataString(part)] = string.Empty;
            }
            else
            {
                var key = Uri.UnescapeDataString(part[..idx]);
                var value = Uri.UnescapeDataString(part[(idx + 1)..]);
                map[key] = value;
            }
        }

        return map;
    }

    [Fact]
    public async Task SearchPreservesSpecialCharsPaginationAndFilter()
    {
        const string query = "cells & \"mitosis\" + αβ?";
        string? path = null;
        string? rawQuery = null;
        string? auth = null;
        string? desk = null;

        var api = Fake.Api(req =>
        {
            path = req.RequestUri!.AbsolutePath;
            rawQuery = req.RequestUri.Query;
            auth = req.Headers.Authorization?.ToString();
            desk = req.Headers.TryGetValues(NotaeoApi.DesktopTokenHeader, out var v) ? v.FirstOrDefault() : null;
            return Fake.Json(
                "{\"query\":\"cells & \\\"mitosis\\\" + αβ?\",\"hits\":[{\"source_id\":\"src1\",\"source_title\":\"Bio text\",\"pages\":[3,5],\"score\":0.9,\"snippet\":\"... mitosis ...\",\"matched_terms\":[\"mitosis\"]}],\"total\":1,\"limit\":10,\"offset\":20,\"has_more\":false,\"took_ms\":4,\"related\":true}",
                HttpStatusCode.OK);
        });

        var page = await api.SearchNotebookAsync(
            "nb123",
            new SearchRequest(query, Kind: "pdf", Related: true, Offset: 20, Limit: 10));

        Assert.Equal("/api/notebooks/nb123/search/page", path);
        Assert.Equal("Bearer acct-1", auth);
        Assert.Equal("desk-per-launch", desk);

        // Raw query must be percent-encoded (no raw spaces/quotes/ampersands).
        Assert.NotNull(rawQuery);
        Assert.DoesNotContain(" ", rawQuery!);
        Assert.DoesNotContain("\"", rawQuery!);

        var parsed = ParseQuery(rawQuery!);
        Assert.Equal(query, parsed["q"]);
        Assert.Equal("pdf", parsed["kind"]);
        Assert.Equal("20", parsed["offset"]);
        Assert.Equal("10", parsed["limit"]);
        Assert.Equal("true", parsed["related"]);

        Assert.Equal(query, page.Query);
        Assert.Equal(1, page.Total);
        Assert.Equal(20, page.Offset);
        Assert.Equal(10, page.Limit);
        Assert.False(page.HasMore);
        Assert.Equal(4, page.TookMs);
        Assert.True(page.Related);
        var hit = Assert.Single(page.Hits);
        Assert.Equal("src1", hit.SourceId);
        Assert.Equal("Bio text", hit.SourceTitle);
        Assert.Equal(new List<int> { 3, 5 }, hit.Pages);
        Assert.Equal(0.9, hit.Score, precision: 5);
        Assert.Contains("mitosis", hit.Snippet);
        Assert.Equal(new List<string> { "mitosis" }, hit.MatchedTerms);
    }

    [Fact]
    public async Task SearchOmitsKindWhenNullAndSendsRelatedFalse()
    {
        string? rawQuery = null;
        var api = Fake.Api(req =>
        {
            rawQuery = req.RequestUri!.Query;
            return Fake.Json(
                "{\"query\":\"cells\",\"hits\":[],\"total\":0,\"limit\":5,\"offset\":0,\"has_more\":false,\"took_ms\":1,\"related\":false}",
                HttpStatusCode.OK);
        });

        var page = await api.SearchNotebookAsync("nb123", new SearchRequest("cells", Related: false, Offset: 0, Limit: 5));
        Assert.NotNull(rawQuery);
        var parsed = ParseQuery(rawQuery!);
        Assert.Equal("cells", parsed["q"]);
        Assert.False(parsed.ContainsKey("kind"));
        Assert.Equal("false", parsed["related"]);
        Assert.Equal(0, page.Total);
        Assert.False(page.Related);
    }

    [Fact]
    public async Task MindMapDecodesRecursiveCitations()
    {
        string? path = null;
        var api = Fake.Api(req =>
        {
            path = req.RequestUri!.AbsolutePath;
            return Fake.Json(
                "{\"id\":\"root-1\",\"name\":\"Biology\",\"children\":[{\"id\":\"source-src1\",\"name\":\"Bio text\",\"children\":[{\"id\":\"concept-src1-mitosis\",\"name\":\"mitosis\",\"children\":[],\"source_id\":\"src1\",\"pages\":[3]}],\"source_id\":\"src1\",\"pages\":[1,3]}],\"source_id\":null,\"pages\":[]}",
                HttpStatusCode.OK);
        });

        var root = await api.GetMindMapAsync("nb123");
        Assert.Equal("/api/notebooks/nb123/mindmap", path);
        Assert.Equal("root-1", root.Id);
        Assert.Equal("Biology", root.Name);
        Assert.Null(root.SourceId);
        var branch = Assert.Single(root.Children);
        Assert.Equal("src1", branch.SourceId);
        Assert.Equal(new List<int> { 1, 3 }, branch.Pages);
        var leaf = Assert.Single(branch.Children);
        Assert.Equal("mitosis", leaf.Name);
        Assert.Equal("src1", leaf.SourceId);
        Assert.Equal(new List<int> { 3 }, leaf.Pages);
        Assert.Empty(leaf.Children);
    }

    [Fact]
    public async Task ExportReturnsMarkdownBytesAndSanitizedServerFilename()
    {
        const string markdown = "# Biology\n\n- Bio text [source src1] (p. 1)\n";
        var api = Fake.Api(req =>
        {
            Assert.Equal("/api/notebooks/nb123/mindmap/export", req.RequestUri!.AbsolutePath);
            Assert.Equal("Bearer acct-1", req.Headers.Authorization!.ToString());
            var resp = new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new ByteArrayContent(Encoding.UTF8.GetBytes(markdown)),
            };
            resp.Content.Headers.ContentType = new MediaTypeHeaderValue("text/markdown");
            resp.Content.Headers.TryAddWithoutValidation("Content-Disposition", "attachment; filename=\"course-mindmap.md\"");
            return resp;
        });

        var export = await api.ExportMindMapAsync("nb123");
        Assert.Equal("course-mindmap.md", export.Filename);
        Assert.Equal(markdown, Encoding.UTF8.GetString(export.Data));
        Assert.StartsWith("# ", Encoding.UTF8.GetString(export.Data));
    }

    [Fact]
    public async Task ExportSanitizesTraversalFilename()
    {
        var api = Fake.Api(_ =>
        {
            var resp = new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new ByteArrayContent(Encoding.UTF8.GetBytes("# x\n")),
            };
            resp.Content.Headers.TryAddWithoutValidation("Content-Disposition", "attachment; filename=\"../../evil.md\"");
            return resp;
        });

        var export = await api.ExportMindMapAsync("nb123");
        Assert.Equal("evil.md", export.Filename);
        Assert.DoesNotContain("..", export.Filename);
        Assert.DoesNotContain("/", export.Filename);
    }

    [Fact]
    public void SanitizeRejectsControlsReservedAndLength()
    {
        Assert.Equal("evil.md", NotaeoApi.SanitizeExportFilename("../../evil.md"));
        Assert.Equal("ab.md", NotaeoApi.SanitizeExportFilename("a\u0001b\u007f.md"));
        Assert.Equal("mindmap.md", NotaeoApi.SanitizeExportFilename(null));
        Assert.Equal("mindmap.md", NotaeoApi.SanitizeExportFilename("   "));
        Assert.Equal("mindmap.md", NotaeoApi.SanitizeExportFilename("..."));

        var reserved = NotaeoApi.SanitizeExportFilename("CON.md");
        Assert.NotEqual("CON.md", reserved);
        Assert.EndsWith(".md", reserved, StringComparison.OrdinalIgnoreCase);

        var longName = new string('a', 300) + ".md";
        var trimmed = NotaeoApi.SanitizeExportFilename(longName);
        Assert.True(Encoding.UTF8.GetByteCount(trimmed) <= 255);
        Assert.EndsWith(".md", trimmed, StringComparison.OrdinalIgnoreCase);

        var illegal = NotaeoApi.SanitizeExportFilename("a/b\\c:d*e?f\"g<h>i|j.md");
        Assert.DoesNotContain("/", illegal);
        Assert.DoesNotContain("\\", illegal);
        Assert.DoesNotContain(":", illegal);
        Assert.DoesNotContain("*", illegal);
        Assert.DoesNotContain("?", illegal);
        Assert.DoesNotContain("\"", illegal);
        Assert.DoesNotContain("<", illegal);
        Assert.DoesNotContain(">", illegal);
        Assert.DoesNotContain("|", illegal);
    }

    [Fact]
    public async Task SearchUnauthorizedInvokesCallbackWithAttemptedToken()
    {
        string? seen = "unset";
        var api = new NotaeoApi(
            new HttpClient(new FakeHandler(_ => Fake.Json("{\"detail\":\"login required\"}", HttpStatusCode.Unauthorized))),
            Fake.Base,
            "desk-per-launch",
            () => "acct-1",
            t => seen = t);

        var ex = await Assert.ThrowsAsync<ApiException>(() =>
            api.SearchNotebookAsync("nb123", new SearchRequest("cells")));
        Assert.Equal(ApiErrorKind.Unauthorized, ex.Kind);
        Assert.Equal("acct-1", seen);
    }

    [Fact]
    public async Task MindMapNotFoundMaps()
    {
        var api = Fake.Api(_ => Fake.Json("{\"detail\":\"notebook not found\"}", HttpStatusCode.NotFound));
        var ex = await Assert.ThrowsAsync<ApiException>(() => api.GetMindMapAsync("nb123"));
        Assert.Equal(ApiErrorKind.NotFound, ex.Kind);
    }

    [Fact]
    public async Task ExportNotFoundMaps()
    {
        var api = Fake.Api(_ => Fake.Json("{\"detail\":\"notebook not found\"}", HttpStatusCode.NotFound));
        var ex = await Assert.ThrowsAsync<ApiException>(() => api.ExportMindMapAsync("nb123"));
        Assert.Equal(ApiErrorKind.NotFound, ex.Kind);
    }

    private sealed class CancellingHandler : HttpMessageHandler
    {
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
        {
            await Task.Delay(5000, cancellationToken).ConfigureAwait(false);
            return Fake.Json("{}", HttpStatusCode.OK);
        }
    }

    [Fact]
    public async Task SearchCancellationSurfacesAsCancelled()
    {
        var api = new NotaeoApi(
            new HttpClient(new CancellingHandler()),
            Fake.Base,
            "desk-per-launch",
            () => "acct-1");

        using var cts = new CancellationTokenSource();
        cts.CancelAfter(20);
        var ex = await Assert.ThrowsAsync<ApiException>(() =>
            api.SearchNotebookAsync("nb123", new SearchRequest("cells"), cts.Token));
        Assert.Equal(ApiErrorKind.Network, ex.Kind);
        Assert.Contains("cancelled", ex.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task MindMapCancellationSurfacesAsCancelled()
    {
        var api = new NotaeoApi(
            new HttpClient(new CancellingHandler()),
            Fake.Base,
            "desk-per-launch",
            () => "acct-1");

        using var cts = new CancellationTokenSource();
        cts.CancelAfter(20);
        var ex = await Assert.ThrowsAsync<ApiException>(() => api.GetMindMapAsync("nb123", cts.Token));
        Assert.Equal(ApiErrorKind.Network, ex.Kind);
        Assert.Contains("cancelled", ex.Message, StringComparison.OrdinalIgnoreCase);
    }
}
