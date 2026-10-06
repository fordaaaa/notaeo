using Notaeo;
using Xunit;

namespace Notaeo.Tests;

public sealed class ThinkingOrbTests
{
    [Theory]
    [InlineData(true, false)]
    [InlineData(false, true)]
    [InlineData(true, true)]
    public void EitherPreferenceKeepsOrbsStill(bool system, bool app)
    {
        for (var i = 0; i < 3; i++)
            Assert.Equal(ThinkingOrbMotion.Sample(0, i, system, app), ThinkingOrbMotion.Sample(99, i, system, app));
    }

    [Fact]
    public void MotionIsBoundedPeriodicAndStaggered()
    {
        for (var i = 0; i < 3; i++)
        for (var time = 0.0; time < 8; time += 0.1)
        {
            var sample = ThinkingOrbMotion.Sample(time, i, false, false);
            var repeat = ThinkingOrbMotion.Sample(time + 4, i, false, false);
            Assert.InRange(sample.Scale, 0.88, 1.12);
            Assert.InRange(sample.X, -3, 3);
            Assert.InRange(sample.Y, -3, 3);
            Assert.InRange(sample.Opacity, 0.65, 0.95);
            Assert.Equal(sample.X, repeat.X, 5);
            Assert.Equal(sample.Scale, repeat.Scale, 5);
        }
        Assert.NotEqual(ThinkingOrbMotion.Sample(0.5, 0, false, false).X, ThinkingOrbMotion.Sample(0.5, 1, false, false).X);
    }
}
