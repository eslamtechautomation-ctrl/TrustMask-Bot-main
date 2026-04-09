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

# 1. جلب محتوى المقال الأخير من RSS المدونة
def get_latest_blog_post():
    rss_url = "https://familytvr.blogspot.com/feeds/posts/default?alt=rss"
    feed = feedparser.parse(rss_url)
    if feed.entries:
        latest_entry = feed.entries[0]
        # تنظيف النص من أكواد HTML ليكون النص صافي
        clean_content = re.sub('<[^<]+?>', '', latest_entry.content[0].value)
        return {
            "title": latest_entry.title,
            "content": clean_content,
            "link": latest_entry.link
        }
    return None

async def generate_content(blog_data):
    if not blog_data:
        return None

    # الموجه الجديد: يركز فقط على محتوى المدونة والتقنية
    prompt = f"""
    Role: You are a professional Tech Content Creator for YouTube and Dailymotion.
    Task: Convert the following blog post into a structured 4-segment video script.
    
    SOURCE MATERIAL (Blog Post):
    Title: {blog_data['title']}
    Content: {blog_data['content']}
    Blog Link: {blog_data['link']}

    STRICT INSTRUCTIONS:
    1. Tone: Professional, informative, and technical (Mirror the blog's style).
    2. Format: Output ONLY a JSON object.
    3. Transformation: Break the article into 4 clear segments that explain the topic thoroughly.
    4. Call to Action: Direct viewers to visit {blog_data['link']} for the full guide.
    5. Promotion: Mention our official apps available on the blog.
    6. Metadata: Provide a 'youtube_title' based on the blog title, an SEO 'description', and 20 relevant 'tags'.
    """
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(completion.choices[0].message.content)

async def text_to_speech(text, output_file):
    # استخدام صوت Christopher الاحترافي
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(output_file)

def update_rss(data, run_number, blog_link):
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    audio_url = f"https://github.com/eslamtechautomation-ctrl/TrustMask-Bot-main/releases/download/v{run_number}/episode.mp3"
    main_cover_url = "https://raw.githubusercontent.com/eslamtechautomation-ctrl/TrustMask-Bot-main/main/podcast_cover.jpg"
    
    meta = data.get('metadata', {})
    actual_title = meta.get('youtube_title', f"Tech Update v{run_number}")
    tags_string = ", ".join(meta.get('tags', ["Tech", "Android", "Tutorial"]))
    
    stories = data.get('stories', [])
    summary_text = "\n".join([f"- {s.get('summary', 'Latest tech update.')}" for s in stories])
    
    # الوصف يركز على الرابط والمحتوى التقني
    full_description = f"{meta.get('description', '')}\n\nFull Guide & App Download: {blog_link}\n\n#Technology #TechNews #FamilyTVR"
    file_size = os.path.getsize("episode.mp3") if os.path.exists("episode.mp3") else "1024"

    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Family TVR: Tech &amp; Software Updates</title>
    <link>{blog_link}</link>
    <description>Official video podcast for familytvr.blogspot.com - Covering latest apps and tech guides.</description>
    <language>en-us</language>
    <itunes:category text="Technology"/>
    <itunes:image href="{main_cover_url}"/>
    <item>
      <title><![CDATA[{actual_title}]]></title> 
      <description><![CDATA[{full_description}]]></description>
      <pubDate>{pub_date}</pubDate>
      <itunes:keywords>{tags_string}</itunes:keywords>
      <enclosure url="{audio_url}" length="{file_size}" type="audio/mpeg"/>
      <guid isPermaLink="false">v{run_number}_{int(time.time())}</guid>
    </item>
  </channel>
</rss>"""
    with open("podcast.xml", "w", encoding="utf-8") as f:
        f.write(rss_content.strip())

async def main():
    print("📡 Fetching latest content from your blog...")
    blog_data = get_latest_blog_post()
    
    if not blog_data:
        print("❌ Could not find any posts on the blog.")
        return

    print(f"🤖 Processing Article: {blog_data['title']}...")
    data = await generate_content(blog_data)
    
    if not data or not data.get('stories'):
        print("❌ AI failed to repurpose content.")
        return

    run_num = os.getenv("GITHUB_RUN_NUMBER", "1")
    full_script = "\n\n".join([s.get('content', '') for s in data.get('stories', [])])
    
    print(f"🎙️ Creating Audio for Video v{run_num}...")
    await text_to_speech(full_script, "episode.mp3")
    
    print("📝 Writing final RSS for YouTube/Dailymotion...")
    update_rss(data, run_num, blog_data['link'])
    print(f"✅ Success! Content synced for: {blog_data['title']}")

if __name__ == "__main__":
    asyncio.run(main())
