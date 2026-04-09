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

def get_smart_blog_post():
    """يجلب مقالاً عشوائياً ويضمن استخراج النص بنجاح."""
    rss_url = "https://familytvr.blogspot.com/feeds/posts/default?alt=rss&max-results=50"
    feed = feedparser.parse(rss_url)
    
    if not feed.entries:
        return None

    # اختيار مقال عشوائي لضمان التغيير الدائم في الـ RSS
    entry = random.choice(feed.entries)
    
    # فحص شامل لاستخراج المحتوى مهما كان وسمه في Blogger
    raw_content = ""
    if 'content' in entry:
        raw_content = entry.content[0].value
    elif 'summary' in entry:
        raw_content = entry.summary
    
    clean_text = re.sub('<[^<]+?>', '', raw_content) # تنظيف HTML
    
    if len(clean_text.strip()) < 100:
        # إذا كان المقال المختار فارغاً، نحاول اختيار أول مقال متاح كخطة بديلة
        entry = feed.entries[0]
        raw_content = entry.get('content', [{}])[0].get('value', entry.get('summary', ''))
        clean_text = re.sub('<[^<]+?>', '', raw_content)

    return {"title": entry.title, "content": clean_text[:4000], "link": entry.link}

async def generate_content(blog_data):
    """صياغة محتوى احترافي متوافق مع معايير يوتيوب 2026."""
    prompt = f"""
    Role: Professional Tech Video Scriptwriter.
    Target: {blog_data['title']}
    Source Content: {blog_data['content']}
    
    Task: Create a YouTube script in JSON.
    1. 4 unique segments (English).
    2. Professional, engaging tone.
    3. Metadata: 'youtube_title', 'description', and 20 SEO 'tags'.
    4. Call to Action: Visit {blog_data['link']}.
    """
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(completion.choices[0].message.content)

def update_rss(data, run_number, blog_link):
    """توليد ملف RSS ببيانات يوتيوب الإلزامية (Owner, Email, Category)."""
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    audio_url = f"https://github.com/eslamtechautomation-ctrl/TrustMask-Bot-main/releases/download/v{run_number}/episode.mp3"
    cover_url = "https://raw.githubusercontent.com/eslamtechautomation-ctrl/TrustMask-Bot-main/main/podcast_cover.jpg"
    
    meta = data.get('metadata', {})
    actual_title = meta.get('youtube_title', f"Tech Insight v{run_number}")
    tags = ", ".join(meta.get('tags', ["Tech", "Android", "Software"]))
    
    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Family TVR Official Podcast</title>
    <itunes:author>Family TVR</itunes:author>
    <itunes:owner>
      <itunes:name>Family TVR Admin</itunes:name>
      <itunes:email>eslammosde@gmail.com</itunes:email>
    </itunes:owner>
    <itunes:category text="Technology"><itunes:category text="Tech News"/></itunes:category>
    <itunes:image href="{cover_url}"/>
    <language>en-us</language>
    <item>
      <title><![CDATA[{actual_title}]]></title>
      <description><![CDATA[{meta.get('description', '')}]]></description>
      <pubDate>{pub_date}</pubDate>
      <itunes:keywords>{tags}</itunes:keywords>
      <enclosure url="{audio_url}" length="1048576" type="audio/mpeg"/>
      <guid isPermaLink="false">v{run_number}_{int(time.time())}</guid>
    </item>
  </channel>
</rss>"""
    with open("podcast.xml", "w", encoding="utf-8") as f:
        f.write(rss_content.strip())

async def main():
    blog_data = get_smart_blog_post()
    if not blog_data: 
        print("❌ RSS Empty"); return

    data = await generate_content(blog_data)
    run_num = os.getenv("GITHUB_RUN_NUMBER", "1")
    
    # تجميع النص مع فحص السلامة
    stories = data.get('stories', [])
    full_script = "\n\n".join([s.get('content', '') for s in stories])

    if len(full_script.strip()) > 50:
        print(f"🎙️ Generating Audio for: {blog_data['title']}")
        communicate = edge_tts.Communicate(full_script, "en-US-ChristopherNeural")
        await communicate.save("episode.mp3")
        
        # الفحص الحرج: التأكد من أن الملف ليس فارغاً قبل تحديث الـ RSS
        if os.path.exists("episode.mp3") and os.path.getsize("episode.mp3") > 0:
            update_rss(data, run_num, blog_data['link'])
            print(f"✅ RSS Updated with fresh random content.")
        else:
            print("❌ Audio file is empty. Skipping RSS update to prevent 422 error.")
    else:
        print("❌ AI returned empty script.")

if __name__ == "__main__":
    asyncio.run(main())
