using System.Net;
using System.Text.Json;
using Notaeo;
using Xunit;

namespace Notaeo.Tests;

// Portable selected-site index regressions: transport (auth + snake_case,
// 204 delete, foreign 404) and controller lifecycle (cancel/rebind/stale,
// selection, safe errors). No WinForms; real ApiClient + controller units.
public sealed class SiteIndexTransportTests
{
    private static SiteIndexSite SampleSite(
        string id = "aaaaaaaaaaaa",
        string url = "https://example.edu/book",
        string created = "2026-10-06T00:00:00Z",
        string? indexed = "2026-10-07T00:00:00Z",
        int pages = 2,
        string notice = "complete",
        int revision = 1) => new(id, url, created, indexed, pages, notice, revision);

    private static string SiteJson(SiteIndexSite s) =>
        "{\"id\":\"" + s.Id + "\",\"url\":\"" + s.Url + "\",\"created_at\":\"" + s.CreatedAt +
        "\",\"indexed_at\":" + (s.IndexedAt is null ? "null" : "\"" + s.IndexedAt + "\"") +
        ",\"page_count\":" + s.PageCount + ",\"notice\":\"" + s.Notice + "\",\"revision\":" + s.Revision + "}";

    [Fact]
    public async Task ListSendsAuthHeadersAndDecodesSnakeCase()
    {
        string? path = null;
        string? method = null;
        string? auth = null;
        string? desk = null;
        var expected = SampleSite();
        var api = Fake.Api(req =>
        {
            path = req.RequestUri!.AbsolutePath;
            method = req.Method.Method;
            auth = req.Headers.Authorization?.ToString();
            desk = req.Headers.TryGetValues(NotaeoApi.DesktopTokenHeader, out var v) ? v.FirstOrDefault() : null;
            return Fake.Json("[" + SiteJson(expected) + "]", HttpStatusCode.OK);
        });

        var sites = await api.ListIndexSitesAsync();

        Assert.Equal("/api/web/index/sites", path);
        Assert.Equal("GET", method);
        Assert.Equal("Bearer acct-1", auth);
        Assert.Equal("desk-per-launch", desk);
        Assert.Single(sites);
        Assert.Equal("aaaaaaaaaaaa", sites[0].Id);
        Assert.Equal("https://example.edu/book", sites[0].Url);
        Assert.Equal("2026-10-06T00:00:00Z", sites[0].CreatedAt);
        Assert.Equal("2026-10-07T00:00:00Z", sites[0].IndexedAt);
        Assert.Equal(2, sites[0].PageCount);
        Assert.Equal("complete", sites[0].Notice);
        Assert.Equal(1, sites[0].Revision);
    }

    [Fact]
    public async Task ListDecodesNullIndexedAt()
    {
        var api = Fake.Api(_ => Fake.Json(
            "[{\"id\":\"bbbbbbbbbbbb\",\"url\":\"https://example.edu/other\",\"created_at\":\"2026-10-06T00:00:00Z\",\"indexed_at\":null,\"page_count\":0,\"notice\":\"complete\",\"revision\":1}]",
            HttpStatusCode.OK));
        var sites = await api.ListIndexSitesAsync();
        Assert.Single(sites);
        Assert.Null(sites[0].IndexedAt);
        Assert.Equal(0, sites[0].PageCount);
    }

    [Fact]
    public async Task AddSendsPostWithUrlBody()
    {
        string? path = null;
        string? method = null;
        string? body = null;
        string? auth = null;
        var expected = SampleSite();
        var api = Fake.Api(req =>
        {
            path = req.RequestUri!.AbsolutePath;
            method = req.Method.Method;
            auth = req.Headers.Authorization?.ToString();
            body = req.Content!.ReadAsStringAsync().Result;
            return Fake.Json(SiteJson(expected), HttpStatusCode.Created);
        });

        var site = await api.AddIndexSiteAsync("https://example.edu/book");

        Assert.Equal("/api/web/index/sites", path);
        Assert.Equal("POST", method);
        Assert.Equal("Bearer acct-1", auth);
        Assert.NotNull(body);
        using var doc = JsonDocument.Parse(body!);
        Assert.Equal("https://example.edu/book", doc.RootElement.GetProperty("url").GetString());
        Assert.Equal("aaaaaaaaaaaa", site.Id);
        Assert.Equal(2, site.PageCount);
    }

    [Fact]
    public async Task RefreshPostsToRefreshPath()
    {
        string? path = null;
        string? method = null;
        var expected = SampleSite(revision: 2, notice: "page_limit");
        var api = Fake.Api(req =>
        {
            path = req.RequestUri!.AbsolutePath;
            method = req.Method.Method;
            return Fake.Json(SiteJson(expected), HttpStatusCode.OK);
        });

        var site = await api.RefreshIndexSiteAsync("aaaaaaaaaaaa");

        Assert.Equal("/api/web/index/sites/aaaaaaaaaaaa/refresh", path);
        Assert.Equal("POST", method);
        Assert.Equal(2, site.Revision);
        Assert.Equal("page_limit", site.Notice);
    }

    [Fact]
    public async Task DeleteSendsDeleteAndAccepts204()
    {
        string? path = null;
        string? method = null;
        string? auth = null;
        string? desk = null;
        var api = Fake.Api(req =>
        {
            path = req.RequestUri!.AbsolutePath;
            method = req.Method.Method;
            auth = req.Headers.Authorization?.ToString();
            desk = req.Headers.TryGetValues(NotaeoApi.DesktopTokenHeader, out var v) ? v.FirstOrDefault() : null;
            return new HttpResponseMessage(HttpStatusCode.NoContent);
        });

        await api.DeleteIndexSiteAsync("aaaaaaaaaaaa");

        Assert.Equal("/api/web/index/sites/aaaaaaaaaaaa", path);
        Assert.Equal("DELETE", method);
        Assert.Equal("Bearer acct-1", auth);
        Assert.Equal("desk-per-launch", desk);
    }

    [Fact]
    public async Task RefreshForeignIdMapsToNotFound()
    {
        var api = Fake.Api(_ => Fake.Json("{\"detail\":\"indexed site not found\"}", HttpStatusCode.NotFound));
        var ex = await Assert.ThrowsAsync<ApiException>(() => api.RefreshIndexSiteAsync("ffffffffffff"));
        Assert.Equal(ApiErrorKind.NotFound, ex.Kind);
        Assert.Equal(404, ex.StatusCode);
    }

    [Fact]
    public async Task DeleteForeignIdMapsToNotFound()
    {
        var api = Fake.Api(_ => Fake.Json("{\"detail\":\"indexed site not found\"}", HttpStatusCode.NotFound));
        var ex = await Assert.ThrowsAsync<ApiException>(() => api.DeleteIndexSiteAsync("ffffffffffff"));
        Assert.Equal(ApiErrorKind.NotFound, ex.Kind);
    }

    [Fact]
    public async Task IndexUnauthorizedInvokesCallbackWithStaleToken()
    {
        string? seen = "unset";
        var api = new NotaeoApi(
            new HttpClient(new FakeHandler(_ => Fake.Json("{\"detail\":\"login required\"}", HttpStatusCode.Unauthorized))),
            Fake.Base,
            "desk-per-launch",
            () => "acct-1",
            t => seen = t);
        var ex = await Assert.ThrowsAsync<ApiException>(() => api.ListIndexSitesAsync());
        Assert.Equal(ApiErrorKind.Unauthorized, ex.Kind);
        Assert.Equal("acct-1", seen);
    }

    [Fact]
    public async Task AddValidationMaps()
    {
        var api = Fake.Api(_ => Fake.Json("{\"detail\":\"url must be an https educational address\"}", HttpStatusCode.UnprocessableEntity));
        var ex = await Assert.ThrowsAsync<ApiException>(() => api.AddIndexSiteAsync("https://evil.example/x"));
        Assert.Equal(ApiErrorKind.Validation, ex.Kind);
        Assert.Contains("educational", ex.Message, StringComparison.Ordinal);
    }

    [Fact]
    public async Task RefreshConflictMapsToValidation()
    {
        var api = Fake.Api(_ => Fake.Json("{\"detail\":\"refresh already running\"}", (HttpStatusCode)409));
        var ex = await Assert.ThrowsAsync<ApiException>(() => api.RefreshIndexSiteAsync("aaaaaaaaaaaa"));
        Assert.Equal(ApiErrorKind.Validation, ex.Kind);
        Assert.Equal(409, ex.StatusCode);
    }

    [Fact]
    public async Task RefreshRobotsFailureMapsToSafe502()
    {
        var api = Fake.Api(_ => Fake.Json("{\"detail\":\"refresh failed\"}", HttpStatusCode.BadGateway));
        var ex = await Assert.ThrowsAsync<ApiException>(() => api.RefreshIndexSiteAsync("aaaaaaaaaaaa"));
        Assert.Equal(ApiErrorKind.Server, ex.Kind);
        Assert.Equal(502, ex.StatusCode);
        Assert.Equal("refresh failed", ex.Message);
    }
}

public sealed class SiteIndexControllerTests
{
    private static Notebook Course(string id = "course") => new(id, "Biology", "2026-10-01T00:00:00Z");

    private static SiteIndexSite Site(
        string id,
        string url = "https://example.edu/book",
        int pages = 2,
        string? indexed = "2026-10-07T00:00:00Z",
        string notice = "complete",
        int revision = 1) => new(id, url, "2026-10-06T00:00:00Z", indexed, pages, notice, revision);

    private static SiteIndexController Controller(
        Func<CancellationToken, Task<List<SiteIndexSite>>>? list = null,
        Func<string, CancellationToken, Task<SiteIndexSite>>? add = null,
        Func<string, CancellationToken, Task<SiteIndexSite>>? refresh = null,
        Func<string, CancellationToken, Task>? delete = null)
    {
        return new SiteIndexController(
            list ?? ((_) => Task.FromResult(new List<SiteIndexSite>())),
            add ?? ((_, _) => Task.FromResult(Site("new-site-1234"))),
            refresh ?? ((id, _) => Task.FromResult(Site(id))),
            delete ?? ((_, _) => Task.CompletedTask));
    }

    [Fact]
    public async Task LoadStoresSitesAndClearsBusy()
    {
        var first = Site("aaaaaaaaaaaa");
        var second = Site("bbbbbbbbbbbb");
        var controller = Controller(list: (_) => Task.FromResult(new List<SiteIndexSite> { first, second }));
        controller.BindNotebook(Course());

        await controller.LoadAsync();

        Assert.False(controller.IsBusy);
        Assert.Null(controller.Error);
        Assert.Equal(2, controller.Sites.Count);
        Assert.Equal("aaaaaaaaaaaa", controller.Sites[0].Id);
    }

    [Fact]
    public async Task LoadErrorIsSafeAndKeepsPriorSites()
    {
        var kept = Site("aaaaaaaaaaaa");
        var controller = Controller(
            list: (_) => Task.FromResult(new List<SiteIndexSite> { kept }));
        controller.BindNotebook(Course());
        await controller.LoadAsync();
        Assert.Single(controller.Sites);

        var failing = Controller(
            list: (_) => Task.FromException<List<SiteIndexSite>>(new InvalidOperationException("index unavailable")),
            add: (_, _) => Task.FromResult(Site("x")),
            refresh: (id, _) => Task.FromResult(Site(id)),
            delete: (_, _) => Task.CompletedTask);
        // Reuse same sites via fresh controller seeded then failed load.
        var controller2 = new SiteIndexController(
            (_) => Task.FromException<List<SiteIndexSite>>(new InvalidOperationException("index unavailable")),
            (_, _) => Task.FromResult(Site("x")),
            (id, _) => Task.FromResult(Site(id)),
            (_, _) => Task.CompletedTask);
        controller2.BindNotebook(Course());
        await controller2.LoadAsync();
        Assert.False(controller2.IsBusy);
        Assert.NotNull(controller2.Error);
        Assert.Contains("index unavailable", controller2.Error, StringComparison.Ordinal);
        Assert.Empty(controller2.Sites);
    }

    [Fact]
    public async Task OlderListCannotClobberNewer()
    {
        var firstGate = new TaskCompletionSource<List<SiteIndexSite>>(TaskCreationOptions.RunContinuationsAsynchronously);
        var secondSites = new List<SiteIndexSite> { Site("bbbbbbbbbbbb") };
        var calls = 0;
        var controller = new SiteIndexController(
            (_) =>
            {
                calls++;
                return calls == 1 ? firstGate.Task : Task.FromResult(secondSites);
            },
            (_, _) => Task.FromResult(Site("x")),
            (id, _) => Task.FromResult(Site(id)),
            (_, _) => Task.CompletedTask);
        controller.BindNotebook(Course());

        var first = controller.LoadAsync();
        await controller.LoadAsync();
        Assert.Single(controller.Sites);
        Assert.Equal("bbbbbbbbbbbb", controller.Sites[0].Id);

        firstGate.SetResult(new List<SiteIndexSite> { Site("aaaaaaaaaaaa") });
        await first;

        Assert.Single(controller.Sites);
        Assert.Equal("bbbbbbbbbbbb", controller.Sites[0].Id);
        Assert.False(controller.IsBusy);
    }

    [Fact]
    public async Task CancelPreventsLateList()
    {
        var gate = new TaskCompletionSource<List<SiteIndexSite>>(TaskCreationOptions.RunContinuationsAsynchronously);
        var controller = Controller(list: (_) => gate.Task);
        controller.BindNotebook(Course());

        var pending = controller.LoadAsync();
        Assert.True(controller.IsBusy);
        controller.Cancel();
        Assert.False(controller.IsBusy);

        gate.SetResult(new List<SiteIndexSite> { Site("aaaaaaaaaaaa") });
        await pending;

        Assert.Empty(controller.Sites);
        Assert.False(controller.IsBusy);
    }

    [Fact]
    public async Task BindNullClearsSitesSelectionAndCancelsPending()
    {
        var gate = new TaskCompletionSource<List<SiteIndexSite>>(TaskCreationOptions.RunContinuationsAsynchronously);
        var controller = Controller(list: (_) => gate.Task);
        controller.BindNotebook(Course());
        var pending = controller.LoadAsync();
        Assert.True(controller.IsBusy);

        controller.BindNotebook(null);
        Assert.False(controller.IsBusy);
        Assert.Empty(controller.Sites);
        Assert.Null(controller.SelectedId);
        Assert.Null(controller.Error);
        Assert.Null(controller.Notebook);

        gate.SetResult(new List<SiteIndexSite> { Site("aaaaaaaaaaaa") });
        await pending;
        Assert.Empty(controller.Sites);
        Assert.False(controller.IsBusy);
    }

    [Fact]
    public async Task RebindDifferentNotebookRetainsSitesPerAccount()
    {
        var sites = new List<SiteIndexSite> { Site("aaaaaaaaaaaa") };
        var controller = Controller(list: (_) => Task.FromResult(sites));
        controller.BindNotebook(Course("nb1"));
        await controller.LoadAsync();
        Assert.Single(controller.Sites);
        controller.Select("aaaaaaaaaaaa");
        Assert.Equal("aaaaaaaaaaaa", controller.SelectedId);

        controller.BindNotebook(Course("nb2"));
        Assert.Single(controller.Sites);
        Assert.Equal("aaaaaaaaaaaa", controller.SelectedId);
        Assert.Equal("nb2", controller.Notebook?.Id);
    }

    [Fact]
    public async Task RebindCancelsPendingWrite()
    {
        var gate = new TaskCompletionSource<SiteIndexSite>(TaskCreationOptions.RunContinuationsAsynchronously);
        var controller = new SiteIndexController(
            (_) => Task.FromResult(new List<SiteIndexSite>()),
            (_, _) => gate.Task,
            (id, _) => Task.FromResult(Site(id)),
            (_, _) => Task.CompletedTask);
        controller.BindNotebook(Course("nb1"));
        var pending = controller.AddAsync("https://example.edu/book");
        Assert.True(controller.IsBusy);

        controller.BindNotebook(Course("nb2"));
        Assert.False(controller.IsBusy);

        gate.SetResult(Site("cccccccccccc"));
        await pending;
        Assert.Empty(controller.Sites);
        Assert.False(controller.IsBusy);
    }

    [Fact]
    public async Task AddUpsertsAndSelectsNewSite()
    {
        var existing = Site("aaaaaaaaaaaa");
        var added = Site("cccccccccccc", url: "https://example.edu/new", pages: 0, indexed: null, revision: 1);
        var controller = new SiteIndexController(
            (_) => Task.FromResult(new List<SiteIndexSite> { existing }),
            (_, _) => Task.FromResult(added),
            (id, _) => Task.FromResult(Site(id)),
            (_, _) => Task.CompletedTask);
        controller.BindNotebook(Course());
        await controller.LoadAsync();

        await controller.AddAsync("https://example.edu/new");

        Assert.False(controller.IsBusy);
        Assert.Null(controller.Error);
        Assert.Equal(2, controller.Sites.Count);
        Assert.Equal("cccccccccccc", controller.SelectedId);
    }

    [Fact]
    public async Task AddEmptyUrlSetsErrorWithoutNetwork()
    {
        var calls = 0;
        var controller = new SiteIndexController(
            (_) => { calls++; return Task.FromResult(new List<SiteIndexSite>()); },
            (url, _) => { calls++; return Task.FromResult(Site("x")); },
            (id, _) => { calls++; return Task.FromResult(Site(id)); },
            (id, _) => { calls++; return Task.CompletedTask; });
        controller.BindNotebook(Course());

        await controller.AddAsync("   ");

        Assert.Equal(0, calls);
        Assert.NotNull(controller.Error);
        Assert.False(controller.IsBusy);
    }

    [Fact]
    public async Task OlderAddCannotOverwriteNewer()
    {
        var firstGate = new TaskCompletionSource<SiteIndexSite>(TaskCreationOptions.RunContinuationsAsynchronously);
        var controller = new SiteIndexController(
            (_) => Task.FromResult(new List<SiteIndexSite>()),
            (url, _) => url.EndsWith("/first", StringComparison.Ordinal)
                ? firstGate.Task
                : Task.FromResult(Site("bbbbbbbbbbbb", url: "https://example.edu/second")),
            (id, _) => Task.FromResult(Site(id)),
            (_, _) => Task.CompletedTask);
        controller.BindNotebook(Course());

        var first = controller.AddAsync("https://example.edu/first");
        await Task.Delay(10);
        await controller.AddAsync("https://example.edu/second");
        Assert.Equal("bbbbbbbbbbbb", controller.SelectedId);

        firstGate.SetResult(Site("aaaaaaaaaaaa", url: "https://example.edu/first"));
        await first;

        Assert.Equal("bbbbbbbbbbbb", controller.SelectedId);
        Assert.False(controller.IsBusy);
    }

    [Fact]
    public async Task RefreshReplacesSiteKeepsSelection()
    {
        var original = Site("aaaaaaaaaaaa", pages: 1, revision: 1);
        var refreshed = Site("aaaaaaaaaaaa", pages: 5, indexed: "2026-10-07T12:00:00Z", notice: "page_limit", revision: 2);
        var controller = new SiteIndexController(
            (_) => Task.FromResult(new List<SiteIndexSite> { original }),
            (_, _) => Task.FromResult(Site("x")),
            (_, _) => Task.FromResult(refreshed),
            (_, _) => Task.CompletedTask);
        controller.BindNotebook(Course());
        await controller.LoadAsync();
        controller.Select("aaaaaaaaaaaa");

        await controller.RefreshAsync("aaaaaaaaaaaa");

        Assert.False(controller.IsBusy);
        Assert.Null(controller.Error);
        Assert.Single(controller.Sites);
        Assert.Equal(5, controller.Sites[0].PageCount);
        Assert.Equal(2, controller.Sites[0].Revision);
        Assert.Equal("page_limit", controller.Sites[0].Notice);
        Assert.Equal("aaaaaaaaaaaa", controller.SelectedId);
    }

    [Fact]
    public async Task FailedRefreshPreservesPriorData()
    {
        var original = Site("aaaaaaaaaaaa", pages: 3, revision: 1);
        var controller = new SiteIndexController(
            (_) => Task.FromResult(new List<SiteIndexSite> { original }),
            (_, _) => Task.FromResult(Site("x")),
            (_, _) => Task.FromException<SiteIndexSite>(new InvalidOperationException("robots disallowed")),
            (_, _) => Task.CompletedTask);
        controller.BindNotebook(Course());
        await controller.LoadAsync();
        Assert.Single(controller.Sites);

        await controller.RefreshAsync("aaaaaaaaaaaa");

        Assert.False(controller.IsBusy);
        Assert.NotNull(controller.Error);
        Assert.Contains("robots", controller.Error, StringComparison.Ordinal);
        Assert.Single(controller.Sites);
        Assert.Equal(3, controller.Sites[0].PageCount);
        Assert.Equal(1, controller.Sites[0].Revision);
    }

    [Fact]
    public async Task DeleteRemovesSiteAndClearsSelection()
    {
        var first = Site("aaaaaaaaaaaa");
        var second = Site("bbbbbbbbbbbb");
        string? deleted = null;
        var controller = new SiteIndexController(
            (_) => Task.FromResult(new List<SiteIndexSite> { first, second }),
            (_, _) => Task.FromResult(Site("x")),
            (id, _) => Task.FromResult(Site(id)),
            (id, _) => { deleted = id; return Task.CompletedTask; });
        controller.BindNotebook(Course());
        await controller.LoadAsync();
        controller.Select("aaaaaaaaaaaa");

        await controller.DeleteAsync("aaaaaaaaaaaa");

        Assert.Equal("aaaaaaaaaaaa", deleted);
        Assert.False(controller.IsBusy);
        Assert.Null(controller.Error);
        Assert.Single(controller.Sites);
        Assert.Equal("bbbbbbbbbbbb", controller.Sites[0].Id);
        Assert.Null(controller.SelectedId);
    }

    [Fact]
    public async Task DeleteOtherKeepsSelection()
    {
        var first = Site("aaaaaaaaaaaa");
        var second = Site("bbbbbbbbbbbb");
        var controller = new SiteIndexController(
            (_) => Task.FromResult(new List<SiteIndexSite> { first, second }),
            (_, _) => Task.FromResult(Site("x")),
            (id, _) => Task.FromResult(Site(id)),
            (_, _) => Task.CompletedTask);
        controller.BindNotebook(Course());
        await controller.LoadAsync();
        controller.Select("bbbbbbbbbbbb");

        await controller.DeleteAsync("aaaaaaaaaaaa");

        Assert.Single(controller.Sites);
        Assert.Equal("bbbbbbbbbbbb", controller.SelectedId);
    }

    [Fact]
    public async Task StaleDeleteCannotRemoveNewerAdd()
    {
        var gate = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        var controller = new SiteIndexController(
            (_) => Task.FromResult(new List<SiteIndexSite>()),
            (_, _) => Task.FromResult(Site("bbbbbbbbbbbb")),
            (id, _) => Task.FromResult(Site(id)),
            async (_, ct) => { await Task.Delay(50, ct).ConfigureAwait(false); });
        controller.BindNotebook(Course());

        var pendingDelete = controller.DeleteAsync("aaaaaaaaaaaa");
        await controller.AddAsync("https://example.edu/second");
        Assert.Equal("bbbbbbbbbbbb", controller.SelectedId);

        await pendingDelete;
        Assert.Single(controller.Sites);
        Assert.Equal("bbbbbbbbbbbb", controller.Sites[0].Id);
    }

    [Fact]
    public async Task ControllerErrorIsSafeMessage()
    {
        var controller = new SiteIndexController(
            (_) => Task.FromResult(new List<SiteIndexSite>()),
            (_, _) => Task.FromException<SiteIndexSite>(new InvalidOperationException("boom")),
            (id, _) => Task.FromResult(Site(id)),
            (_, _) => Task.CompletedTask);
        controller.BindNotebook(Course());

        await controller.AddAsync("https://example.edu/book");

        Assert.False(controller.IsBusy);
        Assert.NotNull(controller.Error);
        Assert.Contains("boom", controller.Error, StringComparison.Ordinal);
        Assert.Empty(controller.Sites);
    }

    [Fact]
    public void UrlValidationRequiresNonempty()
    {
        Assert.False(SiteIndexController.IsUrlValid(null));
        Assert.False(SiteIndexController.IsUrlValid("   "));
        Assert.True(SiteIndexController.IsUrlValid("https://example.edu/book"));
    }
}
