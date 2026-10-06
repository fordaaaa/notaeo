using System.Diagnostics;
using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;
using Microsoft.Win32;

namespace Notaeo;

internal sealed class ThinkingOrbControl : Control
{
    private readonly WorkspacePreferences _preferences;
    private readonly System.Windows.Forms.Timer _timer = new() { Interval = 34 };
    private readonly Stopwatch _clock = Stopwatch.StartNew();
    private bool _systemReduceMotion;
    private bool _watchingSystem;

    internal ThinkingOrbControl(WorkspacePreferences preferences)
    {
        _preferences = preferences;
        SetStyle(ControlStyles.OptimizedDoubleBuffer | ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint, true);
        SetStyle(ControlStyles.Selectable, false);
        Size = new Size(380, 42);
        TabStop = false;
        AccessibleRole = AccessibleRole.StaticText;
        Text = "Working…";
        _timer.Tick += (_, _) => Invalidate();
        _preferences.Changed += PreferencesChanged;
    }

    protected override void OnHandleCreated(EventArgs e)
    {
        base.OnHandleCreated(e);
        SystemEvents.UserPreferenceChanged += SystemPreferenceChanged;
        _watchingSystem = true;
        RefreshMotion();
    }

    protected override void OnHandleDestroyed(EventArgs e)
    {
        StopWatchingSystem();
        _timer.Stop();
        base.OnHandleDestroyed(e);
    }

    protected override void OnVisibleChanged(EventArgs e) { base.OnVisibleChanged(e); RefreshMotion(); }
    protected override void OnTextChanged(EventArgs e) { base.OnTextChanged(e); AccessibleName = Text; Invalidate(); }
    private void PreferencesChanged(object? sender, EventArgs e) => RefreshOnUiThread();
    private void SystemPreferenceChanged(object sender, UserPreferenceChangedEventArgs e) => RefreshOnUiThread();

    private void RefreshOnUiThread()
    {
        if (IsDisposed || Disposing || !IsHandleCreated) return;
        if (!InvokeRequired) { RefreshMotion(); return; }
        try { BeginInvoke((MethodInvoker)RefreshMotion); }
        catch (Exception ex) when (ex is InvalidOperationException or ObjectDisposedException) { }
    }

    private void RefreshMotion()
    {
        if (IsDisposed || Disposing) return;
        _systemReduceMotion = !WindowsAnimationsEnabled();
        if (Visible && IsHandleCreated && !_systemReduceMotion && !_preferences.ReduceMotion) _timer.Start();
        else _timer.Stop();
        Invalidate();
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
        var dpi = DeviceDpi / 96f;
        var tints = new[] { Color.FromArgb(37, 107, 98), Color.FromArgb(65, 171, 210), Color.FromArgb(124, 112, 191) };
        for (var i = 0; i < 3; i++)
        {
            var sample = ThinkingOrbMotion.Sample(_clock.Elapsed.TotalSeconds, i, _systemReduceMotion, _preferences.ReduceMotion);
            var size = (float)(20 * sample.Scale) * dpi;
            var bounds = new RectangleF((float)(14 + i * 15 + sample.X) * dpi - size / 2,
                Height / 2f + (float)((i == 1 ? -2 : 2) + sample.Y) * dpi - size / 2, size, size);
            using var path = new GraphicsPath();
            path.AddEllipse(bounds);
            using var brush = new PathGradientBrush(path)
            {
                CenterColor = Color.FromArgb((int)(230 * sample.Opacity), SystemInformation.HighContrast ? SystemColors.WindowText : Color.White),
                SurroundColors = [Color.FromArgb((int)(255 * sample.Opacity), SystemInformation.HighContrast ? SystemColors.Highlight : tints[i])],
                CenterPoint = new PointF(bounds.Left + size * 0.3f, bounds.Top + size * 0.3f),
            };
            e.Graphics.FillPath(brush, path);
        }
        var label = new Rectangle((int)(72 * dpi), 0, Math.Max(0, Width - (int)(72 * dpi)), Height);
        TextRenderer.DrawText(e.Graphics, Text, Font, label, ForeColor,
            TextFormatFlags.Left | TextFormatFlags.VerticalCenter | TextFormatFlags.EndEllipsis | TextFormatFlags.NoPrefix);
    }

    // Read the client's animation preference; never change the OS setting.
    // https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-systemparametersinfow
    private static bool WindowsAnimationsEnabled() => OperatingSystem.IsWindows()
        && SystemParametersInfo(0x1042, 0, out var enabled, 0) && enabled;

    [DllImport("user32.dll", EntryPoint = "SystemParametersInfoW")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool SystemParametersInfo(uint action, uint param, [MarshalAs(UnmanagedType.Bool)] out bool value, uint flags);

    private void StopWatchingSystem()
    {
        if (!_watchingSystem) return;
        SystemEvents.UserPreferenceChanged -= SystemPreferenceChanged;
        _watchingSystem = false;
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            StopWatchingSystem();
            _preferences.Changed -= PreferencesChanged;
            _timer.Dispose();
        }
        base.Dispose(disposing);
    }
}
