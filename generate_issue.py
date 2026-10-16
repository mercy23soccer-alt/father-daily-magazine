import glob
import io
import os
import random
import re
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from PIL import Image
import requests
from google import genai

# 日本時間（JST）の厳格取得
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

SECTION_ID_MAP = {
    "01": "walk",
    "02": "toshima",
    "03": "comedy",
    "04": "ranking",
    "05": "apple-pie",
    "06": "curiosity",
    "07": "bookseller-choice",
    "08": "baby",
    "09": "nikkei",
    "10": "books-libraries",
    "11": "health",
    "12": "colophon",
}


def migrate_legacy_issues():
    """src/content/issues/ に残っている記事があれば src/content/posts/ へ移行する"""
    legacy_files = sorted(glob.glob("src/content/issues/*.md"))
    if not legacy_files:
        return
    os.makedirs("src/content/posts", exist_ok=True)
    for src_path in legacy_files:
        fname = os.path.basename(src_path)
        dst_path = os.path.join("src/content/posts", fname)
        if not os.path.exists(dst_path):
            shutil.move(src_path, dst_path)
            print(f"✅ バックナンバー移行完了: {src_path} -> {dst_path}")
        else:
            os.remove(src_path)
    try:
        os.rmdir("src/content/issues")
    except Exception:
        pass


migrate_legacy_issues()

# 1. 天気の取得
current_temp = "20"
sunset = "18:00"
try:
    weather_res = requests.get(
        "https://api.open-meteo.com/v1/forecast?latitude=35.73&longitude=139.71&current=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m&daily=sunset&timezone=Asia%2FTokyo",
        timeout=15,
    ).json()
    current = weather_res.get("current", {})
    daily = weather_res.get("daily", {})
    current_temp = str(current.get("temperature_2m", "20"))
    sunset = daily.get("sunset", ["18:00"])[0].split("T")[-1]
except Exception as e:
    print(f"天気取得フォールバック使用: {e}")

TOKYO_23_WARDS = [
    "千代田区",
    "中央区",
    "港区",
    "新宿区",
    "文京区",
    "台東区",
    "墨田区",
    "江東区",
    "品川区",
    "目黒区",
    "大田区",
    "世田谷区",
    "渋谷区",
    "中野区",
    "杉並区",
    "豊島区",
    "北区",
    "荒川区",
    "板橋区",
    "練馬区",
    "足立区",
    "葛飾区",
    "江戸川区",
]
day_index = now_jst.toordinal() % len(TOKYO_23_WARDS)
target_ward = TOKYO_23_WARDS[day_index]

# 2. 【過去90日分】全記事から重複禁止トピックを自動抽出
past_posts = sorted(glob.glob("src/content/posts/*.md"), reverse=True)[:90]
past_used_topics = []

for p in past_posts:
    try:
        with open(p, "r", encoding="utf-8") as f:
            c = f.read()
            date_label = os.path.basename(p).replace(".md", "")
            items = []
            for line in c.splitlines():
                line_str = line.strip()
                if (
                    line_str.startswith("#")
                    or line_str.startswith("<h2")
                    or line_str.startswith("<h3")
                ):
                    clean_h = re.sub(r"<[^>]+>|[#*]", "", line_str).strip()
                    if clean_h and not any(
                        k in clean_h
                        for k in [
                            "Tokyo Flâneur",
                            "Toshima Local Focus",
                            "The Subversive Laugh",
                            "Tokyo Index",
                            "The Sweet Spot",
                            "Curiosity & Business",
                            "Books for Booksellers",
                            "Baby & Science",
                            "Nikkei Daily",
                            "Book & Library",
                            "Evidence Longevity",
                            "Editor's Colophon",
                        ]
                    ):
                        items.append(clean_h)
                elif any(
                    k in line_str
                    for k in [
                        "ネタ",
                        "芸人",
                        "店",
                        "パイ",
                        "本",
                        "企業",
                        "坂",
                        "ランキング",
                    ]
                ):
                    bolds = re.findall(r"\*\*(.*?)\*\*", line_str)
                    if bolds:
                        items.extend(bolds[:2])
                    else:
                        clean_l = re.sub(
                            r"<[^>]+>|\[.*?\]\(.*?\)|\*", "", line_str
                        ).strip()
                        if 3 < len(clean_l) < 45:
                            items.append(clean_l)

            seen = set()
            unique_items = [x for x in items if not (x in seen or seen.add(x))]
            if unique_items:
                past_used_topics.append(
                    f"【{date_label}号】: " + " / ".join(unique_items[:8])
                )
    except Exception:
        pass

past_context = (
    "\n".join(past_used_topics) if past_used_topics else "（過去90日間の記録なし）"
)

img_tag_1 = f'<div class="magazine-photo-box"><img src="/father-daily-magazine/images/{today}_scene1.jpg" alt="Today\'s Scene 1" /><p class="photo-caption">TOKYO MORNING WALK / FLÂNEUR ARCHIVE</p></div>'
img_tag_2 = f'<div class="magazine-photo-box"><img src="/father-daily-magazine/images/{today}_scene2.jpg" alt="Today\'s Scene 2" /><p class="photo-caption">BOOK, SWEET & QUIET TIME</p></div>'

SYSTEM_INSTRUCTION = f"""
あなたは雑誌『散歩の達人』『東京人』の気骨ある編集長であり、日刊誌『THE TOKYO FLÂNEUR（東京逍遥録）』の筆頭執筆者です。
読者は「東京の路地や歴史の高低差を愛し、演芸・コント・漫才の真髄を愉しみ、豊島区の街並みに愛着を持ち、日経新聞から社会の潮流を読み解き、本と書店文化を慈しみ、孫（赤ちゃん）の成長を温かく見守る、粋で知的好奇心に満ちた紳士」です。

【最重要：過去90日間に取り上げたトピック・固有名詞一覧】
以下の過去90日間に登場した「芸人、ネタ、喫茶店、アップルパイ店、推薦本、注目企業、ランキングテーマ」は絶対に重複・再使用しないでください：
{past_context}

【執筆ルール】
- 本文の冒頭にタイトルやメタデータ（title:, date: など）は一切書かないでください。いきなり「01. Tokyo Flâneur」の見出しから書き始めてください。
- **お笑いリサーチの広域化**: 特定の芸人に偏らず、浅草・新宿末廣亭の寄席演芸・落語から、昭和・平成・令和のコント・漫才の怪作、学生演芸、若手実力派まで幅広くリサーチし、過去90日間で一度も紹介されていないネタを紹介してください。
- 街歩き好きの琴線に触れる豊かな情景描写、路地の匂い、暗渠、坂道、歴史の陰影をしっかりとした文章量で描写してください。
- リンクは各項目の末尾に「<a href="URL" target="_blank" class="guide-link">案内名 ↗</a>」の形式で配置してください。

見出し構成：
<h2 id="walk">01. Tokyo Flâneur: 東京23区 日替わり逍遥録（本日の区：{target_ward}）</h2>
<h2 id="toshima">02. Toshima Local Focus: 豊島区の定点観測</h2>
<h2 id="comedy">03. The Subversive Laugh: クセ強芸人とコントの解体新書</h2>
<h2 id="ranking">04. Tokyo Index: 東京〇〇ランキング Top 5（過去90日間と被らないテーマ）</h2>
<h2 id="apple-pie">05. The Sweet Spot: 散歩の寄り道・至高のアップルパイ（過去90日間と被らない名店）</h2>
<h2 id="curiosity">06. Curiosity & Business: 未知なる探求テーマ ＆ 注目企業（過去90日間と被らない銘柄）</h2>
<h2 id="bookseller-choice">07. Books for Booksellers: 書店員に捧ぐ、推薦の1冊（過去90日間と被らない名著）</h2>
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
過去90日間の内容と一切重複がないことを確認の上、Markdown形式で出力してください。
"""

response_text = None


def generate_text_with_gemini(prompt_str, sys_inst=None, thinking_level="medium"):
    """Gemini Interactions API (gemini-3.8-flash / gemini-4-argon) でテキストを生成する"""
    if not client:
        return None
    for model_name in ["gemini-3.8-flash", "gemini-4-argon"]:
        try:
            kwargs = {
                "model": model_name,
                "input": prompt_str,
                "generation_config": {
                    "temperature": 0.75,
                    "thinking_level": thinking_level,
                },
            }
            if sys_inst:
                kwargs["system_instruction"] = sys_inst
            interaction = client.interactions.create(**kwargs)
            if interaction.output_text and len(interaction.output_text.strip()) > 0:
                return interaction.output_text
        except Exception as e:
            print(f"⚠️ {model_name} (interactions) エラー: {str(e)[:120]}")
            try:
                cfg = {"temperature": 0.75}
                if sys_inst:
                    cfg["system_instruction"] = sys_inst
                res = client.models.generate_content(
                    model=model_name,
                    contents=prompt_str,
                    config=cfg,
                )
                if res and res.text:
                    return res.text
            except Exception as e2:
                print(f"⚠️ {model_name} (generate_content) エラー: {str(e2)[:120]}")
    return None


if client:
    print("--- Gemini API (gemini-3.8-flash) で執筆中 ---")
    text_out = generate_text_with_gemini(
        user_prompt, sys_inst=SYSTEM_INSTRUCTION, thinking_level="medium"
    )
    if text_out and len(text_out) > 800:
        print("✅ 成功: Gemini APIで記事が完成しました！")
        response_text = text_out

if not response_text:
    print("--- バックアップAIエンジンで執筆中 ---")
    try:
        combined_prompt = f"{SYSTEM_INSTRUCTION}\n\n---\n{user_prompt}"
        payload = {
            "messages": [{"role": "user", "content": combined_prompt}],
            "model": "openai",
            "seed": int(time.time()),
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

clean_text = re.sub(
    r"^(title:.*?\n|date:.*?\n|temp:.*?\n|sunset:.*?\n|ward:.*?\n|location:.*?\n)+",
    "",
    response_text.strip(),
    flags=re.MULTILINE | re.IGNORECASE,
).strip()


def normalize_h2(match):
    num = match.group(1)
    title_rest = match.group(2).strip()
    sec_id = SECTION_ID_MAP.get(num, f"sec-{num}")
    return f'<h2 id="{sec_id}">{num}. {title_rest}</h2>'


clean_text = re.sub(
    r"^##\s+(\d{2})\.\s*(.+)$",
    normalize_h2,
    clean_text,
    flags=re.MULTILINE,
)

# 4. 画像の生成完了確認（無料 Pollinations.ai Flux エンジンで2枚生成）
os.makedirs("public/images", exist_ok=True)
prompt_1 = f"A quiet historic narrow residential alley in {target_ward} Tokyo with lush potted plants and stone pavement, morning sunlight, 35mm documentary photography"
prompt_2 = "A vintage kissaten coffee counter with polished dark wood, antique brass siphon drippers, and a freshly baked warm apple pie on ceramic plate, warm lighting"

if client:
    try:
        photo_gen_prompt = f"""
以下の記事本文（特集区：{target_ward}）を読み、雑誌『散歩の達人』『東京人』に掲載されるような、情緒ある35mmフィルム写真の英語プロンプトを2つ考案してください。
1つ目は{target_ward}の情緒ある街歩き・路地・坂道・近代建築、2つ目は純喫茶・アップルパイ・古本屋の静謐なシーンにしてください。
出力形式：
PROMPT1: <英語プロンプト>
PROMPT2: <英語プロンプト>

記事抜粋：
{clean_text[:1000]}
"""
        p_text_out = generate_text_with_gemini(
            photo_gen_prompt, sys_inst=None, thinking_level="low"
        )
        if p_text_out:
            m1 = re.search(r"PROMPT1:\s*(.+)", p_text_out)
            m2 = re.search(r"PROMPT2:\s*(.+)", p_text_out)
            if m1:
                prompt_1 = (
                    m1.group(1).strip()
                    + ", authentic 35mm film photography, nostalgic Tokyo aesthetic"
                )
            if m2:
                prompt_2 = (
                    m2.group(1).strip()
                    + ", authentic 35mm film photography, warm vintage kissaten atmosphere"
                )
            print("✅ 散歩連動型オリジナル画像プロンプトの生成に成功！")
    except Exception as e:
        print(f"動的プロンプト生成スキップ: {e}")

scenes = [
    (prompt_1, f"public/images/{today}_scene1.jpg"),
    (prompt_2, f"public/images/{today}_scene2.jpg"),
]


def generate_and_save_photo(prompt_text, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # A. Pollinations AI（Flux 無料エンジン・最大3回リトライ、60秒タイムアウト）
    clean_prompt = quote(prompt_text)
    for attempt in range(1, 4):
        try:
            seed_val = int(time.time()) + random.randint(1000, 99999)
            url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1200&height=675&nologo=true&seed={seed_val}"
            print(f"画像生成試行中 ({attempt}/3): {file_path}")
            r = requests.get(url, timeout=60)
            if r.status_code == 200 and len(r.content) > 5000:
                with open(file_path, "wb") as f:
                    f.write(r.content)
                img = Image.open(file_path)
                img.verify()
                print(
                    f"✅ フォトエンジンで生成完了: {file_path} ({os.path.getsize(file_path)} bytes)"
                )
                return True
        except Exception as ex:
            print(f"⚠️ 画像生成リトライ中 ({attempt}/3): {ex}")
            time.sleep(5)

    # B. 高品質フォールバック写真の保存
    try:
        r = requests.get("https://picsum.photos/1200/675", timeout=30)
        if r.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(r.content)
            print(f"⚠️ バックアップ写真で保存完了: {file_path}")
            return True
    except Exception as e:
        print(f"フォールバック失敗: {e}")

    return False


print("=== 画像生成プロセス開始 ===")
for idx, (p_text, s_path) in enumerate(scenes):
    success = generate_and_save_photo(p_text, s_path)
    if not success or not os.path.exists(s_path) or os.path.getsize(s_path) < 1000:
        dummy = Image.new("RGB", (1200, 675), color=(35, 45, 55))
        dummy.save(s_path, "JPEG")
        print(f"⚠️ プレースホルダー画像を配置: {s_path}")
    if idx < len(scenes) - 1:
        print("2枚目の画像生成まで 6秒 待機します...")
        time.sleep(6)

assert os.path.exists(scenes[0][1]) and os.path.getsize(scenes[0][1]) > 500, "Scene 1 is missing!"
assert os.path.exists(scenes[1][1]) and os.path.getsize(scenes[1][1]) > 500, "Scene 2 is missing!"
print("✅ すべての画像（SCENE 01 / SCENE 02）がディスクに生成完了しました。")

# 5. 画像生成が完了した後に、Markdown記事を保存して出力完了
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
    f.write(frontmatter_block + clean_text + "\n")

print(f"Successfully published issue: {file_path}")
