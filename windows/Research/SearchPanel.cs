// Native course search: query + source-type/related filters, paged results,
// explicit empty/error/cancel states, and keyboard-accessible open-source
// actions. Mirrors macos/SearchView.swift contracts against the existing
// GET /api/notebooks/{id}/search/page route.
namespace Notaeo;

internal sealed class SearchPanel : UserControl
{
    private readonly Func<NotaeoApi?> _apiFactory;
    private readonly WorkspacePreferences _preferences;
    private readonly SearchController _controller;

    private Notebook? _notebook;

    private readonly TextBox _queryBox = new() { PlaceholderText = "Topic, question, or exact phrase", Width = 320, MaxLength = 500 };
    private readonly ComboBox _kindBox = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 180 };
    private readonly CheckBox _relatedBox = new() { Text = "Include related terms", Checked = true, AutoSize = true };
    private readonly Button _searchButton = new() { Text = "Search", AutoSize = true };
    private readonly Button _cancelButton = new() { Text = "Cancel", AutoSize = true, Visible = false };
    private readonly Button _clearButton = new() { Text = "Clear", AutoSize = true };
    private readonly ThinkingOrbControl _orb;
    private readonly Label _validationLabel = new() { AutoSize = true, ForeColor = System.Drawing.Color.Red, MaximumSize = new Size(600, 0) };
    private readonly Label _hintLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0) };
    private readonly Label _statusLabel = new() { AutoSize = true, Font = new Font(FontFamily.GenericSansSerif, 10, System.Drawing.FontStyle.Bold), MaximumSize = new Size(640, 0) };
    private readonly Label _queryEchoLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0) };
    private readonly Label _relatedEchoLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0) };
    private readonly Label _errorLabel = new() { AutoSize = true, ForeColor = System.Drawing.Color.Red, MaximumSize = new Size(600, 0) };
    private readonly Button _tryAgainButton = new() { Text = "Try again", AutoSize = true, Visible = false };
    private readonly Label _emptyLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0) };
    private readonly Button _backToFirstButton = new() { Text = "Back to first results", AutoSize = true, Visible = false };
    private readonly Button _prevButton = new() { Text = "Previous results", AutoSize = true, Visible = false };
    private readonly Button _nextButton = new() { Text = "Next results", AutoSize = true, Visible = false };
    private readonly FlowLayoutPanel _resultsHost = new()
    {
        FlowDirection = FlowDirection.TopDown,
        WrapContents = false,
        AutoSize = true,
        Dock = DockStyle.Top,
    };

    internal event Action<string,int?>? OpenSourceRequested;

    internal SearchPanel(Func<NotaeoApi?> apiFactory, WorkspacePreferences preferences)
    {
        _apiFactory = apiFactory ?? throw new ArgumentNullException(nameof(apiFactory));
        _preferences = preferences ?? throw new ArgumentNullException(nameof(preferences));
        _controller = new SearchController(SearchViaApiAsync);
        _orb = new ThinkingOrbControl(preferences) { Text = "Searching your material…", Visible = false };
        Dock = DockStyle.Fill;

        _kindBox.Items.Add("All material");
        _kindBox.Items.Add("PDF documents");
        _kindBox.Items.Add("Word documents");
        _kindBox.Items.Add("Text files");
        _kindBox.Items.Add("Markdown files");
        _kindBox.Items.Add("Pasted notes");
        _kindBox.Items.Add("Web articles");
        _kindBox.SelectedIndex = 0;

        var scroll = new Panel { Dock = DockStyle.Fill, AutoScroll = true };
        var flow = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
            AutoScroll = true,
            Padding = new Padding(10),
        };
        flow.Controls.Add(new Label { Text = "Find the passage you need", AutoSize = true, Font = new Font(FontFamily.GenericSansSerif, 12, System.Drawing.FontStyle.Bold) });
        flow.Controls.Add(new Label { Text = "Search your imported course material. Use quotes for an exact phrase.", AutoSize = true, MaximumSize = new Size(640, 0) });
        flow.Controls.Add(BuildSearchBox());
        flow.Controls.Add(_validationLabel);
        flow.Controls.Add(_orb);
        flow.Controls.Add(BuildLoadingRow());
        flow.Controls.Add(_hintLabel);
        flow.Controls.Add(_errorLabel);
        flow.Controls.Add(_tryAgainButton);
        flow.Controls.Add(_statusLabel);
        flow.Controls.Add(_queryEchoLabel);
        flow.Controls.Add(_relatedEchoLabel);
        flow.Controls.Add(_emptyLabel);
        flow.Controls.Add(_backToFirstButton);
        flow.Controls.Add(_resultsHost);
        flow.Controls.Add(BuildPagingRow());
        scroll.Controls.Add(flow);
        Controls.Add(scroll);

        _queryBox.TextChanged += (_, _) => UpdateSearchEnabled();
        _queryBox.KeyDown += async (s, e) =>
        {
            if (e.KeyCode == Keys.Enter)
            {
                e.SuppressKeyPress = true;
                e.Handled = true;
                await SubmitAsync().ConfigureAwait(true);
            }
        };
        _searchButton.Click += async (_, _) => await SubmitAsync().ConfigureAwait(true);
        _cancelButton.Click += (_, _) => { _controller.Cancel(); Render(); };
        _clearButton.Click += (_, _) =>
        {
            _queryBox.Text = string.Empty;
            _controller.Clear();
            Render();
        };
        _tryAgainButton.Click += async (_, _) => await TryAgainAsync().ConfigureAwait(true);
        _backToFirstButton.Click += async (_, _) => await PaginateAsync(0).ConfigureAwait(true);
        _prevButton.Click += async (_, _) => await PreviousAsync().ConfigureAwait(true);
        _nextButton.Click += async (_, _) => await NextAsync().ConfigureAwait(true);

        UpdateSearchEnabled();
        Render();
    }

    private GroupBox BuildSearchBox()
    {
        var box = new GroupBox { Text = "Search this notebook", AutoSize = true, Dock = DockStyle.Top, Width = 660 };
        var layout = new FlowLayoutPanel { FlowDirection = FlowDirection.TopDown, AutoSize = true, Dock = DockStyle.Fill, Padding = new Padding(8) };
        var row = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.LeftToRight, WrapContents = false };
        row.Controls.Add(_queryBox);
        row.Controls.Add(_searchButton);
        row.Controls.Add(_cancelButton);
        row.Controls.Add(_clearButton);
        var options = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.LeftToRight };
        options.Controls.Add(new Label { Text = "Sources:", AutoSize = true });
        options.Controls.Add(_kindBox);
        options.Controls.Add(_relatedBox);
        layout.Controls.Add(row);
        layout.Controls.Add(options);
        layout.Controls.Add(new Label { Text = "Related terms include supported academic aliases and clear typos. No AI key needed.", AutoSize = true, MaximumSize = new Size(600, 0) });
        box.Controls.Add(layout);
        return box;
    }

    private FlowLayoutPanel BuildLoadingRow()
    {
        var row = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.LeftToRight };
        return row;
    }

    private FlowLayoutPanel BuildPagingRow()
    {
        var row = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.LeftToRight };
        row.Controls.Add(_prevButton);
        row.Controls.Add(_nextButton);
        return row;
    }

    private Task<SearchPage> SearchViaApiAsync(string notebookId, SearchRequest request, CancellationToken ct)
    {
        var api = _apiFactory();
        if (api is null)
        {
            throw new InvalidOperationException("Backend is not ready yet.");
        }

        return api.SearchNotebookAsync(notebookId, request, ct);
    }

    internal void BindNotebook(Notebook? notebook)
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        var previousId = _notebook?.Id;
        var nextId = notebook?.Id;
        _notebook = notebook;
        _controller.BindNotebook(nextId);
        if (!string.Equals(previousId, nextId, StringComparison.Ordinal))
        {
            // New course: start fresh; same course keeps its query/results.
            _queryBox.Text = _controller.LastRequest?.Query ?? string.Empty;
            ApplyKind(_controller.LastRequest?.Kind);
            _relatedBox.Checked = _controller.LastRequest?.Related ?? true;
        }

        Render();
    }

    internal void FocusQuery()
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        try
        {
            if (IsHandleCreated && InvokeRequired)
            {
                BeginInvoke((MethodInvoker)(() =>
                {
                    if (!IsDisposed && !Disposing)
                    {
                        _queryBox.Focus();
                    }
                }));
            }
            else
            {
                _queryBox.Focus();
            }
        }
        catch (Exception ex) when (ex is InvalidOperationException or ObjectDisposedException)
        {
        }
    }

    internal void Deactivate()
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        // Leaving the pane cancels pending work but retains completed results/query.
        _controller.Deactivate();
        Render();
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing) _controller.Cancel();
        base.Dispose(disposing);
    }

    private string? SelectedKind() => _kindBox.SelectedIndex switch
    {
        1 => "pdf",
        2 => "docx",
        3 => "txt",
        4 => "md",
        5 => "paste",
        6 => "url",
        _ => null,
    };

    private void ApplyKind(string? kind) => _kindBox.SelectedIndex = kind switch
    {
        "pdf" => 1,
        "docx" => 2,
        "txt" => 3,
        "md" => 4,
        "paste" => 5,
        "url" => 6,
        _ => 0,
    };

    private void UpdateSearchEnabled()
    {
        var text = _queryBox.Text ?? string.Empty;
        if (string.IsNullOrWhiteSpace(text))
        {
            _searchButton.Enabled = false;
            _validationLabel.Text = string.Empty;
        }
        else if (text.Trim().Length > 500)
        {
            _searchButton.Enabled = false;
            _validationLabel.Text = "Use 500 characters or fewer.";
        }
        else
        {
            _searchButton.Enabled = _notebook is not null && !_controller.IsLoading;
            _validationLabel.Text = string.Empty;
        }
    }

    private async Task SubmitAsync()
    {
        var notebook = _notebook;
        if (notebook is null)
        {
            _hintLabel.Text = "Select a notebook to search.";
            return;
        }

        var trimmed = (_queryBox.Text ?? string.Empty).Trim();
        if (!SearchController.IsQueryValid(trimmed))
        {
            _validationLabel.Text = string.IsNullOrWhiteSpace(trimmed)
                ? "Enter a topic, question, or exact phrase."
                : "Use 500 characters or fewer.";
            return;
        }

        var request = new SearchRequest(trimmed, Kind: SelectedKind(), Related: _relatedBox.Checked, Offset: 0, Limit: 10);
        var capturedId = notebook.Id;
        _validationLabel.Text = string.Empty;
        try
        {
            var operation = _controller.SearchAsync(capturedId, request);
            Render();
            await operation.ConfigureAwait(true);
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
        {
            if (IsDisposed || Disposing || _notebook?.Id != capturedId)
            {
                return;
            }

            _validationLabel.Text = ex.Message;
            Render();
            return;
        }

        if (IsDisposed || Disposing || _notebook?.Id != capturedId)
        {
            return;
        }

        if (!IsHandleCreated)
        {
            return;
        }

        Render();
    }

    private async Task PaginateAsync(int offset)
    {
        var notebook = _notebook;
        if (notebook is null || _controller.LastRequest is null)
        {
            return;
        }

        var capturedId = notebook.Id;
        try
        {
            var operation = _controller.GoToOffsetAsync(offset);
            Render();
            await operation.ConfigureAwait(true);
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
        {
            if (IsDisposed || Disposing || _notebook?.Id != capturedId)
            {
                return;
            }
        }

        if (IsDisposed || Disposing || _notebook?.Id != capturedId || !IsHandleCreated)
        {
            return;
        }

        Render();
    }

    private Task NextAsync()
    {
        var last = _controller.LastRequest;
        var page = _controller.Page;
        var offset = page?.Offset ?? last?.Offset ?? 0;
        var limit = page?.Limit ?? last?.Limit ?? 10;
        return PaginateAsync(offset + limit);
    }

    private Task PreviousAsync()
    {
        var last = _controller.LastRequest;
        var page = _controller.Page;
        var offset = page?.Offset ?? last?.Offset ?? 0;
        var limit = page?.Limit ?? last?.Limit ?? 10;
        return PaginateAsync(Math.Max(0, offset - limit));
    }

    private async Task TryAgainAsync()
    {
        var notebook = _notebook;
        var last = _controller.LastRequest;
        if (notebook is null || last is null)
        {
            return;
        }

        var capturedId = notebook.Id;
        try
        {
            var operation = _controller.SearchAsync(capturedId, last);
            Render();
            await operation.ConfigureAwait(true);
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
        {
            if (IsDisposed || Disposing || _notebook?.Id != capturedId)
            {
                return;
            }
        }

        if (IsDisposed || Disposing || _notebook?.Id != capturedId || !IsHandleCreated)
        {
            return;
        }

        Render();
    }

    private void Render()
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        var loading = _controller.IsLoading;
        var page = _controller.Page;
        var error = _controller.Error;
        var last = _controller.LastRequest;

        _orb.Visible = loading;
        _cancelButton.Visible = loading;
        UpdateSearchEnabled();
        if (loading)
        {
            _searchButton.Enabled = false;
        }

        while (_resultsHost.Controls.Count > 0)
            _resultsHost.Controls[0].Dispose();
        _statusLabel.Text = string.Empty;
        _queryEchoLabel.Text = string.Empty;
        _relatedEchoLabel.Text = string.Empty;
        _emptyLabel.Text = string.Empty;
        _errorLabel.Text = string.Empty;
        _tryAgainButton.Visible = false;
        _backToFirstButton.Visible = false;
        _prevButton.Visible = false;
        _nextButton.Visible = false;
        _hintLabel.Text = string.Empty;

        if (_notebook is null)
        {
            _hintLabel.Text = "Select a notebook to search your imported material.";
            return;
        }

        if (loading)
        {
            _hintLabel.Text = string.Empty;
            return;
        }

        if (!string.IsNullOrEmpty(error))
        {
            _errorLabel.Text = error;
            _tryAgainButton.Visible = last is not null;
            return;
        }

        if (page is not null)
        {
            RenderPage(page);
            return;
        }

        if (last is not null)
        {
            // A pending search was cancelled: keep the query so Try again can resubmit.
            _emptyLabel.Text = "Search cancelled.";
            _tryAgainButton.Visible = true;
            return;
        }

        _hintLabel.Text = "Try a topic from your lecture notes, then open a result to read it in context.";
    }

    private void RenderPage(SearchPage page)
    {
        // Never truncate backend results: every hit renders with its full snippet.
        _queryEchoLabel.Text = $"Results for “{page.Query}”";
        _relatedEchoLabel.Text = page.Related ? "Related terms included" : "Keyword matches";

        if (page.Hits.Count == 0)
        {
            if (page.Offset > 0)
            {
                _emptyLabel.Text = "No more passages for this search.";
                _backToFirstButton.Visible = true;
                _prevButton.Visible = true;
                _prevButton.Enabled = true;
                _nextButton.Visible = true;
                _nextButton.Enabled = false;
            }
            else
            {
                _emptyLabel.Text = "No matching passages. Try fewer words, another source filter, or related terms.";
            }

            return;
        }

        _statusLabel.Text = $"{page.Offset + 1}–{page.Offset + page.Hits.Count} of {page.Total} passages";
        foreach (var hit in page.Hits)
        {
            _resultsHost.Controls.Add(BuildHitCard(hit));
        }

        _prevButton.Visible = true;
        _nextButton.Visible = true;
        _prevButton.Enabled = page.Offset > 0;
        _nextButton.Enabled = page.HasMore;
    }

    private Control BuildHitCard(SearchHit hit)
    {
        var card = new GroupBox { Text = hit.SourceTitle, AutoSize = true, Width = 640, Dock = DockStyle.Top };
        var layout = new FlowLayoutPanel
        {
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
            AutoSize = true,
            Dock = DockStyle.Fill,
            Padding = new Padding(6),
        };
        var snippet = new TextBox
        {
            Multiline = true,
            ReadOnly = true,
            ScrollBars = ScrollBars.Vertical,
            Height = 64,
            Width = 600,
            Text = hit.Snippet,
        };
        snippet.AccessibleName = $"Passage from {hit.SourceTitle}";
        var pages = hit.Pages.Count == 0
            ? "No page reference"
            : $"Page {string.Join(", ", hit.Pages)}";
        var meta = new Label { Text = pages, AutoSize = true, MaximumSize = new Size(600, 0) };
        var open = new Button { Text = "Open source", AutoSize = true };
        open.AccessibleName = $"Open {hit.SourceTitle} at cited page";
        var captured = hit;
        open.Click += (_, _) =>
        {
            if (IsDisposed || Disposing)
            {
                return;
            }

            int? cited = captured.Pages.Count > 0 ? captured.Pages[0] : null;
            try
            {
                OpenSourceRequested?.Invoke(captured.SourceId, cited);
            }
            catch (Exception)
            {
            }
        };
        layout.Controls.Add(snippet);
        layout.Controls.Add(meta);
        layout.Controls.Add(open);
        card.Controls.Add(layout);
        return card;
    }
}
