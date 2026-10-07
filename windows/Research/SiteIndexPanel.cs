// Native selected-site index: add starting HTTPS URLs, explicitly refresh
// (up to 5 pages, robots-respecting), show page counts/last-indexed status,
// and remove sites. Add/list/remove never fetch external pages; refresh runs
// only on explicit user action via the loopback API. No browser opens.
namespace Notaeo;

internal sealed class SiteIndexPanel : UserControl
{
    private readonly Func<NotaeoApi?> _apiFactory;
    private readonly WorkspacePreferences _preferences;
    private readonly SiteIndexController _controller;

    private Notebook? _notebook;

    private readonly TextBox _urlBox = new() { PlaceholderText = "https://example.edu/book", Width = 320, MaxLength = 2000 };
    private readonly Button _addButton = new() { Text = "Add", AutoSize = true };
    private readonly ListBox _sitesBox = new() { Width = 600, Height = 140 };
    private readonly Label _detailLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0) };
    private readonly Button _refreshButton = new() { Text = "Refresh selected", AutoSize = true };
    private readonly Button _removeButton = new() { Text = "Remove selected", AutoSize = true };
    private readonly Button _cancelButton = new() { Text = "Cancel", AutoSize = true, Visible = false };
    private readonly Button _reloadButton = new() { Text = "Reload", AutoSize = true };
    private readonly ThinkingOrbControl _orb;
    private readonly Label _validationLabel = new() { AutoSize = true, ForeColor = System.Drawing.Color.Red, MaximumSize = new Size(640, 0) };
    private readonly Label _statusLabel = new() { AutoSize = true, Font = new Font(FontFamily.GenericSansSerif, 10, System.Drawing.FontStyle.Bold), MaximumSize = new Size(640, 0) };
    private readonly Label _errorLabel = new() { AutoSize = true, ForeColor = System.Drawing.Color.Red, MaximumSize = new Size(640, 0) };
    private readonly Label _emptyLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0) };
    private readonly Label _cancelHintLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0), Text = "Cancel stops waiting; refresh may finish in backend." };
    private readonly Label _scopeLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0), Text = "Refresh fetches up to 5 pages per site, respecting robots rules." };
    private readonly Label _hintLabel = new() { AutoSize = true, MaximumSize = new Size(640, 0), Text = "Choose Indexed sites in Discover to search cached passages locally. Import fetches live article." };

    internal SiteIndexPanel(Func<NotaeoApi?> apiFactory, WorkspacePreferences preferences)
    {
        _apiFactory = apiFactory ?? throw new ArgumentNullException(nameof(apiFactory));
        _preferences = preferences ?? throw new ArgumentNullException(nameof(preferences));
        _controller = new SiteIndexController(ListViaApiAsync, AddViaApiAsync, RefreshViaApiAsync, DeleteViaApiAsync);
        _orb = new ThinkingOrbControl(preferences) { Text = "Working with site index…", Visible = false };
        Dock = DockStyle.Fill;

        _urlBox.AccessibleName = "Site URL";
        _addButton.AccessibleName = "Add site";
        _sitesBox.AccessibleName = "Indexed sites";
        _refreshButton.AccessibleName = "Refresh selected site";
        _removeButton.AccessibleName = "Remove selected site";
        _cancelButton.AccessibleName = "Cancel site index operation";
        _reloadButton.AccessibleName = "Reload indexed sites";

        var scroll = new Panel { Dock = DockStyle.Fill, AutoScroll = true };
        var flow = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
            AutoScroll = true,
            Padding = new Padding(10),
        };
        flow.Controls.Add(new Label { Text = "Site index", AutoSize = true, Font = new Font(FontFamily.GenericSansSerif, 12, System.Drawing.FontStyle.Bold) });
        flow.Controls.Add(new Label { Text = "Keep a small index of educational sites. Adding lists a starting page only; refresh explicitly crawls it.", AutoSize = true, MaximumSize = new Size(640, 0) });
        flow.Controls.Add(BuildIndexBox());
        flow.Controls.Add(_validationLabel);
        flow.Controls.Add(_orb);
        flow.Controls.Add(_cancelButton);
        flow.Controls.Add(_cancelHintLabel);
        flow.Controls.Add(_statusLabel);
        flow.Controls.Add(_sitesBox);
        flow.Controls.Add(_detailLabel);
        flow.Controls.Add(BuildActionsRow());
        flow.Controls.Add(_errorLabel);
        flow.Controls.Add(_emptyLabel);
        flow.Controls.Add(_scopeLabel);
        flow.Controls.Add(_hintLabel);
        scroll.Controls.Add(flow);
        Controls.Add(scroll);

        _urlBox.TextChanged += (_, _) => UpdateAddEnabled();
        _urlBox.KeyDown += async (s, e) =>
        {
            if (e.KeyCode == Keys.Enter)
            {
                e.SuppressKeyPress = true;
                e.Handled = true;
                await AddAsync().ConfigureAwait(true);
            }
        };
        _addButton.Click += async (_, _) => await AddAsync().ConfigureAwait(true);
        _refreshButton.Click += async (_, _) => await RefreshSelectedAsync().ConfigureAwait(true);
        _removeButton.Click += async (_, _) => await RemoveSelectedAsync().ConfigureAwait(true);
        _cancelButton.Click += (_, _) => { _controller.Cancel(); Render(); };
        _reloadButton.Click += async (_, _) => await ReloadAsync().ConfigureAwait(true);
        _sitesBox.SelectedIndexChanged += (_, _) =>
        {
            if (IsDisposed || Disposing)
            {
                return;
            }

            if (_sitesBox.SelectedItem is SiteIndexSite site)
            {
                _controller.Select(site.Id);
            }
            else
            {
                _controller.Select(null);
            }

            Render();
        };

        _cancelHintLabel.Visible = false;
        UpdateAddEnabled();
        Render();
    }

    private GroupBox BuildIndexBox()
    {
        var box = new GroupBox { Text = "Indexed sites", AutoSize = true, Dock = DockStyle.Top, Width = 660 };
        var layout = new FlowLayoutPanel { FlowDirection = FlowDirection.TopDown, AutoSize = true, Dock = DockStyle.Fill, Padding = new Padding(8) };
        var row = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.LeftToRight, WrapContents = false };
        row.Controls.Add(_urlBox);
        row.Controls.Add(_addButton);
        row.Controls.Add(_reloadButton);
        layout.Controls.Add(row);
        layout.Controls.Add(new Label { Text = "Seed an HTTPS educational URL. Adding, listing and removing never fetch external pages.", AutoSize = true, MaximumSize = new Size(600, 0) });
        box.Controls.Add(layout);
        return box;
    }

    private FlowLayoutPanel BuildActionsRow()
    {
        var row = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.LeftToRight };
        row.Controls.Add(_refreshButton);
        row.Controls.Add(_removeButton);
        return row;
    }

    private Task<List<SiteIndexSite>> ListViaApiAsync(CancellationToken ct)
    {
        var api = _apiFactory();
        if (api is null)
        {
            throw new InvalidOperationException("Backend is not ready yet.");
        }

        return api.ListIndexSitesAsync(ct);
    }

    private Task<SiteIndexSite> AddViaApiAsync(string url, CancellationToken ct)
    {
        var api = _apiFactory();
        if (api is null)
        {
            throw new InvalidOperationException("Backend is not ready yet.");
        }

        return api.AddIndexSiteAsync(url, ct);
    }

    private Task<SiteIndexSite> RefreshViaApiAsync(string id, CancellationToken ct)
    {
        var api = _apiFactory();
        if (api is null)
        {
            throw new InvalidOperationException("Backend is not ready yet.");
        }

        return api.RefreshIndexSiteAsync(id, ct);
    }

    private Task DeleteViaApiAsync(string id, CancellationToken ct)
    {
        var api = _apiFactory();
        if (api is null)
        {
            throw new InvalidOperationException("Backend is not ready yet.");
        }

        return api.DeleteIndexSiteAsync(id, ct);
    }

    internal void BindNotebook(Notebook? notebook)
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        _notebook = notebook;
        if (notebook is null) _urlBox.Clear();
        _controller.BindNotebook(notebook);
        Render();
    }

    internal void Activate()
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        // Tab selection lists cached sites only; never starts a crawl.
        _ = LoadAsync();
    }

    internal void Deactivate()
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        // Leaving the pane cancels waiting but retains the cached list.
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

    private void UpdateAddEnabled()
    {
        var text = _urlBox.Text ?? string.Empty;
        _addButton.Enabled = !string.IsNullOrWhiteSpace(text) && !_controller.IsBusy;
    }

    private async Task LoadAsync()
    {
        if (_notebook is null)
        {
            Render();
            return;
        }

        var captured = _notebook;
        try
        {
            var operation = _controller.LoadAsync();
            Render();
            await operation.ConfigureAwait(true);
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
        {
            if (IsDisposed || Disposing || !ReferenceEquals(_notebook, captured))
            {
                return;
            }
        }

        if (IsDisposed || Disposing || !ReferenceEquals(_notebook, captured) || !IsHandleCreated)
        {
            return;
        }

        Render();
    }

    private async Task ReloadAsync()
    {
        await LoadAsync().ConfigureAwait(true);
    }

    private async Task AddAsync()
    {
        var trimmed = (_urlBox.Text ?? string.Empty).Trim();
        if (!SiteIndexController.IsUrlValid(trimmed))
        {
            _validationLabel.Text = "Enter a site URL.";
            return;
        }

        _validationLabel.Text = string.Empty;
        var captured = _notebook;
        try
        {
            var operation = _controller.AddAsync(trimmed);
            Render();
            await operation.ConfigureAwait(true);
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
        {
            if (IsDisposed || Disposing || !ReferenceEquals(_notebook, captured))
            {
                return;
            }
        }

        if (IsDisposed || Disposing || !ReferenceEquals(_notebook, captured) || !IsHandleCreated)
        {
            return;
        }

        if (string.IsNullOrEmpty(_controller.Error))
        {
            _urlBox.Text = string.Empty;
        }

        Render();
    }

    private async Task RefreshSelectedAsync()
    {
        var id = _controller.SelectedId;
        if (string.IsNullOrEmpty(id))
        {
            _validationLabel.Text = "Select an indexed site to refresh.";
            return;
        }

        _validationLabel.Text = string.Empty;
        var captured = _notebook;
        try
        {
            var operation = _controller.RefreshAsync(id);
            Render();
            await operation.ConfigureAwait(true);
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
        {
            if (IsDisposed || Disposing || !ReferenceEquals(_notebook, captured))
            {
                return;
            }
        }

        if (IsDisposed || Disposing || !ReferenceEquals(_notebook, captured) || !IsHandleCreated)
        {
            return;
        }

        Render();
    }

    private async Task RemoveSelectedAsync()
    {
        var id = _controller.SelectedId;
        if (string.IsNullOrEmpty(id))
        {
            _validationLabel.Text = "Select an indexed site to remove.";
            return;
        }

        _validationLabel.Text = string.Empty;
        var captured = _notebook;
        try
        {
            var operation = _controller.DeleteAsync(id);
            Render();
            await operation.ConfigureAwait(true);
        }
        catch (Exception ex) when (ex is ArgumentException or InvalidOperationException)
        {
            if (IsDisposed || Disposing || !ReferenceEquals(_notebook, captured))
            {
                return;
            }
        }

        if (IsDisposed || Disposing || !ReferenceEquals(_notebook, captured) || !IsHandleCreated)
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

        var busy = _controller.IsBusy;
        var sites = _controller.Sites;
        var error = _controller.Error;
        var selected = _controller.SelectedSite;

        _orb.Visible = busy;
        _cancelButton.Visible = busy;
        _cancelHintLabel.Visible = busy;
        UpdateAddEnabled();
        if (busy)
        {
            _addButton.Enabled = false;
            _refreshButton.Enabled = false;
            _removeButton.Enabled = false;
            _reloadButton.Enabled = false;
        }
        else
        {
            _reloadButton.Enabled = _notebook is not null;
            _refreshButton.Enabled = selected is not null;
            _removeButton.Enabled = selected is not null;
        }

        _sitesBox.BeginUpdate();
        try
        {
            _sitesBox.Items.Clear();
            _sitesBox.DisplayMember = "Url";
            foreach (var site in sites)
            {
                _sitesBox.Items.Add(site);
            }

            if (selected is not null)
            {
                foreach (var item in _sitesBox.Items)
                {
                    if (item is SiteIndexSite s && string.Equals(s.Id, selected.Id, StringComparison.Ordinal))
                    {
                        _sitesBox.SelectedItem = item;
                        break;
                    }
                }
            }
            else
            {
                _sitesBox.ClearSelected();
            }
        }
        finally
        {
            _sitesBox.EndUpdate();
        }

        _statusLabel.Text = string.Empty;
        _detailLabel.Text = string.Empty;
        _errorLabel.Text = string.Empty;
        _emptyLabel.Text = string.Empty;

        if (_notebook is null)
        {
            _emptyLabel.Text = "Select a notebook to manage indexed sites. Signing out clears the list.";
            _statusLabel.Text = string.Empty;
            return;
        }

        if (busy)
        {
            _statusLabel.Text = "Working…";
            return;
        }

        _statusLabel.Text = sites.Count == 1 ? "1 indexed site" : $"{sites.Count} indexed sites";

        if (!string.IsNullOrEmpty(error))
        {
            _errorLabel.Text = error;
        }

        if (sites.Count == 0)
        {
            _emptyLabel.Text = string.IsNullOrEmpty(error)
                ? "No indexed sites yet. Add an HTTPS educational starting URL."
                : string.Empty;
            return;
        }

        if (selected is not null)
        {
            // Plain text only; never render backend HTML.
            var indexed = string.IsNullOrEmpty(selected.IndexedAt) ? "never" : selected.IndexedAt;
            var notice = selected.Notice switch
            {
                "complete" => "Refresh complete",
                "page_limit" => "Five-page limit reached",
                "time_limit" => "Refresh time limit reached",
                "partial" => "Some pages could not be indexed",
                _ => "Not refreshed yet"
            };
            _detailLabel.Text = $"Pages: {selected.PageCount} · Last indexed: {indexed} · {notice}";
        }
        else
        {
            _detailLabel.Text = "Select a site to see page count, last-indexed status and notice.";
        }
    }
}
