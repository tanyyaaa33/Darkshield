# Extension ONNX models

1. Train the sklearn pipeline: `python ml/models/train.py`
2. Export ONNX: `python ml/models/export_onnx.py` (writes `darkshield_pipeline.onnx` + `labels.json`).
3. For ONNX Runtime Web, copy **`ort.min.js`** and **`ort-wasm-simd.wasm`** (or the `.mjs` bundle your ORT version uses) from `node_modules/onnxruntime-web/dist/` into `extension/vendor/` so `onnx_classifier.js` can load them offline.

If `ort` is missing, the extension falls back to **keyword rules only** (`keyword_rules.json`).
