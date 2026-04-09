import os
import asyncio
import json
import edge_tts
import time
import re
import feedparser
import random
from groq import Groq
from datetime import datetime, timezone

# إعداد المفاتيح
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# 1. وظيفة جلب مقال عشوائي غير مكرر
def get_random_blog_post():
    rss_url = "https://familytvr.blogspot.com/feeds/posts/default?alt=rss&max-results=50"
    feed = feedparser.parse(rss_url)
    
    if not feed.entries:
        return None

    # نختار مقالاً عشوائياً من آخر 50 مقال لضمان عدم التكرار المستمر
    entry = random.choice(feed.entries)
    
    raw_content = entry.get('content', [{}])[0].get('value', entry.get('summary', ''))
    clean_text = re.sub('<[^<]+?>', '', raw_content)
    
    return {
        "title": entry.title,
        "content": clean_text[:4000],
        "link": entry.link
    }

async def generate_content(blog_data):
    # الموجه التقني الاحترافي (بدون غموض)
    prompt = f"""
    Role: Tech Content Specialist.
    Topic: {blog_data['title']}
    Source: {blog_data['content']}
    
    Task: Produce a viral YouTube script in JSON.
    1. 4 unique segments explaining the technology.
    2. Professional and engaging tone for US/Europe markets.
    3. Metadata: catchy title, SEO description, and 20 tags.
    """
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(completion.choices[0].message.content)

def update_rss(data, run_number, blog_link):
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    audio_url = f"https://github.com/eslamtechautomation-ctrl/TrustMask-Bot-main/releases/download/v{run_number}/episode.mp3"
    cover_url = "https://raw.githubusercontent.com/eslamtechautomation-ctrl/TrustMask-Bot-main/main/podcast_cover.jpg"
    
    meta = data.get('metadata', {})
    actual_title = meta.get('youtube_title', f"Tech Insight v{run_number}")
    tags = ", ".join(meta.get('tags', ["Tech", "Android"]))
    
    # إضافة بيانات يوتيوب المطلوبة (الإيميل، المالك، التصنيف الدقيق)
    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Family TVR Official Podcast</title>
    <link>https://familytvr.blogspot.com/</link>
    <language>en-us</language>
    <copyright>Family TVR 2026</copyright>
    <itunes:author>Family TVR Team</itunes:author>
    <itunes:owner>
      <itunes:name>Eslam Technology</itunes:name>
      <itunes:email>eslammosde@gmail.com</itunes:email>
    </itunes:owner>
    <itunes:category text="Technology">
      <itunes:category text="Tech News"/>
    </itunes:category>
    <itunes:image href="{cover_url}"/>
    <description>Your daily source for software updates and tech guides.</description>
    <item>
      <title><![CDATA[{actual_title}]]></title>
      <itunes:author>Family TVR</itunes:author>
      <description><![CDATA[{meta.get('description', '')}]]></description>
      <pubDate>{pub_date}</pubDate>
      <itunes:keywords>{tags}</itunes:keywords>
      <enclosure url="{audio_url}" length="1048576" type="audio/mpeg"/>
      <guid isPermaLink="false">v{run_number}_{int(time.time())}</guid>
      <itunes:explicit>no</itunes:explicit>
    </item>
  </channel>
</rss>"""
    with open("podcast.xml", "w", encoding="utf-8") as f:
        f.write(rss_content.strip())

async def main():
    blog_data = get_random_blog_post()
    if not blog_data: return

    data = await generate_content(blog_data)
    run_num = os.getenv("GITHUB_RUN_NUMBER", "1")
    full_script = "\n\n".join([s.get('content', '') for s in data.get('stories', [])])

    print(f"🎙️ Creating Audio for: {blog_data['title']}")
    communicate = edge_tts.Communicate(full_script, "en-US-ChristopherNeural")
    await communicate.save("episode.mp3")

    if os.path.exists("episode.mp3") and os.path.getsize("episode.mp3") > 0:
        update_rss(data, run_num, blog_data['link'])
        print(f"✅ RSS Updated with YouTube requirements.")

if __name__ == "__main__":
    asyncio.run(main())
