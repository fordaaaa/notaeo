// Native Settings: account + motion preview + read-only AI availability + sign out.
// Available logged-out (AI section explains login is required).
namespace Notaeo;

internal sealed class SettingsForm : Form
{
    private readonly SessionStore _session;
    private readonly WorkspacePreferences _preferences;
    private readonly CheckBox _reduceMotionBox = new() { Text = "Reduce motion", AutoSize = true, AccessibleName = "Reduce motion" };
    private readonly Button _previewButton = new() { Text = "Preview AI loading", AutoSize = true };
    private readonly Label _appearanceNotice = new() { AutoSize = true, MaximumSize = new Size(380, 0) };
    private readonly ThinkingOrbControl _previewOrbs;
    private readonly System.Windows.Forms.Timer _previewTimer = new() { Interval = 3000 };

    private readonly Label _accountLabel = new() { AutoSize = true };
    private readonly Button _signOutButton = new() { Text = "Sign out", AutoSize = true };
    private readonly Label _statusLabel = new() { AutoSize = true, MaximumSize = new Size(380, 0) };
    private readonly Label _modelLabel = new() { AutoSize = true, MaximumSize = new Size(380, 0) };
    private readonly Label _messageLabel = new() { AutoSize = true, MaximumSize = new Size(380, 0) };

    private bool _busy;
    private bool CanRender => !IsDisposed && !Disposing;

    internal SettingsForm(SessionStore session, WorkspacePreferences? preferences = null)
    {
        _session = session ?? throw new ArgumentNullException(nameof(session));
        _preferences = preferences ?? new WorkspacePreferences();
        _previewOrbs = new ThinkingOrbControl(_preferences) { Text = "Preparing an explanation…", Visible = false };
        Text = "Notaeo Settings";
        MinimumSize = new Size(480, 650);
        StartPosition = FormStartPosition.CenterParent;
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        MinimizeBox = false;

        _signOutButton.Click += async (_, _) => await SignOutAsync();

        var layout = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 1,
            RowCount = 4,
            Padding = new Padding(12),
            AutoSize = true,
        };

        var appearance = new GroupBox { Text = "Motion", Dock = DockStyle.Fill, AutoSize = true };
        var appearanceLayout = new FlowLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, FlowDirection = FlowDirection.TopDown, WrapContents = false };
        _reduceMotionBox.Checked = _preferences.ReduceMotion;
        _reduceMotionBox.CheckedChanged += (_, _) =>
        {
            try { _preferences.SetReduceMotion(_reduceMotionBox.Checked); _appearanceNotice.Text = ""; }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
            {
                _reduceMotionBox.Checked = _preferences.ReduceMotion;
                _appearanceNotice.Text = "Couldn't save the motion preference: " + ex.Message;
            }
        };
        _previewButton.Click += (_, _) =>
        {
            _previewOrbs.Visible = true;
            _previewButton.Enabled = false;
            _previewTimer.Start();
        };
        _previewTimer.Tick += (_, _) =>
        {
            _previewTimer.Stop();
            _previewOrbs.Visible = false;
            _previewButton.Enabled = true;
        };
        appearanceLayout.Controls.AddRange([_reduceMotionBox, _previewButton, _previewOrbs,
            new Label { Text = "A three-second local preview. No AI request is made.", AutoSize = true }, _appearanceNotice]);
        appearance.Controls.Add(appearanceLayout);

        var account = new GroupBox { Text = "Account", Dock = DockStyle.Fill, AutoSize = true };
        var accountLayout = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, AutoSize = true };
        accountLayout.Controls.Add(_accountLabel);
        accountLayout.Controls.Add(_signOutButton);
        account.Controls.Add(accountLayout);

        var ai = new GroupBox { Text = "Optional AI", Dock = DockStyle.Fill, AutoSize = true };
        var aiLayout = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, AutoSize = true, Padding = new Padding(8) };
        aiLayout.Controls.Add(new Label { Text = "Source, search, and practice work without AI.", AutoSize = true, MaximumSize = new Size(380, 0) });
        aiLayout.Controls.Add(_statusLabel);
        aiLayout.Controls.Add(_modelLabel);
        aiLayout.Controls.Add(_messageLabel);
        ai.Controls.Add(aiLayout);

        var closeButton = new Button { Text = "Close", DialogResult = DialogResult.OK, AutoSize = true };
        var closeHost = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.RightToLeft, AutoSize = true };
        closeHost.Controls.Add(closeButton);

        layout.Controls.Add(appearance, 0, 0);
        layout.Controls.Add(account, 0, 1);
        layout.Controls.Add(ai, 0, 2);
        layout.Controls.Add(closeHost, 0, 3);
        Controls.Add(layout);
        AcceptButton = closeButton;

        Shown += async (_, _) => await LoadAsync();
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing) _previewTimer.Dispose();
        base.Dispose(disposing);
    }

    private async Task LoadAsync()
    {
        if (!CanRender || _busy) return;
        var account = _session.AccountToken;
        RenderAccount();
        if (!_session.IsLoggedIn)
        {
            _statusLabel.Text = "Sign in to see AI availability. Source, search, and practice work without AI.";
            _modelLabel.Text = string.Empty;
            SetAiEnabled(false);
            return;
        }

        var api = _session.MakeApi();
        if (api is null)
        {
            _messageLabel.Text = "Backend is not ready yet.";
            return;
        }

        _busy = true;
        SetAiEnabled(false);
        try
        {
            var status = await api.GetAIStatusAsync().ConfigureAwait(true);
            if (!CanRender || account != _session.AccountToken) return;
            _statusLabel.Text = status.Enabled
                ? "AI is available."
                : "AI is not available. Source, search, and practice work without AI.";
            _modelLabel.Text = status.Enabled && !string.IsNullOrEmpty(status.Model)
                ? $"Model: {status.Model}"
                : string.Empty;
        }
        catch (ApiException ex)
        {
            if (CanRender && account == _session.AccountToken) _messageLabel.Text = ex.Message;
        }
        catch (Exception ex)
        {
            if (CanRender && account == _session.AccountToken) _messageLabel.Text = ex.Message;
        }
        finally
        {
            _busy = false;
            if (CanRender) { RenderAccount(); SetAiEnabled(_session.IsLoggedIn); }
        }
    }

    private void RenderAccount()
    {
        if (_session.IsLoggedIn)
        {
            _accountLabel.Text = _session.UserEmail ?? "Signed in";
            _signOutButton.Text = "Sign out";
        }
        else
        {
            _accountLabel.Text = "Sign in to access notebooks and see AI availability.";
        }
    }

    private void SetAiEnabled(bool enabled)
    {
        if (!CanRender) return;
        enabled = enabled && !_busy && _session.MakeApi() is not null;
        _signOutButton.Enabled = !_busy && _session.IsLoggedIn;
    }

    private async Task SignOutAsync()
    {
        if (!CanRender || _busy) return;
        var account = _session.AccountToken;
        var api = _session.MakeApi();
        _busy = true;
        SetAiEnabled(false);
        try
        {
            if (api is not null && account is not null)
            {
                try
                {
                    using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
                    await api.LogoutAsync(cts.Token).ConfigureAwait(true);
                }
                catch (Exception) { }
            }
            _session.ClearAccountIfMatching(account);
            if (!CanRender) return;
            RenderAccount();
            _messageLabel.Text = "Signed out.";
            _statusLabel.Text = "Sign in to see AI availability. Source, search, and practice work without AI.";
            _modelLabel.Text = string.Empty;
        }
        finally
        {
            _busy = false;
            if (CanRender) SetAiEnabled(_session.IsLoggedIn);
        }
    }
}
