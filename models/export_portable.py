"""Export portable XGB JSON + metadata sidecar from a training joblib bundle."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _underlying_xgb(model: object):
    if hasattr(model, "get_booster"):
        return model
    if hasattr(model, "calibrated_classifiers_"):
        return model.calibrated_classifiers_[0].estimator
    if hasattr(model, "estimator"):
        return getattr(model, "estimator")
    raise TypeError(f"Cannot extract XGBoost estimator from {type(model)}")


def export_version(version: str) -> None:
    art_dir = ROOT / "models" / "artifacts"
    joblib_path = art_dir / f"{version}.joblib"
    if not joblib_path.exists():
        raise FileNotFoundError(joblib_path)

    bundle = joblib.load(joblib_path)
    model = bundle["model"]
    xgb = _underlying_xgb(model)

    json_path = art_dir / f"{version}.xgb.json"
    meta_path = art_dir / f"{version}.meta.joblib"
    xgb.save_model(json_path)

    meta = {k: v for k, v in bundle.items() if k != "model"}
    meta["xgb_json"] = json_path.name
    joblib.dump(meta, meta_path)
    print(f"Wrote {json_path.name} and {meta_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version", default="xgb-v0.2.2", nargs="?")
    args = parser.parse_args()
    export_version(args.version)


if __name__ == "__main__":
    main()
