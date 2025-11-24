# Multi-hash & region hashing (auto 2025-08-09T12:25:01.106136Z)
from PIL import Image, ImageOps
import io, numpy as np
def _to_gray(img: Image.Image, size=256): im=img.convert("L"); return im.resize((size,size)) if size else im
def ahash(img: Image.Image, hash_size=8)->int:
    g=_to_gray(img, hash_size); p=np.asarray(g, dtype=np.float32); avg=p.mean(); bits=(p>avg).flatten(); h=0
    for b in bits: h=(h<<1)|int(b); return h
def dhash(img: Image.Image, hash_size=8)->int:
    g=_to_gray(img, hash_size+1); a=np.asarray(g, dtype=np.int16); diff=a[:,1:]>a[:,:-1]; h=0
    for b in diff.flatten(): h=(h<<1)|int(b); return h
def phash(img: Image.Image, hash_size=8, highfreq_factor=4)->int:
    g=_to_gray(img, hash_size*highfreq_factor); arr=np.asarray(g, dtype=np.float32)
    try: import scipy.fftpack as fp; d=fp.dct(fp.dct(arr,axis=0,norm='ortho'),axis=1,norm='ortho')
    except Exception: d=np.fft.fft2(arr).real
    low=d[:hash_size,:hash_size]; med=np.median(low[1:,1:]); bits=(low>med).flatten(); h=0
    for b in bits: h=(h<<1)|int(b); return h
def hamming(x:int,y:int)->int: return int(bin(int(x)^int(y)).count("1"))
def region_hashes(img: Image.Image, grid=3, hash_fn=phash, hash_size=8):
    W,H=img.size; xs=[int(W*i/grid) for i in range(grid+1)]; ys=[int(H*i/grid) for i in range(grid+1)]; out=[]
    for i in range(grid):
        for j in range(grid):
            tile=img.crop((xs[i],ys[j],xs[i+1],ys[j+1])); out.append(hash_fn(tile, hash_size=hash_size))
    return out
def compute_all_hashes(image_bytes: bytes):
    img=Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return { "phash": phash(img), "dhash": dhash(img), "ahash": ahash(img), "regions": region_hashes(img) }


def calculate_image_hash(image_bytes: bytes) -> str:
    """Backward-compatible wrapper: return phash hex string."""
    data = compute_all_hashes(image_bytes)
    # represent phash as 16-char hex (for hash_size=8 -> 64 bits)
    return format(int(data.get("phash", 0)), "016x")
