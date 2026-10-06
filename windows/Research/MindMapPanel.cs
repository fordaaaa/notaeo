// Native course mind map: notebook → source branches → concept leaves.
//
// Keyless terms extracted from the notebook's own imported material; the UI
// never implies AI inference or semantic relationships. Backed by the
// authenticated /mindmap + /mindmap/export routes. Canvas (GDI+) plus a
// readable TreeView outline alternative; every concept/source action opens
// its actual source and cited page via OpenSourceRequested.
namespace Notaeo;

internal sealed class MindMapPanel : UserControl
{
    private readonly Func<NotaeoApi?> _apiFactory;
    private readonly WorkspacePreferences _preferences;

    private Notebook? _notebook;
    private MindMapNode? _root;
    private readonly HashSet<string> _collapsed = new(StringComparer.Ordinal);
    private float _zoom = 1.0f;
    private int _generation;
    private CancellationTokenSource? _loadCts;
    private CancellationTokenSource? _exportCts;
    private bool _loading;
    private bool _exporting;
    private bool _syncingOutline;

    private MindMapLayoutResult? _layout;

    private readonly Label _titleLabel = new()
    {
        Text = "Course mind map",
        AutoSize = true,
        Font = new Font(FontFamily.GenericSansSerif, 12, System.Drawing.FontStyle.Bold),
    };
    private readonly Label _subtitleLabel = new()
    {
        Text = "Each source branches into its key concepts. Open any citation to read it in context.",
        AutoSize = true,
        MaximumSize = new Size(700, 0),
    };
    private readonly Label _keylessLabel = new()
    {
        Text = "Built from your course material. No AI key needed.",
        AutoSize = true,
        MaximumSize = new Size(700, 0),
    };
    private readonly Button _refreshButton = new() { Text = "Refresh map", AutoSize = true };
    private readonly Button _exportButton = new() { Text = "Export Markdown…", AutoSize = true };
    private readonly Button _cancelButton = new() { Text = "Cancel", AutoSize = true, Visible = false };
    private readonly Button _collapseAllButton = new() { Text = "Collapse all", AutoSize = true };
    private readonly Button _expandAllButton = new() { Text = "Expand all", AutoSize = true };
    private readonly Button _zoomOutButton = new() { Text = "−", AccessibleName = "Zoom out", AutoSize = true, Width = 36 };
    private readonly Button _zoomInButton = new() { Text = "+", AccessibleName = "Zoom in", AutoSize = true, Width = 36 };
    private readonly Label _zoomLabel = new() { Text = "100%", AutoSize = true };
    private readonly Label _countsLabel = new() { AutoSize = true, MaximumSize = new Size(700, 0) };
    private readonly ThinkingOrbControl _orb;
    private readonly TabControl _tabs = new() { Dock = DockStyle.Fill };
    private readonly TabPage _mapPage = new("Map");
    private readonly TabPage _outlinePage = new("Outline");
    private readonly Panel _mapScroll = new() { Dock = DockStyle.Fill, AutoScroll = true };
    private readonly MindMapCanvas _canvas;
    private readonly Label _mapHint = new()
    {
        Text = "Scroll to explore. Use Outline for a compact reading view.",
        Dock = DockStyle.Bottom,
        AutoSize = true,
    };
    private readonly TreeView _outline = new() { Dock = DockStyle.Fill, HideSelection = false };
    private readonly Button _openSelectedButton = new() { Text = "Open selected citation", AutoSize = true };
    private readonly Label _errorLabel = new() { AutoSize = true, ForeColor = System.Drawing.Color.Red, MaximumSize = new Size(700, 0) };
    private readonly Label _noticeLabel = new() { AutoSize = true, MaximumSize = new Size(700, 0) };

    internal event Action<string, int?>? OpenSourceRequested;

    internal MindMapPanel(Func<NotaeoApi?> apiFactory, WorkspacePreferences preferences)
    {
        _apiFactory = apiFactory ?? throw new ArgumentNullException(nameof(apiFactory));
        _preferences = preferences ?? throw new ArgumentNullException(nameof(preferences));
        Dock = DockStyle.Fill;

        _orb = new ThinkingOrbControl(_preferences)
        {
            Text = "Mapping your sources…",
            Visible = false,
            AutoSize = false,
            Width = 320,
            Height = 42,
        };
        _canvas = new MindMapCanvas(ToggleBranch, RequestOpen);

        var header = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
            AutoSize = true,
            Padding = new Padding(10),
        };
        header.Controls.Add(_titleLabel);
        header.Controls.Add(_subtitleLabel);
        header.Controls.Add(_keylessLabel);

        var toolbar = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            FlowDirection = FlowDirection.LeftToRight,
            WrapContents = true,
            AutoSize = true,
            Padding = new Padding(10),
        };
        toolbar.Controls.Add(_refreshButton);
        toolbar.Controls.Add(_exportButton);
        toolbar.Controls.Add(_cancelButton);
        toolbar.Controls.Add(_collapseAllButton);
        toolbar.Controls.Add(_expandAllButton);
        toolbar.Controls.Add(_zoomOutButton);
        toolbar.Controls.Add(_zoomLabel);
        toolbar.Controls.Add(_zoomInButton);
        toolbar.Controls.Add(_orb);
        toolbar.Controls.Add(_countsLabel);

        _mapPage.Controls.Add(_mapScroll);
        _mapPage.Controls.Add(_mapHint);
        _mapScroll.Controls.Add(_canvas);

        var outlineBottom = new FlowLayoutPanel
        {
            Dock = DockStyle.Bottom,
            FlowDirection = FlowDirection.LeftToRight,
            AutoSize = true,
            Padding = new Padding(8),
        };
        outlineBottom.Controls.Add(_openSelectedButton);
        outlineBottom.Controls.Add(new Label
        {
            Text = "Enter opens the selected citation.",
            AutoSize = true,
        });
        _outlinePage.Controls.Add(_outline);
        _outlinePage.Controls.Add(outlineBottom);

        _tabs.TabPages.Add(_mapPage);
        _tabs.TabPages.Add(_outlinePage);

        var status = new FlowLayoutPanel
        {
            Dock = DockStyle.Bottom,
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
            AutoSize = true,
            Padding = new Padding(10),
        };
        status.Controls.Add(_errorLabel);
        status.Controls.Add(_noticeLabel);

        Controls.Add(_tabs);
        Controls.Add(toolbar);
        Controls.Add(header);
        Controls.Add(status);

        _outline.ShowNodeToolTips = true;
        _outline.AccessibleName = "Mind map outline";
        _outline.AccessibleDescription = "Readable outline of sources and key terms. Press Enter to open the selected citation.";
        _openSelectedButton.AccessibleName = "Open selected citation";
        _refreshButton.AccessibleName = "Refresh map";
        _exportButton.AccessibleName = "Export mind map as Markdown";
        _cancelButton.AccessibleName = "Cancel pending mind map work";
        _canvas.AccessibleName = "Course mind map graph. Use the Outline tab for keyboard access.";
        _canvas.AccessibleRole = AccessibleRole.Graphic;
        _zoomLabel.AccessibleName = "Map zoom 100 percent";

        _refreshButton.Click += (_, _) => _ = LoadAsync();
        _exportButton.Click += (_, _) => _ = ExportAsync();
        _cancelButton.Click += (_, _) => CancelPending();
        _collapseAllButton.Click += (_, _) => CollapseAll();
        _expandAllButton.Click += (_, _) => ExpandAll();
        _zoomOutButton.Click += (_, _) => SetZoom(_zoom - 0.15f);
        _zoomInButton.Click += (_, _) => SetZoom(_zoom + 0.15f);
        _openSelectedButton.Click += (_, _) => OpenSelectedOutline();
        _outline.DoubleClick += (_, _) => OpenSelectedOutline();
        _outline.KeyDown += (_, e) =>
        {
            if (e.KeyCode is Keys.Enter or Keys.Space)
            {
                e.Handled = true;
                e.SuppressKeyPress = true;
                OpenSelectedOutline();
            }
        };
        _outline.AfterCollapse += (_, e) => SyncCollapseFromOutline(e.Node, collapsed: true);
        _outline.AfterExpand += (_, e) => SyncCollapseFromOutline(e.Node, collapsed: false);

        UpdateButtons();
        UpdateEmptyState();
    }

    // ---------- lifecycle (sync reset / activate / deactivate) ----------

    internal void BindNotebook(Notebook? notebook)
    {
        CancelPending();
        _generation++;
        _notebook = notebook;
        _root = null;
        _layout = null;
        _collapsed.Clear();
        _loading = false;
        _exporting = false;
        _errorLabel.Text = string.Empty;
        _noticeLabel.Text = string.Empty;
        _countsLabel.Text = string.Empty;
        if (IsDisposed || Disposing)
        {
            return;
        }

        _canvas.SetLayout(null, _zoom);
        RebuildOutline();
        UpdateButtons();
        UpdateEmptyState();
    }

    internal void Activate()
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        if (_notebook is null)
        {
            UpdateEmptyState();
            return;
        }

        if (_root is not null)
        {
            UpdateMapViews();
            return;
        }

        if (_loading)
        {
            return;
        }

        _ = LoadAsync();
    }

    internal void Deactivate()
    {
        // Invalidate pending load/export (including late dialogs + writes)
        // while retaining the current map when the course is unchanged.
        _generation++;
        CancelPending();
        _loading = false;
        _exporting = false;
        if (IsDisposed || Disposing)
        {
            return;
        }

        try
        {
            if (IsHandleCreated)
            {
                _orb.Visible = false;
                _cancelButton.Visible = false;
                UpdateButtons();
            }
            else
            {
                _orb.Visible = false;
                _cancelButton.Visible = false;
            }
        }
        catch (Exception ex) when (ex is InvalidOperationException or ObjectDisposedException)
        {
        }
    }

    private void CancelPending()
    {
        try { _loadCts?.Cancel(); } catch (Exception) { }
        try { _exportCts?.Cancel(); } catch (Exception) { }
        try { _loadCts?.Dispose(); } catch (Exception) { }
        try { _exportCts?.Dispose(); } catch (Exception) { }
        _loadCts = null;
        _exportCts = null;
    }

    // ---------- loading ----------

    private async Task LoadAsync()
    {
        var api = _apiFactory();
        if (api is null || _notebook is null)
        {
            if (!IsDisposed && !Disposing)
            {
                _errorLabel.Text = api is null ? "Backend is not ready yet." : "Select a notebook to see its mind map.";
            }

            return;
        }

        var gen = ++_generation;
        var notebookId = _notebook.Id;
        CancelPending();
        _loadCts = new CancellationTokenSource();
        var ct = _loadCts.Token;

        _loading = true;
        _errorLabel.Text = string.Empty;
        _noticeLabel.Text = string.Empty;
        _orb.Text = "Mapping your sources…";
        _orb.Visible = true;
        _cancelButton.Visible = true;
        UpdateButtons();

        try
        {
            var tree = await api.GetMindMapAsync(notebookId, ct).ConfigureAwait(true);
            if (gen != _generation || IsDisposed || Disposing || _notebook?.Id != notebookId)
            {
                return;
            }

            if (ct.IsCancellationRequested)
            {
                _noticeLabel.Text = "Mapping cancelled.";
                return;
            }

            _root = tree;
            _collapsed.Clear();
            UpdateMapViews();
        }
        catch (OperationCanceledException)
        {
            if (gen != _generation || IsDisposed || Disposing || _notebook?.Id != notebookId)
            {
                return;
            }

            _noticeLabel.Text = "Mapping cancelled.";
        }
        catch (ApiException ex) when (ex.Kind == ApiErrorKind.Network && ex.Message.Contains("cancelled", StringComparison.OrdinalIgnoreCase))
        {
            if (gen != _generation || IsDisposed || Disposing || _notebook?.Id != notebookId)
            {
                return;
            }

            _noticeLabel.Text = "Mapping cancelled.";
        }
        catch (ApiException ex)
        {
            if (gen != _generation || IsDisposed || Disposing || _notebook?.Id != notebookId)
            {
                return;
            }

            if (ex.StatusCode == 400)
            {
                _root = null;
                _layout = null;
                _canvas.SetLayout(null, _zoom);
                RebuildOutline();
                _noticeLabel.Text = "Add course material, then refresh to see each source and its key concepts.";
            }
            else
            {
                _errorLabel.Text = ex.Message;
            }
        }
        catch (Exception ex)
        {
            if (gen != _generation || IsDisposed || Disposing || _notebook?.Id != notebookId)
            {
                return;
            }

            _errorLabel.Text = ex.Message;
        }
        finally
        {
            if (gen == _generation && !IsDisposed && !Disposing && _notebook?.Id == notebookId)
            {
                _loading = false;
                _orb.Visible = _exporting;
                if (_exporting)
                {
                    _orb.Text = "Exporting mind map…";
                }

                _cancelButton.Visible = _exporting;
                UpdateButtons();
                UpdateEmptyState();
            }
        }
    }

    // ---------- export (authenticated Markdown, stale-guarded) ----------

    private async Task ExportAsync()
    {
        var api = _apiFactory();
        if (api is null || _notebook is null)
        {
            if (!IsDisposed && !Disposing)
            {
                _noticeLabel.Text = "Backend is not ready yet.";
            }

            return;
        }

        if (_root is null)
        {
            if (!IsDisposed && !Disposing)
            {
                _noticeLabel.Text = "Refresh the map before exporting.";
            }

            return;
        }

        var gen = ++_generation;
        var notebookId = _notebook.Id;
        CancelPending();
        _exportCts = new CancellationTokenSource();
        var ct = _exportCts.Token;

        _exporting = true;
        _errorLabel.Text = string.Empty;
        _noticeLabel.Text = string.Empty;
        _orb.Text = "Exporting mind map…";
        _orb.Visible = true;
        _cancelButton.Visible = true;
        UpdateButtons();

        try
        {
            var export = await api.ExportMindMapAsync(notebookId, ct).ConfigureAwait(true);
            // Guard before dialog: stale generation, disposed, session/notebook change.
            if (gen != _generation || IsDisposed || Disposing)
            {
                return;
            }

            if (_apiFactory() is null || _notebook?.Id != notebookId)
            {
                return;
            }

            if (ct.IsCancellationRequested)
            {
                _noticeLabel.Text = "Export cancelled.";
                return;
            }

            using var dialog = new SaveFileDialog
            {
                Filter = "Markdown (*.md)|*.md",
                FileName = export.Filename,
                OverwritePrompt = true,
            };
            if (dialog.ShowDialog(this) != DialogResult.OK)
            {
                if (gen == _generation && !IsDisposed && !Disposing && _notebook?.Id == notebookId)
                {
                    _noticeLabel.Text = "Export cancelled.";
                }

                return;
            }

            // Guard before write: navigation/rebind/cancel must prevent stale writes.
            if (gen != _generation || IsDisposed || Disposing)
            {
                return;
            }

            if (_apiFactory() is null || _notebook?.Id != notebookId)
            {
                return;
            }

            // Prepare beside the destination so a cancelled export never truncates it.
            var temporary = dialog.FileName + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                await File.WriteAllBytesAsync(temporary, export.Data, ct).ConfigureAwait(true);
                if (gen != _generation || IsDisposed || Disposing ||
                    _apiFactory() is null || _notebook?.Id != notebookId || ct.IsCancellationRequested)
                    return;
                File.Move(temporary, dialog.FileName, overwrite: true);
            }
            finally
            {
                if (File.Exists(temporary)) File.Delete(temporary);
            }
            if (gen != _generation || IsDisposed || Disposing || _notebook?.Id != notebookId)
            {
                return;
            }

            _noticeLabel.Text = $"Exported {export.Data.Length} bytes to {Path.GetFileName(dialog.FileName)}.";
        }
        catch (OperationCanceledException)
        {
            if (gen != _generation || IsDisposed || Disposing || _notebook?.Id != notebookId)
            {
                return;
            }

            _noticeLabel.Text = "Export cancelled.";
        }
        catch (ApiException ex) when (ex.Kind == ApiErrorKind.Network && ex.Message.Contains("cancelled", StringComparison.OrdinalIgnoreCase))
        {
            if (gen != _generation || IsDisposed || Disposing || _notebook?.Id != notebookId)
            {
                return;
            }

            _noticeLabel.Text = "Export cancelled.";
        }
        catch (ApiException ex)
        {
            if (gen != _generation || IsDisposed || Disposing || _notebook?.Id != notebookId)
            {
                return;
            }

            _errorLabel.Text = ex.Message;
        }
        catch (Exception ex)
        {
            if (gen != _generation || IsDisposed || Disposing || _notebook?.Id != notebookId)
            {
                return;
            }

            _errorLabel.Text = ex.Message;
        }
        finally
        {
            if (gen == _generation && !IsDisposed && !Disposing && _notebook?.Id == notebookId)
            {
                _exporting = false;
                _orb.Visible = _loading;
                if (_loading)
                {
                    _orb.Text = "Mapping your sources…";
                }

                _cancelButton.Visible = _loading;
                UpdateButtons();
            }
        }
    }

    // ---------- map views ----------

    private void UpdateMapViews()
    {
        if (IsDisposed || Disposing || _root is null)
        {
            UpdateEmptyState();
            UpdateButtons();
            return;
        }

        _layout = MindMapLayout.Layout(_root, _collapsed);
        _canvas.SetLayout(_layout, _zoom);
        RebuildOutline();
        _countsLabel.Text = $"{_layout.VisibleSources} source{(_layout.VisibleSources == 1 ? "" : "s")} · {_layout.VisibleConcepts} concept{(_layout.VisibleConcepts == 1 ? "" : "s")}";
        _zoomLabel.Text = $"{(int)Math.Round(_zoom * 100)}%";
        _zoomLabel.AccessibleName = $"Map zoom {(int)Math.Round(_zoom * 100)} percent";
        if (_layout.VisibleSources == 0)
        {
            _noticeLabel.Text = "Add course material, then refresh to see each source and its key concepts.";
        }

        UpdateButtons();
        UpdateEmptyState();
    }

    private void RebuildOutline()
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        _syncingOutline = true;
        try
        {
            _outline.BeginUpdate();
            _outline.Nodes.Clear();
            if (_root is not null)
            {
                var rootNode = new TreeNode($"{_root.Name}")
                {
                    Tag = null,
                    ToolTipText = _root.Name,
                };
                foreach (var branch in _root.Children)
                {
                    var pages = branch.Pages.Count == 0 ? "" : $" · p. {string.Join(", ", branch.Pages)}";
                    var branchNode = new TreeNode($"{branch.Name} · {branch.Children.Count} concept{(branch.Children.Count == 1 ? "" : "s")}{pages}")
                    {
                        Tag = branch.SourceId is null ? null : Tuple.Create(branch.SourceId, MindMapLayout.FirstPage(branch.Pages)),
                        ToolTipText = $"{branch.Name}{pages}",
                    };
                    foreach (var leaf in branch.Children)
                    {
                        var leafPages = leaf.Pages.Count == 0 ? "" : $" · p. {string.Join(", ", leaf.Pages)}";
                        var leafNode = new TreeNode($"{leaf.Name}{leafPages}")
                        {
                            Tag = leaf.SourceId is null ? null : Tuple.Create(leaf.SourceId, MindMapLayout.FirstPage(leaf.Pages)),
                            ToolTipText = $"{leaf.Name}{leafPages}",
                        };
                        branchNode.Nodes.Add(leafNode);
                    }

                    rootNode.Nodes.Add(branchNode);
                    if (_collapsed.Contains(branch.Id))
                    {
                        branchNode.Collapse();
                    }
                    else
                    {
                        branchNode.Expand();
                    }
                }

                _outline.Nodes.Add(rootNode);
                rootNode.Expand();
            }

            _outline.EndUpdate();
        }
        finally
        {
            _syncingOutline = false;
        }
    }

    private void SyncCollapseFromOutline(TreeNode? node, bool collapsed)
    {
        if (_syncingOutline || node is null || _root is null)
        {
            return;
        }

        var branchId = FindBranchIdForOutlineNode(node);
        if (branchId is null)
        {
            return;
        }

        if (collapsed)
        {
            _collapsed.Add(branchId);
        }
        else
        {
            _collapsed.Remove(branchId);
        }

        UpdateMapViews();
    }

    private string? FindBranchIdForOutlineNode(TreeNode node)
    {
        if (_root is null)
        {
            return null;
        }

        // Outline branch nodes are direct children of the root outline node;
        // leaf nodes map back to their parent branch.
        TreeNode? branchOutline = node.Parent is null ? null : (node.Parent.Parent is null ? node : node.Parent);
        if (node.Parent is null)
        {
            return null;
        }

        if (branchOutline is null)
        {
            return null;
        }

        var index = branchOutline.Index;
        if (index < 0 || index >= _root.Children.Count)
        {
            return null;
        }

        return _root.Children[index].Id;
    }

    private void OpenSelectedOutline()
    {
        var tag = _outline.SelectedNode?.Tag as Tuple<string, int?>;
        if (tag?.Item1 is null)
        {
            if (!IsDisposed && !Disposing)
            {
                _noticeLabel.Text = "Select a source or concept to open its citation.";
            }

            return;
        }

        RequestOpen(tag.Item1, tag.Item2);
    }

    private void RequestOpen(string sourceId, int? page)
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        try
        {
            OpenSourceRequested?.Invoke(sourceId, page);
        }
        catch (Exception)
        {
        }
    }

    private void ToggleBranch(string branchId)
    {
        if (_root is null || string.IsNullOrEmpty(branchId))
        {
            return;
        }

        if (!_collapsed.Remove(branchId))
        {
            _collapsed.Add(branchId);
        }

        UpdateMapViews();
    }

    private void CollapseAll()
    {
        if (_root is null)
        {
            return;
        }

        foreach (var b in _root.Children)
        {
            _collapsed.Add(b.Id);
        }

        UpdateMapViews();
    }

    private void ExpandAll()
    {
        if (_collapsed.Count == 0)
        {
            return;
        }

        _collapsed.Clear();
        UpdateMapViews();
    }

    private void SetZoom(float next)
    {
        var clamped = MindMapLayout.ClampZoom(next);
        if (Math.Abs(clamped - _zoom) < 0.001f)
        {
            return;
        }

        _zoom = clamped;
        if (_layout is not null)
        {
            _canvas.SetLayout(_layout, _zoom);
        }

        _zoomLabel.Text = $"{(int)Math.Round(_zoom * 100)}%";
        _zoomLabel.AccessibleName = $"Map zoom {(int)Math.Round(_zoom * 100)} percent";
        UpdateButtons();
    }

    private void UpdateButtons()
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        var hasNotebook = _notebook is not null;
        var busy = _loading || _exporting;
        _refreshButton.Enabled = hasNotebook && !busy;
        _exportButton.Enabled = hasNotebook && _root is not null && !busy;
        _cancelButton.Visible = busy;
        var hasBranches = _root is not null && _root.Children.Count > 0;
        _collapseAllButton.Enabled = hasBranches && !busy && _collapsed.Count < (_root?.Children.Count ?? 0);
        _expandAllButton.Enabled = hasBranches && !busy && _collapsed.Count > 0;
        _zoomOutButton.Enabled = _root is not null && _zoom > MindMapLayout.MinZoom + 0.001f;
        _zoomInButton.Enabled = _root is not null && _zoom < MindMapLayout.MaxZoom - 0.001f;
        _openSelectedButton.Enabled = _root is not null;
    }

    private void UpdateEmptyState()
    {
        if (IsDisposed || Disposing)
        {
            return;
        }

        if (_loading || _exporting)
        {
            return;
        }

        if (_notebook is null)
        {
            _countsLabel.Text = string.Empty;
            if (string.IsNullOrEmpty(_noticeLabel.Text) && string.IsNullOrEmpty(_errorLabel.Text))
            {
                _noticeLabel.Text = "Select a notebook to see its mind map.";
            }
        }
        else if (_root is null && string.IsNullOrEmpty(_errorLabel.Text) && string.IsNullOrEmpty(_noticeLabel.Text))
        {
            _noticeLabel.Text = "No map yet — press Refresh to build one from your sources.";
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            _generation++;
            CancelPending();
        }

        base.Dispose(disposing);
    }

    // ---------- GDI+ canvas (zoom + scroll + hit actions) ----------

    private sealed class MindMapCanvas : Control
    {
        private readonly Action<string> _toggle;
        private readonly Action<string, int?> _open;
        private MindMapLayoutResult? _layout;
        private float _zoom = 1.0f;
        private readonly ToolTip _tip = new();
        private readonly Font _titleFont;
        private readonly Font _bodyFont;
        private readonly Font _smallFont;
        private string _hoverTip = string.Empty;

        internal MindMapCanvas(Action<string> toggle, Action<string, int?> open)
        {
            _toggle = toggle;
            _open = open;
            SetStyle(ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint, true);
            SetStyle(ControlStyles.Selectable, false);
            BackColor = System.Drawing.Color.White;
            TabStop = false;
            _titleFont = new Font(FontFamily.GenericSansSerif, 10, System.Drawing.FontStyle.Bold);
            _bodyFont = new Font(FontFamily.GenericSansSerif, 9);
            _smallFont = new Font(FontFamily.GenericSansSerif, 8);
            Size = new Size(10, 10);
        }

        internal void SetLayout(MindMapLayoutResult? layout, float zoom)
        {
            _layout = layout;
            _zoom = MindMapLayout.ClampZoom(zoom);
            if (layout is null)
            {
                Size = new Size(10, 10);
            }
            else
            {
                var (w, h) = MindMapLayout.ScaledSize(layout, _zoom);
                Size = new Size(Math.Max(10, (int)Math.Ceiling(w)), Math.Max(10, (int)Math.Ceiling(h)));
            }

            Invalidate();
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            var g = e.Graphics;
            g.Clear(BackColor);
            if (_layout is null)
            {
                TextRenderer.DrawText(g, "No map yet.", _bodyFont, ClientRectangle, ForeColor,
                    TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.WordBreak);
                return;
            }

            g.ScaleTransform(_zoom, _zoom);
            var byId = _layout.Nodes.ToDictionary(n => n.Id);

            using (var connectorPen = new Pen(System.Drawing.Color.FromArgb(120, 90, 140, 160), 2))
            {
                foreach (var c in _layout.Connectors)
                {
                    if (!byId.ContainsKey(c.FromId) || !byId.ContainsKey(c.ToId))
                    {
                        continue;
                    }

                    g.DrawLine(connectorPen, c.X1, c.Y1, c.X2, c.Y2);
                }
            }

            foreach (var node in _layout.Nodes)
            {
                var rect = new RectangleF(node.X, node.Y, node.Width, node.Height);
                var isRoot = node.Depth == 0;
                var fill = isRoot
                    ? System.Drawing.Color.FromArgb(232, 244, 242)
                    : node.Depth == 1
                        ? System.Drawing.Color.FromArgb(255, 255, 255)
                        : System.Drawing.Color.FromArgb(247, 249, 252);
                var border = isRoot
                    ? System.Drawing.Color.FromArgb(37, 107, 98)
                    : System.Drawing.Color.FromArgb(180, 190, 200);
                using (var brush = new SolidBrush(SystemInformation.HighContrast ? SystemColors.Window : fill))
                {
                    g.FillRectangle(brush, rect);
                }

                using (var pen = new Pen(SystemInformation.HighContrast ? SystemColors.WindowText : border, isRoot ? 2 : 1))
                {
                    g.DrawRectangle(pen, rect.X, rect.Y, rect.Width, rect.Height);
                }

                var inset = new RectangleF(rect.X + 8, rect.Y + 6, rect.Width - 16, rect.Height - 12);
                if (node.Depth == 1)
                {
                    // Collapse glyph (top-right) + wrapped title + pages + open affordance.
                    var glyph = new RectangleF(rect.Right - 28, rect.Top + 6, 20, 20);
                    using (var glyphPen = new Pen(SystemInformation.HighContrast ? SystemColors.WindowText : System.Drawing.Color.FromArgb(90, 90, 90), 1))
                    {
                        g.DrawRectangle(glyphPen, glyph.X, glyph.Y, glyph.Width, glyph.Height);
                    }

                    DrawCentered(g, node.IsCollapsed ? "+" : "−", _bodyFont, glyph, SystemColors.WindowText);

                    var titleRect = new RectangleF(inset.X, inset.Y, inset.Width - 26, Math.Max(10, inset.Height - 36));
                    DrawWrapped(g, node.DisplayName, _bodyFont, titleRect);
                    if (node.Pages.Count > 0)
                    {
                        var pagesRect = new RectangleF(inset.X, inset.Y + inset.Height - 34, inset.Width, 14);
                        DrawWrapped(g, $"p. {string.Join(", ", node.Pages)}", _smallFont, pagesRect, System.Drawing.Color.Gray);
                    }

                    if (node.SourceId is not null)
                    {
                        var openRect = new RectangleF(inset.X, inset.Bottom - 18, inset.Width, 16);
                        DrawWrapped(g, "Open source ↗", _smallFont, openRect, System.Drawing.Color.FromArgb(20, 90, 160));
                    }
                }
                else if (node.Depth == 2)
                {
                    DrawWrapped(g, node.DisplayName, _bodyFont, new RectangleF(inset.X, inset.Y, inset.Width, Math.Max(10, inset.Height - 16)));
                    if (node.Pages.Count > 0)
                    {
                        DrawWrapped(g, $"p. {string.Join(", ", node.Pages)}", _smallFont,
                            new RectangleF(inset.X, inset.Bottom - 14, inset.Width - 24, 14), System.Drawing.Color.Gray);
                    }

                    if (node.SourceId is not null)
                    {
                        DrawCentered(g, "↗", _bodyFont,
                            new RectangleF(rect.Right - 24, rect.Bottom - 22, 18, 16),
                            System.Drawing.Color.FromArgb(20, 90, 160));
                    }
                }
                else
                {
                    DrawWrapped(g, node.DisplayName, _titleFont, inset, System.Drawing.Color.FromArgb(20, 60, 55));
                }
            }
        }

        private static void DrawCentered(Graphics g, string text, Font font, RectangleF rect, Color color)
        {
            using var format = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center };
            using var brush = new SolidBrush(SystemInformation.HighContrast ? SystemColors.WindowText : color);
            g.DrawString(text, font, brush, rect, format);
        }

        private static void DrawWrapped(System.Drawing.Graphics g, string text, Font font, RectangleF rect, System.Drawing.Color? color = null)
        {
            if (rect.Width <= 0 || rect.Height <= 0 || string.IsNullOrEmpty(text))
            {
                return;
            }

            using var format = new StringFormat(StringFormatFlags.LineLimit)
            {
                Trimming = StringTrimming.EllipsisWord,
                FormatFlags = StringFormatFlags.LineLimit,
            };
            using var brush = new SolidBrush(SystemInformation.HighContrast ? SystemColors.WindowText : color ?? System.Drawing.Color.Black);
            g.DrawString(text, font, brush, rect, format);
        }

        protected override void OnMouseClick(MouseEventArgs e)
        {
            base.OnMouseClick(e);
            if (_layout is null || e.Button != MouseButtons.Left)
            {
                return;
            }

            var hit = HitTest(e.Location);
            if (hit is null)
            {
                return;
            }

            var (node, zone) = hit.Value;
            if (zone == HitZone.Collapse)
            {
                _toggle(node.Id);
            }
            else if (zone == HitZone.Open && node.SourceId is not null)
            {
                _open(node.SourceId, MindMapLayout.FirstPage(node.Pages));
            }
            else if (node.Depth == 2 && node.SourceId is not null)
            {
                _open(node.SourceId, MindMapLayout.FirstPage(node.Pages));
            }
        }

        protected override void OnMouseMove(MouseEventArgs e)
        {
            base.OnMouseMove(e);
            if (_layout is null)
            {
                Cursor = Cursors.Default;
                UpdateTip(string.Empty);
                return;
            }

            var hit = HitTest(e.Location);
            if (hit is null)
            {
                Cursor = Cursors.Default;
                UpdateTip(string.Empty);
                return;
            }

            var (node, zone) = hit.Value;
            var clickable = zone is HitZone.Collapse or HitZone.Open
                || (node.Depth == 2 && node.SourceId is not null);
            Cursor = clickable ? Cursors.Hand : Cursors.Default;

            var pages = node.Pages.Count == 0 ? "" : $" · p. {string.Join(", ", node.Pages)}";
            UpdateTip($"{node.Name}{pages}");
        }

        protected override void OnMouseLeave(EventArgs e)
        {
            base.OnMouseLeave(e);
            Cursor = Cursors.Default;
            UpdateTip(string.Empty);
        }

        private void UpdateTip(string text)
        {
            if (_hoverTip == text)
            {
                return;
            }

            _hoverTip = text;
            try
            {
                _tip.SetToolTip(this, string.IsNullOrEmpty(text) ? string.Empty : text);
                _tip.Active = !string.IsNullOrEmpty(text);
            }
            catch (Exception)
            {
            }
        }

        private enum HitZone { Body, Collapse, Open }

        private (MindMapLayoutNode Node, HitZone Zone)? HitTest(Point location)
        {
            if (_layout is null)
            {
                return null;
            }

            var x = location.X / _zoom;
            var y = location.Y / _zoom;
            // Leaves last so concept hits win over branch headers.
            for (var i = _layout.Nodes.Count - 1; i >= 0; i--)
            {
                var node = _layout.Nodes[i];
                if (x < node.X || x > node.X + node.Width || y < node.Y || y > node.Y + node.Height)
                {
                    continue;
                }

                if (node.Depth == 1)
                {
                    var glyph = new RectangleF(node.X + node.Width - 28, node.Y + 6, 20, 20);
                    if (x >= glyph.X && x <= glyph.X + glyph.Width && y >= glyph.Y && y <= glyph.Y + glyph.Height)
                    {
                        return (node, HitZone.Collapse);
                    }

                    if (node.SourceId is not null)
                    {
                        var openTop = node.Y + node.Height - 20;
                        if (y >= openTop)
                        {
                            return (node, HitZone.Open);
                        }
                    }

                    return (node, HitZone.Body);
                }

                if (node.Depth == 2)
                {
                    if (node.SourceId is not null)
                    {
                        return (node, HitZone.Open);
                    }

                    return (node, HitZone.Body);
                }

                return (node, HitZone.Body);
            }

            return null;
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                try { _tip.RemoveAll(); } catch (Exception) { }
                _tip.Dispose();
                _titleFont.Dispose();
                _bodyFont.Dispose();
                _smallFont.Dispose();
            }

            base.Dispose(disposing);
        }
    }
}
