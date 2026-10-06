using System.Text.Json;

namespace Notaeo;

/// Device-only preferences; kept separate from the DPAPI account file.
internal sealed class WorkspacePreferences
{
    private readonly string _path;
    internal SourceOrder SourceOrder { get; private set; } = SourceOrder.Newest;
    internal bool ReduceMotion { get; private set; }
    internal event EventHandler? Changed;

    internal WorkspacePreferences(string? path = null)
    {
        _path = path ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "research", "preferences.json");
        try
        {
            if (!File.Exists(_path)) return;
            using var json = JsonDocument.Parse(File.ReadAllText(_path));
            if (json.RootElement.ValueKind != JsonValueKind.Object) return;
            if (json.RootElement.TryGetProperty("source_order", out var sort) && sort.ValueKind == JsonValueKind.String
                && Enum.TryParse<SourceOrder>(sort.GetString(), true, out var parsed) && Enum.IsDefined(parsed)) SourceOrder = parsed;
            if (json.RootElement.TryGetProperty("reduce_motion", out var motion) && motion.ValueKind is JsonValueKind.True or JsonValueKind.False)
                ReduceMotion = motion.GetBoolean();
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or JsonException) { }
    }

    internal void SetSourceOrder(SourceOrder order)
    {
        if (!Enum.IsDefined(order)) throw new ArgumentOutOfRangeException(nameof(order));
        if (SourceOrder == order) return;
        Save(order, ReduceMotion);
        SourceOrder = order;
        Changed?.Invoke(this, EventArgs.Empty);
    }

    internal void SetReduceMotion(bool reduceMotion)
    {
        if (ReduceMotion == reduceMotion) return;
        Save(SourceOrder, reduceMotion);
        ReduceMotion = reduceMotion;
        Changed?.Invoke(this, EventArgs.Empty);
    }

    private void Save(SourceOrder order, bool reduceMotion)
    {
        var directory = Path.GetDirectoryName(_path);
        if (!string.IsNullOrEmpty(directory)) Directory.CreateDirectory(directory);
        var temporary = _path + ".tmp-" + Guid.NewGuid().ToString("N");
        try
        {
            File.WriteAllText(temporary, JsonSerializer.Serialize(new { source_order = order.ToString(), reduce_motion = reduceMotion }));
            File.Move(temporary, _path, overwrite: true);
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }
}
