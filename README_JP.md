# potato-skills

[English](README.md)

**最終更新:** 2026-09-26

Cursor 公式プラグイン集 [`cursor/plugins`](https://github.com/cursor/plugins) の Skills を、Claude Code と Codex で読み込める形式に変換した配布リポジトリです。

## 内容

- `skills/claude-code/skills/` — Claude Code 用 Skills（親ディレクトリは検証可能な Claude Code plugin）
- `skills/codex/` — Codex 用 Skills（`agents/openai.yaml` を含む）
- `install.sh` — ユーザー単位またはプロジェクト単位のインストーラ
- `scripts/build_skills.py` — `ref/plugins` から配布物を再生成する変換スクリプト
- `skills/manifest.json` — 変換元、バージョン、互換性上の注意を記録したマニフェスト

変換対象は各 Cursor プラグインの `plugin.json` が `skills` として宣言したものだけです。MCP 設定しか持たないプラグインは Skills ではないため変換しません。重複する2組は、付属ファイルが充実した版または本来のプラグイン側の版に統合しています。
現在の参照 revision からは、各ホスト向けに91個の Skills を生成します。

## インストール

リポジトリを取得します。

```bash
git clone https://github.com/takurot/potato-skills.git
cd potato-skills
```

両方へユーザー単位でインストールします。

```bash
./install.sh
```

片方だけにインストールする場合:

```bash
./install.sh --target claude
./install.sh --target codex
```

プロジェクト単位でインストールする場合:

```bash
./install.sh --target both --scope project --project-dir /path/to/project
```

Claude Code は `<project>/.claude/skills/`、Codex は `<project>/.agents/skills/` に配置されます。

特定の Skill だけを選ぶこともできます。

```bash
./install.sh --list
./install.sh --target codex --skill thermos --skill tdd
```

`--skill` には空でない正確な Skill 名を1つ指定してください。複数選択する場合はオプションを
繰り返し、全 Skill をインストールする場合だけ `--skill` を省略します。

主なオプション:

- `--dry-run` — 書き込まずに予定を表示
- `--force` — 既存 Skill をタイムスタンプ付きバックアップへ移してから更新
- `--scope user|project` — インストール範囲を選択
- `--target claude|codex|both` — 対象を選択

既存の同名 Skill は標準では上書きせず、`skipped` と表示します。同一内容なら `unchanged` です。
バックアップは有効なSkillの探索対象外に保存します。

- Claude Code: ユーザー単位は `~/.claude/skill-backups/`、プロジェクト単位は `<project>/.claude/skill-backups/`。`CLAUDE_CONFIG_DIR` が設定されている場合は `~/.claude` を置き換えます。
- Codex: ユーザー単位は `~/.codex/skill-backups/`、プロジェクト単位は `<project>/.agents/skill-backups/`。`CODEX_HOME` が設定されている場合は `~/.codex` を置き換えます。

強制更新はインストール先と同じファイルシステムでステージングします。既存Skillのバックアップ後に有効化が失敗した場合、元のSkillを自動で復元し、一時ステージングディレクトリを削除します。

## 変換方針

Claude Code と Codex は Skill frontmatter の仕様が異なるため、配布物を分けています。

| Cursor の要素 | Claude Code | Codex |
|---|---|---|
| `name`, `description` | 対応形式へ正規化 | 対応形式へ正規化 |
| `disable-model-invocation` | そのまま保持 | `agents/openai.yaml` の `allow_implicit_invocation: false` に変換 |
| `icon`, `color`, `mode`, `reminder`, `paths` | 未対応項目を除去 | 未対応項目を除去 |
| Skill 内の scripts/references/assets | 保持 | 保持 |
| Cursor の専用 agent 定義 | `references/cursor-agents/` に同梱 | `references/cursor-agents/` に同梱 |
| `.cursor/skills/` への参照 | `.claude/skills/` へ変換 | `.agents/skills/` または `~/.codex/skills/` へ変換 |

名前は小文字 kebab-case に正規化し、壊れた YAML frontmatter も有効な YAML として再出力します。

## 互換性の境界

Skill の文章やローカルスクリプトは移植できますが、Cursor 固有のランタイムそのものは同梱していません。

- Cursor hooks に依存する自動反復や終了割り込みは、Claude Code/Codex では自動実行されません。
- Cursor Canvas は、利用できない場合に通常の HTML 成果物へフォールバックする注記を追加しています。
- MCP を使う Skills は、対応する MCP サーバーを Claude Code/Codex 側で別途設定する必要があります。
- Cursor SDK や Cursor Cloud Agents を操作する Skill は、引き続き Cursor の認証情報とサービスを必要とします。
- 固有名の subagent は自動登録しません。元の agent 定義を `references/cursor-agents/` に同梱しているので、利用可能な汎用 subagent へのプロンプトとして使います。
- `setup-pstack` はホスト別の共有 Markdown ファイルを書き込みます。ホスト自体が設定として自動読込するのではなく、変換済みの pstack Skills が呼び出し時に明示的に読み、そのホストが受理したモデル識別子だけを使用します。

各 Skill の先頭にも、利用ホストで存在しない機能を実行済みと扱わないための互換性注記があります。個別の制約は `skills/manifest.json` で確認できます。

## 再生成

`ref/plugins` を更新した後、次を実行します。

```bash
git clone https://github.com/cursor/plugins.git ref/plugins
python3 scripts/build_skills.py
```

`ref/` はこのリポジトリには含めません。すでに `ref/plugins` がある場合は、そのリポジトリを更新してから変換してください。変換スクリプトは `plugin.json` の `skills` 宣言だけを探索し、`skills/` を決定的に再生成します。

## ライセンス

このリポジトリで独自に作成したインストーラ、変換スクリプト、ドキュメントには[MIT License](LICENSE)を適用します。

変換済みSkillsは、変換元のMITライセンスを引き継ぎます。該当するライセンスは各Skillの `LICENSE` に同梱され、著作権表示はCursor、Lauren Tan、またはAnysphere, Inc.に帰属します。ルートのライセンスはこれらの表示を置き換えません。変換物を再配布するときは、対応する各Skillの `LICENSE` を保持してください。
