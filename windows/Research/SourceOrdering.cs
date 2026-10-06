using System.Globalization;

namespace Notaeo;

internal enum SourceOrder { Newest, Oldest, Name, Kind }

internal static class SourceOrdering
{
    internal static DateTimeOffset? CreationDate(SourceSummary source) =>
        DateTimeOffset.TryParse(source.CreatedAt, CultureInfo.InvariantCulture,
            DateTimeStyles.AssumeUniversal, out var date) ? date : null;

    internal static string Label(SourceOrder order) => order switch
    {
        SourceOrder.Oldest => "Oldest first",
        SourceOrder.Name => "Name",
        SourceOrder.Kind => "File type",
        _ => "Newest first",
    };

    internal static List<SourceSummary> Order(IEnumerable<SourceSummary> sources, SourceOrder order)
    {
        var dated = sources.Select(source => (Source: source, Date: CreationDate(source))).ToList();
        dated.Sort((a, b) =>
        {
            var result = 0;
            if (order is SourceOrder.Newest or SourceOrder.Oldest)
            {
                if (a.Date.HasValue != b.Date.HasValue) return a.Date.HasValue ? -1 : 1;
                if (a.Date.HasValue && b.Date.HasValue)
                    result = order == SourceOrder.Newest ? b.Date.Value.CompareTo(a.Date.Value) : a.Date.Value.CompareTo(b.Date.Value);
            }
            else
            {
                if (order == SourceOrder.Kind) result = StringComparer.Ordinal.Compare(a.Source.Kind, b.Source.Kind);
                if (result == 0) result = CompareNames(a.Source.Title, b.Source.Title);
            }
            return result != 0 ? result : StringComparer.Ordinal.Compare(a.Source.Id, b.Source.Id);
        });
        return dated.Select(item => item.Source).ToList();
    }

    private static int CompareNames(string left, string right)
    {
        var a = 0; var b = 0;
        while (a < left.Length && b < right.Length)
        {
            var numeric = char.IsAsciiDigit(left[a]) && char.IsAsciiDigit(right[b]);
            var endA = a + 1; var endB = b + 1;
            while (endA < left.Length && char.IsAsciiDigit(left[endA]) == char.IsAsciiDigit(left[a])) endA++;
            while (endB < right.Length && char.IsAsciiDigit(right[endB]) == char.IsAsciiDigit(right[b])) endB++;
            int result;
            if (numeric)
            {
                var numberA = left.AsSpan(a, endA - a).TrimStart('0');
                var numberB = right.AsSpan(b, endB - b).TrimStart('0');
                // Compare lengths/digits instead of parsing integers, so very
                // large lecture numbers and leading zeroes remain well defined.
                result = numberA.Length.CompareTo(numberB.Length);
                if (result == 0) result = numberA.SequenceCompareTo(numberB);
            }
            else result = CultureInfo.CurrentCulture.CompareInfo.Compare(left[a..endA], right[b..endB], CompareOptions.IgnoreCase);
            if (result != 0) return result;
            a = endA; b = endB;
        }
        return (left.Length - a).CompareTo(right.Length - b);
    }
}
