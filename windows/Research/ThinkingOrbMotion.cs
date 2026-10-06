namespace Notaeo;

internal readonly record struct OrbSample(double Scale, double X, double Y, double Opacity);

internal static class ThinkingOrbMotion
{
    internal static OrbSample Sample(double time, int index, bool systemReduceMotion, bool appReduceMotion)
    {
        if (systemReduceMotion || appReduceMotion) return new(1, 0, 0, 0.8);
        var phase = time % 4 / 4 * 2 * Math.PI - index * 0.85;
        var wave = Math.Sin(phase);
        return new(1 + 0.08 * wave, 2.5 * Math.Cos(phase), -3 * Math.Max(0, wave) + 1.5, 0.8 + 0.125 * wave);
    }
}
