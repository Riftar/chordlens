"""Minimal DSP core: iterative radix-2 FFT, Hann window, framing."""

import math


def fft(buf):
    """In-place iterative Cooley-Tukey FFT. len(buf) must be a power of two."""
    n = len(buf)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            buf[i], buf[j] = buf[j], buf[i]
    length = 2
    while length <= n:
        ang = -2.0 * math.pi / length
        step = complex(math.cos(ang), math.sin(ang))
        half = length // 2
        for start in range(0, n, length):
            w = 1.0 + 0.0j
            for k in range(start, start + half):
                u = buf[k]
                v = buf[k + half] * w
                buf[k] = u + v
                buf[k + half] = u - v
                w *= step
        length <<= 1
    return buf


def hann(n):
    """Hann window of length n."""
    return [0.5 - 0.5 * math.cos(2.0 * math.pi * i / (n - 1)) for i in range(n)]


def frames(samples, size, hop):
    """Yield (offset, sublist) windows; skips the tail if shorter than size."""
    for off in range(0, len(samples) - size + 1, hop):
        yield off, samples[off:off + size]


def block_mean(samples, factor):
    """Cheap low-pass decimation: average each run of `factor` samples."""
    if factor < 2:
        return samples
    out = []
    for i in range(0, len(samples) - factor + 1, factor):
        out.append(sum(samples[i:i + factor]) / factor)
    return out
