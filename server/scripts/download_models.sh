#!/usr/bin/env bash
# Fetches the two OpenCV Zoo ONNX models the vision service needs.
set -euo pipefail
dir="$(cd "$(dirname "$0")/.." && pwd)/models"
mkdir -p "$dir"
base="https://github.com/opencv/opencv_zoo/raw/main/models"
curl -sSL -o "$dir/face_detection_yunet_2023mar.onnx" "$base/face_detection_yunet/face_detection_yunet_2023mar.onnx"
curl -sSL -o "$dir/face_recognition_sface_2021dec.onnx" "$base/face_recognition_sface/face_recognition_sface_2021dec.onnx"
echo "models ready in $dir"
