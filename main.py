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
    # سحب آخر 50 مقال لضمان التنوع العشوائي
    rss_url = "https://familytvr.blogspot.com/feeds/posts/default?alt=rss&max-results=50"
    feed = feedparser.parse(rss_url)
    
    if not feed.entries:
        return None

    # اختيار مقال عشوائي لضمان عدم التكرار حتى لو لم تنشر جديداً
    entry = random.choice(feed.entries)
    
    # معالجة اختلاف وسوم Blogger (content أو summary)
    raw_content = entry.get('content', [{}])[0].get('value', entry.get('summary', ''))
    clean_text = re.sub('<[^<]+?>', '', raw_content) # تنظيف HTML
    
    return {
        "title": entry.title,
        "content": clean_text[:4000],
        "link": entry.link
    }

async def generate_content(blog_data):
    # الموجه يركز على المحتوى التقني الاحترافي لمدونتك
    prompt = f"""
    Role: Professional Tech Content Creator.
    Task: Convert this blog article into a viral 4-segment YouTube script.
    Topic: {blog_data['title']}
    Source Content: {blog_data['content']}
    
    Instructions:
    1. Tone: Professional and educational (No dark themes).
    2. Output ONLY a JSON object.
    3. Metadata: Provide 'youtube_title', 'description', and 'tags' (20 keywords).
    4. Call to Action: Mention visiting {blog_data['link']} for the full technical guide.
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
    tags_string = ", ".join(meta.get('tags', ["Tech", "Software"]))
    
    # إضافة بيانات يوتيوب المطلوبة (الإيميل والمالك والتصنيف الفرعي)
    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Family TVR Tech Podcast</title>
    <link>https://familytvr.blogspot.com/</link>
    <language>en-us</language>
    <itunes:author>Family TVR</itunes:author>
    <itunes:owner>
      <itunes:name>Family TVR Admin</itunes:name>
      <itunes:email>eslammosde@gmail.com</itunes:email>
    </itunes:owner>
    <itunes:category text="Technology">
      <itunes:category text="Tech News"/>
    </itunes:category>
    <itunes:image href="{cover_url}"/>
    <description>Latest technical updates and software guides from familytvr.blogspot.com.</description>
    <item>
      <title><![CDATA[{actual_title}]]></title>
      <description><![CDATA[{meta.get('description', '')}]]></description>
      <pubDate>{pub_date}</pubDate>
      <itunes:keywords>{tags_string}</itunes:keywords>
      <enclosure url="{audio_url}" length="1048576" type="audio/mpeg"/>
      <guid isPermaLink="false">v{run_number}_{int(time.time())}</guid>
      <itunes:explicit>no</itunes:explicit>
    </item>
  </channel>
</rss>"""
    with open("podcast.xml", "w", encoding="utf-8") as f:
        f.write(rss_content.strip())

async def main():
    print("📡 Fetching smart content...")
    blog_data = get_smart_blog_post()
    if not blog_data: 
        print("❌ No articles found."); return

    data = await generate_content(blog_data)
    run_num = os.getenv("GITHUB_RUN_NUMBER", "1")
    full_script = "\n\n".join([s.get('content', '') for s in data.get('stories', [])])

    if len(full_script.strip()) > 50:
        print("🎙️ Generating Audio...")
        communicate = edge_tts.Communicate(full_script, "en-US-ChristopherNeural")
        await communicate.save("episode.mp3")
        
        # التأكد من نجاح إنتاج الملف قبل تحديث الـ RSS
        if os.path.exists("episode.mp3") and os.path.getsize("episode.mp3") > 0:
            update_rss(data, run_num, blog_data['link'])
            print(f"✅ Success: {blog_data['title']}")
        else:
            print("❌ Audio generation failed.")
    else:
        print("❌ Script content too short.")

if __name__ == "__main__":
    asyncio.run(main())
