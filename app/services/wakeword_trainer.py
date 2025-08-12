# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.

import os
import re
import time
import traceback
from pathlib import Path

import numpy as np
import tensorflow as tf
import librosa

# ------------------ NUMBA CACHE FIX ----------------
os.environ["NUMBA_CACHE_DIR"] = "/tmp/numba_cache"
os.makedirs("/tmp/numba_cache", exist_ok=True)
# ---------------------------------------------------

#------------------PATH SET--------------------------
MASTER_WAKE_AUDIO = Path("/tmp/wake_audio")
RAW_AUDIO_BASE = MASTER_WAKE_AUDIO / "raw"
MODEL_BASE = MASTER_WAKE_AUDIO / "models"

os.makedirs(RAW_AUDIO_BASE, exist_ok=True)
os.makedirs(MODEL_BASE, exist_ok=True)
#----------------------------------------------------

# fixed parameters
SR = 16000
N_MFCC = 13
FIXED_FRAMES = 50  # number of time frames for MFCC (tunable)
EPOCHS = 10        # reduced from 20 to avoid overfitting small dataset

_safe_re = re.compile(r'[^A-Za-z0-9_.-]')

def _sanitize(name: str) -> str:
    return _safe_re.sub('_', str(name))

def _mfcc_fixed(y, sr=SR, n_mfcc=N_MFCC, fixed_frames=FIXED_FRAMES):
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    # transpose to (frames, coeffs)
    mfcc = mfcc.T  # shape: (frames, n_mfcc)
    # normalize per-file
    mfcc = (mfcc - mfcc.mean()) / (mfcc.std() + 1e-9)
    # pad or truncate to fixed_frames
    if mfcc.shape[0] < fixed_frames:
        pad = np.zeros((fixed_frames - mfcc.shape[0], n_mfcc), dtype=np.float32)
        mfcc = np.vstack([mfcc, pad])
    else:
        mfcc = mfcc[:fixed_frames, :]
    return mfcc.astype(np.float32)  # (fixed_frames, n_mfcc)

def train_wakeword_model(device_id, filepaths, label):
    """
    Trains a tiny wakeword model and saves a .tflite file.
    Returns: absolute tflite_path (string)
    """

    device_id_safe = _sanitize(device_id)
    label_safe = _sanitize(label)

    print(f"[wakeword] Starting training for device={device_id_safe}, label={label_safe}")
    try:
        samples = []
        labels = []

        # load each audio, validate, compute fixed mfcc
        for path in filepaths:
            try:
                y, sr = librosa.load(path, sr=SR, mono=True)
            except Exception as e:
                raise RuntimeError(f"Failed to load audio file {path}: {e}")

            if y.size < 0.1 * SR:
                # too short
                raise RuntimeError(f"Audio file too short: {path}")

            mfcc = _mfcc_fixed(y, sr=sr)
            samples.append(mfcc)
            labels.append(1)

        # Build some 'negative' examples: silence and small noise
        for _ in range(3):
            noise = np.random.normal(0, 0.05, SR).astype(np.float32)
            mfcc_noise = _mfcc_fixed(noise)
            samples.append(mfcc_noise)
            labels.append(0)

        X = np.stack(samples, axis=0)  # shape (N, fixed_frames, n_mfcc)
        y = np.array(labels).astype(np.float32)

        print(f"[wakeword] Prepared data shapes X={X.shape}, y={y.shape}")

        # Build model: simple but stable shape
        inp_shape = (FIXED_FRAMES, N_MFCC)
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=inp_shape),
            tf.keras.layers.Conv1D(32, 3, activation='relu'),
            tf.keras.layers.MaxPooling1D(2),
            tf.keras.layers.Conv1D(32, 3, activation='relu'),
            tf.keras.layers.MaxPooling1D(2),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])

        # small dataset -> verbose fit minimal
        model.fit(X, y, epochs=EPOCHS, batch_size=max(1, len(X)), verbose=0)

        # convert to tflite
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        tflite_model = converter.convert()

        # filename includes timestamp so we keep history
        timestamp = int(time.time())
        model_filename = f"{device_id_safe}_{label_safe}_{timestamp}.tflite"
        tflite_path = MODEL_BASE / model_filename

        # ensure parent exists (should already)
        tflite_path.parent.mkdir(parents=True, exist_ok=True)

        with open(tflite_path, "wb") as f:
            f.write(tflite_model)

        print(f"[wakeword] Model saved to: {tflite_path}")

        # cleanup raw files (optional)
        try:
            for p in filepaths:
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception:
            pass

        return str(tflite_path)

    except Exception as e:
        tb = traceback.format_exc()
        print("[wakeword] Training failed:", e)
        print(tb)
        raise

