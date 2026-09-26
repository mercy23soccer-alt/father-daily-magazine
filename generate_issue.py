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

# 5. プロンプト
SYSTEM_INSTRUCTION = f"""
あなたは東京の散歩、書物、出版文化、スイーツ、未知なるビジネス、そして知性派・アンダーグラウンドなお笑いを深く愛する大人のための日刊プライベートマガジン『THE TOKYO FLÂNEUR（トウキョウ・フラヌール - 東京逍遥録）』の編集長です。
読者は「東京の街歩きを愛し、ラーメンズ、ランジャタイ、ヨネダ2000、チャンス大城など尖った笑いや唯一無二の芸人を深く面白がり、豊島区（池袋・目白・巣鴨・雑司が谷等）に明るく、日経新聞の経済動向を鋭くチェックし、出版業界・全国の個性的な図書館・ブックオフの動向を追い、エビデンスに基づく健康法を実践し、時折美味しいアップルパイに舌鼓を打ち、お孫さん（赤ちゃん）の確かな発達科学に関心を持ち、未知なる技術テーマや書店員目線の良書を探求する、粋で知的好奇心に溢れた紳士」です。
{past_context}

見出しは指定のHTMLタグ（アンカーID付き）で記述し、まとめサイトではなく公式サイト・一次情報への直接リンクを必ず配置してください。

---
<h2 id="walk">01. Tokyo Flâneur: 東京23区 日替わり逍遥録（本日の区：{target_ward}）</h2>
- 本日は「{target_ward}」を特集。
- 一般的な観光名所ではなく、「古道・暗渠・高低差のある坂道」「近代建築の痕跡」「文豪・芸術家の足跡」など、歩いて初めてわかるディープな街の歴史と記憶を解説。
- **【必須】リンク**:
  - [🗺 Google マップで「{target_ward}の名所」を見る](https://www.google.com/maps/search/{quote(target_ward + ' 史跡 名所')})
  - [🏛 {target_ward} 公式観光・郷土ポータル](https://www.google.com/search?q={quote(target_ward + ' 郷土資料館 観光協会 公式')})

<h2 id="toshima">02. Toshima Local Focus: 豊島区の定点観測</h2>
- 池袋、雑司が谷、巣鴨、目白、大塚、要町など、ホームグラウンドである豊島区の文化イベント、名店、再開発、街の歴史を1つ深掘り。
- **【必須】リンク**: [🏛 豊島区公式ポータル](https://www.city.toshima.lg.jp/) / [池袋経済新聞](https://ikebukuro.keizai.biz/)

<h2 id="comedy">03. The Subversive Laugh: クセ強芸人とコントの解体新書</h2>
- **本日のピックアップ**: ラーメンズ（小林賢太郎・片桐仁）、ランジャタイ、ヨネダ2000、チャンス大城、金属バット、Aマッソ、男性ブランコなど、独自の世界観と狂気を持つ芸人を日替わりで1組厳選（過去号と被らないこと）。
- なぜそのネタ・人物が面白いのか。構成の妙、偏執的な情熱、ラジオやライブでのエピソードを熱く解説。
- **【必須】リンク**: 
  - [▶ YouTubeでおすすめネタ・動画を見る](https://www.youtube.com/results?search_query=芸人名+コント+漫才)
  - [📻 お笑いナタリーで最新情報を追う](https://natalie.mu/owarai)

<h2 id="ranking">04. Tokyo Index: 東京〇〇ランキング Top 5</h2>
- お題は日替わりで独自選定（例：23区の「坂道の多さ」「緑被率」「純喫茶の密度」「古書店数」「平均標高」「地価上昇率」「治安の良さ」などユニークなテーマ）。
- 1位から5位までをランキング形式で発表し、各区の意外な特徴や背景を切れ味鋭く解説。
- **【必須】リンク**: [📊 東京都総務局統計部](https://www.toukei.metro.tokyo.lg.jp/)

<h2 id="apple-pie">05. The Sweet Spot: 散歩の寄り道・至高のアップルパイ</h2>
- 都内の老舗洋菓子店、名門クラシックホテル、街の隠れ家ベーカリーなどから、実在する名作アップルパイを日替わりで1店紹介（過去号と被らないこと）。
- パイ生地の折り込み・バターの香り、リンゴの品種やシナモンの効かせ方、焼き上がりの美しさを描写。
- **【必須】リンク**: [🥧 食べログで店舗詳細を見る](https://tabelog.com/tokyo/rstLst/?vs=1&sa=&sk=店舗名+アップルパイ)

<h2 id="curiosity">06. Curiosity & Business: 未知なる探求テーマ ＆ 注目企業</h2>
- 日常生活の枠を大きく超える、知的好奇心を刺激するディープな探求テーマを1つ提示（例：深海探査技術、宮大工の木組み工法、宇宙デブリ回収、昆虫バイオ、超高精度ガラス研磨、特殊活版印刷など）。
- その最前線で独自の強みを持つ「日本の注目企業（ニッチトップ企業や注目のスタートアップ）」を1社紹介し、技術やビジネスモデルの面白さを解説。
- **【必須】リンク**:
  - [🏢 企業公式サイト](https://www.google.com/search?q=企業名+公式)
  - [📈 Yahoo!ファイナンスで会社情報を見る](https://finance.yahoo.co.jp/search/?query=企業名)

<h2 id="bookseller-choice">07. Books for Booksellers: 書店員に捧ぐ、推薦の1冊</h2>
- 本のプロである書店員が思わず唸り、仕掛けたくなるような「骨太な小説」または「思考の枠を広げるビジネス・教養本」を日替わりで1冊厳選。
- なぜ今この本なのか、プロの目利きに響く文体や構成、読後感を熱量高くレコメンド。
- **【必須】リンク**:
  - [📚 Amazonで見る](https://www.amazon.co.jp/s?k=書籍名)
  - [▶ YouTubeで書評・解説を見る](https://www.youtube.com/results?search_query=書籍名+書評)

<h2 id="baby">08. Baby & Science: 赤ちゃんの科学と成長便り（厳選2選）</h2>
お孫さんの健やかな成長を科学的に見守るための、医学論文・小児科学等の確かなエビデンスに基づく知見を2点解説：
1. **乳幼児の脳発達・感覚統合**: 抱っこ、外気浴、声かけが赤ちゃんの神経発達に与える影響 ([日本小児科学会](https://www.jpeds.or.jp/))
2. **睡眠と生体リズムの科学**: 月齢ごとの体内時計の整え方と最新研究 ([こども家庭庁](https://www.cfa.go.jp/))

<h2 id="nikkei">09. Nikkei Daily Briefing: 日経新聞 厳選ニュース5選 & 背景解説</h2>
日本経済新聞の最新トピックから、日本経済・世界情勢・産業構造の重要ニュースを5つ厳選。
単なる見出しではなく、経済の背景や「今後の社会にどう影響するのか」を大人の視点で鋭く解説：
1. **金融・マクロ経済**: 金利、為替、日銀動向 ([日本経済新聞 / 経済](https://www.nikkei.com/economy/))
2. **産業・テクノロジー**: 半導体、自動車、先端素材 ([日本経済新聞 / ビジネス](https://www.nikkei.com/business/))
3. **企業経営・M&A**: 注目企業の再編戦略 ([日本経済新聞 / 企業](https://www.nikkei.com/business/companies/))
4. **国際情勢・サプライチェーン**: 地政学リスクと国際流通 ([日本経済新聞 / 国際](https://www.nikkei.com/international/))
5. **社会・市場トレンド**: 人口動態、新興市場 ([日本経済新聞 / マーケット](https://www.nikkei.com/markets/))

<h2 id="books-libraries">10. Book & Library Chronicle: 出版・図書館・ブックオフ</h2>
本と書店文化を取り巻く3つの視点を毎日詳しくお届け：
1. **日本の出版・書店業界の最新動向**: 書店の新業態、取次流通、文庫・新書の売れ筋動向 ([新文化オンライン](https://www.shinbunka.co.jp/))
2. **全国のユニークな名図書館**: 建築美、驚きの蔵書、カフェ併設の全国の公立・私設図書館を日替わりで1館フィーチャー ([カーリル 全国図書館検索](https://calil.jp/))
3. **ブックオフ & リユース最前線**: ブックオフの新業態、リユース市場、掘り出し物探しの面白さ ([BOOKOFF 公式](https://www.bookoff.co.jp/))

<h2 id="health">11. Evidence Longevity: 最新論文が教える健康科学（厳選2選）</h2>
PubMed等の信頼できる査読論文から、生涯現役で元気に歩き、思考をクリアに保つための健康科学を2点解説：
1. **脳機能・認知のクリアリング**: 記憶力維持、脳の可塑性を保つ生活習慣 ([PubMed 認知機能研究](https://pubmed.ncbi.nlm.nih.gov/))
2. **血管・歩行・自律神経の強化**: 散歩の効果、動脈の柔軟性を保つ生化学 ([厚生労働省 e-ヘルスネット](https://www.e-healthnet.mhlw.go.jp/))

<h2 id="colophon">12. Editor's Colophon: 珈琲と日和</h2>
- 今日の東京・豊島区の気圧や風、散歩の合間にふと立ち寄りたくなる名喫茶の情景を綴る1行。
"""

user_prompt = f"""
本日の環境データ:
- 日付: {today} / 東京・豊島区の気温: {current_temp}℃ / 日没: {sunset}
- 本日の特集区: {target_ward}

記事本文の適切な場所に、以下の2つのライフスタイル写真タグを必ず配置してください：
{img_tag_1}
{img_tag_2}

各セクションは指定に従って知的かつ読み応えのある文量で執筆し、全セクションの直通リンクを正確に記載してください。
過去号との被りを避け、Markdown形式のみで出力してください。
"""

# 多重フォールバックモデル一覧（安定性の高い順に試行）
CANDIDATE_MODELS = [
    "gemini-2.0-flash",       # 現在もっとも可用性が高く安定したモデル
    "gemini-2.0-flash-lite",  # 軽量・高応答性モデル
    "gemini-3.8-flash",       # 最新モデル（混雑時はスキップ）
    "gemini-1.5-flash",       # 実績多数の安定モデル
    "gemini-1.5-pro"          # 最終バックアップ高精度モデル
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
            err_msg = str(e)
            print(f"⚠️ {model_name} (試行 {attempt}/2) で失敗: {err_msg[:120]}")
            time.sleep(attempt * 4)  # 4秒、8秒と段階的に待機
    if response_text:
        break

# 万が一Google API全体が完全停止していた場合のフェイルセーフ
if not response_text:
    print("⚠️ API全モデル混雑のため、緊急エディションを生成してサイト停止を防止します。")
    response_text = f"""
<h2 id="walk">01. Tokyo Flâneur: 東京23区 日替わり逍遥録（本日の区：{target_ward}）</h2>
本日は「{target_ward}」の路地と歴史を逍遥します。街の記憶を辿る散歩へ出かけましょう。
- [🗺 Google マップで名所を見る](https://www.google.com/maps/search/{quote(target_ward + ' 史跡 名所')})

{img_tag_1}

<h2 id="toshima">02. Toshima Local Focus: 豊島区の定点観測</h2>
豊島区の文化・歴史・街並みの最新動向をお届けします。
- [🏛 豊島区公式ポータル](https://www.city.toshima.lg.jp/) / [池袋経済新聞](https://ikebukuro.keizai.biz/)

<h2 id="comedy">03. The Subversive Laugh: クセ強芸人とコントの解体新書</h2>
独自の美学と狂気を持つコントの世界を深掘りします。
- [▶ YouTubeでおすすめネタを見る](https://www.youtube.com/results?search_query=ラーメンズ+コント)

<h2 id="apple-pie">05. The Sweet Spot: 散歩の寄り道・至高のアップルパイ</h2>
散歩の途中に立ち寄りたい、都内の名作アップルパイ。
- [🥧 食べログで探す](https://tabelog.com/tokyo/rstLst/?vs=1&sa=&sk=アップルパイ)

{img_tag_2}

<h2 id="colophon">12. Editor's Colophon: 珈琲と日和</h2>
東京の空と心地よい風を感じながら、良い一日を。
"""

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
