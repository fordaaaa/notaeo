using Notaeo;
using Xunit;

namespace Notaeo.Tests;

public sealed class WorkspacePreferencesTests
{
    [Fact]
    public void PreferencesPersistTogetherAndNeverAlterAccountFile()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"notaeo-prefs-{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        try
        {
            var path = Path.Combine(directory, "preferences.json");
            var account = Path.Combine(directory, "account.json");
            File.WriteAllText(account, "test account sentinel");
            var preferences = new WorkspacePreferences(path);
            preferences.SetSourceOrder(SourceOrder.Name);
            preferences.SetReduceMotion(true);
            var reopened = new WorkspacePreferences(path);
            Assert.Equal(SourceOrder.Name, reopened.SourceOrder);
            Assert.True(reopened.ReduceMotion);
            Assert.Equal("test account sentinel", File.ReadAllText(account));
        }
        finally { Directory.Delete(directory, true); }
    }

    [Fact]
    public void CorruptOrUnknownPreferencesUseSafeDefaults()
    {
        var path = Path.Combine(Path.GetTempPath(), $"notaeo-prefs-{Guid.NewGuid():N}.json");
        try
        {
            File.WriteAllText(path, "corrupt");
            var preferences = new WorkspacePreferences(path);
            Assert.Equal(SourceOrder.Newest, preferences.SourceOrder);
            Assert.False(preferences.ReduceMotion);
            File.WriteAllText(path, "{\"source_order\":\"future-value\",\"reduce_motion\":true}");
            preferences = new WorkspacePreferences(path);
            Assert.Equal(SourceOrder.Newest, preferences.SourceOrder);
            Assert.True(preferences.ReduceMotion);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void FailedSaveDoesNotChangeLivePreferenceOrNotifyListeners()
    {
        var directory = Path.Combine(Path.GetTempPath(), $"notaeo-prefs-{Guid.NewGuid():N}");
        Directory.CreateDirectory(directory);
        try
        {
            var preferences = new WorkspacePreferences(directory); // A directory cannot be replaced by a preferences file.
            var notified = false;
            preferences.Changed += (_, _) => notified = true;
            Assert.ThrowsAny<IOException>(() => preferences.SetReduceMotion(true));
            Assert.False(preferences.ReduceMotion);
            Assert.False(notified);
        }
        finally { Directory.Delete(directory, true); }
    }
}
