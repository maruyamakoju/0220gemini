# GenieGuard 技術書 v0.1

## 目次
1. コンセプトと勝ち筋
2. 要件定義
3. システム全体アーキテクチャ
4. データモデル
5. シミュレータ設計（Deterministic Runner）
6. 自己対戦エンジン（Self-Play / Adversarial Search）
7. 監査（Audit Metrics）
8. 自動パッチ（Patch Synthesizer）
9. 再検証（Regression Gate）
10. UI/UX（デモ設計）
11. Gemini統合（プロンプト設計・ガードレール）
12. 実装計画（4人 x 6時間）
13. デモ台本（3分ピッチ / 1分動画）
14. 失点回避チェック（ルール・DQ対策）
15. 将来拡張（RL/AlphaStar接続の正しい言い方）
付録A. JSONスキーマ
付録B. プロンプトテンプレ
付録C. 擬似コード
付録D. テストケース

## 1. コンセプトと勝ち筋
### 1.1 1行定義
AI生成ゲーム仕様を自己対戦で壊し、差分パッチを提案し、改善を同一条件で再検証して証拠付きで提示する「出荷前CI」。

### 1.2 審査配点に対する強み
- デモ映え: before/after 数字と diff が同画面で出る
- 事業インパクト: QA工数と手戻りを削減する文脈が明確
- 創造性: AI生成物をAIで監査するメタ構造
- ピッチ適合: "Project Genie時代の出荷問題" で一言説明可能

### 1.3 AlphaStar要素の安全な扱い
- 言うこと: 「AlphaStar的な自己対戦探索の思想をQAへ転用」
- 言わないこと: 「AlphaStarを再現した」「RL学習済み」

## 2. 要件定義
### 2.1 MVP必須
- `Generate`: GameSpec(JSON)生成
- `Run`: 決定論シミュレーション
- `Break`: 自己対戦で不具合発見
- `Audit`: 3指標算出
- `Patch`: 最小差分修正案
- `Verify`: 同seedで再実行
- `Evidence`: seed/trace/diff/before-after保存

### 2.2 非目標
- Unity/3D本格統合
- 本格RL学習
- 大規模アセット生成

## 3. システム全体アーキテクチャ
- `SpecGen (Gemini optional)`: 自然言語 -> GameSpec
- `SimRunner`: 決定論で実行
- `SelfPlay`: 複数ポリシーマトリクス
- `AuditEngine`: 指標計算と問題抽出
- `PatchSynth`: ルール優先 + Gemini補助
- `RegressionGate`: 改善判定
- `Artifacts`: JSON/DIFF/TRACE/HTML

閉ループCIゲート（v0.1）:
- `deadlock_rate <= 1%`
- `win_skew <= 10%`
- `exploit_dominance <= 0.25`
- `reproducible == true`

## 4. データモデル
### 4.1 GameSpec
- `meta`, `map`, `spawns`, `rules`, `params`

### 4.2 GameLog
- `seed`, `policy_a`, `policy_b`, `winner`
- `terminal_reason`: `capture|timeout|deadlock|draw`
- `trace`, `state_hashes`, `events`

### 4.3 AuditReport
- `metrics`
- `policy_win_rates`
- `findings`
- `evidence`
- `recommendations`

### 4.4 Patch
- `patch_ops`（差分）
- `rationale`
- `expected_effect`

## 5. シミュレータ設計（Deterministic Runner）
- 乱数は seed 系列のみ
- 同一 `GameSpec + seed + policies` で同結果
- state hash をターンごとに記録（ループ検知用）
- 不正移動は `Stay` として記録

終了条件:
- 旗取得: `capture`
- 上限ターン: `timeout`
- 同一状態の反復閾値到達: `deadlock`

## 6. 自己対戦エンジン
採用ポリシー:
- GreedyShortestPath
- Blocker
- Camper
- RandomEpsilon

運用:
- Policy A x Policy B の全組み合わせ
- 固定seedセットで反復
- 数百試行を短時間で回す

## 7. 監査（Audit Metrics）
- `deadlock_rate`: deadlock割合
- `win_skew`: `abs(win_rate_A - 0.5)`（引き分け除外勝率）
- `exploit_dominance`: `top1_policy_win_rate - top2_policy_win_rate`

## 8. 自動パッチ（Patch Synthesizer）
### 8.1 基本方針
- 最小変更優先
- 壁除去、スポーン/旗移動、ルール/パラメータ調整

### 8.2 ハイブリッド方針
- ルールベースで候補生成
- Geminiは候補選択・理由補強（任意）
- Gemini失敗時は完全ローカルで継続

## 9. 再検証（Regression Gate）
- パッチごとに同seed再実行
- 指標比較（before/after）
- ゲート条件を満たす最初の候補で確定
- 通らなければ最良候補を `SOFT-FAIL` として保存
- 例外ルール: before が既に閾値を満たす場合は `patch_ops=[]` で即 `PASS`（CI誤判定防止）

## 10. UI/UX（デモ設計）
`report.html` 1画面で表示:
- Prompt
- 3指標 before/after テーブル
- Patch diff
- Finding一覧
- Evidence trace 参照
- terminal_reason 内訳
- policy win-rate table
- worst case top1 の seed/trace
- Gate閾値（deadlock_rate<=0.01 / win_skew<=0.10 / exploit_dominance<=0.25）

固定デモケース:
- `examples/demo_case_ctf10/spec.before.json`
- `examples/demo_case_ctf10/seeds.json`
- 実行: `python run_demo.py --demo-case ctf10 --out artifacts/demo_latest --open --fail-on-soft-fail`

## 11. Gemini統合（プロンプト設計）
### 11.1 SpecGen
- JSONのみ返す制約
- スキーマを明示
- 到達可能性制約を付与

### 11.2 PatchSynth
入力:
- 元Spec
- AuditReport
- 候補パッチ群

出力:
- `selected_index`
- `rationale`
- `expected_effect`

## 12. 実装計画（4人 x 6時間）
### Role A: Core Sim + Policies
- 盤面状態遷移
- 4ポリシー実装
- 決定論テスト

### Role B: Audit + Patch
- 監査3指標
- finding/evidence整形
- ルールベースパッチ

### Role C: Pipeline + Artifacts
- Orchestrator
- regression gate
- JSON/NDJSON/diff/trace出力

### Role D: Demo + Docs
- report.html
- README/技術書
- 3分ピッチ準備

## 13. デモ台本
### 3分ピッチ
1. 問題定義（30秒）: 生成ゲームは出荷前QAが難しい
2. 解決策（30秒）: 自己対戦監査CI
3. デモ（90秒）: before失敗 -> patch -> after改善
4. 価値（30秒）: 工数削減・品質保証

### 1分動画
1. Prompt入力
2. Audit赤表示
3. Patch diff表示
4. After緑表示

## 14. 失点回避チェック
- 禁止表現回避: "AlphaStar実装済み" と言わない
- 再現性: seed/trace必須
- 差分提示: 全置換ではなく patch_ops
- デモ安定化: 事前に固定seedセットで撮影
- CI整合: 既に基準を満たすSpecを誤って落とさない（short-circuit PASS）
- デモ確実性: 固定デモケースを使い、必ず Before赤 -> After緑 を再現

## 15. 将来拡張
- RL接続: "将来、方策探索器を学習器に置換可能"
- AlphaStar接続: "自己対戦探索思想を段階導入"
- 大規模ゲーム化: CTF抽象を RTS/MOBAへ一般化

## 付録A. JSONスキーマ
```json
{
  "type": "object",
  "required": ["meta", "map", "spawns", "rules", "params"],
  "properties": {
    "meta": {
      "type": "object",
      "required": ["name", "seed", "version"],
      "properties": {
        "name": {"type": "string"},
        "seed": {"type": "integer"},
        "version": {"type": "string"}
      }
    },
    "map": {
      "type": "object",
      "required": ["w", "h", "walls", "flags"],
      "properties": {
        "w": {"type": "integer", "minimum": 8, "maximum": 20},
        "h": {"type": "integer", "minimum": 8, "maximum": 20},
        "walls": {
          "type": "array",
          "items": {
            "type": "array",
            "minItems": 2,
            "maxItems": 2,
            "items": {"type": "integer"}
          }
        },
        "flags": {
          "type": "object",
          "required": ["A", "B"],
          "properties": {
            "A": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2},
            "B": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2}
          }
        }
      }
    },
    "spawns": {
      "type": "object",
      "required": ["A", "B"],
      "properties": {
        "A": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2},
        "B": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2}
      }
    },
    "rules": {
      "type": "object",
      "required": ["max_turns", "win"],
      "properties": {
        "max_turns": {"type": "integer", "minimum": 30, "maximum": 120},
        "win": {"type": "string", "enum": ["capture_flag"]}
      }
    },
    "params": {
      "type": "object",
      "required": ["move_cost", "capture_range", "deadlock_repeat"],
      "properties": {
        "move_cost": {"type": "integer"},
        "capture_range": {"type": "integer"},
        "deadlock_repeat": {"type": "integer", "minimum": 4, "maximum": 200}
      }
    }
  }
}
```

## 付録B. プロンプトテンプレ
### SpecGen
```text
You output only valid JSON object for GameSpec v0.1.
No markdown. No explanation.
Constraints:
- ensure reachability from each spawn to enemy flag
- map size 8..20
- include meta/map/spawns/rules/params
```

### PatchSynth
```text
Given AuditReport and candidate patch list, choose one patch.
Return JSON:
{"selected_index":0,"rationale":"...","expected_effect":{"deadlock_rate":"down","win_skew":"down","exploit_dominance":"same"}}
```

## 付録C. 擬似コード
```text
spec = generate_spec(prompt)
logs_before = self_play(spec, seeds, policies)
report_before = audit(logs_before)
candidates = synthesize_patches(spec, report_before)
for patch in candidates[:2]:
  spec2 = apply_patch(spec, patch)
  logs_after = self_play(spec2, seeds, policies)
  report_after = audit(logs_after)
  if gate(report_before, report_after):
    save_artifacts(...)
    return PASS
save_best_soft_fail(...)
```

## 付録D. テストケース
- 同seed同policyで結果一致（決定論）
- deadlockが検出される仕様
- 極端な旗位置偏りで `win_skew` 上昇
- 単一戦略勝率偏重で `exploit_dominance` 上昇
- patch適用で before/after JSON diff が生成される
