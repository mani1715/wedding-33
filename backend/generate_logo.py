"""
One-shot logo generator for MAJA Creations using Gemini Nano Banana.
Run once: python generate_logo.py
"""
import os
import sys
import asyncio
import base64
from pathlib import Path
from dotenv import load_dotenv
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv()

OUT_DIR = Path("/app/frontend/public/brand")
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOGO_PROMPT = """A luxury monogram logo for "MAJA Creations" — a premium Indian wedding 
photography & invitation platform. Design a sophisticated MJ monogram where 
the capital M and capital J interlock seamlessly: the M forms the outer 
architectural frame with two tall pointed Mughal-style arches reminiscent 
of Taj Mahal jharokhas, and the J cascades through the centre with a 
calligraphic flourish curling at the bottom like a lotus stem. 
Single-line stroke construction, hairline-thin elegant serifs, drawn in 
brushed antique gold (#D4AF37) with a subtle champagne highlight 
(#E8C766) on the inner curves and a deeper antique-gold shadow (#8C6A1A) 
on the descender. Background: deep royal ink (#0E0A06) with imperceptible 
warm grain texture. 

Below the monogram, the wordmark "MAJA" set in refined Cinzel-style 
inscriptional serif capitals with wide letter-spacing, in cream silk 
(#FFF8DC). Beneath that, the word "creations" in a delicate hand-script 
italic (Tangerine-style) in champagne gold, half the width of MAJA. 
Between the monogram and wordmark, a small diamond glyph as a 
ceremonial punctuation. 

Style references: Tiffany & Co. monogram restraint, Sabyasachi Mukherjee 
label crest, vintage Mughal coin inscriptions, Apple product reveal 
typography. Vector-clean, geometrically precise, perfectly symmetrical, 
cinema-grade. 

No mandalas, no peacocks, no flower clusters, no rangoli, no brides, no 
rings, no doves. No drop shadows, no 3D bevels, no neon. Negative space 
must be intentional. 

Output: flat 2D logo, square 2048x2048, ultra high detail, magazine-cover 
quality, vector-ready, suitable for embossing on white card stock and 
gold foiling on dark card stock."""

ICON_PROMPT = """Standalone MJ monogram only (no wordmark), perfectly centred inside a 
1024x1024 square. The capital M and capital J interlock: the M has two 
tall pointed Mughal-style arches reminiscent of Taj Mahal jharokhas, and 
the J cascades through the centre with a calligraphic lotus-stem flourish. 
Brushed imperial gold (#D4AF37) with champagne highlight (#E8C766) and 
antique-gold shadow (#8C6A1A) on the descender. Deep royal ink (#0E0A06) 
background. Geometric, balanced, recognisable at 16x16 pixels. iOS app 
icon ready. No drop shadows, no 3D, no extra ornament. Tiffany monogram 
restraint, Sabyasachi label crest reference."""

LIGHT_PROMPT = """A luxury monogram logo for "MAJA Creations" on a LIGHT pearl-white 
(#FAF3E7) background. MJ monogram where the M has two tall pointed 
Mughal arches and the J cascades through with a calligraphic lotus 
flourish. Drawn in deep antique gold (#8C6A1A) with a brushed-metal 
texture and subtle champagne highlight (#D4AF37) on the inner curves. 
Below: wordmark "MAJA" in Cinzel-style inscriptional serif capitals in 
royal ink (#16110C), wide letter-spacing. Beneath: "creations" in 
delicate hand-script italic in antique gold, half the width of MAJA. 
A small diamond glyph between monogram and wordmark. Tiffany & Co. 
restraint, vintage Mughal coin inscription. Vector-clean, perfectly 
symmetrical. No drop shadows, no 3D, no extra ornament. Square 
2048x2048, magazine-cover quality."""

async def gen(prompt: str, filename: str, session_id: str):
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        print("ERROR: EMERGENT_LLM_KEY missing")
        sys.exit(1)
    chat = LlmChat(api_key=api_key, session_id=session_id,
                    system_message="You are a master luxury brand identity designer.") \
        .with_model("gemini", "gemini-3.1-flash-image-preview") \
        .with_params(modalities=["image", "text"])
    msg = UserMessage(text=prompt)
    text, images = await chat.send_message_multimodal_response(msg)
    print(f"[{filename}] text-response head: {(text or '')[:80]}")
    if not images:
        print(f"[{filename}] NO IMAGES RETURNED")
        return False
    image_bytes = base64.b64decode(images[0]['data'])
    out_path = OUT_DIR / filename
    out_path.write_bytes(image_bytes)
    print(f"[{filename}] saved {len(image_bytes)} bytes -> {out_path}")
    return True

async def main():
    print("Generating MAJA logo set ...")
    await gen(LOGO_PROMPT,  "maja-logo-dark.png",  "maja-logo-dark")
    await gen(ICON_PROMPT,  "maja-icon.png",       "maja-icon")
    await gen(LIGHT_PROMPT, "maja-logo-light.png", "maja-logo-light")
    print("DONE")

if __name__ == "__main__":
    asyncio.run(main())
