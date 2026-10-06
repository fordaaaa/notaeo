// Portable search state for the Windows native Search tab.
// No WinForms refs so the portable net10 test project exercises the real
// generation + cancellation guards used by SearchPanel.
namespace Notaeo;

internal sealed class SearchController
{
    private readonly Func<string, SearchRequest, CancellationToken, Task<SearchPage>> _searchFunc;
    private readonly object _gate = new();
    private CancellationTokenSource? _cts;
    private int _generation;

    internal SearchController(Func<string, SearchRequest, CancellationToken, Task<SearchPage>> searchFunc)
    {
        _searchFunc = searchFunc ?? throw new ArgumentNullException(nameof(searchFunc));
    }

    internal string? NotebookId { get; private set; }
    internal SearchRequest? LastRequest { get; private set; }
    internal SearchPage? Page { get; private set; }
    internal string? Error { get; private set; }
    internal bool IsLoading { get; private set; }
    internal int Generation => Volatile.Read(ref _generation);

    internal static bool IsQueryValid(string? query)
    {
        if (string.IsNullOrWhiteSpace(query))
        {
            return false;
        }

        return query.Trim().Length <= 500;
    }

    internal void BindNotebook(string? notebookId)
    {
        CancellationTokenSource? previous;
        lock (_gate)
        {
            previous = InvalidatePending();
            if (!string.Equals(NotebookId, notebookId, StringComparison.Ordinal))
            {
                NotebookId = notebookId;
                LastRequest = null;
                Page = null;
                Error = null;
            }
        }
        CancelPrevious(previous);
    }

    internal void Cancel()
    {
        CancellationTokenSource? previous;
        lock (_gate) previous = InvalidatePending();
        CancelPrevious(previous);
    }

    internal void Deactivate() => Cancel();

    internal void Clear()
    {
        CancellationTokenSource? previous;
        lock (_gate)
        {
            previous = InvalidatePending();
            LastRequest = null;
            Page = null;
            Error = null;
        }
        CancelPrevious(previous);
    }

    // Caller holds the gate; each operation owns disposal of its own CTS.
    private CancellationTokenSource? InvalidatePending()
    {
        var previous = _cts;
        _cts = null;
        _generation++;
        IsLoading = false;
        return previous;
    }

    private static void CancelPrevious(CancellationTokenSource? previous)
    {
        try { previous?.Cancel(); }
        catch (ObjectDisposedException) { } // Completion may have disposed it.
    }

    internal async Task SearchAsync(string notebookId, SearchRequest request, CancellationToken callerCt = default)
    {
        if (string.IsNullOrWhiteSpace(notebookId))
            throw new ArgumentException("Notebook id must not be empty.", nameof(notebookId));
        ArgumentNullException.ThrowIfNull(request);
        if (callerCt.IsCancellationRequested) return;

        CancellationTokenSource? previous;
        CancellationTokenSource linked;
        CancellationToken token;
        int current;
        lock (_gate)
        {
            if (callerCt.IsCancellationRequested) return;
            previous = _cts;
            linked = CancellationTokenSource.CreateLinkedTokenSource(callerCt);
            token = linked.Token;
            _cts = linked;
            current = ++_generation;
            NotebookId = notebookId;
            LastRequest = request;
            Page = null;
            Error = null;
            IsLoading = true;
        }
        CancelPrevious(previous);

        try
        {
            var result = await _searchFunc(notebookId, request, token).ConfigureAwait(false);
            lock (_gate)
            {
                if (_generation != current || token.IsCancellationRequested) return;
                Page = result;
                Error = null;
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception ex)
        {
            lock (_gate)
            {
                if (_generation != current || token.IsCancellationRequested) return;
                Page = null;
                Error = ex.Message;
            }
        }
        finally
        {
            lock (_gate)
            {
                if (_generation == current) IsLoading = false;
                if (ReferenceEquals(_cts, linked)) _cts = null;
            }
            linked.Dispose();
        }
    }

    internal Task GoToOffsetAsync(int offset, CancellationToken callerCt = default)
    {
        var notebook = NotebookId;
        var last = LastRequest;
        if (notebook is null || last is null)
        {
            return Task.CompletedTask;
        }

        var next = last with { Offset = Math.Max(0, offset) };
        return SearchAsync(notebook, next, callerCt);
    }

    internal Task NextPageAsync(CancellationToken callerCt = default)
    {
        var page = Page;
        var last = LastRequest;
        var offset = page?.Offset ?? last?.Offset ?? 0;
        var limit = page?.Limit ?? last?.Limit ?? 10;
        return GoToOffsetAsync(offset + limit, callerCt);
    }

    internal Task PreviousPageAsync(CancellationToken callerCt = default)
    {
        var page = Page;
        var last = LastRequest;
        var offset = page?.Offset ?? last?.Offset ?? 0;
        var limit = page?.Limit ?? last?.Limit ?? 10;
        return GoToOffsetAsync(Math.Max(0, offset - limit), callerCt);
    }
}
