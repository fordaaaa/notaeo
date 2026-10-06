using Notaeo;
using Xunit;

namespace Notaeo.Tests;

public sealed class SourceReaderDocumentTests
{
    [Fact]
    public void ReaderPreservesActualPageNumbersAndTargetsRequestedPage()
    {
        var detail = new SourceDetail("source", "course", "pdf", "Notes", [], "", [new(2, "α first"), new(7, "second")], [], null, null, null, null, null);
        var document = SourceReaderDocument.Create(detail, 7);
        Assert.Contains("PAGE 2", document.Text);
        Assert.Contains("PAGE 7", document.Text);
        Assert.Equal("PAGE 7", document.Text.Substring(document.SelectionStart, 6));
        Assert.Equal(7, document.OpenedPage);
        var missing = SourceReaderDocument.Create(detail, 99);
        Assert.Equal(2, missing.OpenedPage);
    }

    [Fact]
    public void ChunkOnlySourcesRemainReadableWithCitedPageOffsets()
    {
        var detail = new SourceDetail("source", "course", "txt", "Notes", [], "", [], [new(0, [4], "Fallback passage")], null, null, null, null, null);
        var document = SourceReaderDocument.Create(detail, 4);
        Assert.Contains("Fallback passage", document.Text);
        Assert.Equal(4, document.OpenedPage);
        Assert.Equal(0, document.SelectionStart);
    }

    [Fact]
    public void SharedChunkPageTargetsFirstPassageAndEmptyPagesAreNotInvented()
    {
        var detail = new SourceDetail("source", "course", "txt", "Notes", [], "", [],
            [new(0, [4], "First"), new(1, [4], "Second")], null, null, null, null, null);
        Assert.Equal(0, SourceReaderDocument.Create(detail, 4).SelectionStart);
        detail = detail with { Chunks = [new(0, [], "No page metadata")] };
        Assert.Null(SourceReaderDocument.Create(detail, null).OpenedPage);
    }
}
