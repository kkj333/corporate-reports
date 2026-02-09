---
name: tag
description: semverタグを作成してpushする。使い方 /tag
---

# リリースタグ作成

前回タグからの変更を分析し、semver に従ったタグを作成・push する。

---

## Phase 1: 現状把握

以下を実行して状況を把握する:

```bash
git tag -l --sort=-v:refname   # 既存タグ一覧（降順）
git log <最新タグ>..HEAD --oneline  # 前回タグからのコミット
```

タグが存在しない場合は `v0.1.0` をデフォルトとする。

## Phase 2: バージョン判断

コミット履歴を分析し、semver の bump レベルを判断する:

| bump | 条件 | 例 |
|---|---|---|
| **major** | 破壊的変更（API変更、既存機能削除） | `breaking:` prefix、互換性のない変更 |
| **minor** | 新機能追加、スキル追加 | `feat:`、新ファイル追加、新スキル |
| **patch** | バグ修正、ドキュメント更新、リファクタ | `fix:`、`docs:`、`refactor:` |

判断結果をユーザーに提示する:

```
現在: v0.1.0
コミット数: 7
主な変更:
  - fix: API_KEY取得タイミング修正
  - feat: サイドバーTOC追加
  - docs: アーキテクチャ文書追加

提案: v0.2.0 (minor: 新機能追加あり)
```

**ユーザーの承認を得てから次へ進む。**

## Phase 3: タグ作成 & push

ユーザーが承認したバージョンでタグを作成する:

```bash
git tag -a v{VERSION} -m "v{VERSION}: 変更サマリー（1行）"
git push origin v{VERSION}
```

注釈付きタグ (`-a`) を使用する。軽量タグは使わない。
