# GenieGuard 3分ピッチ台本（実装同期版）

## 0:00-0:25 課題
「生成ゲームは出力が毎回違うため、人手QAだけでは短時間で“出荷できるか”を証明しづらいです。」

## 0:25-0:50 解決
「GenieGuardは、自己対戦で壊れるまでテストし、差分パッチを提案し、同一条件で再検証して、証拠を artifacts に保存する出荷前CIです。」

## 0:50-2:10 デモ
「`tools/demo.bat` を実行します。1コマンドで `artifacts/demo_latest/report.html` が開きます。」
「デモケースは固定 (`--demo-case ctf10`) なので、毎回同じ赤→緑が再現されます。」
「加えて、GitHub Pagesで sample report を常時公開しているので、実行せずにブラウザで確認できます。」

「最初に `deadlock_rate / win_skew / exploit_dominance` の before が赤になっていることを確認します。」

「次に `Patch Proposal` の diff を見せます。全置換ではなく `patch_ops` の差分です。」

「最後に after を見ます。同じ seed 条件で再実行して改善し、`terminal_reason` 内訳、`policy win-rate`、`worst case top1` の trace まで残ります。」

## 2:10-2:40 CIとしての説得力
「GitHub Actionsで `pytest` とゲートを毎PRで実行し、落ちたら赤になります。`report.html` と trace は artifact に保存されます。」

## 2:40-3:00 締め
「これはAlphaStarの再現ではなく、AlphaStar的な自己対戦探索の思想をQAに転用した実装です。現在はMVPとして安定運用でき、将来は探索器を学習器へ置換して拡張できます。」
