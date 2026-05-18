#!/usr/bin/env python3
"""
📰 Мэдээ / Нийгмийн сүлжээний пост үүсгэгч бот
Supports: Instagram, Facebook, News, LinkedIn, TikTok
Language: Монгол 🇲🇳 / English 🇬🇧
"""

import re
import sys
import os
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.local_config import (
    DEFAULT_LANG,
    ENABLE_MONGOLIAN_POLISH,
    MODELS,
    MONGOLIAN_FALLBACK_ON_LOW_QUALITY,
    NEWS_OUTPUT,
    NEWS_TEMPERATURE,
    NEWS_TONES,
    POST_TYPES,
)
from agent.ollama_client import OllamaError, generate

# ─── Prompt Templates ─────────────────────────────────────────────────────────

PROMPTS = {
    "instagram": {
        "mn": """Та Instagram-д зориулсан пост бичих мэргэжилтэн.
Дараах сэдвээр Монгол хэлээр Instagram пост бич:

Сэдэв: {topic}
Нэмэлт мэдээлэл: {details}

Дараах форматаар бич:
📸 CAPTION (2-3 өгүүлбэр, engaging, emoji ашиглах)
.
.
.
#hashtag1 #hashtag2 #hashtag3 (5-8 холбогдох hashtag Монгол + Англи хоёуланг)

Нэмэлт дүрэм:
- Кирилл бичлэг баримтал; Latin үсгээр Монгол үг бүү бич.
- Өгүүлбэрийг байгалийн, уншихад амар хэлбэрээр бич.
- Тайлбар, тайлбарласан жагсаалт бүү нэм.

Зөвхөн постын агуулгыг бич, тайлбар нэмэх хэрэггүй.""",

        "en": """You are an Instagram content specialist.
Write an Instagram post in English about:

Topic: {topic}
Additional info: {details}

Format:
📸 CAPTION (2-3 sentences, engaging, use emojis)
.
.
.
#hashtag1 #hashtag2 #hashtag3 (5-8 relevant hashtags)

Write only the post content, no explanations.""",
    },

    "facebook": {
        "mn": """Та Facebook маркетингийн мэргэжилтэн.
Дараах сэдвээр Монгол хэлээр Facebook пост бич:

Сэдэв: {topic}
Нэмэлт мэдээлэл: {details}

Шаардлага:
- 3-5 өгүүлбэр
- Уншигчийг татах нээлтийн өгүүлбэр
- Дунд хэсэгт дэлгэрэнгүй мэдээлэл
- Сүүлд заалт (call to action)
- 3-5 холбогдох hashtag
- Кирилл бичлэг баримтал; Latin үсгээр Монгол үг бүү бич.
- Үг, утга, зөв бичих дүрмийг алдаа багатай баримтал.

Зөвхөн постын агуулгыг бич.""",

        "en": """You are a Facebook marketing specialist.
Write a Facebook post in English about:

Topic: {topic}
Additional info: {details}

Requirements:
- 3-5 sentences
- Engaging opening line
- Informative middle section
- Call to action at the end
- 3-5 relevant hashtags

Write only the post content.""",
    },

    "news": {
        "mn": """Та мэргэжлийн сэтгүүлч.
Дараах сэдвээр Монгол хэлээр мэдээний нийтлэл бич:

Сэдэв: {topic}
Нэмэлт мэдээлэл: {details}

Форматаар бич:
ГАРЧИГ: (анхаарал татах гарчиг)

АГУУЛГА:
(3-4 параграф — Who, What, When, Where, Why)

ДҮГНЭЛТ:
(1 параграф)

Нэмэлт дүрэм:
- Кирилл бичлэг баримтал; Latin үсгээр Монгол үг бүү бич.
- Баримтгүй мэдээлэл зохиохгүй, мэдэхгүй бол ерөнхий байдлаар бич.
- Албан, ойлгомжтой найруулгаар бич.

Зөвхөн нийтлэлийн агуулгыг бич.""",

        "en": """You are a professional journalist.
Write a news article in English about:

Topic: {topic}
Additional info: {details}

Format:
HEADLINE: (attention-grabbing headline)

BODY:
(3-4 paragraphs — Who, What, When, Where, Why)

CONCLUSION:
(1 paragraph)

Write only the article content.""",
    },

    "linkedin": {
        "mn": """Та LinkedIn контентын мэргэжилтэн.
Дараах сэдвээр Монгол хэлээр LinkedIn пост бич:

Сэдэв: {topic}
Нэмэлт мэдээлэл: {details}

Формат:
🎯 HOOK (1 мөр — анхаарал татах)
.
.
📌 ҮНДСЭН САНАА (2-4 өгүүлбэр, мэргэжлийн, ойлгомжтой)
.
.
✅ CTA (1 өгүүлбөр — сэтгэгдэл, хуваалцах, холбогдох уриалга)
.
.
#hashtag1 #hashtag2 (3-5 мэргэжлийн hashtag)

Дүрэм:
- Кирилл бичлэг; Latin-ээр Монгол үг бүү бич.
- LinkedIn-д тохирсон албан, итгэл төрүүлэх өнгө.
- Зөвхөн постын агуулга.""",

        "en": """You are a LinkedIn content specialist.
Write a LinkedIn post in English about:

Topic: {topic}
Additional info: {details}

Format:
🎯 HOOK (1 line — attention-grabbing)
.
.
📌 MAIN IDEA (2-4 sentences, professional, clear)
.
.
✅ CTA (1 sentence — comment, share, or connect)
.
.
#hashtag1 #hashtag2 (3-5 professional hashtags)

Write only the post content.""",
    },

    "tiktok": {
        "mn": """Та TikTok контентын scriptwriter.
Дараах сэдвээр Монгол хэлээр 20-30 секундын TikTok видео script бич:

Сэдэв: {topic}
Нэмэлт мэдээлэл: {details}

Формат:
🎬 HOOK (0-3 сек — анхаарал татах 1 өгүүлбэр)
.
.
🗣️ SCRIPT (15-25 сек — ярианы хэв маяг, богино өгүүлбэр)
.
.
📣 CTA (сүүлийн 3-5 сек — дагах, like, comment уриалга)
.
.
#hashtag1 #hashtag2 (3-6 TikTok hashtag)

Дүрэм:
- Кирилл бичлэг; Latin-ээр Монгол үг бүү бич.
- Уншихад амар, ярианд ойрхон бич.
- Зөвхөн script агуулга.""",

        "en": """You are a TikTok scriptwriter.
Write a 20-30 second TikTok video script in English about:

Topic: {topic}
Additional info: {details}

Format:
🎬 HOOK (0-3 sec — one attention-grabbing line)
.
.
🗣️ SCRIPT (15-25 sec — spoken style, short sentences)
.
.
📣 CTA (last 3-5 sec — follow, like, comment)
.
.
#hashtag1 #hashtag2 (3-6 TikTok hashtags)

Write only the script content.""",
    },
}

POST_TYPE_ICONS = {
    "instagram": "📸",
    "facebook": "📘",
    "news": "📰",
    "linkedin": "💼",
    "tiktok": "🎵",
}

TONES = {
    "balanced": {
        "mn": "Тэнцвэртэй, ойлгомжтой, байгалийн найруулгатай бич.",
        "en": "Use a balanced, clear, natural style.",
    },
    "friendly": {
        "mn": "Илүү найрсаг, дулаан, уншигчтай ойр өнгөөр бич.",
        "en": "Use a friendly, warm, approachable style.",
    },
    "formal": {
        "mn": "Албан, мэргэжлийн, товч тодорхой өнгөөр бич.",
        "en": "Use a formal, professional, concise style.",
    },
    "marketing": {
        "mn": "Маркетингийн өнгө аястай, анхаарал татахуйц, action-oriented бич.",
        "en": "Use a marketing-focused, attention-grabbing, action-oriented style.",
    },
    "short": {
        "mn": "Богино, шахуу, илүү шууд хэлбэрээр бич.",
        "en": "Use a short, compact, direct style.",
    },
}

assert tuple(TONES) == NEWS_TONES

QUALITY_GUIDELINES = {
    "mn": """Чанарын шаардлага:
- Орчуулгын мэт эвдэрхий өгүүлбэр бүү бич.
- Утга тодорхой, энгийн хүнд ойлгомжтой Монгол хэлээр бич.
- "дүрсүүдэд бие бөөрөгч", "учир болох нь" гэх мэт хиймэл, буруу холбоос үгс бүү хэрэглэ.
- Сэдвийг мэдэхгүй бол зохиомол баримт нэмэлгүй ерөнхий, үнэн зөв тайлбарла.
- Гарчиг, дунд хэсэг гэх мэт prompt-ийн тайлбар үгийг хэрэггүй үед битгий хуул.
- Hashtag байвал богино, уншигдахуйц, утгатай байлга.""",
    "en": """Quality rules:
- Avoid awkward literal translation.
- Keep the meaning clear and easy for a general reader.
- Do not invent unsupported facts.
- Do not copy prompt labels unless they are part of the requested format.
- Keep hashtags short, readable, and relevant.""",
}

LOW_QUALITY_MN_MARKERS = (
    "дүрсүүдэд",
    "бие бөөрөгч",
    "учир болох нь",
    "санал буулгах",
    "амьдралт урьдчилан",
    "үндсэн нээлтийн өгүүлбэр",
    "call to action",
    "[link]",
    "холбогдох hashtag",
    "энэ бол бол",
    "гэж байна гэж",
    "юм байна гэж",
)

# Latin transliteration / холимог бичлэг илрүүлэх
LATIN_TRANSLIT_MARKERS = (
    "sain baina",
    "sain uu",
    "bayarlalaa",
    "mongol uls",
    "geh ve",
    "gui baina",
    "uur hun",
)

CYRILLIC_RE = re.compile(r"[\u0400-\u04FFөӨүҮёЁ]")
LATIN_WORD_RE = re.compile(r"\b[a-zA-Z]{3,}\b")
HASHTAG_RE = re.compile(r"#\w+")

# ─── Core functions ───────────────────────────────────────────────────────────

def call_ollama(
    prompt: str,
    model: str = MODELS["news"],
    *,
    temperature: float = NEWS_TEMPERATURE,
    num_predict: int = 800,
) -> str:
    """Ollama API-тай холбогдох"""
    try:
        return generate(
            prompt,
            model,
            options={
                "temperature": temperature,
                "top_p": 0.9,
                "num_predict": num_predict,
            },
        )
    except OllamaError as e:
        return f"❌ Алдаа: {e}"


def build_prompt(post_type: str, topic: str, details: str, lang: str, tone: str) -> str:
    """Prompt-ыг нэг дор угсрах."""
    template = PROMPTS[post_type][lang]
    tone_instruction = TONES[tone][lang]
    prompt = template.format(topic=topic, details=details or "Нэмэлт мэдээлэл байхгүй")
    return (
        f"{prompt}\n\n"
        f"Загвар / Style:\n{tone_instruction}\n\n"
        f"{QUALITY_GUIDELINES[lang]}"
    )


def polish_mongolian_content(content: str, post_type: str, tone: str) -> str:
    """Монгол гаралтыг хоёр дахь pass-аар найруулга, утга, зөв бичих талаас засах."""
    if content.startswith("❌"):
        return content

    script_note = ""
    if has_script_issues(content):
        script_note = (
            "\n- Latin үсгээр бичсэн Монгол үг, transliteration-ийг кирилл болгоно уу.\n"
            "- Hashtag-ийг хэвээр үлдээж болно."
        )

    prompt = f"""Та Монгол хэлний редактор.
Доорх {post_type} төрлийн бичвэрийг зас.

Зорилго:
- Утга алдагдуулахгүй.
- Эвдэрхий, ойлгомжгүй өгүүлбэрийг байгалийн Монгол хэл болго.
- Илүүц prompt label (жишээ нь "ГАРЧИГ:", "HOOK:") хэрэггүй бол ав.
- Цэг, таслал, зайг зөв болго.
- Кирилл бичгээр, уншигдахуйц, {tone} өнгө аястай болго.{script_note}
- Зөвхөн зассан эцсийн бичвэрийг буцаа.

Эх бичвэр:
{content}
"""
    polished = call_ollama(prompt, temperature=0.2, num_predict=900)
    if not polished or polished.startswith("❌"):
        return content

    if has_content_issues(polished) and not has_content_issues(content):
        return content
    return polished


def has_script_issues(content: str) -> bool:
    """Кирилл + Latin transliteration холимог эсэх."""
    if not CYRILLIC_RE.search(content):
        return False

    lowered = content.lower()
    if any(marker in lowered for marker in LATIN_TRANSLIT_MARKERS):
        return True

    hashtag_tags = {h.lstrip("#").lower() for h in HASHTAG_RE.findall(content)}
    latin_words = [
        w.lower()
        for w in LATIN_WORD_RE.findall(content)
        if w.lower() not in hashtag_tags
    ]
    if len(latin_words) >= 2:
        return True
    return False


def has_low_quality_mongolian(content: str) -> bool:
    """Эвдэрхий Монгол гаралтыг илрүүлэх энгийн heuristic."""
    lowered = content.lower()
    if any(marker in lowered for marker in LOW_QUALITY_MN_MARKERS):
        return True
    return lowered.count("**") >= 4 or lowered.count("#") > 12


def has_content_issues(content: str) -> bool:
    """Polish дахин дуудах / fallback шийдвэрт ашиглана."""
    return has_low_quality_mongolian(content) or has_script_issues(content)


def _mn_hashtags(topic: str) -> str:
    cleaned = "".join(ch for ch in topic if ch.isalnum())
    topic_tag = f"#{cleaned}" if cleaned else "#Монгол"
    if "ai" in topic.lower() or "хиймэл" in topic.lower():
        return f"{topic_tag} #AI #ХиймэлОюун #Технологи #ДижиталШийдэл"
    return f"{topic_tag} #Монгол #ШинэМэдээ #Технологи"


def build_safe_mongolian_content(post_type: str, topic: str, details: str, tone: str) -> str:
    """AI Монгол хэлээр эвдэрхий бичвэл уншигдахуйц deterministic fallback үүсгэнэ."""
    context = details.strip() or f"{topic} сэдвийг энгийн, ойлгомжтой байдлаар тайлбарлах."
    hashtags = _mn_hashtags(topic)
    is_ai = "ai" in topic.lower() or "хиймэл" in topic.lower()

    if is_ai:
        simple_explain = (
            "Энгийнээр хэлбэл, AI буюу хиймэл оюун нь мэдээлэлд тулгуурлан суралцаж, "
            "давтамжтай ажлыг автоматжуулах, санаа боловсруулах, шийдвэр гаргалтад туслах технологи юм."
        )
        daily_use = (
            "Бид үүнийг орчуулга хийх, зураг таних, хэрэглэгчийн асуултад хариулах, "
            "судалгаа нэгтгэх, ажил төлөвлөх зэрэг өдөр тутмын олон зүйлд ашиглаж болно."
        )
    else:
        simple_explain = (
            f"{topic} нь хүмүүст мэдээллийг илүү ойлгомжтой авч, ажлаа илүү үр дүнтэй хийхэд "
            "тусалж болох чухал сэдэв юм."
        )
        daily_use = f"Гол санаа нь: {context}"

    opening = {
        "friendly": f"{topic} гэдэг үг сүүлийн үед олон сонсогдох болсон ч ойлгоход заавал хэцүү байх албагүй.",
        "formal": f"{topic} нь өнөөдрийн нийгэм, бизнес, боловсролын орчинд анхаарал татаж буй чухал сэдэв юм.",
        "marketing": f"{topic}-ийг зөв ойлгож ашиглавал цаг хэмнэж, ажлын бүтээмжийг мэдэгдэхүйц нэмэгдүүлэх боломжтой.",
        "short": f"{topic}-ийг энгийнээр ойлгоё.",
        "balanced": f"{topic} нь бидний өдөр тутмын амьдрал, ажилд улам ойртож байна.",
    }.get(tone, f"{topic} нь бидний өдөр тутмын амьдрал, ажилд улам ойртож байна.")

    if post_type == "instagram":
        return (
            f"{opening}\n\n"
            f"{simple_explain} {daily_use}\n\n"
            f"{hashtags}"
        )

    if post_type == "facebook":
        return (
            f"{opening}\n\n"
            f"{simple_explain}\n\n"
            f"{daily_use} Хамгийн гол нь энэ технологийг айдас биш, зөв ойлголттойгоор ашиглах хэрэгтэй.\n\n"
            f"Та үүнийг өдөр тутамдаа юунд ашиглаж үзмээр байна?\n\n"
            f"{hashtags}"
        )

    if post_type == "linkedin":
        return (
            f"🎯 {opening}\n\n"
            f"📌 {simple_explain}\n\n"
            f"{daily_use}\n\n"
            f"✅ Таны бодол юу вэ? Сэтгэгдэлд бичээрэй.\n\n"
            f"{hashtags} #LinkedIn #Мэргэжил"
        )

    if post_type == "tiktok":
        return (
            f"🎬 HOOK: {topic} — та мэдэх үү?\n\n"
            f"🗣️ {simple_explain} {daily_use}\n\n"
            f"📣 Дагаж мэдээ авна уу!\n\n"
            f"{hashtags} #TikTok #FYP"
        )

    return (
        f"ГАРЧИГ: {topic} энгийн хэрэглээнд ойртож байна\n\n"
        f"АГУУЛГА:\n{opening} {simple_explain}\n\n"
        f"{daily_use}\n\n"
        f"Энэ сэдвийг зөв ойлгох нь шинэ боломжийг бодитоор ашиглах эхний алхам юм. "
        f"Иймээс хэрэглэгчид тухайн технологийн давуу тал, хязгаарлалт, эрсдэлийг хамтад нь ойлгох шаардлагатай.\n\n"
        f"ДҮГНЭЛТ:\n{topic} нь зөв ашиглавал хүний ажлыг орлох бус, харин дэмжих хэрэгсэл болж чадна."
    )


def generate_post(
    post_type: str,
    topic: str,
    details: str = "",
    lang: str = DEFAULT_LANG,
    tone: str = "balanced",
) -> dict:
    """Пост үүсгэх үндсэн функц"""
    if post_type not in PROMPTS:
        allowed = " | ".join(POST_TYPES)
        return {"error": f"Тодорхойгүй төрөл: {post_type}. {allowed}"}

    if lang not in ("mn", "en"):
        lang = DEFAULT_LANG

    if tone not in TONES:
        tone = "balanced"

    prompt = build_prompt(post_type, topic, details, lang, tone)

    print(f"\n⏳ Үүсгэж байна ({post_type} / {lang} / {tone})...")
    content = call_ollama(prompt)
    polished = False
    fallback = None
    if lang == "mn" and ENABLE_MONGOLIAN_POLISH:
        print("📝 Монгол найруулгыг засаж байна...")
        content = polish_mongolian_content(content, post_type, tone)
        polished = True
        if has_content_issues(content):
            print("📝 Нэмэлт засвар хийж байна...")
            content = polish_mongolian_content(content, post_type, tone)
        if MONGOLIAN_FALLBACK_ON_LOW_QUALITY and has_content_issues(content):
            print("🛟 Уншигдахуйц Монгол fallback ашиглаж байна...")
            content = build_safe_mongolian_content(post_type, topic, details, tone)
            fallback = "template"

    result = {
        "type": post_type,
        "lang": lang,
        "tone": tone,
        "polished": polished,
        "fallback": fallback,
        "topic": topic,
        "content": content,
        "generated_at": datetime.datetime.now().isoformat(),
    }
    return result


def save_post(result: dict) -> str:
    """Үр дүнг файлд хадгалах"""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{result['type']}_{result['lang']}_{ts}.txt"
    filepath = os.path.join(str(NEWS_OUTPUT), filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"=== {result['type'].upper()} POST ===\n")
        f.write(f"Language : {result['lang']}\n")
        f.write(f"Tone     : {result.get('tone', 'balanced')}\n")
        f.write(f"Polished : {result.get('polished', False)}\n")
        f.write(f"Fallback : {result.get('fallback') or 'none'}\n")
        f.write(f"Topic    : {result['topic']}\n")
        f.write(f"Generated: {result['generated_at']}\n")
        f.write("=" * 40 + "\n\n")
        f.write(result["content"])

    return filepath


def print_result(result: dict):
    """Үр дүнг дэлгэцэнд харуулах"""
    border = "─" * 50
    print(f"\n{border}")
    icon = POST_TYPE_ICONS.get(result["type"], "📝")
    lang_label = "🇲🇳 Монгол" if result["lang"] == "mn" else "🇬🇧 English"
    print(f"{icon}  {result['type'].upper()}  |  {lang_label}  |  {result.get('tone', 'balanced')}")
    print(f"Сэдэв: {result['topic']}")
    print(border)
    print(result["content"])
    print(border)


# ─── Interactive CLI ──────────────────────────────────────────────────────────

MENU = {
    "mn": {
        "welcome":    "🤖 Мэдээ / Пост үүсгэгч бот",
        "type_q":     "Төрөл (instagram/facebook/news/linkedin/tiktok): ",
        "topic_q":    "Сэдэв: ",
        "details_q":  "Нэмэлт мэдээлэл (хоосон үлдээж болно): ",
        "lang_q":     "Хэл (mn=Монгол / en=Англи) [mn]: ",
        "tone_q":     "Загвар (balanced/friendly/formal/marketing/short) [balanced]: ",
        "save_q":     "Файлд хадгалах уу? (y/n) [y]: ",
        "saved":      "💾 Хадгалагдлаа: ",
        "again_q":    "Дахин үүсгэх үү? (y/n): ",
        "bye":        "👋 Баярлалаа!",
    },
    "en": {
        "welcome":    "🤖 News / Post Generator Bot",
        "type_q":     "Select type (instagram/facebook/news/linkedin/tiktok): ",
        "topic_q":    "Topic: ",
        "details_q":  "Extra details (leave blank if none): ",
        "lang_q":     "Language (mn=Mongolian / en=English) [mn]: ",
        "tone_q":     "Tone (balanced/friendly/formal/marketing/short) [balanced]: ",
        "save_q":     "Save to file? (y/n) [y]: ",
        "saved":      "💾 Saved: ",
        "again_q":    "Generate another? (y/n): ",
        "bye":        "👋 Goodbye!",
    },
}


def interactive():
    """Харилцааны горим"""
    # UI хэл — тусдаа (ботын гаралтын хэлнээс ялгаатай)
    ui_lang = input("UI language / Интерфейсийн хэл (mn/en) [mn]: ").strip().lower()
    if ui_lang not in ("mn", "en"):
        ui_lang = "mn"
    m = MENU[ui_lang]

    print(f"\n{'═'*50}")
    print(f"  {m['welcome']}")
    print(f"{'═'*50}\n")

    while True:
        post_type = input(m["type_q"]).strip().lower()
        if post_type not in POST_TYPES:
            print(f"  {' | '.join(POST_TYPES)} — нэгийг сонгоно уу")
            continue

        topic   = input(m["topic_q"]).strip()
        details = input(m["details_q"]).strip()

        lang_raw = input(m["lang_q"]).strip().lower()
        lang = lang_raw if lang_raw in ("mn", "en") else "mn"

        tone_raw = input(m["tone_q"]).strip().lower()
        tone = tone_raw if tone_raw in TONES else "balanced"

        result = generate_post(post_type, topic, details, lang, tone)

        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print_result(result)
            save_choice = input(m["save_q"]).strip().lower()
            if save_choice != "n":
                path = save_post(result)
                print(f"{m['saved']}{path}")

        again = input(m["again_q"]).strip().lower()
        if again != "y":
            print(m["bye"])
            break


# ─── CLI shortcut ─────────────────────────────────────────────────────────────

def quick(
    post_type: str,
    topic: str,
    lang: str = "mn",
    details: str = "",
    tone: str = "balanced",
):
    """
    Скриптээс шууд дуудах:
    python main.py news --type instagram --topic "AI технологи" --lang mn
    """
    result = generate_post(post_type, topic, details, lang, tone)
    print_result(result)
    path = save_post(result)
    print(f"\n💾 {path}")
    return result


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        # python main.py news --type instagram --topic "Сэдэв" --lang mn --details "Нэмэлт" --tone friendly
        _type    = sys.argv[1]
        _topic   = sys.argv[2]
        _lang    = sys.argv[3] if len(sys.argv) > 3 else "mn"
        _details = sys.argv[4] if len(sys.argv) > 4 else ""
        _tone    = sys.argv[5] if len(sys.argv) > 5 else "balanced"
        quick(_type, _topic, _lang, _details, _tone)
    else:
        interactive()
