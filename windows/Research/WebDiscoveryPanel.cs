// Native public-web discovery: query external indexes with transparent
// filters, then import one HTTPS web article into the current notebook.
// Mirrors docs/WEB_DISCOVERY.md against GET /api/web/discover and the
// existing POST /api/notebooks/{id}/sources/url route (force:false).
using System.Diagnostics;

namespace Notaeo;

internal sealed class WebDiscoveryPanel : UserControl
{
    private readonly Func<NotaeoApi?> _apiFactory;
    private readonly WorkspacePreferences _preferences;
    private readonly WebDiscoveryController _controller;

    private Notebook? _notebook;

    private readonly TextBox _queryBox = new() { PlaceholderText = "Search the public web", Width = 320, MaxLength = 500 };
    private readonly ComboBox _engineBox = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 160 };
    private readonly TextBox _siteBox = new() { PlaceholderText = "Site, e.g. example.edu (optional)", Width = 220 };
    private readonly ComboBox _typeBox = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 140 };
    private readonly CheckBox _academicBox = new() { Text = "Academic sites only", AutoSize = true };
    private readonly ComboBox _recencyBox = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 140 };
    private readonly ComboBox _regionBox = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 160 };
    private readonly Button _searchButton = new() { Text = "Search", AutoSize = true };
    private readonly Button _cancelButton = new() { Text = "Cancel", AutoSize = true, Visible = false };
    private readonly Button _clearButton = new() { Text = "Clear", AutoSize = true };
    private readonly ThinkingOrbControl _searchOrb;
    private readonly ThinkingOrbControl _importOrb;
    private readonly Label _validationLabel = new() { AutoSize = true, ForeColor = System.Drawing.Color.Red, MaximumSize = new Size(640, 0) };
    private readonly Label _hintLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0) };
    private readonly Label _statusLabel = new() { AutoSize = true, Font = new Font(FontFamily.GenericSansSerif, 10, System.Drawing.FontStyle.Bold), MaximumSize = new Size(640, 0) };
    private readonly Label _effectiveLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0) };
    private readonly Label _errorLabel = new() { AutoSize = true, ForeColor = System.Drawing.Color.Red, MaximumSize = new Size(640, 0) };
    private readonly Button _tryAgainButton = new() { Text = "Try again", AutoSize = true, Visible = false };
    private readonly Label _emptyLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0) };
    private readonly Label _importStatusLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0) };
    private readonly Button _openSourceButton = new() { Text = "Open source", AutoSize = true, Visible = false };
    private readonly Label _browserErrorLabel = new() { AutoSize = true, ForeColor = System.Drawing.Color.Red, MaximumSize = new Size(640, 0) };
    private readonly Label _googleHelpLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0), Text = "Opens Google with your query, site and type only." };
    private readonly Button _openGoogleButton = new() { Text = "Open in Google", AutoSize = true };
    private readonly FlowLayoutPanel _resultsHost = new()
    {
        FlowDirection = FlowDirection.TopDown,
        WrapContents = false,
        AutoSize = true,
        Dock = DockStyle.Top,
    };

    internal event Action<string, int?>? OpenSourceRequested;

    internal WebDiscoveryPanel(Func<NotaeoApi?> apiFactory, WorkspacePreferences preferences)
    {
        _apiFactory = apiFactory ?? throw new ArgumentNullException(nameof(apiFactory));
        _preferences = preferences ?? throw new ArgumentNullException(nameof(preferences));
        _controller = new WebDiscoveryController(DiscoverViaApiAsync, ImportViaApiAsync);
        _searchOrb = new ThinkingOrbControl(preferences) { Text = "Searching the public web…", Visible = false };
        _importOrb = new ThinkingOrbControl(preferences) { Text = "Importing web article…", Visible = false };
        Dock = DockStyle.Fill;

        _engineBox.Items.Add("Automatic");
        _engineBox.Items.Add("Google");
        _engineBox.Items.Add("DuckDuckGo");
        _engineBox.Items.Add("Brave");
        _engineBox.Items.Add("Mojeek");
        _engineBox.SelectedIndex = 0;
        _engineBox.AccessibleName = "Search engine";

        _typeBox.Items.Add("All pages");
        _typeBox.Items.Add("Web pages");
        _typeBox.Items.Add("PDF links");
        _typeBox.SelectedIndex = 0;
        _typeBox.AccessibleName = "Page type";

        _recencyBox.Items.Add("Any time");
        _recencyBox.Items.Add("Past day");
        _recencyBox.Items.Add("Past week");
        _recencyBox.Items.Add("Past month");
        _recencyBox.Items.Add("Past year");
        _recencyBox.SelectedIndex = 0;
        _recencyBox.AccessibleName = "Recent period";

        _regionBox.Items.Add("US English");
        _regionBox.Items.Add("Canada English");
        _regionBox.Items.Add("UK English");
        _regionBox.Items.Add("Australia English");
        _regionBox.SelectedIndex = 0;
        _regionBox.AccessibleName = "Region";

        _queryBox.AccessibleName = "Web discovery query";
        _siteBox.AccessibleName = "Site filter";
        _academicBox.AccessibleName = "Academic sites only";
        _searchButton.AccessibleName = "Search the public web";
        _cancelButton.AccessibleName = "Cancel web search or import";
        _openGoogleButton.AccessibleName = "Open in Google with query site and type only";
        _openSourceButton.AccessibleName = "Open imported source";

        var scroll = new Panel { Dock = DockStyle.Fill, AutoScroll = true };
        var flow = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
            AutoScroll = true,
            Padding = new Padding(10),
        };
        flow.Controls.Add(new Label { Text = "Discover sources on the public web", AutoSize = true, Font = new Font(FontFamily.GenericSansSerif, 12, System.Drawing.FontStyle.Bold) });
        flow.Controls.Add(new Label { Text = "Find useful course sources on the public web.", AutoSize = true, MaximumSize = new Size(640, 0) });
        flow.Controls.Add(BuildSearchBox());
        flow.Controls.Add(_validationLabel);
        flow.Controls.Add(_searchOrb);
        flow.Controls.Add(_importOrb);
        flow.Controls.Add(_cancelButton);
        flow.Controls.Add(_hintLabel);
        flow.Controls.Add(_errorLabel);
        flow.Controls.Add(_tryAgainButton);
        flow.Controls.Add(_statusLabel);
        flow.Controls.Add(_effectiveLabel);
        flow.Controls.Add(_emptyLabel);
        flow.Controls.Add(_resultsHost);
        flow.Controls.Add(_importStatusLabel);
        flow.Controls.Add(_openSourceButton);
        flow.Controls.Add(_browserErrorLabel);
        flow.Controls.Add(_googleHelpLabel);
        flow.Controls.Add(_openGoogleButton);
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
        _openSourceButton.Click += (_, _) => OpenImportedSource();
        _openGoogleButton.Click += (_, _) => OpenGoogle();

        UpdateSearchEnabled();
        Render();
    }

    private GroupBox BuildSearchBox()
    {
        var box = new GroupBox { Text = "Discover", AutoSize = true, Dock = DockStyle.Top, Width = 660 };
        var layout = new FlowLayoutPanel { FlowDirection = FlowDirection.TopDown, AutoSize = true, Dock = DockStyle.Fill, Padding = new Padding(8) };
        var row = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.LeftToRight, WrapContents = false };
        row.Controls.Add(_queryBox);
        row.Controls.Add(_searchButton);
        row.Controls.Add(_clearButton);
        var filters = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.LeftToRight };
        filters.Controls.Add(new Label { Text = "Engine:", AutoSize = true });
        filters.Controls.Add(_engineBox);
        filters.Controls.Add(new Label { Text = "Site:", AutoSize = true });
        filters.Controls.Add(_siteBox);
        filters.Controls.Add(new Label { Text = "Type:", AutoSize = true });
        filters.Controls.Add(_typeBox);
        filters.Controls.Add(_academicBox);
        filters.Controls.Add(new Label { Text = "Recent:", AutoSize = true });
        filters.Controls.Add(_recencyBox);
        filters.Controls.Add(new Label { Text = "Region:", AutoSize = true });
        filters.Controls.Add(_regionBox);
        layout.Controls.Add(row);
        layout.Controls.Add(filters);
        layout.Controls.Add(new Label { Text = "Academic limits results to educational sites (.edu, .ac.uk, arxiv.org, ncbi.nlm.nih.gov, openstax.org, khanacademy.org, ocw.mit.edu, coursera.org). Listing here is not an endorsement.", AutoSize = true, MaximumSize = new Size(600, 0) });
        box.Controls.Add(layout);
        return box;
    }

    private Task<WebDiscoveryPage> DiscoverViaApiAsync(WebDiscoveryRequest request, CancellationToken ct)
    {
        var api = _apiFactory();
        if (api is null)
        {
            throw new InvalidOperationException("Backend is not ready yet.");
        }

        return api.DiscoverWebAsync(request, ct);
    }

    private Task<PasteResult> ImportViaApiAsync(string notebookId, string url, CancellationToken ct)
    {
        var api = _apiFactory();
        if (api is null)
        {
            throw new InvalidOperationException("Backend is not ready yet.");
        }

        // Never force a duplicate import.
        return api.AddUrlSourceAsync(notebookId, url, false, ct);
    }

    internal void BindNotebook(Notebook? notebook)
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        _notebook = notebook;
        _controller.BindNotebook(notebook);
        Render();
    }

    internal void Deactivate()
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        // Leaving the pane cancels pending work but retains completed results.
        _controller.Deactivate();
        Render();
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _controller.Cancel();
        }

        base.Dispose(disposing);
    }

    private string SelectedEngine() => _engineBox.SelectedIndex switch
    {
        1 => "google",
        2 => "duckduckgo",
        3 => "brave",
        4 => "mojeek",
        _ => "auto",
    };

    private string SelectedFileType() => _typeBox.SelectedIndex switch
    {
        1 => "html",
        2 => "pdf",
        _ => "all",
    };

    private string SelectedRecency() => _recencyBox.SelectedIndex switch
    {
        1 => "day",
        2 => "week",
        3 => "month",
        4 => "year",
        _ => "any",
    };

    private string SelectedRegion() => _regionBox.SelectedIndex switch
    {
        1 => "ca-en",
        2 => "uk-en",
        3 => "au-en",
        _ => "us-en",
    };

    private string? SiteDomain()
    {
        var trimmed = (_siteBox.Text ?? string.Empty).Trim();
        return string.IsNullOrEmpty(trimmed) ? null : trimmed;
    }

    private static string EngineLabel(string engine) => engine switch
    {
        "google" => "Google",
        "duckduckgo" => "DuckDuckGo",
        "brave" => "Brave",
        "mojeek" => "Mojeek",
        _ => "Automatic",
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
            _searchButton.Enabled = !_controller.IsLoading;
            _validationLabel.Text = string.Empty;
        }
    }

    private WebDiscoveryRequest BuildRequest(string trimmedQuery) => new(
        Query: trimmedQuery,
        Limit: 20,
        Engine: SelectedEngine(),
        Domain: SiteDomain(),
        FileType: SelectedFileType(),
        Academic: _academicBox.Checked,
        Recency: SelectedRecency(),
        Region: SelectedRegion());

    private async Task SubmitAsync()
    {
        var trimmed = (_queryBox.Text ?? string.Empty).Trim();
        if (!WebDiscoveryController.IsQueryValid(trimmed))
        {
            _validationLabel.Text = string.IsNullOrWhiteSpace(trimmed)
                ? "Enter a topic, question, or exact phrase."
                : "Use 500 characters or fewer.";
            return;
        }

        var request = BuildRequest(trimmed);
        _validationLabel.Text = string.Empty;
        _browserErrorLabel.Text = string.Empty;
        try
        {
            var operation = _controller.SearchAsync(request);
            Render();
            await operation.ConfigureAwait(true);
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
        {
            if (IsDisposed || Disposing)
            {
                return;
            }

            _validationLabel.Text = ex.Message;
            Render();
            return;
        }

        if (IsDisposed || Disposing || !IsHandleCreated)
        {
            return;
        }

        Render();
    }

    private async Task TryAgainAsync()
    {
        var last = _controller.LastRequest;
        if (last is null)
        {
            return;
        }

        _browserErrorLabel.Text = string.Empty;
        try
        {
            var operation = _controller.SearchAsync(last);
            Render();
            await operation.ConfigureAwait(true);
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
        {
            if (IsDisposed || Disposing)
            {
                return;
            }

            _validationLabel.Text = ex.Message;
            Render();
            return;
        }

        if (IsDisposed || Disposing || !IsHandleCreated)
        {
            return;
        }

        Render();
    }

    private async Task ImportResultAsync(string url, string fileType)
    {
        var notebook = _notebook;
        if (notebook is null)
        {
            _importStatusLabel.Text = "Select a notebook to import web articles.";
            return;
        }

        var capturedId = notebook.Id;
        var capturedUrl = url;
        _browserErrorLabel.Text = string.Empty;
        try
        {
            var operation = _controller.ImportAsync(capturedUrl);
            Render();
            await operation.ConfigureAwait(true);
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
        {
            if (IsDisposed || Disposing || _notebook?.Id != capturedId)
            {
                return;
            }

            _importStatusLabel.Text = ex.Message;
            Render();
            return;
        }

        if (IsDisposed || Disposing || _notebook?.Id != capturedId || !IsHandleCreated)
        {
            return;
        }

        Render();
    }

    private void OpenImportedSource()
    {
        if (IsDisposed || Disposing || _notebook is null)
        {
            return;
        }

        string? sourceId = _controller.ImportedSource?.Id ?? _controller.ImportDuplicate?.Id;
        if (string.IsNullOrEmpty(sourceId))
        {
            return;
        }

        try
        {
            OpenSourceRequested?.Invoke(sourceId, null);
        }
        catch (Exception)
        {
        }
    }

    private void OpenGoogle()
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        var last = _controller.LastRequest;
        var query = last?.Query ?? (_queryBox.Text ?? string.Empty).Trim();
        var domain = last?.Domain ?? SiteDomain();
        var fileType = last?.FileType ?? SelectedFileType();
        if (!WebDiscoveryController.IsQueryValid(query))
        {
            _validationLabel.Text = string.IsNullOrWhiteSpace(query?.Trim())
                ? "Enter a topic, question, or exact phrase."
                : "Use 500 characters or fewer.";
            return;
        }

        var googleUrl = WebDiscoveryController.BuildGoogleUrl(query.Trim(), domain, fileType);
        if (string.IsNullOrEmpty(googleUrl) || !WebDiscoveryController.CanOpenWebsite(googleUrl))
        {
            _browserErrorLabel.Text = "Could not build a safe Google link for this query.";
            return;
        }

        TryOpenWebsite(googleUrl);
    }

    private void TryOpenWebsite(string url)
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        if (!WebDiscoveryController.CanOpenWebsite(url))
        {
            _browserErrorLabel.Text = "That link is not safe to open.";
            return;
        }

        try
        {
            Process.Start(new ProcessStartInfo { FileName = url, UseShellExecute = true });
            _browserErrorLabel.Text = string.Empty;
        }
        catch (Exception ex)
        {
            if (!IsDisposed && !Disposing)
            {
                _browserErrorLabel.Text = ex.Message;
            }
        }
    }

    private void Render()
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        var loading = _controller.IsLoading;
        var importing = _controller.IsImporting;
        var page = _controller.Page;
        var error = _controller.Error;
        var last = _controller.LastRequest;

        _searchOrb.Visible = loading;
        _importOrb.Visible = importing;
        _cancelButton.Visible = loading || importing;
        UpdateSearchEnabled();
        if (loading)
        {
            _searchButton.Enabled = false;
        }

        while (_resultsHost.Controls.Count > 0)
        {
            _resultsHost.Controls[0].Dispose();
        }

        _statusLabel.Text = string.Empty;
        _effectiveLabel.Text = string.Empty;
        _emptyLabel.Text = string.Empty;
        _errorLabel.Text = string.Empty;
        _tryAgainButton.Visible = false;
        _importStatusLabel.Text = string.Empty;
        _openSourceButton.Visible = false;
        _hintLabel.Text = string.Empty;

        if (_notebook is null)
        {
            _hintLabel.Text = "Select a notebook to import web articles.";
        }

        if (loading)
        {
            return;
        }

        if (!string.IsNullOrEmpty(error))
        {
            // Engine errors use a safe retry; never silently fall back.
            _errorLabel.Text = error;
            _tryAgainButton.Visible = last is not null;
            RenderImportState();
            RenderGoogleButton();
            return;
        }

        if (page is not null)
        {
            RenderPage(page);
            RenderImportState();
            RenderGoogleButton();
            return;
        }

        if (last is not null)
        {
            _emptyLabel.Text = "Search cancelled.";
            _tryAgainButton.Visible = true;
            RenderImportState();
            RenderGoogleButton();
            return;
        }

        _hintLabel.Text += (string.IsNullOrEmpty(_hintLabel.Text) ? string.Empty : " ")
            + "Try a topic from your course, then import one article at a time.";
        RenderGoogleButton();
    }

    private void RenderPage(WebDiscoveryPage page)
    {
        var count = page.Results.Count;
        _statusLabel.Text = count == 1 ? "1 web result" : $"{count} web results";
        _effectiveLabel.Text = $"{EngineLabel(page.Engine)} · Results for “{page.Query}”";

        if (count == 0)
        {
            _emptyLabel.Text = "No web results. Try fewer words or different filters.";
            return;
        }

        foreach (var result in page.Results)
        {
            _resultsHost.Controls.Add(BuildResultCard(result));
        }
    }

    private void RenderImportState()
    {
        if (_controller.IsImporting)
        {
            _importStatusLabel.Text = $"Importing {(_controller.ImportingUrl ?? "web article")}…";
            return;
        }

        if (!string.IsNullOrEmpty(_controller.ImportError))
        {
            _importStatusLabel.Text = _controller.ImportError;
            return;
        }

        if (_controller.ImportDuplicate is not null)
        {
            _importStatusLabel.Text = $"Already saved as “{_controller.ImportDuplicate.Title}”.";
            _openSourceButton.Visible = _notebook is not null;
            _openSourceButton.Text = "Open source";
            return;
        }

        if (_controller.ImportedSource is not null)
        {
            _importStatusLabel.Text = _controller.ImportNotice ?? "Imported.";
            _openSourceButton.Visible = _notebook is not null;
            _openSourceButton.Text = "Open source";
        }
    }

    private void RenderGoogleButton()
    {
        // Explicit action only; works even when DDGS fails.
        _openGoogleButton.Enabled = _controller.LastRequest is not null || WebDiscoveryController.IsQueryValid(_queryBox.Text);
        _googleHelpLabel.Text = "Opens Google with your query, site and type only.";
    }

    private Control BuildResultCard(WebDiscoveryResult result)
    {
        var card = new GroupBox { Text = result.Title, AutoSize = true, Width = 640, Dock = DockStyle.Top };
        var layout = new FlowLayoutPanel
        {
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
            AutoSize = true,
            Dock = DockStyle.Fill,
            Padding = new Padding(6),
        };
        var meta = new Label { Text = $"{result.Domain} · {result.TypeLabel}", AutoSize = true, MaximumSize = new Size(600, 0) };
        var snippet = new TextBox
        {
            Multiline = true,
            ReadOnly = true,
            ScrollBars = ScrollBars.Vertical,
            Height = 64,
            Width = 600,
            Text = result.Snippet,
        };
        snippet.AccessibleName = $"Result from {result.Domain}";
        layout.Controls.Add(meta);
        layout.Controls.Add(snippet);

        var actions = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.LeftToRight };
        var open = new Button { Text = "Open website", AutoSize = true };
        open.AccessibleName = $"Open {result.Domain} website";
        var capturedUrl = result.Url;
        open.Click += (_, _) => TryOpenWebsite(capturedUrl);
        actions.Controls.Add(open);

        var isPdf = string.Equals(result.FileType, "pdf", StringComparison.OrdinalIgnoreCase);
        var isHttps = WebDiscoveryController.IsHttpsImportable(result.Url);
        if (isPdf)
        {
            var pdfHelp = new Label { Text = "Download the PDF, then upload it in Sources.", AutoSize = true, MaximumSize = new Size(600, 0) };
            layout.Controls.Add(pdfHelp);
        }
        else if (!isHttps)
        {
            var httpHelp = new Label { Text = "Import needs an HTTPS link.", AutoSize = true, MaximumSize = new Size(600, 0) };
            layout.Controls.Add(httpHelp);
        }
        else
        {
            var import = new Button { Text = "Import", AutoSize = true };
            import.AccessibleName = $"Import {result.Title} into current notebook";
            var captured = result;
            import.Click += async (_, _) => await ImportResultAsync(captured.Url, captured.FileType).ConfigureAwait(true);
            actions.Controls.Add(import);
        }

        layout.Controls.Add(actions);
        card.Controls.Add(layout);
        return card;
    }
}
