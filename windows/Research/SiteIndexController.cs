// Portable selected-site index state for the Windows native Site index tab.
// No WinForms refs so the portable net10 test project exercises the real
// generation + cancellation guards used by SiteIndexPanel.
namespace Notaeo;

internal sealed class SiteIndexController
{
    private readonly Func<CancellationToken, Task<List<SiteIndexSite>>> _listFunc;
    private readonly Func<string, CancellationToken, Task<SiteIndexSite>> _addFunc;
    private readonly Func<string, CancellationToken, Task<SiteIndexSite>> _refreshFunc;
    private readonly Func<string, CancellationToken, Task> _deleteFunc;
    private readonly object _gate = new();
    private CancellationTokenSource? _cts;
    private int _generation;

    internal SiteIndexController(
        Func<CancellationToken, Task<List<SiteIndexSite>>> listFunc,
        Func<string, CancellationToken, Task<SiteIndexSite>> addFunc,
        Func<string, CancellationToken, Task<SiteIndexSite>> refreshFunc,
        Func<string, CancellationToken, Task> deleteFunc)
    {
        _listFunc = listFunc ?? throw new ArgumentNullException(nameof(listFunc));
        _addFunc = addFunc ?? throw new ArgumentNullException(nameof(addFunc));
        _refreshFunc = refreshFunc ?? throw new ArgumentNullException(nameof(refreshFunc));
        _deleteFunc = deleteFunc ?? throw new ArgumentNullException(nameof(deleteFunc));
    }

    internal Notebook? Notebook { get; private set; }
    internal List<SiteIndexSite> Sites { get; private set; } = new();
    internal string? SelectedId { get; private set; }
    internal SiteIndexSite? SelectedSite => Sites.FirstOrDefault(s => string.Equals(s.Id, SelectedId, StringComparison.Ordinal));
    internal string? Error { get; private set; }
    internal bool IsBusy { get; private set; }
    internal int Generation => Volatile.Read(ref _generation);

    internal static bool IsUrlValid(string? url)
    {
        return !string.IsNullOrWhiteSpace(url);
    }

    internal void BindNotebook(Notebook? notebook)
    {
        CancellationTokenSource? previous;
        lock (_gate)
        {
            previous = InvalidateLocked();
            Notebook = notebook;
            if (notebook is null)
            {
                Sites = new();
                SelectedId = null;
                Error = null;
            }
        }

        CancelPrevious(previous);
    }

    internal void Cancel()
    {
        CancellationTokenSource? previous;
        lock (_gate)
        {
            previous = InvalidateLocked();
        }

        CancelPrevious(previous);
    }

    internal void Deactivate() => Cancel();

    internal void Clear()
    {
        CancellationTokenSource? previous;
        lock (_gate)
        {
            previous = InvalidateLocked();
            Sites = new();
            SelectedId = null;
            Error = null;
        }

        CancelPrevious(previous);
    }

    internal void Select(string? id)
    {
        lock (_gate)
        {
            if (string.IsNullOrWhiteSpace(id))
            {
                SelectedId = null;
                return;
            }

            var trimmed = id.Trim();
            SelectedId = Sites.Any(s => string.Equals(s.Id, trimmed, StringComparison.Ordinal))
                ? trimmed
                : null;
        }
    }

    // Caller holds the gate; each operation owns disposal of its own CTS.
    private CancellationTokenSource? InvalidateLocked()
    {
        var previous = _cts;
        _cts = null;
        _generation++;
        IsBusy = false;
        return previous;
    }

    private static void CancelPrevious(CancellationTokenSource? previous)
    {
        try { previous?.Cancel(); }
        catch (ObjectDisposedException) { }
    }

    internal async Task LoadAsync(CancellationToken callerCt = default)
    {
        if (callerCt.IsCancellationRequested)
        {
            return;
        }

        CancellationTokenSource? previous;
        CancellationTokenSource linked;
        CancellationToken token;
        int current;
        lock (_gate)
        {
            if (callerCt.IsCancellationRequested)
            {
                return;
            }

            previous = _cts;
            linked = CancellationTokenSource.CreateLinkedTokenSource(callerCt);
            token = linked.Token;
            _cts = linked;
            current = ++_generation;
            Error = null;
            IsBusy = true;
        }

        CancelPrevious(previous);

        try
        {
            var result = await _listFunc(token).ConfigureAwait(false);
            lock (_gate)
            {
                if (_generation != current || token.IsCancellationRequested)
                {
                    return;
                }

                Sites = result is not null ? new List<SiteIndexSite>(result) : new();
                if (SelectedId is not null && !Sites.Any(s => string.Equals(s.Id, SelectedId, StringComparison.Ordinal)))
                {
                    SelectedId = null;
                }

                Error = null;
            }
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception ex)
        {
            lock (_gate)
            {
                if (_generation != current || token.IsCancellationRequested)
                {
                    return;
                }

                Error = ex.Message;
            }
        }
        finally
        {
            lock (_gate)
            {
                if (_generation == current)
                {
                    IsBusy = false;
                }

                if (ReferenceEquals(_cts, linked))
                {
                    _cts = null;
                }
            }

            linked.Dispose();
        }
    }

    internal async Task AddAsync(string url, CancellationToken callerCt = default)
    {
        var trimmed = (url ?? string.Empty).Trim();
        if (!IsUrlValid(trimmed))
        {
            lock (_gate)
            {
                Error = "Enter a site URL.";
            }

            return;
        }

        if (callerCt.IsCancellationRequested)
        {
            return;
        }

        CancellationTokenSource? previous;
        CancellationTokenSource linked;
        CancellationToken token;
        int current;
        lock (_gate)
        {
            if (callerCt.IsCancellationRequested)
            {
                return;
            }

            previous = _cts;
            linked = CancellationTokenSource.CreateLinkedTokenSource(callerCt);
            token = linked.Token;
            _cts = linked;
            current = ++_generation;
            Error = null;
            IsBusy = true;
        }

        CancelPrevious(previous);

        try
        {
            var added = await _addFunc(trimmed, token).ConfigureAwait(false);
            lock (_gate)
            {
                if (_generation != current || token.IsCancellationRequested)
                {
                    return;
                }

                var next = new List<SiteIndexSite>(Sites);
                var idx = next.FindIndex(s => string.Equals(s.Id, added.Id, StringComparison.Ordinal));
                if (idx >= 0)
                {
                    next[idx] = added;
                }
                else
                {
                    next.Add(added);
                }

                Sites = next;
                SelectedId = added.Id;
                Error = null;
            }
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception ex)
        {
            lock (_gate)
            {
                if (_generation != current || token.IsCancellationRequested)
                {
                    return;
                }

                Error = ex.Message;
            }
        }
        finally
        {
            lock (_gate)
            {
                if (_generation == current)
                {
                    IsBusy = false;
                }

                if (ReferenceEquals(_cts, linked))
                {
                    _cts = null;
                }
            }

            linked.Dispose();
        }
    }

    internal async Task RefreshAsync(string id, CancellationToken callerCt = default)
    {
        var trimmed = (id ?? string.Empty).Trim();
        if (string.IsNullOrEmpty(trimmed))
        {
            lock (_gate)
            {
                Error = "Select an indexed site to refresh.";
            }

            return;
        }

        if (callerCt.IsCancellationRequested)
        {
            return;
        }

        CancellationTokenSource? previous;
        CancellationTokenSource linked;
        CancellationToken token;
        int current;
        lock (_gate)
        {
            if (callerCt.IsCancellationRequested)
            {
                return;
            }

            previous = _cts;
            linked = CancellationTokenSource.CreateLinkedTokenSource(callerCt);
            token = linked.Token;
            _cts = linked;
            current = ++_generation;
            Error = null;
            IsBusy = true;
        }

        CancelPrevious(previous);

        try
        {
            var refreshed = await _refreshFunc(trimmed, token).ConfigureAwait(false);
            lock (_gate)
            {
                if (_generation != current || token.IsCancellationRequested)
                {
                    return;
                }

                var next = new List<SiteIndexSite>(Sites);
                var idx = next.FindIndex(s => string.Equals(s.Id, refreshed.Id, StringComparison.Ordinal));
                if (idx >= 0)
                {
                    next[idx] = refreshed;
                }
                else
                {
                    // Refresh of a site missing locally still surfaces the result.
                    next.Add(refreshed);
                }

                Sites = next;
                Error = null;
            }
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception ex)
        {
            lock (_gate)
            {
                if (_generation != current || token.IsCancellationRequested)
                {
                    return;
                }

                Error = ex.Message;
            }
        }
        finally
        {
            lock (_gate)
            {
                if (_generation == current)
                {
                    IsBusy = false;
                }

                if (ReferenceEquals(_cts, linked))
                {
                    _cts = null;
                }
            }

            linked.Dispose();
        }
    }

    internal async Task DeleteAsync(string id, CancellationToken callerCt = default)
    {
        var trimmed = (id ?? string.Empty).Trim();
        if (string.IsNullOrEmpty(trimmed))
        {
            lock (_gate)
            {
                Error = "Select an indexed site to remove.";
            }

            return;
        }

        if (callerCt.IsCancellationRequested)
        {
            return;
        }

        CancellationTokenSource? previous;
        CancellationTokenSource linked;
        CancellationToken token;
        int current;
        lock (_gate)
        {
            if (callerCt.IsCancellationRequested)
            {
                return;
            }

            previous = _cts;
            linked = CancellationTokenSource.CreateLinkedTokenSource(callerCt);
            token = linked.Token;
            _cts = linked;
            current = ++_generation;
            Error = null;
            IsBusy = true;
        }

        CancelPrevious(previous);

        try
        {
            await _deleteFunc(trimmed, token).ConfigureAwait(false);
            lock (_gate)
            {
                if (_generation != current || token.IsCancellationRequested)
                {
                    return;
                }

                var next = Sites.Where(s => !string.Equals(s.Id, trimmed, StringComparison.Ordinal)).ToList();
                Sites = next;
                if (string.Equals(SelectedId, trimmed, StringComparison.Ordinal))
                {
                    SelectedId = null;
                }

                Error = null;
            }
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception ex)
        {
            lock (_gate)
            {
                if (_generation != current || token.IsCancellationRequested)
                {
                    return;
                }

                Error = ex.Message;
            }
        }
        finally
        {
            lock (_gate)
            {
                if (_generation == current)
                {
                    IsBusy = false;
                }

                if (ReferenceEquals(_cts, linked))
                {
                    _cts = null;
                }
            }

            linked.Dispose();
        }
    }
}
