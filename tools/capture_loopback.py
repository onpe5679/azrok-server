"""Capture the default Windows playback device through WASAPI loopback."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundcard as sc
import soundfile as sf


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--rate", type=int, default=48_000)
    args = parser.parse_args()

    speaker = sc.default_speaker()
    microphone = sc.get_microphone(id=str(speaker.name), include_loopback=True)
    frames = round(args.rate * args.seconds)
    with microphone.recorder(samplerate=args.rate, channels=2, blocksize=4096) as recorder:
        data = recorder.record(numframes=frames)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.output, data, args.rate, subtype="PCM_16")
    rms = np.sqrt(np.mean(np.square(data), axis=0))
    peak = np.max(np.abs(data), axis=0)
    print(
        json.dumps(
            {
                "speaker": speaker.name,
                "path": str(args.output.resolve()),
                "frames": int(data.shape[0]),
                "channels": int(data.shape[1]),
                "rms": rms.tolist(),
                "peak": peak.tolist(),
                "nonzero_samples": int(np.count_nonzero(np.abs(data) > 1e-5)),
                "total_samples": int(data.size),
                "mean_abs": float(np.mean(np.abs(data))),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
