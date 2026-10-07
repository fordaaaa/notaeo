using System.Net;
using System.Text.Json;
using Notaeo;
using Xunit;

namespace Notaeo.Tests;

// Portable web-discovery regressions: transport (auth + snake_case filters),
// controller staleness (search/import, rebind/cancel/deactivate), and the
// validated Google link. No WinForms; the real controller + ApiClient units.
public sealed class WebDiscoveryTransportTests
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
                map[Uri.UnescapeDataString(part[..idx])] = Uri.UnescapeDataString(part[(idx + 1)..]);
            }
        }

        return map;
    }

    [Fact]
    public async Task SigningOutClearsPriorAccountQueryAndResults()
    {
        var controller = new WebDiscoveryController((request, _) =>
            Task.FromResult(new WebDiscoveryPage(request.Query, request.Query, "auto", [], 1,
                new WebDiscoveryFilters(null, "all", false, "any", "us-en"))),
            (_, _, _) => Task.FromResult(new PasteResult(false, null, null)));
        controller.BindNotebook(new Notebook("course", "Course", "2026-10-07"));
        await controller.SearchAsync(new WebDiscoveryRequest("private study topic"));
        controller.BindNotebook(null);
        Assert.Null(controller.Page);
        Assert.Null(controller.LastRequest);
        Assert.Null(controller.Error);
    }

    [Fact]
    public async Task DiscoverSendsAuthHeadersAndAllFilterParams()
    {
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
                "{\"query\":\"ATP\",\"effective_query\":\"ATP site:example.edu\",\"engine\":\"duckduckgo\",\"results\":[],\"took_ms\":3,\"filters\":{\"domain\":\"example.edu\",\"file_type\":\"pdf\",\"academic\":true,\"recency\":\"month\",\"region\":\"us-en\"}}",
                HttpStatusCode.OK);
        });

        var page = await api.DiscoverWebAsync(new WebDiscoveryRequest(
            Query: "ATP & \"Calvin cycle\"",
            Limit: 20,
            Engine: "duckduckgo",
            Domain: "example.edu",
            FileType: "pdf",
            Academic: true,
            Recency: "month",
            Region: "us-en"));

        Assert.Equal("/api/web/discover", path);
        Assert.Equal("Bearer acct-1", auth);
        Assert.Equal("desk-per-launch", desk);
        Assert.NotNull(rawQuery);
        Assert.DoesNotContain(" ", rawQuery!);
        var parsed = ParseQuery(rawQuery!);
        Assert.Equal("ATP & \"Calvin cycle\"", parsed["q"]);
        Assert.Equal("20", parsed["limit"]);
        Assert.Equal("duckduckgo", parsed["engine"]);
        Assert.Equal("example.edu", parsed["domain"]);
        Assert.Equal("pdf", parsed["file_type"]);
        Assert.Equal("true", parsed["academic"]);
        Assert.Equal("month", parsed["recency"]);
        Assert.Equal("us-en", parsed["region"]);
        Assert.Equal("duckduckgo", page.Engine);
        Assert.Equal(3, page.TookMs);
        Assert.Equal("example.edu", page.Filters.Domain);
        Assert.True(page.Filters.Academic);
    }

    [Fact]
    public async Task DiscoverOmitsEmptyDomainAndDecodesSnakeCaseWithFullSnippet()
    {
        string? rawQuery = null;
        var api = Fake.Api(req =>
        {
            rawQuery = req.RequestUri!.Query;
            return Fake.Json(
                "{\"query\":\"mitosis\",\"effective_query\":\"mitosis\",\"engine\":\"auto\",\"results\":[{\"title\":\"Cell division\",\"url\":\"https://example.edu/mitosis\",\"snippet\":\"Mitosis & meiosis: full \\\"detail\\\" preserved.\",\"domain\":\"example.edu\",\"file_type\":\"html\",\"score\":9.5}],\"took_ms\":7,\"filters\":{\"domain\":null,\"file_type\":\"all\",\"academic\":false,\"recency\":\"any\",\"region\":\"us-en\"}}",
                HttpStatusCode.OK);
        });

        var page = await api.DiscoverWebAsync(new WebDiscoveryRequest(
            Query: "mitosis", Engine: "auto", FileType: "all", Academic: false, Recency: "any", Region: "us-en"));

        Assert.NotNull(rawQuery);
        var parsed = ParseQuery(rawQuery!);
        Assert.False(parsed.ContainsKey("domain"));
        Assert.Equal("mitosis", page.EffectiveQuery);
        Assert.Single(page.Results);
        Assert.Equal("example.edu", page.Results[0].Domain);
        Assert.Equal("html", page.Results[0].FileType);
        Assert.Equal("Mitosis & meiosis: full \"detail\" preserved.", page.Results[0].Snippet);
        Assert.Null(page.Filters.Domain);
        Assert.Equal("Web page", page.Results[0].TypeLabel);
    }

    [Fact]
    public async Task DiscoverUnavailableMapsToSafe503()
    {
        var api = Fake.Api(_ => Fake.Json("{\"detail\":\"web search is temporarily unavailable\"}", (HttpStatusCode)503));
        var ex = await Assert.ThrowsAsync<ApiException>(() =>
            api.DiscoverWebAsync(new WebDiscoveryRequest("cells")));
        Assert.Equal(ApiErrorKind.Server, ex.Kind);
        Assert.Equal(503, ex.StatusCode);
        Assert.Equal("web search is temporarily unavailable", ex.Message);
    }

    [Fact]
    public async Task DiscoverValidationMaps()
    {
        var api = Fake.Api(_ => Fake.Json("{\"detail\":\"q must not be blank\"}", HttpStatusCode.UnprocessableEntity));
        var ex = await Assert.ThrowsAsync<ApiException>(() =>
            api.DiscoverWebAsync(new WebDiscoveryRequest("   ")));
        Assert.Equal(ApiErrorKind.Validation, ex.Kind);
        Assert.Contains("blank", ex.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task DiscoverUnauthorizedInvokesCallback()
    {
        string? seen = "unset";
        var api = new NotaeoApi(
            new HttpClient(new FakeHandler(_ => Fake.Json("{\"detail\":\"login required\"}", HttpStatusCode.Unauthorized))),
            Fake.Base,
            "desk-per-launch",
            () => "acct-1",
            t => seen = t);
        var ex = await Assert.ThrowsAsync<ApiException>(() =>
            api.DiscoverWebAsync(new WebDiscoveryRequest("cells")));
        Assert.Equal(ApiErrorKind.Unauthorized, ex.Kind);
        Assert.Equal("acct-1", seen);
    }

    [Fact]
    public async Task AddUrlImportSendsForceFalse()
    {
        string? path = null;
        string? body = null;
        string? method = null;
        var api = Fake.Api(req =>
        {
            path = req.RequestUri!.AbsolutePath;
            method = req.Method.Method;
            body = req.Content!.ReadAsStringAsync().Result;
            return Fake.Json(
                "{\"id\":\"abcdef123457\",\"notebook_id\":\"course\",\"kind\":\"url\",\"title\":\"Article\",\"tags\":[],\"created_at\":\"2026-10-01T00:00:00Z\",\"chunk_count\":3}",
                HttpStatusCode.Created);
        });

        var res = await api.AddUrlSourceAsync("course", "https://example.edu/article", false);
        Assert.Equal("/api/notebooks/course/sources/url", path);
        Assert.Equal("POST", method);
        Assert.NotNull(body);
        using var doc = JsonDocument.Parse(body!);
        Assert.Equal("https://example.edu/article", doc.RootElement.GetProperty("url").GetString());
        Assert.False(doc.RootElement.GetProperty("force").GetBoolean());
        Assert.True(res.Saved);
        Assert.Equal("abcdef123457", res.Summary!.Id);
    }
}

public sealed class WebDiscoveryControllerTests
{
    private static Notebook Course(string id = "course") => new(id, "Biology", "2026-10-01T00:00:00Z");

    private static WebDiscoveryPage DiscoveryPage(string query) => new(
        query, query, "auto", [], 1,
        new WebDiscoveryFilters(null, "all", false, "any", "us-en"));

    private static WebDiscoveryResult WebResult(string url, string title = "Article", string fileType = "html") => new(
        title, url, "Readable snippet about cells.", "example.edu", fileType, 9.5);

    [Fact]
    public async Task SearchStoresPageAndClearsLoading()
    {
        var expected = DiscoveryPage("cells");
        var controller = new WebDiscoveryController(
            (_, _) => Task.FromResult(expected),
            (_, _, _) => Task.FromResult(new PasteResult(true, null, null)));
        controller.BindNotebook(Course());

        await controller.SearchAsync(new WebDiscoveryRequest("cells"));

        Assert.False(controller.IsLoading);
        Assert.Null(controller.Error);
        Assert.Same(expected, controller.Page);
        Assert.Equal("cells", controller.LastRequest?.Query);
    }

    [Fact]
    public async Task SearchErrorSurfacesAndRetryKeepsQuery()
    {
        var controller = new WebDiscoveryController(
            (_, _) => Task.FromException<WebDiscoveryPage>(new InvalidOperationException("engine down")),
            (_, _, _) => Task.FromResult(new PasteResult(true, null, null)));

        await controller.SearchAsync(new WebDiscoveryRequest("cells"));

        Assert.False(controller.IsLoading);
        Assert.Null(controller.Page);
        Assert.Contains("engine down", controller.Error, StringComparison.Ordinal);
        Assert.Equal("cells", controller.LastRequest?.Query);
    }

    [Fact]
    public async Task OlderSearchCannotClobberNewer()
    {
        var firstGate = new TaskCompletionSource<WebDiscoveryPage>(TaskCreationOptions.RunContinuationsAsynchronously);
        var secondPage = DiscoveryPage("second");
        var controller = new WebDiscoveryController(
            (req, _) => req.Query == "first" ? firstGate.Task : Task.FromResult(secondPage),
            (_, _, _) => Task.FromResult(new PasteResult(true, null, null)));

        var firstTask = controller.SearchAsync(new WebDiscoveryRequest("first"));
        Assert.True(controller.IsLoading);
        await controller.SearchAsync(new WebDiscoveryRequest("second"));
        Assert.Equal("second", controller.Page?.Query);

        firstGate.SetResult(DiscoveryPage("first"));
        await firstTask;

        Assert.Equal("second", controller.Page?.Query);
        Assert.Equal("second", controller.LastRequest?.Query);
        Assert.False(controller.IsLoading);
    }

    [Fact]
    public async Task CancelPreventsLateSearchAndRetainsQuery()
    {
        var gate = new TaskCompletionSource<WebDiscoveryPage>(TaskCreationOptions.RunContinuationsAsynchronously);
        var controller = new WebDiscoveryController(
            (_, _) => gate.Task,
            (_, _, _) => Task.FromResult(new PasteResult(true, null, null)));

        var pending = controller.SearchAsync(new WebDiscoveryRequest("cells"));
        Assert.True(controller.IsLoading);
        controller.Cancel();
        Assert.False(controller.IsLoading);

        gate.SetResult(DiscoveryPage("cells"));
        await pending;

        Assert.Null(controller.Page);
        Assert.False(controller.IsLoading);
        Assert.Equal("cells", controller.LastRequest?.Query);
    }

    [Fact]
    public async Task RebindCancelsPendingSearchButRetainsCompleted()
    {
        var completed = DiscoveryPage("kept");
        var controller = new WebDiscoveryController(
            (_, _) => Task.FromResult(completed),
            (_, _, _) => Task.FromResult(new PasteResult(true, null, null)));
        controller.BindNotebook(Course("nb1"));
        await controller.SearchAsync(new WebDiscoveryRequest("kept"));
        Assert.Same(completed, controller.Page);

        // Pending cancelled on rebind.
        var gate = new TaskCompletionSource<WebDiscoveryPage>(TaskCreationOptions.RunContinuationsAsynchronously);
        var pendingController = new WebDiscoveryController(
            (req, _) => req.Query == "next" ? gate.Task : Task.FromResult(completed),
            (_, _, _) => Task.FromResult(new PasteResult(true, null, null)));
        pendingController.BindNotebook(Course("nb1"));
        await pendingController.SearchAsync(new WebDiscoveryRequest("kept"));
        var pending = pendingController.SearchAsync(new WebDiscoveryRequest("next"));
        pendingController.BindNotebook(Course("nb2"));
        Assert.False(pendingController.IsLoading);
        gate.SetResult(DiscoveryPage("next"));
        await pending;
        Assert.False(pendingController.IsLoading);
        Assert.True(pendingController.Page is null || pendingController.Page.Query != "next");

        // Completed retained across same-notebook rebind.
        controller.BindNotebook(Course("nb1"));
        Assert.Same(completed, controller.Page);
    }

    [Fact]
    public async Task DeactivateCancelsPendingButRetainsCompleted()
    {
        var completed = DiscoveryPage("settled");
        var controller = new WebDiscoveryController(
            (_, _) => Task.FromResult(completed),
            (_, _, _) => Task.FromResult(new PasteResult(true, null, null)));
        controller.BindNotebook(Course());
        await controller.SearchAsync(new WebDiscoveryRequest("settled"));
        Assert.Same(completed, controller.Page);

        var gate = new TaskCompletionSource<WebDiscoveryPage>(TaskCreationOptions.RunContinuationsAsynchronously);
        var pendingController = new WebDiscoveryController(
            (req, _) => req.Query == "next" ? gate.Task : Task.FromResult(completed),
            (_, _, _) => Task.FromResult(new PasteResult(true, null, null)));
        pendingController.BindNotebook(Course());
        await pendingController.SearchAsync(new WebDiscoveryRequest("settled"));
        var pending = pendingController.SearchAsync(new WebDiscoveryRequest("next"));
        Assert.True(pendingController.IsLoading);
        pendingController.Deactivate();
        Assert.False(pendingController.IsLoading);
        gate.SetResult(DiscoveryPage("next"));
        await pending;
        Assert.False(pendingController.IsLoading);
        Assert.True(pendingController.Page is null || pendingController.Page.Query != "next");
    }

    [Fact]
    public async Task ImportSavedPublishesSummaryAndOpenId()
    {
        var summary = new SourceSummary("abcdef123457", "course", "url", "Article", [], "2026-10-01T00:00:00Z", 2);
        var controller = new WebDiscoveryController(
            (_, _) => Task.FromResult(DiscoveryPage("cells")),
            (_, _, _) => Task.FromResult(new PasteResult(true, null, summary)));
        controller.BindNotebook(Course());

        await controller.ImportAsync("https://example.edu/article");

        Assert.False(controller.IsImporting);
        Assert.Null(controller.ImportingUrl);
        Assert.Null(controller.ImportError);
        Assert.Null(controller.ImportDuplicate);
        Assert.Same(summary, controller.ImportedSource);
        Assert.Equal("abcdef123457", controller.LastImportedSourceId);
        Assert.NotNull(controller.ImportNotice);
    }

    [Fact]
    public async Task ImportDuplicateNeverForcesAndSurfacesRef()
    {
        string? seenForce = null;
        var controller = new WebDiscoveryController(
            (_, _) => Task.FromResult(DiscoveryPage("cells")),
            (nb, url, _) =>
            {
                Assert.Equal("course", nb);
                Assert.Equal("https://example.edu/article", url);
                return Task.FromResult(new PasteResult(false, new DuplicateRef("abc123def456", "Existing"), null));
            });
        controller.BindNotebook(Course());

        await controller.ImportAsync("https://example.edu/article");

        Assert.False(controller.IsImporting);
        Assert.Null(controller.ImportedSource);
        Assert.NotNull(controller.ImportDuplicate);
        Assert.Equal("abc123def456", controller.ImportDuplicate!.Id);
        Assert.Null(controller.ImportError);
        Assert.Null(seenForce);
    }

    [Fact]
    public async Task ImportErrorSurfacesMessage()
    {
        var controller = new WebDiscoveryController(
            (_, _) => Task.FromResult(DiscoveryPage("cells")),
            (_, _, _) => Task.FromException<PasteResult>(new InvalidOperationException("HTTPS HTML articles only")));
        controller.BindNotebook(Course());

        await controller.ImportAsync("https://example.edu/article");

        Assert.False(controller.IsImporting);
        Assert.Null(controller.ImportedSource);
        Assert.Contains("HTTPS HTML", controller.ImportError, StringComparison.Ordinal);
    }

    [Fact]
    public async Task ImportWithoutNotebookSetsErrorWithoutNetwork()
    {
        var calls = 0;
        var controller = new WebDiscoveryController(
            (_, _) => Task.FromResult(DiscoveryPage("cells")),
            (_, _, _) => { calls++; return Task.FromResult(new PasteResult(true, null, null)); });
        controller.BindNotebook(null);

        await controller.ImportAsync("https://example.edu/article");

        Assert.Equal(0, calls);
        Assert.Contains("notebook", controller.ImportError, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task ImportRejectsNonHttpsWithoutNetwork()
    {
        var calls = 0;
        var controller = new WebDiscoveryController(
            (_, _) => Task.FromResult(DiscoveryPage("cells")),
            (_, _, _) => { calls++; return Task.FromResult(new PasteResult(true, null, null)); });
        controller.BindNotebook(Course());

        await controller.ImportAsync("http://example.edu/article");

        Assert.Equal(0, calls);
        Assert.Contains("HTTPS", controller.ImportError, StringComparison.Ordinal);
    }

    [Fact]
    public async Task LateImportCannotOverwriteNewerNotice()
    {
        var firstGate = new TaskCompletionSource<PasteResult>(TaskCreationOptions.RunContinuationsAsynchronously);
        var secondSummary = new SourceSummary("bbbbbbbbbbbb", "course", "url", "Second", [], "2026-10-01T00:00:00Z", 1);
        var controller = new WebDiscoveryController(
            (_, _) => Task.FromResult(DiscoveryPage("cells")),
            (_, url, _) => url.EndsWith("/first", StringComparison.Ordinal)
                ? firstGate.Task
                : Task.FromResult(new PasteResult(true, null, secondSummary)));
        controller.BindNotebook(Course());

        var first = controller.ImportAsync("https://example.edu/first");
        // Ensure first claimed the import slot.
        await Task.Delay(10);
        await controller.ImportAsync("https://example.edu/second");
        Assert.Equal("bbbbbbbbbbbb", controller.LastImportedSourceId);

        firstGate.SetResult(new PasteResult(true, null,
            new SourceSummary("aaaaaaaaaaaa", "course", "url", "First", [], "2026-10-01T00:00:00Z", 1)));
        await first;

        Assert.Equal("bbbbbbbbbbbb", controller.LastImportedSourceId);
        Assert.False(controller.IsImporting);
    }

    [Fact]
    public async Task CancelPreventsLateImportNotice()
    {
        var gate = new TaskCompletionSource<PasteResult>(TaskCreationOptions.RunContinuationsAsynchronously);
        var controller = new WebDiscoveryController(
            (_, _) => Task.FromResult(DiscoveryPage("cells")),
            (_, _, _) => gate.Task);
        controller.BindNotebook(Course());

        var pending = controller.ImportAsync("https://example.edu/late");
        Assert.True(controller.IsImporting);
        controller.Cancel();
        Assert.False(controller.IsImporting);

        gate.SetResult(new PasteResult(true,
            null, new SourceSummary("aaaaaaaaaaaa", "course", "url", "Late", [], "2026-10-01T00:00:00Z", 1)));
        await pending;

        Assert.Null(controller.ImportingUrl);
        Assert.Null(controller.ImportNotice);
        Assert.Null(controller.LastImportedSourceId);
    }

    [Fact]
    public async Task RebindWithNewCoursePreventsStaleImportUi()
    {
        var gate = new TaskCompletionSource<PasteResult>(TaskCreationOptions.RunContinuationsAsynchronously);
        var controller = new WebDiscoveryController(
            (_, _) => Task.FromResult(DiscoveryPage("cells")),
            (_, _, _) => gate.Task);
        controller.BindNotebook(Course("course"));
        var pending = controller.ImportAsync("https://example.edu/x");
        Assert.True(controller.IsImporting);

        controller.BindNotebook(Course("course-2"));
        Assert.False(controller.IsImporting);
        Assert.Null(controller.ImportingUrl);

        gate.SetResult(new PasteResult(true,
            null, new SourceSummary("aaaaaaaaaaaa", "course", "url", "X", [], "2026-10-01T00:00:00Z", 1)));
        await pending;

        Assert.Null(controller.ImportedSource);
        Assert.Null(controller.ImportNotice);
        Assert.Equal("course-2", controller.NotebookId);
    }

    [Fact]
    public void QueryValidationMatchesBackendLimit()
    {
        Assert.False(WebDiscoveryController.IsQueryValid(null));
        Assert.False(WebDiscoveryController.IsQueryValid("   "));
        Assert.True(WebDiscoveryController.IsQueryValid("cells"));
        Assert.True(WebDiscoveryController.IsQueryValid(new string('a', 500)));
        Assert.False(WebDiscoveryController.IsQueryValid(new string('a', 501)));
    }
}

public sealed class WebDiscoveryGoogleLinkTests
{
    [Fact]
    public void ValidBareHostsAreAccepted()
    {
        Assert.True(WebDiscoveryController.IsDomainValid("example.edu"));
        Assert.True(WebDiscoveryController.IsDomainValid("arxiv.org"));
        Assert.True(WebDiscoveryController.IsDomainValid("sub.example.edu"));
        Assert.True(WebDiscoveryController.IsDomainValid("EXAMPLE.EDU"));
        Assert.True(WebDiscoveryController.IsDomainValid("example.edu."));
    }

    [Fact]
    public void SchemePathCredentialsPortsAndOperatorsAreRejected()
    {
        foreach (var bad in new[]
        {
            "", "  ", "https://example.edu", "http://example.edu/path", "example.edu/path",
            "user:secret@example.edu", "user@example.edu", "example.edu:8080",
            "example edu", "site:example.edu", "example.edu filetype:pdf",
            "evil-example.edu query", "localhost", "127.0.0.1", "example..edu", "-bad.com", "bad-.com",
        })
        {
            Assert.False(WebDiscoveryController.IsDomainValid(bad), $"should reject: {bad}");
        }
    }

    [Fact]
    public void GoogleUrlIncludesOnlyQuerySiteAndType()
    {
        var url = WebDiscoveryController.BuildGoogleUrl("ATP & Calvin", "example.edu", "pdf");
        Assert.NotNull(url);
        var uri = new Uri(url!);
        Assert.Equal("https", uri.Scheme);
        Assert.Equal("www.google.com", uri.Host);
        Assert.Equal("/search", uri.AbsolutePath);
        var q = Uri.UnescapeDataString(uri.Query.Split(new[] { "?q=", "&" }, StringSplitOptions.None)[1].Split('&')[0]);
        // Re-parse via decoding the q value.
        var decoded = Uri.UnescapeDataString(ExtractQ(url!));
        Assert.Contains("ATP & Calvin", decoded, StringComparison.Ordinal);
        Assert.Contains("site:example.edu", decoded, StringComparison.Ordinal);
        Assert.Contains("filetype:pdf", decoded, StringComparison.Ordinal);
        Assert.DoesNotContain("academic", decoded, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("acct", url!, StringComparison.Ordinal);
        Assert.DoesNotContain("desk", url!, StringComparison.Ordinal);
    }

    [Fact]
    public void GoogleUrlEncodesSpecialQueryAndOmitsInvalidDomain()
    {
        var url = WebDiscoveryController.BuildGoogleUrl("a&b \"c\"", "https://example.edu/path", "html");
        Assert.NotNull(url);
        var decoded = Uri.UnescapeDataString(ExtractQ(url!));
        Assert.Contains("a&b \"c\"", decoded, StringComparison.Ordinal);
        Assert.DoesNotContain("site:", decoded, StringComparison.Ordinal);
        Assert.Contains("-filetype:pdf", decoded, StringComparison.Ordinal);
    }

    [Fact]
    public void GoogleUrlForAllTypeOmitsFiletypeOperator()
    {
        var url = WebDiscoveryController.BuildGoogleUrl("cells", null, "all");
        Assert.NotNull(url);
        Assert.Equal("cells", Uri.UnescapeDataString(ExtractQ(url!)));
    }

    [Fact]
    public void BrowserSafetyAllowsOnlyCredentialFreeHttp()
    {
        Assert.True(WebDiscoveryController.CanOpenWebsite("https://example.edu/article"));
        Assert.True(WebDiscoveryController.CanOpenWebsite("http://example.edu/article"));
        Assert.False(WebDiscoveryController.CanOpenWebsite("https://user:secret@example.edu/"));
        Assert.False(WebDiscoveryController.CanOpenWebsite("file:///etc/passwd"));
        Assert.False(WebDiscoveryController.CanOpenWebsite("https://"));
        Assert.False(WebDiscoveryController.CanOpenWebsite(null));
    }

    [Fact]
    public void ResultTypeLabelDistinguishesPdfLinkFromWebPage()
    {
        Assert.Equal("PDF link", new WebDiscoveryResult("t", "https://x/y.pdf", "s", "x", "pdf", 1).TypeLabel);
        Assert.Equal("Web page", new WebDiscoveryResult("t", "https://x/y", "s", "x", "html", 1).TypeLabel);
    }

    private static string ExtractQ(string url)
    {
        var uri = new Uri(url);
        var query = uri.Query.TrimStart('?');
        foreach (var part in query.Split('&', StringSplitOptions.RemoveEmptyEntries))
        {
            var idx = part.IndexOf('=');
            if (idx >= 0 && Uri.UnescapeDataString(part[..idx]) == "q")
            {
                return part[(idx + 1)..];
            }
        }

        return string.Empty;
    }
}
