import os
import re
import json
import requests
import anthropic
from datetime import datetime, timezone, timedelta

# ───────────────────────────────
# 設定
# ───────────────────────────────
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
PRODUCTHUNT_TOKEN  = os.environ["PRODUCTHUNT_TOKEN"]
ARTICLES_DIR       = "articles"
JST                = timezone(timedelta(hours=9))
TODAY              = datetime.now(JST).strftime("%Y-%m-%d")
TOP_N              = 5

EMOJIS = ["🚀", "🛠️", "💡", "🎯", "✨", "🤖", "📊", "🔥", "⚡", "🌟"]

# ───────────────────────────────
# Product Hunt GraphQL APIで上位5件を取得
# ───────────────────────────────
def fetch_producthunt_posts():
    query = """
    {
      posts(order: RANKING, first: 10) {
        edges {
          node {
            id
            name
            tagline
            description
            url
            votesCount
            website
            topics {
              edges {
                node { name }
              }
            }
          }
        }
      }
    }
    """
    res = requests.post(
        "https://api.producthunt.com/v2/api/graphql",
        json={"query": query},
        headers={
            "Authorization": f"Bearer {PRODUCTHUNT_TOKEN}",
            "Content-Type":  "application/json",
        },
        timeout=30,
    )
    res.raise_for_status()
    data = res.json()
    edges = data["data"]["posts"]["edges"]
    posts = []
    for edge in edges[:TOP_N]:
        node   = edge["node"]
        topics = [t["node"]["name"] for t in node["topics"]["edges"]]
        posts.append({
            "name":        node["name"],
            "tagline":     node["tagline"],
            "description": node.get("description") or "",
            "url":         node["url"],
            "website":     node.get("website") or node["url"],
            "votes":       node["votesCount"],
            "topics":      topics,
        })
    return posts


# ───────────────────────────────
# Claude Haiku で日本語記事を生成
# ───────────────────────────────
def generate_article(post: dict, idx: int) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""
以下のProduct Huntプロダクトについて、日本語のZenn記事を書いてください。

プロダクト名: {post['name']}
キャッチコピー: {post['tagline']}
説明: {post['description']}
URL: {post['url']}
公式サイト: {post['website']}
投票数: {post['votes']}票
カテゴリ: {', '.join(post['topics'])}

以下の構成でmarkdown形式で書いてください（frontmatterは不要）：

## {post['name']}とは

（2〜3文で概要を説明）

## 何ができるか

（箇条書きで3〜5個の主要機能）

## こんな人に向いている

（ターゲットユーザーを2〜3文で）

## 料金・使い方

（わかる範囲で。不明な場合は「公式サイトで確認してください」）

## まとめ

（2〜3文で締める。日本市場での可能性にも触れる）

注意：
- 全て日本語で書く
- 専門用語は日本語で説明を添える
- 「〜です・〜ます」調で統一
- 公式サイトへの誘導を末尾に含める
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


# ───────────────────────────────
# Zennフロントマターを付けてファイルを保存
# ───────────────────────────────
def slugify(name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:40]


def save_article(post: dict, body: str, idx: int):
    os.makedirs(ARTICLES_DIR, exist_ok=True)

    slug      = f"ph-{TODAY}-{slugify(post['name'])}"
    filepath  = os.path.join(ARTICLES_DIR, f"{slug}.md")

    if os.path.exists(filepath):
        print(f"スキップ（既存）: {filepath}")
        return

    emoji  = EMOJIS[idx % len(EMOJIS)]
    topics = post["topics"][:3] if post["topics"] else ["AI", "ProductHunt"]
    zenn_topics = [re.sub(r"[^\w]", "", t.lower())[:20] for t in topics[:4]]
    zenn_topics = [t for t in zenn_topics if t][:4]

    frontmatter = f"""---
title: "【ProductHunt話題】{post['name']}——{post['tagline']}"
emoji: "{emoji}"
type: "idea"
topics: {json.dumps(zenn_topics, ensure_ascii=False)}
published: true
---

> **ProductHunt {TODAY} ランキング入り · {post['votes']}票獲得**
>
> 公式サイト: [{post['website']}]({post['website']})

"""

    content = frontmatter + body + f"\n\n---\n*この記事はAI副業ラボがProductHuntの新着情報をもとに自動生成したものです。*\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ 生成完了: {filepath}")


# ───────────────────────────────
# エントリーポイント
# ───────────────────────────────
def main():
    print(f"=== ProductHunt 記事生成 {TODAY} ===")

    print("Product Hunt からデータ取得中...")
    posts = fetch_producthunt_posts()
    print(f"{len(posts)}件取得しました")

    for idx, post in enumerate(posts):
        print(f"\n[{idx+1}/{len(posts)}] {post['name']} ({post['votes']}票)")
        try:
            body = generate_article(post, idx)
            save_article(post, body, idx)
        except Exception as e:
            print(f"❌ エラー: {e}")
            continue

    print("\n=== 完了 ===")


if __name__ == "__main__":
    main()
