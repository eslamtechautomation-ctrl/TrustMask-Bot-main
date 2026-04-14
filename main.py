import os
import asyncio
import time
import feedparser
import random
import re
import edge_tts
from newspaper import Article
from groq import Groq
from datetime import datetime, timezone
from newspaper import Article, Config
# إعدادات
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)


async def main():
    # 1. جلب المقالات من RSS
    rss_url = "https://www.economist.com/latest/rss.xml"
    feed = feedparser.parse(rss_url)
    if not feed.entries: return

   # 1. جلب البيانات الأساسية من RSS
    entry = random.choice(feed.entries)
    title = entry.title
    link = entry.link
    summary = re.sub('<[^<]+?>', '', entry.summary)

    # 2. توليد "سكريبت" كامل للبودكاست بدلاً من مجرد وصف
    # سنطلب من الذكاء الاصطناعي كتابة مقال مفصل بناءً على العنوان
    script_prompt = f"Write a detailed professional podcast script in English about: {title}. Based on this context: {summary}. Make it around 300-400 words long to last about 2-3 minutes."
    
    chat_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": script_prompt}]
    )
    podcast_script = chat_response.choices[0].message.content

    # 3. توليد الوصف لليوتيوب (اختياري)
    desc_prompt = f"Create a short SEO description for a podcast titled: {title}"
    desc_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": desc_prompt}]
    )
    description = desc_response.choices[0].message.content

    # 4. تحويل السكريبت (الذي كتبه الذكاء الاصطناعي) إلى صوت
    audio_file = "episode.mp3"
    # نستخدم podcast_script هنا لضمان الطول
    communicate = edge_tts.Communicate(podcast_script, "en-US-ChristopherNeural")
    await communicate.save(audio_file)
    
    # 4. إنشاء ملف RSS (حتى لو حذف يحيا من جديد)
    run_num = os.getenv("GITHUB_RUN_NUMBER", "1")
    timestamp = int(time.time())
    audio_url = f"https://github.com/eslamtechautomation-ctrl/TrustMask-Bot-main/releases/download/v{run_num}/episode.mp3"
    # تأكد أن هذا السطر يبدأ بنفس مستوى المسافات للأسطر السابقة في الكود الخاص بك
   # تأكد أن هذا السطر يبدأ بنفس مستوى المسافات للأسطر السابقة في الكود الخاص بك
    rss_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
    xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" 
    xmlns:content="http://purl.org/rss/1.0/modules/content/"
    xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <atom:link href="https://eslamtechautomation-ctrl.github.io/TrustMask-Bot-main/podcast.xml" rel="self" type="application/rss+xml" />
    <title>The Economic Edge: Master Your Wealth</title>
    <link>https://familytvr.blogspot.com/</link>
    <language>en-us</language>
    <itunes:author>Family TVR</itunes:author>
    <itunes:summary>Stop guessing with your money. While the world panics, the top 1% are positioning themselves for the biggest wealth transfer in history.</itunes:summary>
    <itunes:owner>
        <itunes:name>Eslam Tech</itunes:name>
        <itunes:email>eslammosde@gmail.com</itunes:email>
    </itunes:owner>
    <itunes:explicit>no</itunes:explicit>
    <itunes:image href="https://raw.githubusercontent.com/eslamtechautomation-ctrl/TrustMask-Bot-main/refs/heads/main/podcast_cover.jpg" />
    <description><![CDATA[Stop guessing with your money. The global economy is changing faster than ever.]]></description>
    <itunes:category text="Business">
        <itunes:category text="Investing"/>
    </itunes:category>
    <item>
        <title>{title}</title>
        <description>{description}</description>
        <pubDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
        <enclosure url="{audio_url}" length="1048576" type="audio/mpeg"/>
        <guid>v{run_num}_{timestamp}</guid>
        <itunes:explicit>no</itunes:explicit>
    </item>
</channel>
</rss>"""
    
    with open("podcast.xml", "w", encoding="utf-8") as f:
        f.write(rss_template)

if __name__ == "__main__":
    asyncio.run(main())
