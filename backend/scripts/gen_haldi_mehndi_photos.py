"""One-off script — generate single-person Haldi & Mehndi placeholder photos
via Gemini Nano Banana, save them under /app/uploads/themes/ so they're
served via the existing /uploads StaticFiles mount.

Usage:
    cd /app/backend && python scripts/gen_haldi_mehndi_photos.py
"""
from __future__ import annotations

import asyncio
import base64
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: E402

OUT_DIR = Path("/app/uploads/themes")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPTS = {
    "haldi-single.png": (
        "Hyper-realistic photograph of a single beautiful Indian bride during "
        "her Haldi ceremony. She is alone, smiling joyfully, with bright yellow "
        "turmeric paste applied on her cheeks, arms and forehead. Wearing a "
        "vibrant marigold-yellow traditional cotton kurta with fresh marigold "
        "flower jewellery. Soft natural golden-hour sunlight, soft bokeh of "
        "yellow marigolds in the background. Vertical 4:5 portrait, "
        "professional wedding photography, no other people in frame, single "
        "person only, joyful candid expression."
    ),
    "mehndi-single.png": (
        "Hyper-realistic photograph of a single beautiful Indian bride during "
        "her Mehndi ceremony. She is alone, sitting gracefully and showing off "
        "her freshly-applied intricate dark green henna designs on both hands "
        "and forearms. Wearing a deep emerald-green lehenga embroidered with "
        "gold zardosi, traditional gold jhumka earrings and a maang tikka. "
        "Warm candlelit ambient lighting, soft bokeh of marigold and rose "
        "petals in the background. Vertical 4:5 portrait, professional wedding "
        "photography, no other people in frame, single person only, elegant "
        "serene expression."
    ),
}


async def main() -> None:
    api_key = os.getenv("EMERGENT_LLM_KEY")
    if not api_key:
        raise SystemExit("EMERGENT_LLM_KEY missing in backend/.env")

    for filename, prompt in PROMPTS.items():
        out_path = OUT_DIR / filename
        if out_path.exists() and out_path.stat().st_size > 1024:
            print(f"[skip] {out_path} already exists ({out_path.stat().st_size} bytes)")
            continue

        print(f"[gen ] {filename} ...")
        chat = LlmChat(
            api_key=api_key,
            session_id=f"haldi-mehndi-{uuid.uuid4()}",
            system_message="You are an expert Indian wedding photographer who generates realistic photographs.",
        )
        chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(
            modalities=["image", "text"],
        )
        msg = UserMessage(text=prompt)
        text, images = await chat.send_message_multimodal_response(msg)

        if not images:
            print(f"[fail] {filename}: no image returned. Text: {text[:120] if text else ''}")
            continue

        img = images[0]
        image_bytes = base64.b64decode(img["data"])
        out_path.write_bytes(image_bytes)
        print(f"[ok  ] saved {out_path} ({len(image_bytes)} bytes, {img.get('mime_type')})")


if __name__ == "__main__":
    asyncio.run(main())
