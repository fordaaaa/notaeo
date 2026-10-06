// Native Settings: actual /api/settings/ai provider settings + sign out.
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
    private readonly ComboBox _providerBox = new() { DropDownStyle = ComboBoxStyle.DropDownList };
    private readonly TextBox _apiKeyBox = new() { UseSystemPasswordChar = true, Width = 280 };
    private readonly TextBox _modelBox = new() { Width = 280 };
    private readonly Button _saveButton = new() { Text = "Save AI settings", AutoSize = true };
    private readonly Button _removeButton = new() { Text = "Remove key", AutoSize = true };
    private readonly Label _statusLabel = new() { AutoSize = true };
    private readonly Label _messageLabel = new() { AutoSize = true, MaximumSize = new Size(380, 0) };

    private static readonly Dictionary<string, string> DefaultModels = new()
    {
        ["gemini"] = "gemini-3.5-flash-lite",
        ["openrouter"] = "nvidia/nemotron-3-ultra-550b-a55b:free",
        ["groq"] = "openai/gpt-oss-20b",
    };

    private bool _busy;
    private bool _configured;
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

        _providerBox.Items.AddRange(["gemini", "openrouter", "groq"]);
        _providerBox.SelectedIndex = 0;
        _providerBox.SelectedIndexChanged += (_, _) =>
        {
            if (DefaultModels.TryGetValue(CurrentProvider(), out var model))
            {
                _modelBox.Text = model;
            }
        };

        _signOutButton.Click += async (_, _) => await SignOutAsync();
        _saveButton.Click += async (_, _) => await SaveAsync();
        _removeButton.Click += async (_, _) => await RemoveAsync();

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
        var aiLayout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 6, Padding = new Padding(8), AutoSize = true };
        aiLayout.Controls.Add(new Label { Text = "Provider:", AutoSize = true }, 0, 0);
        aiLayout.Controls.Add(_providerBox, 1, 0);
        aiLayout.Controls.Add(new Label { Text = "API key:", AutoSize = true }, 0, 1);
        aiLayout.Controls.Add(_apiKeyBox, 1, 1);
        aiLayout.Controls.Add(new Label { Text = "Model:", AutoSize = true }, 0, 2);
        aiLayout.Controls.Add(_modelBox, 1, 2);
        var buttons = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.LeftToRight };
        buttons.Controls.Add(_saveButton);
        buttons.Controls.Add(_removeButton);
        aiLayout.Controls.Add(buttons, 0, 3);
        aiLayout.SetColumnSpan(buttons, 2);
        aiLayout.Controls.Add(_statusLabel, 0, 4);
        aiLayout.SetColumnSpan(_statusLabel, 2);
        aiLayout.Controls.Add(_messageLabel, 0, 5);
        aiLayout.SetColumnSpan(_messageLabel, 2);
        var hint = new Label
        {
            Text = "Your key is saved with your account and used only when you request an AI feature.",
            AutoSize = true,
            MaximumSize = new Size(380, 0),
        };
        aiLayout.Controls.Add(hint, 0, 6);
        aiLayout.SetColumnSpan(hint, 2);
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

    private string CurrentProvider() => _providerBox.SelectedItem?.ToString() ?? "gemini";

    private async Task LoadAsync()
    {
        if (!CanRender || _busy) return;
        var account = _session.AccountToken;
        RenderAccount();
        if (!_session.IsLoggedIn)
        {
            _statusLabel.Text = "AI is not configured. Sign in to manage an optional key. Coach works without a key.";
            SetAiEnabled(false);
            return;
        }

        var api = _session.MakeApi();
        if (api is null)
        {
            _messageLabel.Text = "Backend is not ready yet.";
            return;
        }

        try
        {
            var settings = await api.GetAISettingsAsync().ConfigureAwait(true);
            if (!CanRender || account != _session.AccountToken) return;
            _configured = settings.Configured;
            _statusLabel.Text = settings.Configured ? "AI is configured." : "AI is not configured. Coach works without a key.";
            if (!string.IsNullOrEmpty(settings.Provider))
            {
                var idx = _providerBox.Items.IndexOf(settings.Provider);
                if (idx >= 0)
                {
                    _providerBox.SelectedIndex = idx;
                }
            }

            if (!string.IsNullOrEmpty(settings.Model))
            {
                _modelBox.Text = settings.Model;
            }
            else if (DefaultModels.TryGetValue(CurrentProvider(), out var def))
            {
                _modelBox.Text = def;
            }

            _removeButton.Enabled = settings.Configured && !_busy;
            SetAiEnabled(true);
        }
        catch (ApiException ex)
        {
            if (CanRender && account == _session.AccountToken) _messageLabel.Text = ex.Message;
        }
        catch (Exception ex)
        {
            if (CanRender && account == _session.AccountToken) _messageLabel.Text = ex.Message;
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
            _accountLabel.Text = "Sign in to access notebooks and optional AI settings.";
            _configured = false;
            _apiKeyBox.Clear();
        }
    }

    private void SetAiEnabled(bool enabled)
    {
        if (!CanRender) return;
        enabled = enabled && !_busy && _session.MakeApi() is not null;
        _removeButton.Enabled = enabled && _configured;
        _signOutButton.Enabled = !_busy && _session.IsLoggedIn;
        _providerBox.Enabled = enabled;
        _apiKeyBox.Enabled = enabled;
        _modelBox.Enabled = enabled;
        _saveButton.Enabled = enabled && !_busy;
    }

    private async Task SaveAsync()
    {
        if (!CanRender || _busy) return;
        var account = _session.AccountToken;
        var api = _session.MakeApi();
        if (api is null)
        {
            _messageLabel.Text = "Backend is not ready yet.";
            return;
        }

        if (!_session.IsLoggedIn)
        {
            _messageLabel.Text = "Sign in first.";
            return;
        }

        var key = _apiKeyBox.Text.Trim();
        if (key.Length < 10)
        {
            _messageLabel.Text = "API key looks too short.";
            return;
        }

        _busy = true;
        SetAiEnabled(false);
        try
        {
            var saved = await api.SaveAISettingsAsync(CurrentProvider(), key, _modelBox.Text.Trim()).ConfigureAwait(true);
            if (!CanRender || account != _session.AccountToken) return;
            _configured = saved.Configured;
            _statusLabel.Text = saved.Configured ? "AI is configured." : "AI settings saved.";
            _apiKeyBox.Text = string.Empty;
            _messageLabel.Text = "AI settings saved.";
            _removeButton.Enabled = saved.Configured;
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

    private async Task RemoveAsync()
    {
        if (!CanRender || _busy) return;
        var account = _session.AccountToken;
        var api = _session.MakeApi();
        if (api is null)
        {
            return;
        }

        _busy = true;
        SetAiEnabled(false);
        try
        {
            await api.ClearAISettingsAsync().ConfigureAwait(true);
            if (!CanRender || account != _session.AccountToken) return;
            _configured = false;
            _statusLabel.Text = "AI is not configured. Coach works without a key.";
            _messageLabel.Text = "AI key removed.";
            _removeButton.Enabled = false;
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
            _statusLabel.Text = "Sign in to manage an optional AI key. Coach works without a key.";
        }
        finally
        {
            _busy = false;
            if (CanRender) SetAiEnabled(_session.IsLoggedIn);
        }
    }
}
