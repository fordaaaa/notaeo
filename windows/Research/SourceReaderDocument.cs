using System.Text;

namespace Notaeo;

internal sealed record SourceReaderDocument(string Text, int SelectionStart, int? OpenedPage)
{
    internal static SourceReaderDocument Create(SourceDetail source, int? requestedPage)
    {
        var text = new StringBuilder();
        var selected = 0;
        var targetFound = false;
        int? opened = source.Pages.FirstOrDefault()?.Number ?? source.Chunks.FirstOrDefault()?.Pages.Select(page => (int?)page).FirstOrDefault();
        if (source.Pages.Count > 0)
        {
            foreach (var page in source.Pages)
            {
                if (text.Length > 0) text.Append("\r\n\r\n");
                if (page.Number == requestedPage) { selected = text.Length; opened = page.Number; }
                text.Append($"PAGE {page.Number}\r\n\r\n").Append(page.Text);
            }
        }
        else
        {
            foreach (var chunk in source.Chunks)
            {
                if (text.Length > 0) text.Append("\r\n\r\n");
                if (!targetFound && requestedPage.HasValue && chunk.Pages.Contains(requestedPage.Value))
                {
                    selected = text.Length; opened = requestedPage; targetFound = true;
                }
                text.Append(chunk.Text);
            }
        }
        return new(text.ToString(), selected, opened);
    }
}
