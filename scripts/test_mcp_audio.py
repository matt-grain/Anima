#!/usr/bin/env python3
"""Test audio playback methods to find what works in MCP context."""

import subprocess
import tempfile
import wave
import io
import os
import sys

def generate_beep() -> bytes:
    """Generate a simple beep WAV."""
    import struct
    sample_rate = 22050
    duration = 0.5
    frequency = 440
    samples = int(sample_rate * duration)
    
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for i in range(samples):
            import math
            value = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * i / sample_rate))
            w.writeframes(struct.pack('<h', value))
    return buf.getvalue()

def test_pygame():
    """Test pygame mixer."""
    print("Testing pygame...")
    try:
        import pygame
        pygame.mixer.init(frequency=22050, size=-16, channels=1)
        sound = pygame.mixer.Sound(buffer=generate_beep())
        sound.play()
        pygame.time.wait(600)
        print("  pygame: OK")
        return True
    except Exception as e:
        print(f"  pygame: FAILED - {e}")
        return False

def test_powershell_playsync():
    """Test PowerShell SoundPlayer."""
    print("Testing PowerShell PlaySync...")
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(generate_beep())
            tmp = f.name
        
        ps = f'$p = New-Object System.Media.SoundPlayer("{tmp}"); $p.PlaySync(); Remove-Item "{tmp}" -EA 0'
        result = subprocess.run(
            ["powershell", "-Command", ps],
            capture_output=True,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
            timeout=5
        )
        print(f"  PowerShell PlaySync: OK (returncode={result.returncode})")
        return True
    except Exception as e:
        print(f"  PowerShell PlaySync: FAILED - {e}")
        return False

def test_powershell_detached():
    """Test PowerShell detached."""
    print("Testing PowerShell detached...")
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(generate_beep())
            tmp = f.name
        
        ps = f'$p = New-Object System.Media.SoundPlayer("{tmp}"); $p.PlaySync(); Remove-Item "{tmp}" -EA 0'
        proc = subprocess.Popen(
            ["powershell", "-Command", ps],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x08000000 | 0x00000008,  # CREATE_NO_WINDOW | DETACHED_PROCESS
        )
        proc.wait(timeout=5)
        print(f"  PowerShell detached: OK (returncode={proc.returncode})")
        return True
    except Exception as e:
        print(f"  PowerShell detached: FAILED - {e}")
        return False

if __name__ == "__main__":
    print(f"Python: {sys.executable}")
    print(f"OPENBLAS_NUM_THREADS: {os.environ.get('OPENBLAS_NUM_THREADS', 'not set')}")
    print()
    test_pygame()
    print()
    test_powershell_playsync()
    print()
    test_powershell_detached()
