from __future__ import annotations

# image_utils_fixed.py
from typing import Tuple, List, Optional, Dict
import warnings
from PIL import Image, ImageSequence
warnings.filterwarnings("ignore",
    message="Palette images with Transparency expressed in bytes should be converted to RGBA images",
    category=UserWarning, module="PIL.Image")

def ensure_rgba(img: Image.Image) -> Image.Image:
    if img.mode == "RGBA": return img
    if img.mode == "LA": return img.convert("RGBA")
    if img.mode == "P":
        if "transparency" in img.info: return img.convert("RGBA")
        return img.convert("RGB")
    if img.mode == "RGB": return img
    return img.convert("RGBA")

def ensure_rgb(img: Image.Image, background: Tuple[int,int,int]=(255,255,255)) -> Image.Image:
    if img.mode == "RGB": return img
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, background); bg.paste(img, mask=img.split()[-1]); return bg
    return img.convert("RGB")
