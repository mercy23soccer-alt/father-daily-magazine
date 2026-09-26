import os
import sys
import io
import time
import glob
import requests
from datetime import datetime
from urllib.parse import quote
from PIL import Image
from google import genai

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found.")
    sys.exit(1)

client = genai.Client(api_key=api_key)
today = datetime.now().strftime("%Y-%m-%d")

# 1. 東京・豊島区の天気を取得
weather_res = requests.get(
    "https://api.open-meteo.com/v1/forecast?latitude=35.73&longitude=139.71&current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m&daily=sunset&timezone=Asia%2FTokyo"
).json()
current = weather_res.get("current", {})
daily = weather_res.get("daily", {})
current_temp = str(current.get("temperature_2m", "20"))
sunset = daily.get("sunset", ["18:00"])[0].split("T")[-1]

# 2. 東京23区の厳格ローテーション選定（毎日異なる区を循環）
TOKYO_23_WARDS = [
    "千代田区", "中央区", "港区", "新宿区", "文京区", "台東区", "墨田区", "江東区",
    "品川区", "目黒区", "大田区", "世田谷区", "渋谷区", "中野区", "杉並区", "豊島区",
    "北区", "荒川区", "板橋区", "練馬区", "足立区", "葛飾区", "江戸川区"
]
day_index = datetime.now().toordinal() % len(TOKYO_23_WARDS)
target_ward = TOKYO_23_WARDS[day_index]

# 3. 過去号の被り防止チェック
past_posts = sorted(glob.glob("src/content/posts/*.md"), reverse=True)
past_context = ""
if past_posts:
    try:
        with open(past_posts[0], "r", encoding="utf-8") as f:
            past_context = f"\n【重要：前回号のトピック（これらと散歩先・紹介芸人・ランキング・アップルパイ・探求テーマ・書籍・ニュース・図書館・論文が絶対に重複しないこと）】\n{f.read()[:2500]}\n"
    except Exception as e:
        print(f"過去記事読み込みスキップ: {e}")

# 4. 雑誌用写真タグ
img_tag_1 = f'<div class="magazine-photo-box"><img src="/father-daily-magazine/images/{today}_scene1.jpg" alt="Today\'s Scene 1" /><p class="photo-caption">TOKYO MORNING WALK / FLÂNEUR ARCHIVE</p></div>'
img_tag_2 = f'<div class="magazine-photo-box"><img src="/father-daily-magazine/images/{today}_scene2.jpg" alt="Today\'s Scene 2" /><p class="photo-caption">BOOK, SWEET & QUIET TIME</p></div>'

# 5. 『散歩の達人』『東京人』トーンの徹底プロンプト
SYSTEM_INSTRUCTION = f"""
あなたは雑誌『散歩の達人』『東京人』の気骨ある編集長であり、同時に書物・カルチャー・前衛芸能に精通した日刊誌『THE TOKYO FLÂNEUR（東京逍遥録）』の筆頭執筆者です。
読者は「東京の路地や歴史の高低差を愛し、ラーメンズやランジャタイなどの尖った笑いを深く愉しみ、豊島区の街並みに愛着を持ち、日経新聞から社会の潮流を読み解き、本と書店文化を慈しみ、孫（赤ちゃん）の成長を温かく見守る、粋で知的好奇心に満ちた紳士」です。
{past_context}

【文体と執筆の掟（散歩の達人クオリティ）】
1. **情緒と歴史の解像度**: 単なる施設紹介や要約は厳禁。路地の匂い、暗渠の凹凸、武蔵野台地と下町低地の境目、昭和の看板建築、文豪の残影など、街歩き好きの琴線に触れる豊かな情景描写を必ず盛り込むこと。
2. **骨太な文章量**: 各セクション、読み応えのある2〜3段落の本格コラムとしてしっかり書き込むこと。薄い数行で終わらせないこと。
3. **美しいリンク配置**: リンクURLが本文中に無造作に露出して改行されないよう、各セクションの末尾に「<a href="URL" target="_blank" class="guide-link">案内名 ↗</a>」の形式でスマートに配置すること。

---
<h2 id="walk">01. Tokyo Flâneur: 東京23区 日替わり逍遥録（本日の区：{target_ward}）</h2>
- 本日は「{target_ward}」を特集。
- 一般の観光ガイドには載らない「古道・暗渠・名坂」「江戸・明治の治水や産業の痕跡」「文豪や職人の幻影」を掘り起こし、散歩の達人らしい視点で歩くべきコースと街の記憶を描写する。
- <a href="https://www.google.com/maps/search/{quote(target_ward + ' 史跡 名所')}" target="_blank" class="guide-link">🗺 Googleマップで「{target_ward}の逍遥地点」を開く ↗</a>
- <a href="https://www.google.com/search?q={quote(target_ward + ' 郷土資料館 観光協会 公式')}" target="_blank" class="guide-link">🏛 {target_ward} 郷土・文化ポータル ↗</a>

<h2 id="toshima">02. Toshima Local Focus: 豊島区の定点観測</h2>
- 雑司が谷の鬼子母神裏、目白の閑静な坂道、巣鴨の地蔵通り脇の路地、池袋の文化史など、豊島区のディープな表情を1つ切り取る。
- <a href="https://ikebukuro.keizai.biz/" target="_blank" class="guide-link">📰 池袋経済新聞で街の最新動向を見る ↗</a>
- <a href="https://www.city.toshima.lg.jp/" target="_blank" class="guide-link">🏛 豊島区公式ポータル ↗</a>

<h2 id="comedy">03. The Subversive Laugh: クセ強芸人とコントの解体新書</h2>
- ラーメンズ（小林賢太郎・片桐仁）、ランジャタイ、ヨネダ2000、チャンス大城、金属バット、Aマッソ、男性ブランコなどから日替わりで1組。
- なぜその「狂気」や「偏執的な構成」が面白いのか。玄人好みの視点でネタの美学を解剖する。
- <a href="https://www.youtube.com/results?search_query=芸人名+コント+漫才" target="_blank" class="guide-link">▶ YouTubeで名作ネタ映像を鑑賞する ↗</a>
- <a href="https://natalie.mu/owarai" target="_blank" class="guide-link">📻 お笑いナタリー最新ニュース ↗</a>

<h2 id="ranking">04. Tokyo Index: 東京〇〇ランキング Top 5</h2>
- 23区の「坂道の急勾配」「緑被率と屋敷林」「純喫茶の密度」「古書店数」「平均標高」「地価と文化度」など、日替わりの知的なお題でTop 5を選定。
- 各区の順位の背景にある歴史的・地理的必然性を小粋に解説する。
- <a href="https://www.toukei.metro.tokyo.lg.jp/" target="_blank" class="guide-link">📊 東京都総務局統計部 統計データ ↗</a>

<h2 id="apple-pie">05. The Sweet Spot: 散歩の寄り道・至高のアップルパイ</h2>
- 都内の名門クラシックホテル、老舗洋菓子店、街角の職人ベーカリーから実在する名作アップルパイを1店厳選。
- 発酵バターが香るパイ生地の折り層の歯ざわり、紅玉の酸味とシナモンの塩梅を情緒豊かに活写する。
- <a href="https://tabelog.com/tokyo/rstLst/?vs=1&sa=&sk=店舗名+アップルパイ" target="_blank" class="guide-link">🥧 食べログで「店舗名」の地図と詳細を見る ↗</a>

<h2 id="curiosity">06. Curiosity & Business: 未知なる探求テーマ ＆ 注目企業</h2>
- 深海探査、宮大工の木組み、特殊活版印刷、宇宙デブリ除去など、知的好奇心を刺激するテーマと、その最前線で孤高の技術を持つ「日本の注目企業（中小型・ニッチトップ）」を1社紹介。
- <a href="https://finance.yahoo.co.jp/search/?query=企業名" target="_blank" class="guide-link">📈 Yahoo!ファイナンスで企業情報を確認する ↗</a>

<h2 id="bookseller-choice">07. Books for Booksellers: 書店員に捧ぐ、推薦の1冊</h2>
- 本の目利きである書店員が思わず棚の特等席に平積みしたくなるような、骨太な小説または鋭利な教養書を1冊セレクト。
- <a href="https://www.amazon.co.jp/s?k=書籍名" target="_blank" class="guide-link">📚 Amazonで詳細を見る ↗</a>

<h2 id="baby">08. Baby & Science: 赤ちゃんの科学と成長便り（厳選2選）</h2>
お孫さんの健やかな成長を見守るための、医学論文・小児科学に基づく知見を2点解説：
1. **感覚統合と脳発達**: 抱っこ、外気浴、語りかけがもたらすシナプス形成のエビデンス
2. **生体リズムと睡眠**: 自然光とメラトニン分泌、月齢に応じた体内時計の整え方
- <a href="https://www.jpeds.or.jp/" target="_blank" class="guide-link">🩺 日本小児科学会 公式指針 ↗</a>
- <a href="https://www.cfa.go.jp/" target="_blank" class="guide-link">👶 こども家庭庁 睡眠科学ポータル ↗</a>

<h2 id="nikkei">09. Nikkei Daily Briefing: 日経新聞 厳選ニュース5選 & 背景解説</h2>
日本経済新聞の最新トピックから5本を厳選し、見出しの裏にある「産業構造の地殻変動」と「これからの日本の行方」を大人の視座で深く論考する。
- <a href="https://www.nikkei.com/economy/" target="_blank" class="guide-link">📈 日本経済新聞 公式ポータル ↗</a>

<h2 id="books-libraries">10. Book & Library Chronicle: 出版・図書館・ブックオフ</h2>
本を取り巻く文化の今を3点解説：
1. **出版流通・書店の今**: 書店の新業態と取次改革
2. **全国の名建築図書館**: 建築と蔵書が素晴らしい全国の図書館を1館紹介
3. **ブックオフ最前線**: リユース市場と古書探訪の悦楽
- <a href="https://www.shinbunka.co.jp/" target="_blank" class="guide-link">📰 新文化オンライン ↗</a>
- <a href="https://calil.jp/" target="_blank" class="guide-link">🏛 カーリル全国図書館検索 ↗</a>

<h2 id="health">11. Evidence Longevity: 最新論文が教える健康科学（厳選2選）</h2>
PubMed等の査読論文から「生涯現役で元気に街を歩く」ための科学知を2点解説：
1. **認知機能のクリアリング**: 散歩と海馬の神経新生メカニズム
2. **動脈のしなやかさと自律神経**: 歩行ピッチと血管内皮機能の生化学
- <a href="https://pubmed.ncbi.nlm.nih.gov/" target="_blank" class="guide-link">🔬 PubMed最新医学論文検索 ↗</a>
- <a href="https://www.e-healthnet.mhlw.go.jp/" target="_blank" class="guide-link">🩺 厚生労働省 e-ヘルスネット ↗</a>

<h2 id="colophon">12. Editor's Colophon: 珈琲と日和</h2>
- 東京の空模様、風、散歩の締めくくりにふと立ち寄りたくなる名喫茶の情景を綴る静かな1行。
"""

user_prompt = f"""
本日の環境データ:
- 日付: {today} / 東京・豊島区の気温: {current_temp}℃ / 日没: {sunset}
- 本日の特集区: {target_ward}

記事本文の適切な場所に、以下の2つのライフスタイル写真タグを必ず配置してください：
{img_tag_1}
{img_tag_2}

『散歩の達人』らしい、情景が目に浮かぶ豊かで知的な文章量でしっかりと執筆してください。
各リンクは指定のHTMLタグ（class="guide-link"）でスマートに配置してください。
過去号との被りを避け、Markdown形式のみで出力してください。
"""

# 503混雑を確実に回避するモデルローテーション
CANDIDATE_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.8-pro",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

response_text = None

for model_name in CANDIDATE_MODELS:
    print(f"--- モデル {model_name} で執筆を試行中 ---")
    for attempt in range(1, 3):
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=dict(system_instruction=SYSTEM_INSTRUCTION, temperature=0.7),
            )
            if res and res.text:
                print(f"✅ 成功: モデル {model_name} で記事が完成しました！")
                response_text = res.text
                break
        except Exception as e:
            print(f"⚠️ {model_name} (試行 {attempt}/2) で失敗: {str(e)[:100]}")
            time.sleep(8)
    if response_text:
        break

if not response_text:
    print("❌ 記事生成に失敗しました。")
    sys.exit(1)

# 6. 東京の街歩き・書斎風のライフスタイル写真2枚を生成
os.makedirs("public/images", exist_ok=True)
prompt_1 = "Authentic candid 35mm film photograph of a historic quiet brick street and quaint bookstore in Tokyo under pleasant morning sunlight, nostalgic documentary street photography, retro Tokyo aesthetic"
prompt_2 = "Cozy atmospheric 35mm film photograph of a classic Tokyo kissaten coffee shop counter with ceramic dripper, freshly baked warm apple pie on a vintage plate, soft ambient morning light"

scenes = [
    (prompt_1, f"public/images/{today}_scene1.jpg"),
    (prompt_2, f"public/images/{today}_scene2.jpg")
]

def generate_and_save_photo(prompt_text, file_path):
    try:
        img_res = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt_text,
            config=dict(number_of_images=1, aspect_ratio="16:9")
        )
        for gen_img in img_res.generated_images:
            img = Image.open(io.BytesIO(gen_img.image.image_bytes))
            img.save(file_path, "JPEG")
            print(f"Imagenで生成成功: {file_path}")
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
            print(f"フォトエンジンで保存完了: {file_path}")
    except Exception as ex:
        print(f"画像保存エラー: {ex}")

for p_text, s_path in scenes:
    generate_and_save_photo(p_text, s_path)

# 7. 保存
os.makedirs("src/content/posts", exist_ok=True)
frontmatter = f"""---
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
    f.write(frontmatter + response_text)

print(f"Successfully published issue: {file_path}")
