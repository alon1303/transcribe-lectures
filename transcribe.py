"""
תמלול הרצאה (MP3 או MP4) בעברית דרך ה-API של OpenAI.

שימוש:
    pip install openai python-dotenv
    בקובץ .env (באותה תיקייה של הסקריפט) צריכה להיות שורה:
        OPENAI_API_KEY=sk-...
    python transcribe.py lecture.mp3

הסקריפט חותך את הקובץ לחלקים של 10 דקות (ה-API מוגבל בגודל ובאורך לכל בקשה),
מתמלל כל חלק, ומחבר הכול לקובץ טקסט אחד ליד הקובץ המקורי.
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# טוען את המפתח מקובץ .env שנמצא באותה תיקייה של הסקריפט (לא משנה מאיפה מריצים אותו)
load_dotenv(Path(__file__).resolve().parent / ".env")

# ---- הגדרות ----
MODEL = "gpt-4o-transcribe"   # אפשר להחליף ל-"gpt-4o-mini-transcribe" (זול יותר) או ל-"whisper-1"
CHUNK_MINUTES = 10            # בטוח מתחת למגבלות הגודל והאורך
LANGUAGE = "he"
# רמז למודל על התחום. ברירת המחדל ריקה כי המודל נוטה להדהד את הרמז בתחילת התמלול,
# ורמז שלא מתאים להרצאה (למשל "אינטגרל" בהרצאה על שדות) רק מזיק.
# אם רוצים, אפשר לכתוב כאן מילות מפתח אמיתיות מההרצאה, למשל: "אלגברה לינארית: שדה, וקטור, מטריצה".
PROMPT = ""


def split_audio(src: str, out_dir: str) -> list[Path]:
    """חותך ומקטין את האודיו: מונו, 16kHz, 48kbps. הרצאה של שעתיים וחצי יוצאת ~50MB בסך הכול."""
    pattern = os.path.join(out_dir, "chunk_%03d.mp3")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", src,
            "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k",
            "-f", "segment", "-segment_time", str(CHUNK_MINUTES * 60),
            "-reset_timestamps", "1",
            pattern,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return sorted(Path(out_dir).glob("chunk_*.mp3"))


def clean_text(text: str) -> str:
    """מנקה 'הזיות' של המודל: הד של ה-PROMPT בתחילת הטקסט, וחזרות אינסופיות של אותו משפט."""
    text = text.strip()
    if PROMPT and text.startswith(PROMPT.strip()):
        text = text[len(PROMPT.strip()):].strip()
    # ביטוי (8 עד 400 תווים) שחוזר 3 פעמים או יותר ברצף נשאר פעם אחת
    text = re.sub(r"(.{8,400}?)(?:\s+\1){2,}", r"\1", text, flags=re.DOTALL)
    return text


def main():
    if len(sys.argv) < 2:
        sys.exit("שימוש: python transcribe.py <קובץ mp3 או mp4>")

    src = Path(sys.argv[1])
    if not src.exists():
        sys.exit(f"הקובץ לא נמצא: {src}")

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("לא נמצא OPENAI_API_KEY. ודא שיש שורה OPENAI_API_KEY=... בקובץ .env ליד הסקריפט.")

    client = OpenAI()  # לוקח את המפתח מ-OPENAI_API_KEY

    out_path = src.with_suffix(".txt")
    parts = []
    raw_parts = []
    raw_path = src.with_suffix(".raw.txt")  # העתק לא מנוקה, למקרה שהניקוי מחק משהו אמיתי

    with tempfile.TemporaryDirectory() as tmp:
        chunks = split_audio(str(src), tmp)
        print(f"נחתך ל-{len(chunks)} חלקים, מתחיל תמלול...")

        for i, chunk in enumerate(chunks, 1):
            kwargs = {"model": MODEL, "language": LANGUAGE}
            if PROMPT:
                kwargs["prompt"] = PROMPT
            with open(chunk, "rb") as f:
                result = client.audio.transcriptions.create(file=f, **kwargs)

            raw = result.text.strip()
            cleaned = clean_text(raw)
            raw_parts.append(raw)
            parts.append(cleaned)

            removed = len(raw) - len(cleaned)
            note = f" (נוקו ~{removed} תווים של חזרות, כנראה הפסקה או רעש)" if removed > 200 else ""
            print(f"  חלק {i}/{len(chunks)} הושלם{note}")

            # שמירה הדרגתית, כדי שלא יאבד הכול אם משהו נופל באמצע
            out_path.write_text("\n\n".join(parts), encoding="utf-8")
            raw_path.write_text("\n\n".join(raw_parts), encoding="utf-8")

    print(f"הסתיים. התמלול נשמר ב: {out_path}")


if __name__ == "__main__":
    main()