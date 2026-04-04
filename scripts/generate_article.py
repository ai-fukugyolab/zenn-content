# v2: タイトル日本語化・URL修正・記事品質向上
import os
import re
import json
import requests
import anthropic
from datetime import datetime, timezone, timedelta

ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
PRODUCTHUNT_TOKEN  = os.environ["PRODUCTHUNT_TOKEN"]
ARTICLES_DIR       = "articles"
JST                = timezone(timedelta(hours=9))
TODAY              = datetime.now(JST).strftime("%Y-%m-%d")
TOP_N              = 5
EMOJIS = ["🚀", "🛠️", "💡", "🎯", "✨", "🤖", "📊", "🔥", "⚡", "🌟"]

def fetch_producthunt_posts():
    query = """{ posts(order: RANKING, first: 10) { edges { node {
        id name tagline description url votesCount website
        topics { edges { node { name } } }
    } } } }"""
    res = requests.post(
        "https://api.producthunt.com/v2/api/graphql",
        json={"query": query},
        headers={"Authorization": f"Bearer {PRODUCTHUNT_TOKEN}", "Content-Type": "application/json"},
        timeout=30,
    )
    res.raise_for_status()
    edges = res.json()["data"]["posts"]["edges"]
    posts = []
    for edge in edges[:TOP_N]:
        node = edge["node"]
        topics = [t["node"]["name"] for t in node["topics"]["edges"]]
        website = node.get("website") or ""
        if not website or "producthunt.com/r/" in website:
            website = node["url"]
        posts.append({
            "name": node["name"], "tagline": node["tagline"],
            "description": node.get("description") or "",
            "url": node["url"], "website": website,
            "votes": node["votesCount"], "topics": topics,
        })
    return posts

def generate_article(post: dict, idx: int) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""以下のProduct Huntプロダクトについて、日本語のZenn記事を書いてください。

プロダクト名: {post['name']}
キャッチコピー: {post['tagline']}
説明: {post['description']}
ProductHunt URL: {post['url']}
公式サイト: {post['website']}
投票数: {post['votes']}票
カテゴリ: {', '.join(post['topics'])}

以下を出力してください：
1行目: 記事タイトル（日本語で魅力的に。例：「AIで議事録を自動生成——NotionAIの使い方完全ガイド」）
2行目: （空行）
3行目以降: 記事本文（markdown）

本文構成：
## {post['name']}とは
（2〜3文で概要）

## 主な機能
（箇条書きで3〜5個）

## こんな人に向いている
（2〜3文）

## 料金・始め方
（わかる範囲で。不明なら「公式サイトで確認してください」）

## まとめ
（2〜3文。日本市場での可能性にも触れる）

注意：全て日本語・です・ます調・末尾に公式サイトへの誘導を含める"""

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=1400,
        messages=[{"role": "user", "content": prompt}],
    )
    lines = msg.content[0].text.strip().split("\n")
    ja_title = lines[0].strip().lstrip("#").strip()
    body = "\n".join(lines[2:]).strip() if len(lines) > 2 else msg.content[0].text
    return {"title": ja_title, "body": body}

def slugify(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")[:40]

def save_article(post: dict, result: dict, idx: int):
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    slug = f"ph-{TODAY}-{slugify(post['name'])}"
    filepath = os.path.join(ARTICLES_DIR, f"{slug}.md")
    if os.path.exists(filepath):
        print(f"スキップ（既存）: {filepath}")
        return
    emoji = EMOJIS[idx % len(EMOJIS)]
    zenn_topics = [re.sub(r"[^\w]", "", t.lower())[:20] for t in post["topics"][:4]]
    zenn_topics = [t for t in zenn_topics if t][:4] or ["producthunt", "ai"]
    ja_title = result["title"] or f"【ProductHunt】{post['name']}"
    content = f"""---
title: "{ja_title}"
emoji: "{emoji}"
type: "idea"
topics: {json.dumps(zenn_topics, ensure_ascii=False)}
published: true
---

> **ProductHunt {TODAY} ランキング入り · {post['votes']}票獲得**
>
> ProductHunt: [{post['name']}]({post['url']}) | 公式: [{post['website']}]({post['website']})

{result['body']}

---
*この記事はAI副業ラボがProductHuntの新着情報をもとに自動生成したものです。*
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ {filepath}")
    print(f"   タイトル: {ja_title}")

def main():
    print(f"=== ProductHunt 記事生成 {TODAY} ===")
    posts = fetch_producthunt_posts()
    print(f"{len(posts)}件取得")
    for idx, post in enumerate(posts):
        print(f"\n[{idx+1}/{len(posts)}] {post['name']} ({post['votes']}票)")
        try:
            result = generate_article(post, idx)
            save_article(post, result, idx)
        except Exception as e:
            print(f"❌ {e}")
    print("\n=== 完了 ===")

if __name__ == "__main__":
    main()
