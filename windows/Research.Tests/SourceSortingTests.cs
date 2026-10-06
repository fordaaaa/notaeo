using Notaeo;
using Xunit;

namespace Notaeo.Tests;

public sealed class SourceSortingTests
{
    private static SourceSummary Source(string id, string title, string date, string kind = "paste") =>
        new(id, "course", kind, title, [], date, 1);

    [Fact]
    public void DatesUseUtcInstantsWithFractionsAndUnknownDatesLast()
    {
        SourceSummary[] sources = [Source("z", "Missing", "invalid"),
            Source("older", "Older", "2026-10-06T10:30:00Z"),
            Source("newer", "Newer", "2026-10-06T07:00:00.123-04:00"),
            Source("same", "Same", "2026-10-06T11:00:00.123+00:00")];
        Assert.Equal(["newer", "same", "older", "z"], SourceOrdering.Order(sources, SourceOrder.Newest).Select(s => s.Id));
        Assert.Equal(["older", "newer", "same", "z"], SourceOrdering.Order(sources, SourceOrder.Oldest).Select(s => s.Id));
        Assert.Null(SourceOrdering.CreationDate(sources[0]));
    }

    [Fact]
    public void NamesSortNaturallyAndKindUsesNameThenStableId()
    {
        SourceSummary[] sources = [Source("b", "Lecture 10", "", "pdf"),
            Source("c", "lecture 2", "", "paste"), Source("a", "Lecture 10", "", "pdf")];
        Assert.Equal(["c", "a", "b"], SourceOrdering.Order(sources, SourceOrder.Name).Select(s => s.Id));
        Assert.Equal(["c", "a", "b"], SourceOrdering.Order(sources, SourceOrder.Kind).Select(s => s.Id));
        Assert.Equal(["a", "b", "c"], SourceOrdering.Order(sources, SourceOrder.Newest).Select(s => s.Id));
    }

    [Fact]
    public void NaturalNumbersDoNotOverflowAndSortingDoesNotMutateInput()
    {
        SourceSummary[] sources = [Source("long", "Lecture 999999999999999999999", ""), Source("short", "Lecture 12", "")];
        Assert.Equal("short", SourceOrdering.Order(sources, SourceOrder.Name)[0].Id);
        Assert.Equal("long", sources[0].Id);
    }
}
