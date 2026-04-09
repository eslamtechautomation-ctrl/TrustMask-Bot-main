import os
import asyncio
import json
import edge_tts
import time
import re
import feedparser
from groq import Groq
from datetime import datetime, timezone

# إعداد المفاتيح
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

def get_latest_blog_post():
    rss_url = "https://familytvr.blogspot.com/feeds/posts/default?alt=rss"
    feed = feedparser.parse(rss_url)
    
    if feed.entries:
        latest_entry = feed.entries[0]
        
        # إصلاح خطأ AttributeError/KeyError: 
        # نبحث عن النص في content أولاً، وإذا لم يوجد نأخذه من summary
        raw_html = ""
        if 'content' in latest_entry:
            raw_html = latest_entry.content[0].value
        elif 'summary' in latest_entry:
            raw_html = latest_entry.summary
        else:
            raw_html = latest_entry.title # حل أخير في حال عدم وجود نص

        # تنظيف النص من أكواد HTML
        clean_content = re.sub('<[^<]+?>', '', raw_html)
        
        return {
            "title": latest_entry.title,
            "content": clean_content[:5000], # نأخذ أول 5000 حرف لضمان عدم تجاوز حدود الـ AI
            "link": latest_entry.link
        }
    return None

async def generate_content(blog_data):
    # الموجه التقني الصافي (بدون غموض وبدون Deep Web)
    prompt = f"""
    Role: Professional Tech Journalist.
    Task: Convert this blog article into a YouTube video script.
    
    SOURCE ARTICLE:
    Title: {blog_data['title']}
    Link: {blog_data['link']}
    Content Summary: {blog_data['content'][:2000]}

    STRICT INSTRUCTIONS:
    1. Tone: Technical, helpful, and professional (Mirror familytvr.blogspot.com).
    2. Format: Output ONLY a JSON object.
    3. Stories: 4 educational segments (400 words each) explaining the tech in the article.
    4. Call to Action: Tell viewers to read the full guide at {blog_data['link']}.
    5. Metadata: Provide 'youtube_title', 'description', and 'tags' (15 keywords).
    6. NO MYSTERY. NO DARK THEMES.
    """
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(completion.choices[0].message.content)

async def text_to_speech(text, output_file):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(output_file)

def update_rss(data, run_number, blog_link):
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    audio_url = f"https://github.com/eslamtechautomation-ctrl/TrustMask-Bot-main/releases/download/v{run_number}/episode.mp3"
    main_cover_url = "https://raw.githubusercontent.com/eslamtechautomation-ctrl/TrustMask-Bot-main/main/podcast_cover.jpg"
    
    meta = data.get('metadata', {})
    actual_title = meta.get('youtube_title', f"Tech Update v{run_number}")
    tags_string = ", ".join(meta.get('tags', ["Tech", "Android"]))
    
    full_description = f"{meta.get('description', '')}\n\n🔗 Full Technical Guide: {blog_link}\n\n#Tech #Android #FamilyTVR"

    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Family TVR Tech Podcast</title>
    <link>{blog_link}</link>
    <description>Latest updates from familytvr.blogspot.com</description>
    <itunes:image href="{main_cover_url}"/>
    <item>
      <title><![CDATA[{actual_title}]]></title> 
      <description><![CDATA[{full_description}]]></description>
      <pubDate>{pub_date}</pubDate>
      <itunes:keywords>{tags_string}</itunes:keywords>
      <enclosure url="{audio_url}" length="1024" type="audio/mpeg"/>
      <guid isPermaLink="false">v{run_number}_{int(time.time())}</guid>
    </item>
  </channel>
</rss>"""
    with open("podcast.xml", "w", encoding="utf-8") as f:
        f.write(rss_content.strip())

async def main():
    blog_data = get_latest_blog_post()
    if not blog_data:
        print("❌ RSS Empty")
        return

    data = await generate_content(blog_data)
    run_num = os.getenv("GITHUB_RUN_NUMBER", "1")
    full_script = "\n\n".join([s.get('content', '') for s in data.get('stories', [])])
    
    await text_to_speech(full_script, "episode.mp3")
    update_rss(data, run_num, blog_data['link'])
    print(f"✅ Synced: {blog_data['title']}")

if __name__ == "__main__":
    asyncio.run(main())
