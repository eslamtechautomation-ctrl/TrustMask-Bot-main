import os
import asyncio
import time
import feedparser
import random
import re
import edge_tts
from groq import Groq
from datetime import datetime, timezone

# إعدادات
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

async def main():
    # 1. جلب المقالات من بلوجر
    rss_url = "https://familytvr.blogspot.com/feeds/posts/default?alt=rss"
    feed = feedparser.parse(rss_url)
    if not feed.entries: return

    entry = random.choice(feed.entries)
    title = entry.title
    link = entry.link
    content = re.sub('<[^<]+?>', '', entry.summary)[:1000]

    # 2. توليد وصف ذكي (SEO)
    prompt = f"Create a short YouTube description for: {title}. Include this link: {link}"
    chat = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    description = chat.choices[0].message.content

    # 3. تحويل النص لصوت
    audio_file = "episode.mp3"
    communicate = edge_tts.Communicate(content, "en-US-ChristopherNeural")
    await communicate.save(audio_file)

    # 4. إنشاء ملف RSS (حتى لو حذف يحيا من جديد)
    run_num = os.getenv("GITHUB_RUN_NUMBER", "1")
    timestamp = int(time.time())
    audio_url = f"https://github.com/eslamtechautomation-ctrl/TrustMask-Bot-main/releases/download/v{run_num}/episode.mp3"
    
    rss_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
    <title>Family TVR News</title>
    <item>
        <title>{title}</title>
        <description>{description}</description>
        <pubDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
        <enclosure url="{audio_url}" length="1048576" type="audio/mpeg"/>
        <guid>v{run_num}_{timestamp}</guid>
    </item>
</channel>
</rss>"""
    
    with open("podcast.xml", "w", encoding="utf-8") as f:
        f.write(rss_template)

if __name__ == "__main__":
    asyncio.run(main())
