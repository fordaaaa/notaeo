// Portable mind-map layout: notebook → source branches → concept leaves.
//
// No WinForms / System.Drawing refs so the net10 test project can exercise
// the real layout used by the WinForms canvas. Positions are unscaled points;
// the canvas scales them by the 60–160% zoom and sizes itself to ScaledSize.
// Collapsed source branches keep their header but hide concept leaves, which
// shrinks the frame. Display names are capped/wrapped for the canvas while
// the full Name stays available for tooltips and the outline. No silent
// truncation: every branch and visible leaf is laid out.
namespace Notaeo;

internal sealed record MindMapLayoutNode(
    string Id,
    string Name,
    string DisplayName,
    string? SourceId,
    IReadOnlyList<int> Pages,
    float X,
    float Y,
    float Width,
    float Height,
    int Depth,
    bool IsCollapsed);

internal sealed record MindMapConnector(
    string FromId,
    string ToId,
    float X1,
    float Y1,
    float X2,
    float Y2);

internal sealed record MindMapLayoutResult(
    IReadOnlyList<MindMapLayoutNode> Nodes,
    IReadOnlyList<MindMapConnector> Connectors,
    float Width,
    float Height,
    int VisibleSources,
    int VisibleConcepts);

internal static class MindMapLayout
{
    internal const float MinZoom = 0.6f;
    internal const float MaxZoom = 1.6f;
    internal const float BranchWidth = 220f;
    internal const float BranchGap = 18f;
    internal const int MaxDisplayChars = 120;
    internal const int MaxLines = 3;

    private const float Padding = 12f;
    private const float RootWidth = 280f;
    private const float RootTop = 12f;
    private const float RootToBranch = 28f;
    private const float LeafInset = 8f;
    private const float HeaderToLeaves = 8f;
    private const float LeafGap = 6f;

    private const int RootCharsPerLine = 36;
    private const int BranchCharsPerLine = 26;
    private const int LeafCharsPerLine = 24;

    internal static int? FirstPage(IReadOnlyList<int> pages) => pages.Count == 0 ? null : pages[0];

    internal static float ClampZoom(float zoom)
    {
        if (float.IsNaN(zoom) || float.IsInfinity(zoom))
        {
            return 1.0f;
        }

        return Math.Clamp(zoom, MinZoom, MaxZoom);
    }

    internal static string DisplayNameFor(string? name)
    {
        if (string.IsNullOrEmpty(name))
        {
            return string.Empty;
        }

        if (name.Length <= MaxDisplayChars)
        {
            return name;
        }

        return name.Substring(0, MaxDisplayChars - 3) + "...";
    }

    internal static int WrappedLines(string? display, int charsPerLine)
    {
        if (string.IsNullOrEmpty(display) || charsPerLine <= 0)
        {
            return 1;
        }

        var lines = (display.Length + charsPerLine - 1) / charsPerLine;
        return Math.Clamp(lines, 1, MaxLines);
    }

    internal static (float Width, float Height) ScaledSize(MindMapLayoutResult result, float zoom)
    {
        ArgumentNullException.ThrowIfNull(result);
        var clamped = ClampZoom(zoom);
        return (result.Width * clamped, result.Height * clamped);
    }

    internal static MindMapLayoutResult Layout(MindMapNode root, IReadOnlySet<string>? collapsed)
    {
        ArgumentNullException.ThrowIfNull(root);
        var collapsedSet = collapsed ?? new HashSet<string>();

        var branches = root.Children ?? [];
        var rootDisplay = DisplayNameFor(root.Name);
        var rootLines = WrappedLines(rootDisplay, RootCharsPerLine);
        var rootHeight = 48f + rootLines * 16f;

        var branchWidth = branches.Count * BranchWidth + Math.Max(0, branches.Count - 1) * BranchGap;
        var totalWidth = Math.Max(RootWidth, branchWidth) + Padding * 2;
        var branchStartX = (totalWidth - branchWidth) / 2f;

        var rootX = (totalWidth - RootWidth) / 2f;
        var branchTop = RootTop + rootHeight + RootToBranch;

        var nodes = new List<MindMapLayoutNode>(1 + branches.Count * 4);
        var connectors = new List<MindMapConnector>(branches.Count * 4);

        nodes.Add(new MindMapLayoutNode(
            root.Id, root.Name ?? string.Empty, rootDisplay,
            root.SourceId, (IReadOnlyList<int>)(root.Pages ?? []),
            rootX, RootTop, RootWidth, rootHeight, 0, false));

        var rootCenterX = rootX + RootWidth / 2f;
        var rootBottom = RootTop + rootHeight;

        float maxColumnBottom = branchTop;
        var visibleConcepts = 0;

        for (var i = 0; i < branches.Count; i++)
        {
            var branch = branches[i];
            var branchDisplay = DisplayNameFor(branch.Name);
            var branchLines = WrappedLines(branchDisplay, BranchCharsPerLine);
            var branchPages = (IReadOnlyList<int>)(branch.Pages ?? []);
            var headerHeight = 54f + branchLines * 14f + (branchPages.Count > 0 ? 12f : 0f);
            var isCollapsed = collapsedSet.Contains(branch.Id);
            var leaves = isCollapsed ? [] : (branch.Children ?? []);

            var x = branchStartX + i * (BranchWidth + BranchGap);
            var y = branchTop;

            nodes.Add(new MindMapLayoutNode(
                branch.Id, branch.Name ?? string.Empty, branchDisplay,
                branch.SourceId, branchPages,
                x, y, BranchWidth, headerHeight, 1, isCollapsed));

            var branchCenterX = x + BranchWidth / 2f;
            connectors.Add(new MindMapConnector(
                root.Id, branch.Id,
                rootCenterX, rootBottom,
                branchCenterX, y));

            var headerBottom = y + headerHeight;
            var leafY = headerBottom + HeaderToLeaves;
            foreach (var leaf in leaves)
            {
                var leafDisplay = DisplayNameFor(leaf.Name);
                var leafLines = WrappedLines(leafDisplay, LeafCharsPerLine);
                var leafPages = (IReadOnlyList<int>)(leaf.Pages ?? []);
                var leafHeight = 36f + leafLines * 12f + (leafPages.Count > 0 ? 12f : 0f);
                var leafWidth = BranchWidth - LeafInset * 2;
                var leafX = x + LeafInset;

                nodes.Add(new MindMapLayoutNode(
                    leaf.Id, leaf.Name ?? string.Empty, leafDisplay,
                    leaf.SourceId, leafPages,
                    leafX, leafY, leafWidth, leafHeight, 2, false));

                connectors.Add(new MindMapConnector(
                    branch.Id, leaf.Id,
                    branchCenterX, headerBottom,
                    leafX + leafWidth / 2f, leafY));

                leafY += leafHeight + LeafGap;
                visibleConcepts++;
            }

            var columnBottom = leaves.Count == 0 ? y + headerHeight : leafY - LeafGap;
            if (columnBottom > maxColumnBottom)
            {
                maxColumnBottom = columnBottom;
            }
        }

        var totalHeight = branches.Count == 0
            ? RootTop + rootHeight + Padding
            : maxColumnBottom + Padding;

        return new MindMapLayoutResult(
            nodes, connectors, totalWidth, totalHeight,
            branches.Count, visibleConcepts);
    }
}
