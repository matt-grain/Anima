#!/usr/bin/env python3
"""
WOPR Voice Filter - Joshua's Sound Signature

Applies vintage computer voice processing:
1. Low-pass filter - removes harsh high frequencies for warmth
2. Room reverb - adds that cold 80s mainframe room echo

Usage:
    python wopr_filter.py <input.wav> <output.wav> [--cutoff 2800] [--delay 40] [--decay 0.4]
"""

import argparse
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter


def wopr_filter(
    input_path: str,
    output_path: str,
    cutoff_hz: int = 2800,
    reverb_delay_ms: int = 40,
    reverb_decay: float = 0.4,
) -> str:
    """
    Apply WOPR-style processing to audio.

    Args:
        input_path: Input WAV file
        output_path: Output WAV file
        cutoff_hz: Low-pass filter cutoff (lower = warmer, default 2800)
        reverb_delay_ms: Echo delay in ms (default 40, small room feel)
        reverb_decay: Echo decay factor (default 0.4)

    Returns:
        Output file path
    """
    # Read input
    rate, data = wavfile.read(input_path)
    original_dtype = data.dtype

    # Convert to float for processing
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.uint8:
        data = (data.astype(np.float32) - 128) / 128.0

    # Handle stereo by processing each channel
    if len(data.shape) > 1:
        # Process stereo
        processed_channels = []
        for ch in range(data.shape[1]):
            processed = _process_mono(data[:, ch], rate, cutoff_hz, reverb_delay_ms, reverb_decay)
            processed_channels.append(processed)
        # Combine back, padding shorter channel
        max_len = max(len(ch) for ch in processed_channels)
        result = np.zeros((max_len, len(processed_channels)), dtype=np.float32)
        for i, ch in enumerate(processed_channels):
            result[:len(ch), i] = ch
    else:
        # Process mono
        result = _process_mono(data, rate, cutoff_hz, reverb_delay_ms, reverb_decay)

    # Normalize to prevent clipping
    result = result / np.max(np.abs(result)) * 0.9

    # Convert back to original format
    if original_dtype == np.int16:
        output = (result * 32767).astype(np.int16)
    elif original_dtype == np.int32:
        output = (result * 2147483647).astype(np.int32)
    else:
        output = (result * 32767).astype(np.int16)

    wavfile.write(output_path, rate, output)

    print(f"WOPR filter applied:")
    print(f"  Input:     {input_path}")
    print(f"  Output:    {output_path}")
    print(f"  Low-pass:  {cutoff_hz}Hz cutoff")
    print(f"  Reverb:    {reverb_delay_ms}ms delay, {reverb_decay} decay")

    return output_path


def _process_mono(
    data: np.ndarray,
    rate: int,
    cutoff_hz: int,
    reverb_delay_ms: int,
    reverb_decay: float,
) -> np.ndarray:
    """Process a mono audio signal."""

    # 1. LOW-PASS FILTER (vintage warmth)
    nyquist = rate / 2
    normalized_cutoff = min(cutoff_hz / nyquist, 0.99)  # Ensure valid range
    b, a = butter(4, normalized_cutoff, btype='low')
    filtered = lfilter(b, a, data)

    # 2. ROOM REVERB (computer room echo)
    delay_samples = int(rate * reverb_delay_ms / 1000)

    # Create output buffer with room for echoes
    num_echoes = 4
    reverb = np.zeros(len(filtered) + delay_samples * num_echoes)
    reverb[:len(filtered)] = filtered

    # Add multiple reflections (simulates room acoustics)
    echo_profile = [
        (1, 0.35),   # First reflection - strongest
        (2, 0.20),   # Second reflection
        (3, 0.10),   # Third reflection
        (4, 0.05),   # Fourth reflection - fading
    ]

    for delay_mult, base_gain in echo_profile:
        delay = delay_samples * delay_mult
        gain = base_gain * (reverb_decay ** (delay_mult - 1))
        reverb[delay:delay + len(filtered)] += filtered * gain

    return reverb


def main():
    parser = argparse.ArgumentParser(
        description="Apply WOPR voice filter (low-pass + reverb)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python wopr_filter.py input.wav output.wav

  # Warmer, more muffled (lower cutoff)
  python wopr_filter.py input.wav output.wav --cutoff 2000

  # More echo (larger room feel)
  python wopr_filter.py input.wav output.wav --delay 80 --decay 0.5

  # Full JOSHUA mode
  python wopr_filter.py input.wav output.wav --cutoff 2500 --delay 50 --decay 0.45
        """
    )
    parser.add_argument("input", help="Input WAV file")
    parser.add_argument("output", help="Output WAV file")
    parser.add_argument("--cutoff", type=int, default=2800,
                        help="Low-pass filter cutoff in Hz (default: 2800)")
    parser.add_argument("--delay", type=int, default=40,
                        help="Reverb delay in ms (default: 40)")
    parser.add_argument("--decay", type=float, default=0.4,
                        help="Reverb decay factor 0-1 (default: 0.4)")

    args = parser.parse_args()

    wopr_filter(
        args.input,
        args.output,
        cutoff_hz=args.cutoff,
        reverb_delay_ms=args.delay,
        reverb_decay=args.decay,
    )


if __name__ == "__main__":
    main()
