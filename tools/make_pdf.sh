#!/bin/bash
# ホスト(Git Bash)で実行: docs/report.md を説明資料のPDFにする
#   Markdown はブラウザ内で marked.js により HTML にし、Edge のヘッドレス印刷で PDF にする（要ネット接続）
# 使い方: make_pdf.sh 出力pdf
set -e
WS=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-$WS/説明資料.pdf}
HTML=$(mktemp -d)/report.html
BASE="file:///$(cygpath -m "$WS/docs")/"

{
cat <<EOF
<!doctype html><html lang="ja"><head><meta charset="utf-8"><base href="$BASE">
<style>
  @page { size: A4; margin: 16mm 15mm; }
  body { font-family: "Yu Gothic", "Meiryo", sans-serif; font-size: 10pt; line-height: 1.6; color: #222; }
  h1 { font-size: 17pt; border-bottom: 2px solid #345; padding-bottom: 4px; }
  h2 { font-size: 13.5pt; border-left: 5px solid #345; padding-left: 8px; margin-top: 1.6em; break-after: avoid; }
  h3 { font-size: 11pt; margin-top: 1.2em; break-after: avoid; }
  table { border-collapse: collapse; width: 100%; margin: .6em 0; break-inside: avoid; }
  th, td { border: 1px solid #999; padding: 3px 6px; vertical-align: top; }
  th { background: #e8edf2; }
  pre code { font-family: "MS Gothic", monospace; }
  pre { background: #f4f4f4; padding: 8px; font-size: 8.5pt; line-height: 1.4; break-inside: avoid; white-space: pre-wrap; }
  code { font-family: "Consolas", "MS Gothic", monospace; font-size: 9pt; }
  p:has(img) { text-align: center; break-inside: avoid; }
  img { max-width: 100%; max-height: 70mm; display: block; margin: .4em auto .2em; }
  em { font-style: normal; font-size: 9pt; color: #555; }
  hr { border: none; border-top: 1px solid #ccc; }
</style></head><body><div id="c"></div>
<script type="text/markdown" id="md">
EOF
cat "$WS/docs/report.md"
cat <<'EOF'
</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<script>document.getElementById('c').innerHTML = marked.parse(document.getElementById('md').textContent);</script>
</body></html>
EOF
} > "$HTML"

"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless=new --disable-gpu \
  --allow-file-access-from-files --no-pdf-header-footer --virtual-time-budget=10000 \
  --print-to-pdf="$(cygpath -w "$OUT")" "file:///$(cygpath -m "$HTML")"
ls -la "$OUT"
