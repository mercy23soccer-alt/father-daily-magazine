import os
import sys
import io
import time
import glob
import re
import requests
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from PIL import Image
from google import genai

# 日本時間（JST = UTC+9）を明示的に取得
JST = timezone(timedelta(hours=9))
now_jst = datetime.now(JST)
today = now_jst.strftime("%Y-%m-%d")

api_key = os.environ.get("GEMINI_API_KEY")
client = None
if api_key:
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Gemini初期化スキップ: {e}")

# 1. 東京・豊島区の天気を取得
weather_res = requests.get(
    "https://api.open-meteo.com/v1/forecast?latitude=35.73&longitude=139.71&current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m&daily=sunset&timezone=Asia%2FTokyo"
).json()
current = weather_res.get("current", {})
daily = weather_res.get("daily", {})
current_temp = str(current.get("temperature_2m", "20"))
sunset = daily.get("sunset", ["18:00"])[0].split("T")[-1]

# 2. 東京23区の厳格ローテーション選定（JST基準）
TOKYO_23_WARDS = [
    "千代田区", "中央区", "港区", "新宿区", "文京区", "台東区", "墨田区", "江東区",
    "品川区", "目黒区", "大田区", "世田谷区", "渋谷区", "中野区", "杉並区", "豊島区",
    "北区", "荒川区", "板橋区", "練馬区", "足立区", "葛飾区", "江戸川区"
]
day_index = now_jst.toordinal() % len(TOKYO_23_WARDS)
target_ward = TOKYO_23_WARDS[day_index]

# 3. 過去号の被り防止チェック
past_posts = sorted(glob.glob("src/content/posts/*.md"), reverse=True)
past_context = ""
if past_posts:
    try:
        with open(past_posts[0], "r", encoding="utf-8") as f:
            past_context = f"\n【重要：前回号のトピック（これらと重複禁止）】\n{f.read()[:2000]}\n"
    except Exception as e:
        print(f"過去記事読み込みスキップ: {e}")

img_tag_1 = f'<div class="magazine-photo-box"><img src="/father-daily-magazine/images/{today}_scene1.jpg" alt="Today\'s Scene 1" /><p class="photo-caption">TOKYO MORNING WALK / FLÂNEUR ARCHIVE</p></div>'
img_tag_2 = f'<div class="magazine-photo-box"><img src="/father-daily-magazine/images/{today}_scene2.jpg" alt="Today\'s Scene 2" /><p class="photo-caption">BOOK, SWEET & QUIET TIME</p></div>'

# 4. プロンプト
SYSTEM_INSTRUCTION = f"""
あなたは雑誌『散歩の達人』『東京人』の気骨ある編集長であり、日刊誌『THE TOKYO FLÂNEUR（東京逍遥録）』の筆頭執筆者です。
読者は「東京の路地や歴史の高低差を愛し、ラーメンズやランジャタイなどの尖った笑いを深く愉しみ、豊島区の街並みに愛着を持ち、日経新聞から社会の潮流を読み解き、本と書店文化を慈しみ、孫（赤ちゃん）の成長を温かく見守る、粋で知的好奇心に満ちた紳士」です。
{past_context}

【執筆ルール】
- 本文の冒頭にタイトルやメタデータ（title:, date: など）は一切書かないでください。いきなり「01. Tokyo Flâneur」の見出しから書き始めてください。
- 街歩き好きの琴線に触れる豊かな情景描写、路地の匂い、暗渠、坂道、歴史の陰影をしっかりとした文章量で描写してください。
- リンクは各項目の末尾に「<a href="URL" target="_blank" class="guide-link">案内名 ↗</a>」の形式で配置してください。

見出し構成：
<h2 id="walk">01. Tokyo Flâneur: 東京23区 日替わり逍遥録（本日の区：{target_ward}）</h2>
<h2 id="toshima">02. Toshima Local Focus: 豊島区の定点観測</h2>
<h2 id="comedy">03. The Subversive Laugh: クセ強芸人とコントの解体新書</h2>
<h2 id="ranking">04. Tokyo Index: 東京〇〇ランキング Top 5</h2>
<h2 id="apple-pie">05. The Sweet Spot: 散歩の寄り道・至高のアップルパイ</h2>
<h2 id="curiosity">06. Curiosity & Business: 未知なる探求テーマ ＆ 注目企業</h2>
<h2 id="bookseller-choice">07. Books for Booksellers: 書店員に捧ぐ、推薦の1冊</h2>
<h2 id="baby">08. Baby & Science: 赤ちゃんの科学と成長便り（厳選2選）</h2>
<h2 id="nikkei">09. Nikkei Daily Briefing: 日経新聞 厳選ニュース5選 & 背景解説</h2>
<h2 id="books-libraries">10. Book & Library Chronicle: 出版・図書館・ブックオフ</h2>
<h2 id="health">11. Evidence Longevity: 最新論文が教える健康科学（厳選2選）</h2>
<h2 id="colophon">12. Editor's Colophon: 珈琲と日和</h2>
"""

user_prompt = f"""
本日の環境データ: 日付 {today} / 東京・豊島区の気温 {current_temp}℃ / 日没 {sunset} / 特集区 {target_ward}
本文の適切な場所に以下の2枚の写真タグを配置してください：
{img_tag_1}
{img_tag_2}
『散歩の達人』らしい豊かな文章量で執筆してください。Markdown形式のみで出力してください。
"""

response_text = None

if client:
    print("--- Gemini API で執筆中 ---")
    try:
        res = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=user_prompt,
            config=dict(system_instruction=SYSTEM_INSTRUCTION, temperature=0.7),
        )
        if res and res.text and len(res.text) > 800:
            print("✅ 成功: Gemini APIで記事が完成しました！")
            response_text = res.text
    except Exception as e:
        print(f"⚠️ Gemini一時エラー: {str(e)[:100]}")

if not response_text:
    print("--- バックアップAIエンジンで執筆中 ---")
    try:
        combined_prompt = f"{SYSTEM_INSTRUCTION}\n\n---\n{user_prompt}"
        payload = {
            "messages": [{"role": "user", "content": combined_prompt}],
            "model": "openai",
            "seed": int(time.time())
        }
        r = requests.post("https://text.pollinations.ai/", json=payload, timeout=60)
        if r.status_code == 200 and len(r.text) > 800:
            print("✅ 成功: バックアップAIで記事が完成しました！")
            response_text = r.text
    except Exception as ex:
        print(f"バックアップAIエラー: {ex}")

if not response_text or len(response_text) < 500:
    print("❌ 記事生成に失敗しました。")
    sys.exit(1)

clean_text = re.sub(r'^(title:.*?\n|date:.*?\n|temp:.*?\n|sunset:.*?\n|ward:.*?\n|location:.*?\n)+', '', response_text.strip(), flags=re.MULTILINE | re.IGNORECASE).strip()

# 5. 写真生成
os.makedirs("public/images", exist_ok=True)
prompt_1 = "Authentic candid 35mm film photograph of a historic quiet brick street and quaint bookstore in Tokyo under pleasant morning sunlight, nostalgic documentary street photography, retro Tokyo aesthetic"
prompt_2 = "Cozy atmospheric 35mm film photograph of a classic Tokyo kissaten coffee shop counter with ceramic dripper, freshly baked warm apple pie on a vintage plate, soft ambient morning light"

scenes = [
    (prompt_1, f"public/images/{today}_scene1.jpg"),
    (prompt_2, f"public/images/{today}_scene2.jpg")
]

def generate_and_save_photo(prompt_text, file_path):
    if client:
        try:
            img_res = client.models.generate_images(
                model="imagen-3.0-generate-002",
                prompt=prompt_text,
                config=dict(number_of_images=1, aspect_ratio="16:9")
            )
            for gen_img in img_res.generated_images:
                img = Image.open(io.BytesIO(gen_img.image.image_bytes))
                img.save(file_path, "JPEG")
                return
        except Exception:
            pass

    try:
        clean_prompt = quote(prompt_text)
        url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1200&height=675&nologo=true&seed={int(time.time())}"
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(r.content)
    except Exception as ex:
        print(f"画像保存エラー: {ex}")

for p_text, s_path in scenes:
    generate_and_save_photo(p_text, s_path)

# 6. 保存
os.makedirs("src/content/posts", exist_ok=True)
frontmatter_block = f"""---
title: "Issue - {today}"
date: "{today}"
temp: "{current_temp}°C"
sunset: "{sunset}"
ward: "{target_ward}"
location: "Tokyo / Toshima"
---

"""

file_path = f"src/content/posts/{today}.md"
with open(file_path, "w", encoding="utf-8") as f:
    f.write(frontmatter_block + clean_text)

print(f"Successfully published issue: {file_path}")
