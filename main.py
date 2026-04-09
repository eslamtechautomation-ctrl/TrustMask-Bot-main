import os
import asyncio
import json
import edge_tts
import time
import feedparser # ستحتاج لإضافتها في متطلبات المشروع
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
        # تنظيف النص من أكواد HTML
        clean_content = re.sub('<[^<]+?>', '', latest_entry.content[0].value)
        return {
            "title": latest_entry.title,
            "content": clean_content,
            "link": latest_entry.link
        }
    return None


async def generate_content(blog_data):
    # نمرر محتوى المقال للموجه
    prompt = f"""
    Role: Professional YouTube Creator & Tech Investigative Journalist.
    Task: Repurpose a Blog Article into a viral Video Podcast script.
    
    SOURCE ARTICLE FROM BLOG:
    Title: {blog_data['title']}
    Content: {blog_data['content']}
    
    STRICT INSTRUCTIONS:
    1. Tone: Deep, dark, and investigative (Deep Web style).
    2. Format: Output ONLY a JSON object.
    3. Transformation: Rewrite the article content into 4 dramatic storytelling segments (400-600 words each).
    4. Integration: Mention that the viewer can find more technical details at {blog_data['link']}.
    5. Promotion: Include a segment about downloading our official apps from familytvr.blogspot.com.
    6. Metadata: Provide catchy YouTube SEO title, description, and 20 keywords.
    """
    # باقي كود الـ completion كما هو...
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(completion.choices[0].message.content)

async def text_to_speech(text, output_file):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
    await communicate.save(output_file)

def update_rss(data, run_number):
    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    audio_url = f"https://github.com/eslamtechautomation-ctrl/TrustMask-Bot-main/releases/download/v{run_number}/episode.mp3"
    main_cover_url = "https://raw.githubusercontent.com/eslamtechautomation-ctrl/TrustMask-Bot-main/main/podcast_cover.jpg"
    
    # استخراج العنوان الفعلي من JSON الـ AI
    # لو الـ AI منساش الـ title هياخده، لو نساه هياخد اسم افتراضي برقم الـ Run
    actual_title = data.get('title', f"Tech Mystery Deep Web v{run_number}")
    
    meta = data.get('metadata', {})
    # تحويل التاجز من JSON إلى نص مفصول بفواصل ليفهمه يوتيوب
    tags_list = meta.get('tags', [])
    tags_string = ", ".join(tags_list) if tags_list else "AI, Tech, 2026, Deep Web"
    # تجميع ملخصات الـ 4 قصص عشان الوصف يتغير كل مرة
    stories = data.get('stories', [])
    chapters = "\n".join([f"- {s.get('summary', 'New tech story update.')}" for s in stories])
    
    full_description = f"{meta.get('description', '')}\n\nWhat's in this episode:\n{chapters}\n\n#2026 #AI #DeepWeb"

    file_size = os.path.getsize("episode.mp3") if os.path.exists("episode.mp3") else "1024"

    # وسم الـ <title> دلوقتي هياخد actual_title المتغير
  # إضافة وسم التصنيف الفرعي ووسوم التحسين
    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" 
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" 
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
     xmlns:media="http://search.yahoo.com/mrss/"
  <channel>
    <itunes:type>episodic</itunes:type>
    <title>Deep Web Tech Stories: AI &amp; 2026 Trends</title>
    <link>https://familytvr.blogspot.com/</link>
    <description>Investigating the dark side of technology and 2026 innovations.</description>
   <language>en-us</language>
    <itunes:category text="Music"/>
    <itunes:category text="Technology"/>
    <itunes:category text="News">
      <itunes:category text="Tech News"/>
    </itunes:category>
    <itunes:image href="{main_cover_url}"/>
    <itunes:author>Broadcast4u</itunes:author>
    <itunes:explicit>yes</itunes:explicit>
    <itunes:block>no</itunes:block> 
    <itunes:owner>
      <itunes:name>Broadcast4u</itunes:name>
      <itunes:email>eslammosde@gmail.com</itunes:email>
    </itunes:owner>
    <item>
      <title><![CDATA[{actual_title}]]></title> 
      <description><![CDATA[{full_description}]]></description>
      <content:encoded><![CDATA[{full_description}]]></content:encoded>
      <pubDate>{pub_date}</pubDate>
      <itunes:keywords>{tags_string}</itunes:keywords>  <itunes:explicit>yes</itunes:explicit>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:episode>{run_number}</itunes:episode>
      <itunes:explicit>yes</itunes:explicit>
      <itunes:image href="{main_cover_url}"/>
      <enclosure url="{audio_url}" length="{file_size}" type="audio/mpeg"/>
      <guid isPermaLink="false">v{run_number}_{int(time.time())}</guid>
    </item>
  </channel>
</rss>"""
    with open("podcast.xml", "w", encoding="utf-8") as f:
        f.write(rss_content.strip())

async def main():
    print("🤖 Generating mystery episode...")
    data = await generate_content()
    
    # التأكد من وجود قصص على الأقل قبل المتابعة
    if not data.get('stories'):
        print("❌ Error: AI returned empty stories. Stopping to prevent corrupted RSS.")
        return

    run_num = os.getenv("GITHUB_RUN_NUMBER", "1")
    
    # تجميع القصص للصوت بأمان (لو الـ content ناقص مش هيطلع Error)
    full_script = "\n\n".join([s.get('content', 'Searching for more deep web data...') for s in data.get('stories', [])])
    
    print(f"🎙️ Creating Audio v{run_num}...")
    await text_to_speech(full_script, "episode.mp3")
    
    print("📝 Writing Fresh RSS Feed...")
    update_rss(data, run_num)
    print(f"✅ Done! Episode v{run_num} is ready.")
if __name__ == "__main__":
    asyncio.run(main())
