from __future__ import annotations

# image_utils.py

from typing import Tuple, List, Optional, Dict
import warnings
from PIL import Image, ImageSequence

# Bungkam warning spesifik dari PIL agar log bersih (kita tetap konversi mode di bawah)
warnings.filterwarnings(
    "ignore",
    message="Palette images with Transparency expressed in bytes should be converted to RGBA images",
    category=UserWarning,
    module="PIL.Image",
)

# =========================
# KONVERSI MODE YANG AMAN
# =========================

def ensure_rgba(img: Image.Image) -> Image.Image:
    """
    Konversi aman ke RGBA jika gambar punya transparansi (mode P dengan transparency/ LA / dll).
    Jika palette (P) TANPA transparency, dikonversi ke RGB agar ukuran kecil.
    """
    if img.mode == "RGBA":
        return img
    if img.mode == "LA":          # L (grayscale) + alpha
        return img.convert("RGBA")
    if img.mode == "P":           # palette-based (PNG/GIF)
        if "transparency" in img.info:
            return img.convert("RGBA")
        return img.convert("RGB")  # tidak ada alpha → hemat
    if img.mode == "RGB":
        return img
    # Mode lain: paksa ke RGBA supaya aman saat compositing
    return img.convert("RGBA")


def ensure_rgb(img: Image.Image, background: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """
    Pastikan gambar RGB. Jika sumber RGBA, jatuhkan alpha ke background.
    """
    if img.mode == "RGB":
        return img
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, background)
        bg.paste(img, mask=img.split()[-1])  # gunakan alpha sebagai mask
        return bg
    return img.convert("RGB")


def ensure_rgba_gif_frames(img: Image.Image) -> List[Image.Image]:
    """
    Untuk GIF animasi: konversi tiap frame ke RGBA/ RGB yang aman.
    """
    frames: List[Image.Image] = []
    for f in ImageSequence.Iterator(img):
        frames.append(ensure_rgba(f.copy()))
    return frames

# =========================
# RESIZE / KOMPRESI
# =========================

def compress_image(image: Image.Image, max_size: Tuple[int, int] = (500, 500)) -> Image.Image:
    """
    Resize in-place style (copy dulu supaya sumber aman). Preserve aspect ratio.
    """
    img = image.copy()
    img.thumbnail(max_size)
    return img


def convert_to_rgb(image: Image.Image) -> Image.Image:
    """
    Kompatibel dengan util lama kamu: paksa ke RGB jika perlu.
    """
    if image.mode != "RGB":
        return image.convert("RGB")
    return image

# =========================
# PIPELINE SIAP PAKAI
# =========================

def prepare_for_save(
    image: Image.Image,
    max_size: Tuple[int, int] = (500, 500),
    prefer_png: bool = True,
    jpeg_bg: Tuple[int, int, int] = (255, 255, 255),
) -> tuple[Image.Image, str]:
    """
    Resize → tentukan format (PNG bila ada transparansi) → pastikan mode benar.
    Return: (image_processed, format_str)
    """
    img = compress_image(image, max_size)
    has_alpha = (
        img.mode == "RGBA"
        or (img.mode in ("LA", "P") and "transparency" in img.info)
    )
    if prefer_png and has_alpha:
        return ensure_rgba(img), "PNG"
    # selain itu, pakai JPEG/ RGB
    return ensure_rgb(img, background=jpeg_bg), "JPEG"


def save_image(
    image: Image.Image,
    path: str,
    max_size: Tuple[int, int] = (500, 500),
    prefer_png: bool = True,
    png_opt: Optional[Dict] = None,
    jpeg_opt: Optional[Dict] = None,
) -> None:
    """
    Simpan gambar dengan opsi default yang bagus:
    - PNG untuk gambar bertansparansi (optimize=True)
    - JPEG kualitas 85 untuk non-transparan
    """
    img, fmt = prepare_for_save(image, max_size, prefer_png=prefer_png)
    if fmt == "PNG":
        opts = {"optimize": True}
        if png_opt:
            opts.update(png_opt)
        img.save(path, format="PNG", **opts)
    else:
        opts = {"optimize": True, "quality": 85}
        if jpeg_opt:
            opts.update(jpeg_opt)
        img.save(path, format="JPEG", **opts)
