# 🇻🇳 HƯỚNG DẪN REDDIT VIDEO MAKER BOT - THỊ TRƯỜNG VIỆT NAM

## MỤC LỤC
1. [Tổng quan dự án](#1-tổng-quan-dự-án)
2. [Phân tích kiến trúc code](#2-phân-tích-kiến-trúc-code)  
3. [Hướng dẫn cài đặt & chạy](#3-hướng-dẫn-cài-đặt--chạy)
4. [Chỉnh sửa cho thị trường Việt Nam](#4-chỉnh-sửa-cho-thị-trường-việt-nam)
5. [Chiến lược nội dung cho Việt Nam](#5-chiến-lược-nội-dung-cho-việt-nam)

---

## 1. TỔNG QUAN DỰ ÁN

### Bot này làm gì?
Tự động tạo video dạng "Reddit Stories" phổ biến trên TikTok/YouTube Shorts/Reels:
- Lấy bài viết từ Reddit
- Chuyển text thành giọng nói (Text-to-Speech)
- Chụp screenshot bài viết Reddit
- Ghép tất cả thành video hoàn chỉnh với video nền (Minecraft, GTA...)

### Luồng xử lý chính
```
1. Lấy bài viết Reddit (PRAW API)
       ↓
2. Text → Audio (TTS Engine) 
       ↓
3. Chụp screenshot bài viết (Playwright Browser)
       ↓
4. Tải video nền + nhạc nền (YouTube/yt-dlp)
       ↓
5. Ghép video cuối cùng (FFmpeg)
       ↓
6. Output: file .mp4 trong thư mục results/
```

---

## 2. PHÂN TÍCH KIẾN TRÚC CODE

### Cấu trúc thư mục
```
RedditVideoMakerBot/
├── main.py                          # Entry point - điều khiển toàn bộ flow
├── config.toml                      # File cấu hình (tự tạo khi chạy lần đầu)
├── requirements.txt                 # Dependencies
│
├── reddit/
│   └── subreddit.py                 # Kết nối Reddit API, lấy threads & comments
│
├── TTS/                             # Text-to-Speech engines
│   ├── engine_wrapper.py            # Wrapper chung - xử lý text → mp3
│   ├── GTTS.py                      # Google Translate TTS (miễn phí)
│   ├── TikTok.py                    # TikTok TTS 
│   ├── openai_tts.py                # OpenAI TTS (trả phí)
│   ├── elevenlabs.py                # ElevenLabs TTS (trả phí)
│   ├── aws_polly.py                 # AWS Polly TTS
│   ├── streamlabs_polly.py          # Streamlabs Polly TTS
│   └── pyttsx.py                    # Offline TTS (Windows/Mac)
│
├── video_creation/
│   ├── voices.py                    # Quản lý chọn TTS engine
│   ├── screenshot_downloader.py     # Chụp screenshot Reddit (Playwright)
│   ├── background.py                # Tải & cắt video/audio nền
│   ├── final_video.py               # FFmpeg - ghép video cuối cùng
│   └── data/
│       ├── cookie-dark-mode.json    # Cookie Reddit dark theme
│       └── cookie-light-mode.json   # Cookie Reddit light theme
│
├── utils/
│   ├── settings.py                  # Đọc & validate config.toml
│   ├── .config.template.toml        # Template cấu hình
│   ├── voice.py                     # Sanitize text cho TTS
│   ├── imagenarator.py              # Tạo ảnh text (story mode)
│   ├── background_videos.json       # Danh sách video nền (YouTube links)
│   ├── background_audios.json       # Danh sách nhạc nền
│   ├── ai_methods.py                # AI sorting (similarity)
│   ├── posttextparser.py            # Parser post text (story mode)
│   ├── console.py                   # Console logging
│   ├── cleanup.py                   # Dọn file tạm
│   ├── videos.py                    # Quản lý video đã tạo
│   └── ffmpeg_install.py            # Auto install FFmpeg
│
├── fonts/                           # Font chữ (Roboto)
├── assets/                          # Template, backgrounds
└── GUI.py                           # Giao diện web (Flask)
```

### Phân tích chi tiết từng module

#### A. `reddit/subreddit.py` - Lấy dữ liệu Reddit
```python
# Kết nối Reddit qua PRAW library
reddit = praw.Reddit(client_id, client_secret, username, password)

# Lấy bài viết hot từ subreddit
threads = subreddit.hot(limit=25)

# Trả về dict chứa: thread_title, thread_url, comments[], thread_post
```
**Quan trọng**: Cần Reddit API credentials (tạo tại reddit.com/prefs/apps)

#### B. `TTS/engine_wrapper.py` - Xử lý Text-to-Speech 
```python
class TTSEngine:
    - add_periods()      # Thêm dấu chấm cuối đoạn
    - call_tts()         # Gọi TTS engine tạo mp3
    - split_post()       # Chia post dài thành nhiều phần
    - run()              # Chạy TTS cho title + comments/post

# process_text() - Dịch text nếu post_lang được set
```
**Quan trọng cho VN**: Hàm `process_text()` có tính năng dịch ngôn ngữ qua `translators` library

#### C. `video_creation/screenshot_downloader.py` - Chụp ảnh
```python
# Dùng Playwright (headless Chrome) để:
1. Login vào Reddit
2. Navigate tới thread
3. Dịch title nếu post_lang được set (inject JS)
4. Chụp screenshot từng comment
```
**Quan trọng cho VN**: Có sẵn tính năng translate title trên screenshot

#### D. `video_creation/final_video.py` - Ghép video
```python
# Dùng FFmpeg Python binding để:
1. Cắt video nền theo tỉ lệ 9:16 (portrait)
2. Ghép audio clips
3. Overlay screenshot lên video nền
4. Merge background audio
5. Export video cuối cùng
```

### Bảng so sánh TTS Engines

| Engine | Tiếng Việt | Chi phí | Chất lượng | Ghi chú |
|---|---|---|---|---|
| **GoogleTranslate** | ✅ CÓ | Miễn phí | ⭐⭐⭐ | Dùng được ngay, giọng robot |
| **OpenAI TTS** | ✅ CÓ | ~$15/1M chars | ⭐⭐⭐⭐⭐ | Giọng tự nhiên nhất |
| **ElevenLabs** | ✅ CÓ | Free tier có | ⭐⭐⭐⭐⭐ | Multilingual v1 model |
| **TikTok** | ❌ KHÔNG | Miễn phí | ⭐⭐⭐⭐ | Chỉ EN/JP/KR/DE/FR... |
| **AWS Polly** | ❌ KHÔNG | Trả phí | ⭐⭐⭐⭐ | Không có voice VN |
| **pyttsx** | ⚠️ Tùy | Miễn phí | ⭐⭐ | Cần cài voice VN trên Windows |
| **Streamlabs** | ❌ KHÔNG | Miễn phí | ⭐⭐⭐ | Chỉ tiếng Anh |

---

## 3. HƯỚNG DẪN CÀI ĐẶT & CHẠY

### Bước 1: Cài Python 3.10/3.11/3.12
1. Tải từ https://www.python.org/downloads/
2. **QUAN TRỌNG**: Tick ✅ "Add Python to PATH" khi cài
3. Kiểm tra: mở CMD/PowerShell → `python --version`

### Bước 2: Cài FFmpeg
1. Tải từ https://ffmpeg.org/download.html
2. Giải nén, thêm thư mục `bin/` vào PATH
3. Hoặc bot sẽ tự cài qua `utils/ffmpeg_install.py`

### Bước 3: Cài dependencies
```powershell
cd C:\Users\Administrator\Desktop\earn\RedditVideoMakerBot
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install
python -m playwright install-deps
```

### Bước 4: Tạo Reddit App
1. Vào https://www.reddit.com/prefs/apps
2. Click "Create App" hoặc "Create Another App"
3. Chọn type: **script**
4. Redirect URI: nhập bất kỳ URL (vd: https://localhost)
5. Lưu lại **client_id** (dưới tên app) và **client_secret**

### Bước 5: Chạy bot
```powershell
python main.py
```
Bot sẽ hỏi bạn điền thông tin lần đầu → tạo file `config.toml`

### Bước 6: Video output
Video sẽ được lưu tại: `results/<tên_subreddit>/<tên_video>.mp4`

---

## 4. CHỈNH SỬA CHO THỊ TRƯỜNG VIỆT NAM

### 4.1. Cấu hình config.toml cho tiếng Việt

Sau khi chạy lần đầu, mở `config.toml` và sửa:

```toml
[reddit.thread]
subreddit = "AskReddit"          # Hoặc subreddit bạn muốn
post_lang = "vi"                  # ← QUAN TRỌNG: Dịch sang tiếng Việt
max_comment_length = 500
min_comment_length = 10

[settings]
theme = "dark"
storymode = false                 # true nếu muốn đọc nguyên bài
channel_name = "Reddit Việt Nam"  # Tên kênh của bạn

[settings.tts]
voice_choice = "googletranslate"  # ← Dùng Google TTS cho tiếng Việt (miễn phí)
# HOẶC
# voice_choice = "OpenAI"         # Nếu có API key OpenAI (giọng đẹp hơn)
# openai_api_key = "sk-..."
# openai_voice_name = "nova"
```

### 4.2. Khi set `post_lang = "vi"`, bot sẽ tự động:
1. **Dịch text** sang tiếng Việt trước khi chuyển thành audio (file `TTS/engine_wrapper.py` → `process_text()`)
2. **Dịch title** trên screenshot Reddit (file `video_creation/screenshot_downloader.py`)
3. **Dịch tên file** video output (file `video_creation/final_video.py` → `name_normalize()`)
4. **Google TTS** sẽ đọc bằng tiếng Việt (file `TTS/GTTS.py` dùng `post_lang`)

### 4.3. Nâng cấp TTS tiếng Việt (Khuyến nghị)

#### Phương án 1: OpenAI TTS (Khuyến nghị nhất - giọng tự nhiên)
```toml
[settings.tts]
voice_choice = "OpenAI"
openai_api_key = "sk-your-key-here"
openai_voice_name = "nova"       # Giọng nữ, hoặc "onyx" cho giọng nam
openai_model = "tts-1"           # "tts-1-hd" cho chất lượng cao hơn
```

#### Phương án 2: ElevenLabs (Giọng tự nhiên, clone giọng được)
```toml
[settings.tts]
voice_choice = "elevenlabs"
elevenlabs_api_key = "your-api-key"
elevenlabs_voice_name = "Bella"
```

#### Phương án 3: Tự tạo TTS Engine riêng cho tiếng Việt
Tạo file `TTS/vietTTS.py`:

```python
# Ví dụ dùng edge-tts (miễn phí, giọng Việt đẹp)
# Cần: pip install edge-tts
import asyncio
import edge_tts

class VietTTS:
    def __init__(self):
        self.max_chars = 5000
        # Voices tiếng Việt có sẵn:
        # vi-VN-HoaiMyNeural (nữ) - KHUYẾN NGHỊ
        # vi-VN-NamMinhNeural (nam)
        self.default_voice = "vi-VN-HoaiMyNeural"
    
    def run(self, text, filepath, random_voice: bool = False):
        voice = self.default_voice
        if random_voice:
            import random
            voice = random.choice([
                "vi-VN-HoaiMyNeural",
                "vi-VN-NamMinhNeural"
            ])
        asyncio.run(self._generate(text, filepath, voice))
    
    async def _generate(self, text, filepath, voice):
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filepath)
```

Sau đó thêm vào `video_creation/voices.py`:
```python
from TTS.vietTTS import VietTTS

TTSProviders = {
    "GoogleTranslate": GTTS,
    # ... (giữ nguyên các engine cũ)
    "VietTTS": VietTTS,        # ← Thêm dòng này
}
```

Config:
```toml
[settings.tts]
voice_choice = "VietTTS"
```

### 4.4. Font tiếng Việt (Unicode support)

Font Roboto trong thư mục `fonts/` đã hỗ trợ Unicode/tiếng Việt.
Nếu gặp lỗi hiển thị dấu, thay bằng font hỗ trợ Việt tốt hơn:
- Tải "Noto Sans" từ Google Fonts
- Đặt vào thư mục `fonts/`
- Sửa trong `video_creation/final_video.py` và `utils/imagenarator.py`:
  ```python
  # Thay "Roboto-Bold.ttf" → "NotoSans-Bold.ttf"
  font = ImageFont.truetype(os.path.join("fonts", "NotoSans-Bold.ttf"), font_title_size)
  ```

### 4.5. Dịch text sanitization cho tiếng Việt

File `utils/voice.py` hàm `sanitize_text()` loại bỏ nhiều ký tự đặc biệt.
Tiếng Việt dùng dấu nên cần đảm bảo KHÔNG loại bỏ ký tự Unicode Vietnamese.
→ Kiểm tra regex trong hàm `sanitize_text()` - hiện tại chỉ loại ký tự ASCII đặc biệt nên tiếng Việt KHÔNG bị ảnh hưởng. ✅

### 4.6. Tùy chỉnh subreddit phù hợp người Việt

Các subreddit hay cho nội dung Việt Nam:
```toml
# Stories/Câu chuyện:
subreddit = "AskReddit"              # Hỏi đáp - nhiều view nhất
subreddit = "tifu"                   # Câu chuyện fail 
subreddit = "relationship_advice"    # Tư vấn tình cảm
subreddit = "AmItheAsshole"          # Drama - rất viral

# Dùng storymode cho:
subreddit = "nosleep"                # Truyện kinh dị
subreddit = "confession"             # Confession/tâm sự
```

---

## 5. CHIẾN LƯỢC NỘI DUNG CHO VIỆT NAM

### 5.1. Nền tảng target
- **TikTok** (video 9:16, < 3 phút) - Resolution: 1080x1920 (đã mặc định)
- **YouTube Shorts** (< 60 giây)
- **Facebook Reels**

### 5.2. Gợi ý cấu hình tối ưu
```toml
[settings]
resolution_w = 1080
resolution_h = 1920
opacity = 0.9
storymode = true                     # Story mode cho truyện
storymodemethod = 1                  # Fancy style
channel_name = "Reddit Việt"

[settings.background]
background_video = "minecraft"       # Hoặc "gta", "rocket-league"
background_audio = "lofi"
background_audio_volume = 0.1        # Nhạc nền nhỏ

[settings.tts]
voice_choice = "googletranslate"     # Miễn phí
silence_duration = 0.3
no_emojis = true                     # Bỏ emoji cho TTS
```

### 5.3. Workflow sản xuất đề xuất
1. Chạy bot → lấy video từ Reddit (tiếng Anh)
2. Bot tự dịch sang tiếng Việt (post_lang = "vi")
3. TTS đọc tiếng Việt (Google/OpenAI)
4. Upload lên TikTok/YouTube/Facebook
5. Thêm hashtag: #reddit #redditvietnam #storytime #truyenreddit

### 5.4. Lưu ý pháp lý
- Nội dung Reddit là PUBLIC nhưng nên credit nguồn
- Tránh nội dung NSFW (set `allow_nsfw = false`)
- Kiểm tra `blocked_words` để lọc nội dung không phù hợp

---

## 6. TROUBLESHOOTING

| Lỗi | Nguyên nhân | Giải pháp |
|---|---|---|
| `Python not found` | Chưa cài Python hoặc chưa thêm PATH | Cài Python, tick "Add to PATH" |
| `FFmpeg not found` | Chưa cài FFmpeg | Bot tự cài hoặc cài manual |
| `Invalid credentials` | Sai Reddit API key | Kiểm tra config.toml |
| `TikTok sessionid required` | Dùng TikTok TTS mà chưa set session | Đổi sang googletranslate |
| Font lỗi dấu tiếng Việt | Font không hỗ trợ Unicode VN | Đổi sang Noto Sans |
| `Ratelimit hit` | Reddit giới hạn request | Đợi hoặc giảm times_to_run |
| Text dịch sai | Google Translate tự động | Review manual, sửa text |
