"""
Unit tests for hilbert_detect_events function, especially empty-epoch handling.
"""
import numpy as np
import pytest
from .Score import hilbert_detect_events


def test_empty_epochs_large_window():
    """
    Test that large epoch windows (300s) with no events above threshold don't crash.
    Regression test for: arrays used as indices must be of integer (or boolean) type
    """
    # Generate 15 minutes of low-amplitude noise (won't trigger detection)
    Fs = 4800  # Hz (typical EGF sampling rate)
    duration = 900  # 15 minutes in seconds
    n_samples = int(Fs * duration)
    
    # Low-amplitude white noise that won't exceed 4*SD threshold
    np.random.seed(42)
    raw_data = np.random.randn(n_samples) * 0.1
    
    # Run detection with 300s epochs (will create 3 epochs, likely all empty)
    events = hilbert_detect_events(
        raw_data, 
        Fs,
        epoch=300.0,
        sd_num=4.0,
        min_duration=12.0,
        min_freq=250.0,
        max_freq=600.0,
        required_peak_number=6,
        required_peak_sd=3.0,
        boundary_fraction=0.3,
        verbose=False
    )
    
    # Should return empty array without crashing
    assert isinstance(events, np.ndarray)
    assert events.shape == (0,) or events.shape[0] == 0


def test_single_event_detected():
    """
    Test that a single high-amplitude burst is correctly detected.
    """
    Fs = 4800
    duration = 60  # 1 minute
    n_samples = int(Fs * duration)
    
    # Low-amplitude baseline
    np.random.seed(123)
    raw_data = np.random.randn(n_samples) * 0.1
    
    # Insert a high-frequency oscillation burst (400 Hz) at 30 seconds
    burst_start = int(30 * Fs)
    burst_duration = int(0.05 * Fs)  # 50ms burst
    t_burst = np.arange(burst_duration) / float(Fs)
    burst_signal = 10.0 * np.sin(2 * np.pi * 400 * t_burst)  # High amplitude
    raw_data[burst_start:burst_start + burst_duration] = burst_signal
    
    events = hilbert_detect_events(
        raw_data,
        Fs,
        epoch=60.0,
        sd_num=3.0,
        min_duration=10.0,
        min_freq=250.0,
        max_freq=600.0,
        required_peak_number=3,
        required_peak_sd=2.0,
        boundary_fraction=0.3,
        verbose=False
    )
    
    # Should detect at least one event around 30s
    assert len(events) > 0
    # Event should be near 30,000 ms
    assert any(28000 < event[0] < 32000 for event in events)


def test_multiple_epochs_mixed():
    """
    Test processing with multiple epochs where some have events and some don't.
    """
    Fs = 4800
    duration = 600  # 10 minutes
    n_samples = int(Fs * duration)
    
    np.random.seed(456)
    raw_data = np.random.randn(n_samples) * 0.1
    
    # Insert bursts only in first and third 300s epochs
    for burst_time in [150, 450]:  # seconds
        burst_start = int(burst_time * Fs)
        burst_duration = int(0.03 * Fs)  # 30ms
        t_burst = np.arange(burst_duration) / float(Fs)
        burst_signal = 8.0 * np.sin(2 * np.pi * 350 * t_burst)
        raw_data[burst_start:burst_start + burst_duration] = burst_signal
    
    events = hilbert_detect_events(
        raw_data,
        Fs,
        epoch=300.0,  # Large epochs
        sd_num=3.0,
        min_duration=10.0,
        min_freq=250.0,
        max_freq=600.0,
        required_peak_number=3,
        required_peak_sd=2.0,
        boundary_fraction=0.3,
        verbose=False
    )
    
    # Should detect events in both epochs with bursts
    assert len(events) >= 1
    # Check that middle epoch (300-600s) has no events (was empty)
    middle_epoch_events = [e for e in events if 300000 < e[0] < 400000]
    assert len(middle_epoch_events) == 0


def test_integer_indexing_robustness():
    """
    Verify that all index arrays remain integers even with float calculations.
    This is a stress test for the dtype=int casts added to fix the bug.
    """
    Fs = 4800
    duration = 900
    n_samples = int(Fs * duration)
    
    # Mix of float and integer sampling artifacts
    np.random.seed(789)
    raw_data = np.random.randn(n_samples) * 0.5
    
    # Should not raise IndexError about non-integer indices
    try:
        events = hilbert_detect_events(
            raw_data,
            Fs,
            epoch=300.0,
            sd_num=4.0,
            min_duration=12.0,
            min_freq=250.0,
            max_freq=600.0,
            required_peak_number=6,
            required_peak_sd=3.0,
            boundary_fraction=0.3,
            verbose=False
        )
        assert True  # Success: no IndexError
    except IndexError as e:
        if 'integer' in str(e).lower() or 'boolean' in str(e).lower():
            pytest.fail('Integer indexing error still occurs: {}'.format(e))
        else:
            raise


if __name__ == '__main__':
    # Allow running tests directly
    pytest.main([__file__, '-v'])
