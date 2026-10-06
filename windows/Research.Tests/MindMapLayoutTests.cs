using Notaeo;
using Xunit;

namespace Notaeo.Tests;

// Portable graph-layout regressions for the Windows mind map.
// Exercises the real MindMapNode DTOs + MindMapLayout (no WinForms),
// covering scaled bounds, collapsed branches, connectors, wrapping caps
// and preservation of source/page actions used by canvas + outline.
public sealed class MindMapLayoutTests
{
    private static MindMapNode Leaf(string id, string name, string sourceId, params int[] pages) =>
        new(id, name, [], sourceId, pages.ToList());

    private static MindMapNode Branch(string id, string name, string sourceId, List<MindMapNode> leaves, params int[] pages) =>
        new(id, name, leaves, sourceId, pages.ToList());

    private static MindMapNode Root(string name, List<MindMapNode> branches) =>
        new("root-1", name, branches, null, []);

    [Fact]
    public void MissingCitationHasNoPageInsteadOfInventingZero()
    {
        Assert.Null(MindMapLayout.FirstPage([]));
        Assert.Equal(3, MindMapLayout.FirstPage([3, 5]));
    }

    [Theory]
    [InlineData(0)]
    [InlineData(1)]
    [InlineData(2)]
    public void SmallMapsKeepEveryNodeInsideCanvas(int sourceCount)
    {
        var branches = Enumerable.Range(0, sourceCount)
            .Select(i => Branch($"b{i}", "Source", $"s{i}", [Leaf($"l{i}", "term", $"s{i}", 1)]))
            .ToList();
        var result = MindMapLayout.Layout(Root("Course", branches), null);
        foreach (var node in result.Nodes)
        {
            Assert.InRange(node.X, 0, result.Width);
            Assert.InRange(node.X + node.Width, 0, result.Width);
            Assert.InRange(node.Y + node.Height, 0, result.Height);
        }
    }

    [Fact]
    public void LayoutIncludesAllBranchesWithoutSilentLimit()
    {
        var branches = new List<MindMapNode>();
        for (var i = 0; i < 60; i++)
        {
            branches.Add(Branch($"branch-{i}", $"Source {i}", $"src-{i}",
                [Leaf($"leaf-{i}-a", $"concept {i} a", $"src-{i}", 1),
                 Leaf($"leaf-{i}-b", $"concept {i} b", $"src-{i}", 2)]));
        }

        var result = MindMapLayout.Layout(Root("Biology", branches), null);

        Assert.Equal(60, result.VisibleSources);
        Assert.Equal(120, result.VisibleConcepts);
        // Root + branches + leaves, nothing silently dropped.
        Assert.Equal(1 + 60 + 120, result.Nodes.Count);
        foreach (var b in branches)
        {
            Assert.Contains(result.Nodes, n => n.Id == b.Id);
        }

        foreach (var node in result.Nodes)
        {
            Assert.InRange(node.X, 0, result.Width);
            Assert.InRange(node.Y, 0, result.Height);
            Assert.True(node.Width > 0);
            Assert.True(node.Height > 0);
            Assert.InRange(node.X + node.Width, 0, result.Width + 0.01f);
            Assert.InRange(node.Y + node.Height, 0, result.Height + 0.01f);
        }
    }

    [Fact]
    public void CollapsedBranchHidesConceptsAndShrinksBounds()
    {
        var root = Root("Biology", [
            Branch("branch-a", "Source A", "src-a",
                [Leaf("leaf-a1", "alpha", "src-a", 1),
                 Leaf("leaf-a2", "beta", "src-a", 2),
                 Leaf("leaf-a3", "gamma", "src-a", 3)], 1),
            Branch("branch-b", "Source B", "src-b",
                [Leaf("leaf-b1", "delta", "src-b", 1)], 1),
        ]);

        var expanded = MindMapLayout.Layout(root, null);
        var collapsed = MindMapLayout.Layout(root, new HashSet<string> { "branch-a" });

        // Collapsed branch keeps its header but hides its leaves.
        Assert.Contains(collapsed.Nodes, n => n.Id == "branch-a" && n.IsCollapsed);
        Assert.DoesNotContain(collapsed.Nodes, n => n.Id == "leaf-a1");
        Assert.DoesNotContain(collapsed.Nodes, n => n.Id == "leaf-a2");
        Assert.DoesNotContain(collapsed.Nodes, n => n.Id == "leaf-a3");
        Assert.Contains(collapsed.Nodes, n => n.Id == "leaf-b1");
        Assert.Contains(collapsed.Nodes, n => n.Id == "branch-b" && !n.IsCollapsed);

        Assert.Equal(2, collapsed.VisibleSources);
        Assert.Equal(1, collapsed.VisibleConcepts);
        Assert.Equal(4, expanded.VisibleConcepts);

        // Hiding a branch must shrink the frame, expanding restores it.
        Assert.True(collapsed.Height < expanded.Height);
        Assert.True(collapsed.Connectors.Count < expanded.Connectors.Count);
    }

    [Fact]
    public void ConnectorsLinkRootToBranchesAndBranchesToLeaves()
    {
        var root = Root("Biology", [
            Branch("branch-a", "Source A", "src-a",
                [Leaf("leaf-a1", "alpha", "src-a", 3)], 1),
            Branch("branch-b", "Source B", "src-b", [], 2),
        ]);

        var result = MindMapLayout.Layout(root, null);
        var byId = result.Nodes.ToDictionary(n => n.Id);

        // One connector per branch from root, one per visible leaf from its branch.
        Assert.Equal(2 + 1, result.Connectors.Count);
        foreach (var c in result.Connectors)
        {
            Assert.True(byId.ContainsKey(c.FromId));
            Assert.True(byId.ContainsKey(c.ToId));
            Assert.True(float.IsFinite(c.X1) && float.IsFinite(c.Y1));
            Assert.True(float.IsFinite(c.X2) && float.IsFinite(c.Y2));
            Assert.InRange(c.X1, 0, result.Width);
            Assert.InRange(c.Y1, 0, result.Height);
            Assert.InRange(c.X2, 0, result.Width);
            Assert.InRange(c.Y2, 0, result.Height);
        }

        Assert.Contains(result.Connectors, c => c.FromId == "root-1" && c.ToId == "branch-a");
        Assert.Contains(result.Connectors, c => c.FromId == "root-1" && c.ToId == "branch-b");
        Assert.Contains(result.Connectors, c => c.FromId == "branch-a" && c.ToId == "leaf-a1");
    }

    [Fact]
    public void DisplayTextCapsLongNamesButPreservesFullForTooltip()
    {
        var longName = new string('m', 300);
        var root = Root(longName, [
            Branch("branch-a", longName, "src-a",
                [Leaf("leaf-a1", longName, "src-a", 3)], 1),
        ]);

        var result = MindMapLayout.Layout(root, null);
        foreach (var node in result.Nodes)
        {
            Assert.Equal(longName, node.Name);
            Assert.True(node.DisplayName.Length <= MindMapLayout.MaxDisplayChars + 3);
            Assert.EndsWith("...", node.DisplayName);
            Assert.NotEqual(longName, node.DisplayName);
        }

        var shortRoot = Root("Biology", []);
        var shortResult = MindMapLayout.Layout(shortRoot, null);
        var shortNode = Assert.Single(shortResult.Nodes);
        Assert.Equal("Biology", shortNode.Name);
        Assert.Equal("Biology", shortNode.DisplayName);
    }

    [Fact]
    public void WrappedHeightGrowsWithLinesButCappedAtThreeLines()
    {
        var oneLine = MindMapLayout.Layout(
            Root("Biology", [Branch("b1", "Short", "s1", [], 1)]), null);
        var twoLineName = new string('w', 60);
        var twoLine = MindMapLayout.Layout(
            Root("Biology", [Branch("b1", twoLineName, "s1", [], 1)]), null);
        var cappedName = new string('w', 400);
        var capped = MindMapLayout.Layout(
            Root("Biology", [Branch("b1", cappedName, "s1", [], 1)]), null);
        var evenLonger = MindMapLayout.Layout(
            Root("Biology", [Branch("b1", cappedName + new string('x', 200), "s1", [], 1)]), null);

        var h1 = oneLine.Nodes.First(n => n.Id == "b1").Height;
        var h2 = twoLine.Nodes.First(n => n.Id == "b1").Height;
        var hCapped = capped.Nodes.First(n => n.Id == "b1").Height;
        var hLonger = evenLonger.Nodes.First(n => n.Id == "b1").Height;

        Assert.True(h2 > h1);
        Assert.True(hCapped >= h2);
        // Beyond the line cap the frame must not keep growing.
        Assert.Equal(hCapped, hLonger);
    }

    [Fact]
    public void ScaledBoundsScaleWithZoomClamped60To160()
    {
        var root = Root("Biology", [
            Branch("branch-a", "Source A", "src-a",
                [Leaf("leaf-a1", "alpha", "src-a", 1)], 1),
        ]);
        var result = MindMapLayout.Layout(root, null);

        var at100 = MindMapLayout.ScaledSize(result, 1.0f);
        Assert.Equal(result.Width, at100.Width, precision: 3);
        Assert.Equal(result.Height, at100.Height, precision: 3);

        var at60 = MindMapLayout.ScaledSize(result, 0.6f);
        Assert.Equal(result.Width * 0.6f, at60.Width, precision: 3);
        Assert.Equal(result.Height * 0.6f, at60.Height, precision: 3);

        var at160 = MindMapLayout.ScaledSize(result, 1.6f);
        Assert.Equal(result.Width * 1.6f, at160.Width, precision: 3);

        // Out-of-range zooms clamp instead of collapsing or exploding.
        var below = MindMapLayout.ScaledSize(result, 0.1f);
        Assert.Equal(at60.Width, below.Width, precision: 3);
        var above = MindMapLayout.ScaledSize(result, 5.0f);
        Assert.Equal(at160.Width, above.Width, precision: 3);

        Assert.Equal(0.6f, MindMapLayout.ClampZoom(0.0f), precision: 5);
        Assert.Equal(1.6f, MindMapLayout.ClampZoom(99.0f), precision: 5);
        Assert.Equal(1.0f, MindMapLayout.ClampZoom(1.0f), precision: 5);
    }

    [Fact]
    public void SourcePageActionsPreservedForOutlineAndCanvas()
    {
        var root = Root("Biology", [
            Branch("branch-a", "Bio text", "src-a",
                [Leaf("leaf-a1", "mitosis", "src-a", 3, 5),
                 Leaf("leaf-a2", "cells", "src-a")], 1, 3),
        ]);

        var result = MindMapLayout.Layout(root, null);
        var branch = Assert.Single(result.Nodes, n => n.Id == "branch-a");
        Assert.Equal("src-a", branch.SourceId);
        Assert.Equal(new List<int> { 1, 3 }, branch.Pages.ToList());
        Assert.Equal(1, branch.Depth);

        var leaf = Assert.Single(result.Nodes, n => n.Id == "leaf-a1");
        Assert.Equal("src-a", leaf.SourceId);
        Assert.Equal(new List<int> { 3, 5 }, leaf.Pages.ToList());
        Assert.Equal(2, leaf.Depth);

        var noPages = Assert.Single(result.Nodes, n => n.Id == "leaf-a2");
        Assert.Equal("src-a", noPages.SourceId);
        Assert.Empty(noPages.Pages);

        var rootNode = Assert.Single(result.Nodes, n => n.Id == "root-1");
        Assert.Null(rootNode.SourceId);
        Assert.Equal(0, rootNode.Depth);
    }

    [Fact]
    public void EmptyMapHasRootOnlyAndPositiveBounds()
    {
        var result = MindMapLayout.Layout(Root("Empty course", []), null);

        var single = Assert.Single(result.Nodes);
        Assert.Equal("root-1", single.Id);
        Assert.Equal("Empty course", single.Name);
        Assert.Empty(result.Connectors);
        Assert.Equal(0, result.VisibleSources);
        Assert.Equal(0, result.VisibleConcepts);
        Assert.True(result.Width > 0);
        Assert.True(result.Height > 0);
    }
}
