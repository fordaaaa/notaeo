// Portable web-discovery state for the Windows native Discover tab.
// No WinForms refs so the portable net10 test project exercises the real
// generation + cancellation guards used by WebDiscoveryPanel.
using System.Globalization;
using System.Net;

namespace Notaeo;

internal sealed class WebDiscoveryController
{
    private readonly Func<WebDiscoveryRequest, CancellationToken, Task<WebDiscoveryPage>> _searchFunc;
    private readonly Func<string, string, CancellationToken, Task<PasteResult>> _importFunc;
    private readonly object _gate = new();
    private CancellationTokenSource? _searchCts;
    private CancellationTokenSource? _importCts;
    private int _searchGeneration;
    private int _importGeneration;

    internal WebDiscoveryController(
        Func<WebDiscoveryRequest, CancellationToken, Task<WebDiscoveryPage>> searchFunc,
        Func<string, string, CancellationToken, Task<PasteResult>> importFunc)
    {
        _searchFunc = searchFunc ?? throw new ArgumentNullException(nameof(searchFunc));
        _importFunc = importFunc ?? throw new ArgumentNullException(nameof(importFunc));
    }

    internal Notebook? Notebook { get; private set; }
    internal string? NotebookId => Notebook?.Id;
    internal WebDiscoveryRequest? LastRequest { get; private set; }
    internal WebDiscoveryPage? Page { get; private set; }
    internal string? Error { get; private set; }
    internal bool IsLoading { get; private set; }
    internal bool IsImporting { get; private set; }
    internal string? ImportingUrl { get; private set; }
    internal string? ImportError { get; private set; }
    internal DuplicateRef? ImportDuplicate { get; private set; }
    internal SourceSummary? ImportedSource { get; private set; }
    internal string? ImportNotice { get; private set; }
    internal string? LastImportedSourceId => ImportedSource?.Id;
    internal int SearchGeneration => Volatile.Read(ref _searchGeneration);
    internal int ImportGeneration => Volatile.Read(ref _importGeneration);

    internal static bool IsQueryValid(string? query)
    {
        if (string.IsNullOrWhiteSpace(query))
        {
            return false;
        }

        return query.Trim().Length <= 500;
    }

    internal void BindNotebook(Notebook? notebook)
    {
        CancellationTokenSource? prevSearch;
        CancellationTokenSource? prevImport;
        lock (_gate)
        {
            prevSearch = InvalidateSearchLocked();
            prevImport = InvalidateImportLocked();
            Notebook = notebook;
            if (notebook is null)
            {
                LastRequest = null;
                Page = null;
                Error = null;
            }
            // Stale import UI must not survive a notebook switch; public
            // search results are retained.
            ImportError = null;
            ImportDuplicate = null;
            ImportedSource = null;
            ImportNotice = null;
        }

        CancelPrevious(prevSearch);
        CancelPrevious(prevImport);
    }

    internal void Cancel()
    {
        CancellationTokenSource? prevSearch;
        CancellationTokenSource? prevImport;
        lock (_gate)
        {
            prevSearch = InvalidateSearchLocked();
            prevImport = InvalidateImportLocked();
        }

        CancelPrevious(prevSearch);
        CancelPrevious(prevImport);
    }

    internal void Deactivate() => Cancel();

    internal void Clear()
    {
        CancellationTokenSource? prevSearch;
        CancellationTokenSource? prevImport;
        lock (_gate)
        {
            prevSearch = InvalidateSearchLocked();
            prevImport = InvalidateImportLocked();
            LastRequest = null;
            Page = null;
            Error = null;
            ImportError = null;
            ImportDuplicate = null;
            ImportedSource = null;
            ImportNotice = null;
        }

        CancelPrevious(prevSearch);
        CancelPrevious(prevImport);
    }

    // Caller holds the gate; each operation owns disposal of its own CTS.
    private CancellationTokenSource? InvalidateSearchLocked()
    {
        var previous = _searchCts;
        _searchCts = null;
        _searchGeneration++;
        IsLoading = false;
        return previous;
    }

    private CancellationTokenSource? InvalidateImportLocked()
    {
        var previous = _importCts;
        _importCts = null;
        _importGeneration++;
        IsImporting = false;
        ImportingUrl = null;
        return previous;
    }

    private static void CancelPrevious(CancellationTokenSource? previous)
    {
        try { previous?.Cancel(); }
        catch (ObjectDisposedException) { }
    }

    internal async Task SearchAsync(WebDiscoveryRequest request, CancellationToken callerCt = default)
    {
        ArgumentNullException.ThrowIfNull(request);
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

            previous = _searchCts;
            linked = CancellationTokenSource.CreateLinkedTokenSource(callerCt);
            token = linked.Token;
            _searchCts = linked;
            current = ++_searchGeneration;
            LastRequest = request;
            Page = null;
            Error = null;
            IsLoading = true;
        }

        CancelPrevious(previous);

        try
        {
            var result = await _searchFunc(request, token).ConfigureAwait(false);
            lock (_gate)
            {
                if (_searchGeneration != current || token.IsCancellationRequested)
                {
                    return;
                }

                Page = result;
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
                if (_searchGeneration != current || token.IsCancellationRequested)
                {
                    return;
                }

                Page = null;
                Error = ex.Message;
            }
        }
        finally
        {
            lock (_gate)
            {
                if (_searchGeneration == current)
                {
                    IsLoading = false;
                }

                if (ReferenceEquals(_searchCts, linked))
                {
                    _searchCts = null;
                }
            }

            linked.Dispose();
        }
    }

    internal async Task ImportAsync(string url, CancellationToken callerCt = default)
    {
        var trimmed = (url ?? string.Empty).Trim();
        string? capturedNotebookId;
        lock (_gate)
        {
            capturedNotebookId = Notebook?.Id;
        }

        if (string.IsNullOrEmpty(capturedNotebookId))
        {
            lock (_gate)
            {
                ImportError = "Select a notebook to import.";
                ImportDuplicate = null;
                ImportedSource = null;
                ImportNotice = null;
            }

            return;
        }

        if (!IsHttpsImportable(trimmed))
        {
            lock (_gate)
            {
                // Panel shows the HTTPS/PDF guidance; keep a safe message here too.
                ImportError = "Import needs an HTTPS web article link.";
                ImportDuplicate = null;
                ImportedSource = null;
                ImportNotice = null;
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

            // A newer notebook binding must invalidate this import.
            if (!string.Equals(Notebook?.Id, capturedNotebookId, StringComparison.Ordinal))
            {
                return;
            }

            previous = _importCts;
            linked = CancellationTokenSource.CreateLinkedTokenSource(callerCt);
            token = linked.Token;
            _importCts = linked;
            current = ++_importGeneration;
            ImportingUrl = trimmed;
            IsImporting = true;
            ImportError = null;
            ImportDuplicate = null;
            ImportedSource = null;
            ImportNotice = null;
        }

        CancelPrevious(previous);

        try
        {
            var result = await _importFunc(capturedNotebookId, trimmed, token).ConfigureAwait(false);
            lock (_gate)
            {
                if (_importGeneration != current || token.IsCancellationRequested)
                {
                    return;
                }

                if (!string.Equals(Notebook?.Id, capturedNotebookId, StringComparison.Ordinal))
                {
                    return;
                }

                if (result.Saved)
                {
                    ImportedSource = result.Summary;
                    ImportDuplicate = null;
                    ImportError = null;
                    ImportNotice = result.Summary is not null
                        ? $"Imported “{result.Summary.Title}”."
                        : "Imported.";
                }
                else if (result.DuplicateOf is not null)
                {
                    ImportDuplicate = result.DuplicateOf;
                    ImportedSource = null;
                    ImportError = null;
                    ImportNotice = null;
                }
                else
                {
                    ImportedSource = null;
                    ImportDuplicate = null;
                    ImportError = "Import did not save.";
                    ImportNotice = null;
                }
            }
        }
        catch (OperationCanceledException)
        {
        }
        catch (Exception ex)
        {
            lock (_gate)
            {
                if (_importGeneration != current || token.IsCancellationRequested)
                {
                    return;
                }

                if (!string.Equals(Notebook?.Id, capturedNotebookId, StringComparison.Ordinal))
                {
                    return;
                }

                ImportedSource = null;
                ImportDuplicate = null;
                ImportError = ex.Message;
                ImportNotice = null;
            }
        }
        finally
        {
            lock (_gate)
            {
                if (_importGeneration == current)
                {
                    IsImporting = false;
                    ImportingUrl = null;
                }

                if (ReferenceEquals(_importCts, linked))
                {
                    _importCts = null;
                }
            }

            linked.Dispose();
        }
    }

    // ---------- Google link + browser safety (portable, no WinForms) ----------

    internal static bool IsDomainValid(string? domain) => TryNormalizeDomain(domain, out _);

    internal static bool TryNormalizeDomain(string? domain, out string? normalized)
    {
        normalized = null;
        if (string.IsNullOrWhiteSpace(domain))
        {
            return false;
        }

        var trimmed = domain.Trim();
        // Reject URL components, credentials, ports, and operators.
        if (trimmed.Contains("://", StringComparison.Ordinal)
            || trimmed.Contains('/')
            || trimmed.Contains('?')
            || trimmed.Contains('#')
            || trimmed.Contains('@')
            || trimmed.Contains(':')
            || trimmed.Contains(' ')
            || trimmed.Contains('\t'))
        {
            return false;
        }

        trimmed = trimmed.TrimEnd('.');
        if (string.IsNullOrWhiteSpace(trimmed))
        {
            return false;
        }

        var lower = trimmed.ToLowerInvariant();
        if (lower == "localhost")
        {
            return false;
        }

        if (IPAddress.TryParse(lower, out _))
        {
            return false;
        }

        string ascii;
        try
        {
            ascii = new IdnMapping().GetAscii(lower);
        }
        catch (ArgumentException)
        {
            return false;
        }

        if (ascii.Length == 0 || ascii.Length > 253)
        {
            return false;
        }

        var labels = ascii.Split('.');
        foreach (var label in labels)
        {
            if (label.Length == 0 || label.Length > 63)
            {
                return false;
            }

            if (label.StartsWith('-') || label.EndsWith('-'))
            {
                return false;
            }

            foreach (var c in label)
            {
                var ok = (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-';
                if (!ok)
                {
                    return false;
                }
            }
        }

        normalized = ascii;
        return true;
    }

    internal static string? BuildGoogleUrl(string query, string? domain, string fileType)
    {
        var trimmed = (query ?? string.Empty).Trim();
        if (trimmed.Length == 0 || trimmed.Length > 500)
        {
            return null;
        }

        var parts = trimmed;
        if (TryNormalizeDomain(domain, out var normalized) && !string.IsNullOrEmpty(normalized))
        {
            parts += $" site:{normalized}";
        }

        var ft = (fileType ?? "all").Trim().ToLowerInvariant();
        if (ft == "pdf")
        {
            parts += " filetype:pdf";
        }
        else if (ft == "html")
        {
            parts += " -filetype:pdf";
        }

        return "https://www.google.com/search?q=" + Uri.EscapeDataString(parts);
    }

    internal static bool CanOpenWebsite(string? url)
    {
        if (string.IsNullOrWhiteSpace(url))
        {
            return false;
        }

        if (!Uri.TryCreate(url.Trim(), UriKind.Absolute, out var uri))
        {
            return false;
        }

        if (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps)
        {
            return false;
        }

        if (string.IsNullOrEmpty(uri.Host))
        {
            return false;
        }

        if (!string.IsNullOrEmpty(uri.UserInfo))
        {
            return false;
        }

        return true;
    }

    internal static bool IsHttpsImportable(string? url)
    {
        if (string.IsNullOrWhiteSpace(url))
        {
            return false;
        }

        if (!Uri.TryCreate(url.Trim(), UriKind.Absolute, out var uri))
        {
            return false;
        }

        if (uri.Scheme != Uri.UriSchemeHttps)
        {
            return false;
        }

        if (string.IsNullOrEmpty(uri.Host))
        {
            return false;
        }

        if (!string.IsNullOrEmpty(uri.UserInfo))
        {
            return false;
        }

        return true;
    }
}
