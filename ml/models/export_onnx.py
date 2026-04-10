"""
Export the trained sklearn TF-IDF + RandomForest pipeline to ONNX for optional browser inference.

Run after ``ml/models/train.py``. Outputs under ``extension/models/``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import StringTensorType

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

PIPE_PATH = _ROOT / "ml" / "models" / "saved" / "darkshield_rf.pkl"
OUT_DIR = _ROOT / "extension" / "models"


def export_pipeline_onnx() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pipe = joblib.load(PIPE_PATH)
    clf = pipe.named_steps["clf"]
    classes = [str(c) for c in clf.classes_]
    (OUT_DIR / "labels.json").write_text(json.dumps({"labels": classes}, indent=2), encoding="utf-8")

    options = {id(pipe): {"zipmap": False}}
    onnx_model = convert_sklearn(
        pipe,
        initial_types=[("input", StringTensorType([None, 1]))],
        options=options,
        target_opset=12,
    )
    out_path = OUT_DIR / "darkshield_pipeline.onnx"
    with open(out_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    print("Wrote", out_path)


if __name__ == "__main__":
    export_pipeline_onnx()
