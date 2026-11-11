"""Model evaluation metrics for multiclass PA outcomes."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import confusion_matrix, log_loss

from data_pipeline.features.constants import OUTCOME_CLASSES


def multiclass_brier(y_true: list[str], probas: np.ndarray) -> float:
    y_idx = [OUTCOME_CLASSES.index(y) for y in y_true]
    y_onehot = np.zeros_like(probas)
    y_onehot[np.arange(len(y_idx)), y_idx] = 1.0
    return float(np.mean(np.sum((probas - y_onehot) ** 2, axis=1)))


def evaluate_multiclass(y_true: list[str], probas: np.ndarray) -> dict:
    labels = list(OUTCOME_CLASSES)
    mask = [y in labels for y in y_true]
    y_f = [y for y, m in zip(y_true, mask) if m]
    p_f = probas[np.array(mask)]
    if len(y_f) == 0:
        return {"n": 0}
    ll = float(log_loss(y_f, p_f, labels=labels))
    brier = multiclass_brier(y_f, p_f)
    pred_idx = np.argmax(p_f, axis=1)
    pred_labels = [labels[i] for i in pred_idx]
    cm = confusion_matrix(y_f, pred_labels, labels=labels)
    true_idx = [labels.index(y) for y in y_f]
    accuracy = float(np.mean(np.array(pred_idx) == np.array(true_idx)))
    return {
        "n": len(y_f),
        "log_loss": ll,
        "multiclass_brier": brier,
        "accuracy_argmax": accuracy,
        "confusion_matrix": cm.tolist(),
        "labels": labels,
    }
