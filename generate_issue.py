import os
import sys
from datetime import datetime
from google import genai
from google.genai import types

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY is not set.")
    sys.exit(1)

client = genai.Client(api_key=API_KEY)

def generate_issue():
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""
日付: {today}
父親・シニア層に向けた日刊ウェブマガジンの特集記事を作成してください。
【条件】
- ビジネス動向、健康・ウェルネス、歴史、趣味・教養などのトピック
- 読みやすく落ち着いたトーン
- 各見出しはMarkdown（## や ###）を使用
"""
    config = types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=1500,
        system_instruction="あなたは落ち着きと信頼感のある日刊マガジンの編集者です。シニア・ビジネス層が毎朝快適に読めるスマートな記事を執筆してください。"
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=config,
    )
    return response.text

def main():
    today_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = "src/content/issues"
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"{today_str}.md")
    
    print(f"Generating issue for {today_str}...")
    article_body = generate_issue()

    content = f"""---
title: "Daily Issue - {today_str}"
date: "{today_str}"
description: "Daily curated magazine issue."
---

{article_body}
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Successfully created: {file_path}")

if __name__ == "__main__":
    main()
