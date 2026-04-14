import os
import asyncio
import time
import feedparser
import random
import re
import edge_tts
from groq import Groq
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont
import textwrap

# إعدادات
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

def create_enhanced_thumbnail(title_text):
    """دالة لإنشاء صورة مصغرة نظيفة واحترافية بدون تداخل نصوص"""
    try:
        # 1. فتح الصورة الأصلية (يجب أن تكون نسخة نظيفة تماماً بدون أي كتابة يدوية)
        # تأكد من رفع صورة باسم "clean_cover.jpg" لا تحتوي على نصوص
        if os.path.exists("clean_cover.jpg"):
            img = Image.open("clean_cover.jpg").copy()
        else:
            img = Image.open("podcast_cover.jpg").copy()
            
        width, height = img.size
        draw = ImageDraw.Draw(img)

        # 2. إعداد الخط (DejaVuSans-Bold متوفر في GitHub Actions)
        try:
            # حجم الخط 60 ليكون كبيراً وواضحاً
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        except:
            font = ImageFont.load_default()

        # 3. تنظيم النص لأسطر قصيرة (20 حرف للسطر) لزيادة نسبة النقر
        lines = textwrap.wrap(title_text, width=20)
        
        # 4. مكان البداية في الجزء العلوي المظلم (بعيداً عن وجه الرجل)
        y_text = 50 
        
        for line in lines:
            # حساب التوسيط
            left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
            w = right - left
            x_text = (width - w) / 2
            
            # 5. رسم النص الأبيض مع إطار أسود (Stroke) لضمان الوضوح التام
            draw.text((x_text, y_text), line, font=font, fill="white", 
                      stroke_width=4, stroke_fill="black")
            
            y_text += 80 # المسافة بين الأسطر

        # 6. حفظ الصورة النهائية كـ podcast_cover.jpg ليقرأها يوتيوب
        img.save("podcast_cover.jpg")
        print("Success: New clean thumbnail generated.")
    except Exception as e:
        print(f"Thumbnail error: {e}")

async def main():
    # 1. جلب المقالات من RSS
    rss_url = "https://www.economist.com/latest/rss.xml"
    feed = feedparser.parse(rss_url)
    if not feed.entries: return

    entry = random.choice(feed.entries)
    title = entry.title
    summary = re.sub('<[^<]+?>', '', entry.summary)

    # 2. توليد السكريبت والوصف عبر Groq
    script_prompt = f"Write a detailed professional podcast script in English about: {title}. Context: {summary}. 350 words."
    chat_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": script_prompt}]
    )
    podcast_script = chat_response.choices[0].message.content

    desc_prompt = f"Create a short SEO description for a podcast titled: {title}"
    desc_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": desc_prompt}]
    )
    description = desc_response.choices[0].message.content

    # --- الخطوة الحاسمة: توليد الصورة قبل رفعها ---
    create_enhanced_thumbnail(title)

    # 3. تحويل الصوت
    audio_file = "episode.mp3"
    communicate = edge_tts.Communicate(podcast_script, "en-US-ChristopherNeural")
    await communicate.save(audio_file)
    
    # 4. تحديث ملف الـ RSS
    run_num = os.getenv("GITHUB_RUN_NUMBER", "1")
    timestamp = int(time.time())
    audio_url = f"https://github.com/eslamtechautomation-ctrl/TrustMask-Bot-main/releases/download/v{run_num}/episode.mp3"
    
    rss_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>The Economic Edge: Master Your Wealth</title>
    <itunes:image href="https://raw.githubusercontent.com/eslamtechautomation-ctrl/TrustMask-Bot-main/refs/heads/main/podcast_cover.jpg" />
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
