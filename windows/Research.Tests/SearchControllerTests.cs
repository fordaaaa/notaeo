using Notaeo;
using Xunit;

namespace Notaeo.Tests;

// Portable search-state regressions: pagination, errors, and stale guards.
// Uses an injectable async delegate so the real generation + CTS logic is
// exercised without WinForms or HTTP.
public sealed class SearchControllerTests
{
    [Fact]
    public async Task AlreadyCancelledRequestDoesNotInvokeServiceOrReplaceCompletedState()
    {
        var calls = 0;
        var saved = Page("saved", [Hit("source", "Notes", "Saved passage")], 1);
        var controller = new SearchController((_, _, _) => { calls++; return Task.FromResult(saved); });
        await controller.SearchAsync("course", new SearchRequest("saved"));
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        await controller.SearchAsync("course", new SearchRequest("cancelled"), cancellation.Token);
        Assert.Equal(1, calls);
        Assert.Same(saved, controller.Page);
        Assert.Equal("saved", controller.LastRequest?.Query);
        Assert.False(controller.IsLoading);
    }

    private static SearchHit Hit(string id, string title, string snippet, List<int>? pages = null) =>
        new(id, title, pages ?? [3], 0.9, snippet, ["mitosis"]);

    private static SearchPage Page(string query, List<SearchHit> hits, int total, int offset = 0, int limit = 10, bool hasMore = false, bool related = true) =>
        new(query, hits, total, limit, offset, hasMore, 4, related);

    [Fact]
    public async Task SearchStoresPageAndClearsLoading()
    {
        var expected = Page("cells", [Hit("s1", "Bio text", "... mitosis ...")], total: 1);
        var controller = new SearchController((_, _, _) => Task.FromResult(expected));

        Assert.False(controller.IsLoading);
        Assert.Null(controller.Page);

        await controller.SearchAsync("nb1", new SearchRequest("cells", Related: true, Offset: 0, Limit: 10));

        Assert.False(controller.IsLoading);
        Assert.Null(controller.Error);
        Assert.Equal("nb1", controller.NotebookId);
        Assert.Equal("cells", controller.LastRequest?.Query);
        Assert.Same(expected, controller.Page);
        Assert.Equal(1, controller.Page?.Total);
        Assert.Single(controller.Page!.Hits);
    }

    [Fact]
    public async Task SearchErrorSurfacesAndClearsLoading()
    {
        var controller = new SearchController((_, _, _) =>
            Task.FromException<SearchPage>(new InvalidOperationException("course unavailable")));

        await controller.SearchAsync("nb1", new SearchRequest("cells"));

        Assert.False(controller.IsLoading);
        Assert.Null(controller.Page);
        Assert.Contains("course unavailable", controller.Error, StringComparison.Ordinal);
        Assert.Equal("cells", controller.LastRequest?.Query);
    }

    [Fact]
    public async Task OlderCompletionCannotClobberNewerResultsOrLoading()
    {
        var firstGate = new TaskCompletionSource<SearchPage>(TaskCreationOptions.RunContinuationsAsynchronously);
        var secondPage = Page("second", [Hit("s2", "Second", "second snippet")], total: 1);
        var firstPage = Page("first", [Hit("s1", "First", "first snippet")], total: 1);

        var controller = new SearchController((_, req, _) =>
            req.Query == "first" ? firstGate.Task : Task.FromResult(secondPage));

        var firstTask = controller.SearchAsync("nb1", new SearchRequest("first"));
        // Let the first search claim loading state.
        Assert.True(controller.IsLoading);

        await controller.SearchAsync("nb1", new SearchRequest("second"));
        Assert.False(controller.IsLoading);
        Assert.Equal("second", controller.Page?.Query);

        // Late first completion must not replace newer results or restart the spinner.
        firstGate.SetResult(firstPage);
        await firstTask;

        Assert.Equal("second", controller.Page?.Query);
        Assert.Equal("second", controller.LastRequest?.Query);
        Assert.False(controller.IsLoading);
        Assert.Null(controller.Error);
    }

    [Fact]
    public async Task CancelPreventsLateResultAndSnapshotsGeneration()
    {
        var gate = new TaskCompletionSource<SearchPage>(TaskCreationOptions.RunContinuationsAsynchronously);
        var controller = new SearchController((_, _, _) => gate.Task);
        var before = controller.Generation;

        var pending = controller.SearchAsync("nb1", new SearchRequest("cells"));
        Assert.True(controller.IsLoading);

        controller.Cancel();
        Assert.False(controller.IsLoading);
        Assert.True(controller.Generation > before);
        var cancelledGeneration = controller.Generation;

        gate.SetResult(Page("cells", [Hit("s1", "Bio", "snippet")], total: 1));
        await pending;

        // Stale completion after Cancel cannot populate results or restart loading.
        Assert.Null(controller.Page);
        Assert.False(controller.IsLoading);
        Assert.Equal(cancelledGeneration, controller.Generation);
        // Query is retained so Try again can resubmit the same request.
        Assert.Equal("cells", controller.LastRequest?.Query);
    }

    [Fact]
    public async Task RebindInvalidatesPendingAndClearsStaleNotebook()
    {
        var gate = new TaskCompletionSource<SearchPage>(TaskCreationOptions.RunContinuationsAsynchronously);
        var controller = new SearchController((_, _, _) => gate.Task);

        var pending = controller.SearchAsync("nb1", new SearchRequest("cells"));
        Assert.True(controller.IsLoading);

        controller.BindNotebook("nb2");

        Assert.False(controller.IsLoading);
        Assert.Equal("nb2", controller.NotebookId);
        Assert.Null(controller.Page);
        Assert.Null(controller.LastRequest);

        gate.SetResult(Page("cells", [Hit("s1", "Bio", "snippet")], total: 1));
        await pending;

        Assert.Null(controller.Page);
        Assert.False(controller.IsLoading);
        Assert.Equal("nb2", controller.NotebookId);
    }

    [Fact]
    public async Task SameNotebookRebindRetainsCompletedResultsButCancelsPending()
    {
        var completed = Page("cells", [Hit("s1", "Bio", "kept snippet")], total: 1);
        var controller = new SearchController((_, _, _) => Task.FromResult(completed));
        await controller.SearchAsync("nb1", new SearchRequest("cells"));
        Assert.Equal("kept snippet", controller.Page?.Hits[0].Snippet);

        controller.BindNotebook("nb1");
        Assert.Same(completed, controller.Page);
        var gate = new TaskCompletionSource<SearchPage>(TaskCreationOptions.RunContinuationsAsynchronously);
        var pendingController = new SearchController((_, req, _) =>
            req.Query == "next" ? gate.Task : Task.FromResult(completed));
        await pendingController.SearchAsync("nb1", new SearchRequest("cells"));
        var pending = pendingController.SearchAsync("nb1", new SearchRequest("next"));
        pendingController.BindNotebook("nb1");
        Assert.False(pendingController.IsLoading);
        gate.SetResult(Page("next", [Hit("s9", "Late", "late")], total: 1));
        await pending;
        // Pending was invalidated; the completed "cells" request is no longer applied either
        // because a newer generation claimed the controller. Importantly no late page appears.
        Assert.False(pendingController.IsLoading);
        Assert.True(pendingController.Page is null || pendingController.Page.Query != "next");
    }

    [Fact]
    public async Task PaginationUsesLastRequestOffset()
    {
        var seen = new List<SearchRequest>();
        var controller = new SearchController((_, req, _) =>
        {
            seen.Add(req);
            return Task.FromResult(Page(req.Query, [], total: 25, offset: req.Offset, limit: req.Limit, hasMore: req.Offset + req.Limit < 25));
        });

        await controller.SearchAsync("nb1", new SearchRequest("cells", Related: true, Offset: 0, Limit: 10));
        await controller.NextPageAsync();
        Assert.Equal(10, controller.LastRequest?.Offset);
        await controller.NextPageAsync();
        Assert.Equal(20, controller.LastRequest?.Offset);
        await controller.PreviousPageAsync();
        Assert.Equal(10, controller.LastRequest?.Offset);
        await controller.GoToOffsetAsync(0);
        Assert.Equal(0, controller.LastRequest?.Offset);
        Assert.Equal("cells", controller.LastRequest?.Query);
        Assert.True(controller.LastRequest?.Related);
        Assert.Equal(5, seen.Count);
    }

    [Fact]
    public async Task PreservesFullBackendResultsWithoutTruncation()
    {
        var snippet = new string('x', 4000);
        var hits = Enumerable.Range(0, 10).Select(i => Hit($"s{i}", $"Title {i}", snippet + i)).ToList();
        var backend = Page("cells", hits, total: 10);
        var controller = new SearchController((_, _, _) => Task.FromResult(backend));

        await controller.SearchAsync("nb1", new SearchRequest("cells"));

        Assert.Equal(10, controller.Page?.Hits.Count);
        Assert.Equal(snippet + "0", controller.Page?.Hits[0].Snippet);
        Assert.Equal("Title 9", controller.Page?.Hits[9].SourceTitle);
    }

    [Fact]
    public void QueryValidationMatchesBackendLimit()
    {
        Assert.False(SearchController.IsQueryValid(null));
        Assert.False(SearchController.IsQueryValid("   "));
        Assert.True(SearchController.IsQueryValid("cells"));
        Assert.True(SearchController.IsQueryValid(new string('a', 500)));
        Assert.False(SearchController.IsQueryValid(new string('a', 501)));
        Assert.True(SearchController.IsQueryValid("  cells  "));
    }

    [Fact]
    public async Task ClearResetsResultsButKeepsNotebook()
    {
        var page = Page("cells", [Hit("s1", "Bio", "snippet")], total: 1);
        var controller = new SearchController((_, _, _) => Task.FromResult(page));
        await controller.SearchAsync("nb1", new SearchRequest("cells"));
        Assert.NotNull(controller.Page);

        controller.Clear();

        Assert.False(controller.IsLoading);
        Assert.Null(controller.Page);
        Assert.Null(controller.LastRequest);
        Assert.Null(controller.Error);
        Assert.Equal("nb1", controller.NotebookId);
    }
}
