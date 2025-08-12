# Copyright (c) 2025 Shiladitya Mallick
# This file is part of the Neura - Your Smart Assistant project.
# Licensed under the MIT License - see the LICENSE file for details.



import tensorflow as tf
import numpy as np
import os
import librosa
from pathlib import Path

#------------------PATH SET--------------------------
MASTER_WAKE_AUDIO = Path("/tmp/wake_audio")
RAW_AUDIO_BASE = MASTER_WAKE_AUDIO / "raw"
MODEL_BASE = MASTER_WAKE_AUDIO / "models"

os.makedirs(RAW_AUDIO_BASE, exist_ok=True)
os.makedirs(MODEL_BASE, exist_ok=True)
#----------------------------------------------------

def train_wakeword_model(device_id, filepaths, label):
    samples, labels = [], []

    for path in filepaths:
        y, sr = librosa.load(path, sr=16000)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        samples.append(mfcc.T)
        labels.append(1)

    # Add dummy unknown class
    for _ in range(3):
        y = np.random.randn(16000)
        mfcc = librosa.feature.mfcc(y=y, sr=16000, n_mfcc=13)
        samples.append(mfcc.T)
        labels.append(0)

    max_len = max([s.shape[0] for s in samples])
    X = np.array([np.pad(s, ((0, max_len - s.shape[0]), (0, 0)), mode='constant') for s in samples])
    y = np.array(labels)

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=X.shape[1:]),
        tf.keras.layers.Conv1D(32, 3, activation='relu'),
        tf.keras.layers.MaxPooling1D(2),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    model.fit(X, y, epochs=20, verbose=0)

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()

    tflite_path = MODEL_BASE / f"{device_id}_{label}.tflite"
    with open(tflite_path, "wb") as f:
        f.write(tflite_model)

    return str(tflite_path)
