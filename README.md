# AI副業ラボ — Zenn記事リポジトリ

ProductHuntの新着プロダクトを毎日自動で日本語解説記事にしてZennへ投稿します。

## 仕組み

- **毎日JST 06:00** にGitHub Actionsが自動実行
- ProductHunt上位5件を取得
- Claude Haiku APIで日本語記事を自動生成
- このリポジトリにpush → Zennへ自動公開

## ディレクトリ構成

```
.
├── .github/workflows/   # GitHub Actionsワークフロー
├── scripts/             # 記事生成スクリプト
└── articles/            # 自動生成された記事（Zennに公開）
```

## 必要なSecrets

| 名前 | 説明 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic APIキー |
| `PRODUCTHUNT_TOKEN` | Product Hunt Developer Token |
| `GH_PAT` | GitHub Personal Access Token（repo権限） |
