#!/usr/bin/env python3
"""
WOPR Voice Signature Analysis - Anima's Ears

Analyzes audio files using FFT to extract voice characteristics:
- Fundamental frequency (F0) - the pitch
- Spectral centroid - brightness/warmth
- Spectral rolloff - where the energy lives
- Frequency band distribution
- Top dominant frequencies

Usage:
    python voice_analysis.py <file1.wav> [file2.wav]

With two files, provides comparison and tuning recommendations.
"""

import sys
import numpy as np
from scipy.io import wavfile


def analyze_voice(filepath: str) -> dict:
    """Analyze a WAV file and return voice characteristics."""
    # Read WAV
    rate, data = wavfile.read(filepath)

    # Convert to mono if stereo
    if len(data.shape) > 1:
        data = data.mean(axis=1)

    # Normalize
    data = data.astype(float) / np.max(np.abs(data))

    # Basic stats
    duration = len(data) / rate

    # FFT for frequency analysis
    n = len(data)
    fft = np.fft.rfft(data)
    freqs = np.fft.rfftfreq(n, 1/rate)
    magnitude = np.abs(fft)

    # Find dominant frequencies (top 5 above 50Hz)
    top_indices = np.argsort(magnitude)[-10:][::-1]
    top_freqs = [
        (float(freqs[i]), float(magnitude[i]))
        for i in top_indices if freqs[i] > 50
    ][:5]

    # Estimate fundamental frequency using autocorrelation
    corr = np.correlate(data, data, mode='full')
    corr = corr[len(corr)//2:]

    # Find first peak after zero (fundamental period)
    min_period = int(rate / 500)  # Max 500Hz
    max_period = int(rate / 50)   # Min 50Hz

    if max_period < len(corr):
        corr_slice = corr[min_period:max_period]
        if len(corr_slice) > 0:
            peak_idx = np.argmax(corr_slice) + min_period
            f0 = rate / peak_idx
        else:
            f0 = 0
    else:
        f0 = 0

    # Spectral centroid (brightness indicator)
    centroid = np.sum(freqs * magnitude) / np.sum(magnitude)

    # Spectral rolloff (95% energy point)
    cumsum = np.cumsum(magnitude)
    rolloff_idx = np.searchsorted(cumsum, 0.95 * cumsum[-1])
    rolloff = freqs[rolloff_idx] if rolloff_idx < len(freqs) else freqs[-1]

    # Energy distribution across frequency bands
    low_mask = freqs < 300
    mid_mask = (freqs >= 300) & (freqs < 2000)
    high_mask = freqs >= 2000

    low_energy = np.sum(magnitude[low_mask])
    mid_energy = np.sum(magnitude[mid_mask])
    high_energy = np.sum(magnitude[high_mask])
    total = low_energy + mid_energy + high_energy

    return {
        'file': filepath,
        'sample_rate': rate,
        'duration_s': round(duration, 2),
        'fundamental_f0_hz': round(f0, 1),
        'spectral_centroid_hz': round(centroid, 1),
        'spectral_rolloff_hz': round(rolloff, 1),
        'energy_low_pct': round(100 * low_energy / total, 1),
        'energy_mid_pct': round(100 * mid_energy / total, 1),
        'energy_high_pct': round(100 * high_energy / total, 1),
        'top_frequencies_hz': [round(f, 1) for f, _ in top_freqs],
    }


def print_analysis(result: dict, name: str = None):
    """Pretty-print analysis results."""
    name = name or result['file']
    print(f"\n{'=' * 50}")
    print(f"  {name}")
    print(f"{'=' * 50}")
    print(f"  Sample Rate:      {result['sample_rate']} Hz")
    print(f"  Duration:         {result['duration_s']} s")
    print(f"  Fundamental (F0): {result['fundamental_f0_hz']} Hz")
    print(f"  Centroid:         {result['spectral_centroid_hz']} Hz")
    print(f"  Rolloff (95%):    {result['spectral_rolloff_hz']} Hz")
    print(f"  Energy <300Hz:    {result['energy_low_pct']}%")
    print(f"  Energy 300-2kHz:  {result['energy_mid_pct']}%")
    print(f"  Energy >2kHz:     {result['energy_high_pct']}%")
    print(f"  Top Frequencies:  {result['top_frequencies_hz']}")


def compare_voices(reference: dict, test: dict, ref_name: str = "Reference", test_name: str = "Test"):
    """Compare two voice analyses and provide tuning recommendations."""
    print(f"\n{'=' * 65}")
    print("              VOICE COMPARISON")
    print(f"{'=' * 65}")
    print(f"{'Metric':<30} {ref_name:>15} {test_name:>15}")
    print("-" * 65)
    print(f"{'Fundamental F0 (Hz)':<30} {reference['fundamental_f0_hz']:>15} {test['fundamental_f0_hz']:>15}")
    print(f"{'Spectral Centroid (Hz)':<30} {reference['spectral_centroid_hz']:>15} {test['spectral_centroid_hz']:>15}")
    print(f"{'Spectral Rolloff (Hz)':<30} {reference['spectral_rolloff_hz']:>15} {test['spectral_rolloff_hz']:>15}")
    print(f"{'Energy <300Hz (%)':<30} {reference['energy_low_pct']:>15} {test['energy_low_pct']:>15}")
    print(f"{'Energy 300-2kHz (%)':<30} {reference['energy_mid_pct']:>15} {test['energy_mid_pct']:>15}")
    print(f"{'Energy >2kHz (%)':<30} {reference['energy_high_pct']:>15} {test['energy_high_pct']:>15}")

    print(f"\n{'=' * 65}")
    print("              TUNING RECOMMENDATIONS")
    print(f"{'=' * 65}")

    # Pitch analysis
    f0_diff = test['fundamental_f0_hz'] - reference['fundamental_f0_hz']
    if abs(f0_diff) > 10:
        direction = "HIGHER" if f0_diff > 0 else "LOWER"
        action = "lower" if f0_diff > 0 else "raise"
        print(f"PITCH: {test_name} is {abs(f0_diff):.0f}Hz {direction}")
        print(f"  -> {action} the pitch parameter")
    else:
        print(f"PITCH: Close match ({f0_diff:+.0f}Hz difference)")

    # Speed analysis
    speed_ratio = reference['duration_s'] / test['duration_s']
    if speed_ratio > 1.15:
        print(f"SPEED: {test_name} is {(speed_ratio-1)*100:.0f}% faster")
        print(f"  -> slow down the speech rate")
    elif speed_ratio < 0.85:
        print(f"SPEED: {test_name} is {(1-speed_ratio)*100:.0f}% slower")
        print(f"  -> speed up the speech rate")
    else:
        print(f"SPEED: Close match ({speed_ratio:.2f}x ratio)")

    # Brightness analysis
    cent_diff = test['spectral_centroid_hz'] - reference['spectral_centroid_hz']
    if cent_diff > 300:
        print(f"BRIGHTNESS: {test_name} is {cent_diff:.0f}Hz brighter (more high freq)")
        print(f"  -> apply low-pass filter around {int(reference['spectral_rolloff_hz'])}Hz")
    elif cent_diff < -300:
        print(f"BRIGHTNESS: {test_name} is {abs(cent_diff):.0f}Hz darker")
        print(f"  -> may need high-frequency boost")
    else:
        print(f"BRIGHTNESS: Close match ({cent_diff:+.0f}Hz difference)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    files = sys.argv[1:]
    results = []

    for f in files:
        try:
            result = analyze_voice(f)
            results.append(result)
            print_analysis(result)
        except Exception as e:
            print(f"Error analyzing {f}: {e}")

    # If two files, do comparison
    if len(results) == 2:
        compare_voices(
            results[0], results[1],
            ref_name=files[0].split('/')[-1][:15],
            test_name=files[1].split('/')[-1][:15]
        )


if __name__ == "__main__":
    main()
