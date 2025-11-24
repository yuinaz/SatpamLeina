
import io
from typing import List, Iterable, Optional, Set
try:
    from PIL import Image, ImageSequence, ImageFile, ImageOps, ImageFilter
    ImageFile.LOAD_TRUNCATED_IMAGES = True
except Exception:
    Image = None
    ImageSequence = None
    ImageOps = None
    ImageFilter = None
try:
    import imagehash
except Exception:
    imagehash = None
try:
    import imageio.v2 as imageio
except Exception:
    imageio = None

def _hamming_hex(a: str, b: str) -> int:
    try:
        return (int(a, 16) ^ int(b, 16)).bit_count()
    except Exception:
        return 9999

def _augment_variants(img: "Image.Image", max_extra: int = 4):
    "Yield simple augmented frames: hflip, rot±7deg, center-crop 95%."
    if not Image or not img:
        return
    count = 0
    try:
        if ImageOps and count < max_extra:
            yield ImageOps.mirror(img); count += 1
    except Exception:
        pass
    try:
        if count < max_extra:
            yield img.rotate(7, expand=True, fillcolor=(0,0,0)); count += 1
        if count < max_extra:
            yield img.rotate(-7, expand=True, fillcolor=(0,0,0)); count += 1
    except Exception:
        pass
    try:
        if count < max_extra:
            w, h = img.size
            dw, dh = int(w*0.025), int(h*0.025)  # crop 95% center
            if w-2*dw > 8 and h-2*dh > 8:
                yield img.crop((dw, dh, w-dw, h-dh)); count += 1
    except Exception:
        pass

def phash_list_from_bytes(data: bytes, max_frames: int = 6, augment: bool = False, augment_per_frame: int = 4) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    if not data:
        return out
    def _add(img):
        try:
            if not imagehash or not Image:
                return
            g = img.convert("RGB")
            hs = str(imagehash.phash(g))
            if hs not in seen:
                seen.add(hs); out.append(hs)
            if augment:
                k = 0
                for v in _augment_variants(g, max_extra=augment_per_frame):
                    try:
                        hv = str(imagehash.phash(v))
                        if hv not in seen:
                            seen.add(hv); out.append(hv)
                        k += 1
                        if k >= augment_per_frame:
                            break
                    except Exception:
                        continue
        except Exception:
            pass
    # Pillow first
    if Image:
        try:
            with Image.open(io.BytesIO(data)) as im:
                nframes = getattr(im, "n_frames", 1)
                if nframes > 1 and ImageSequence is not None:
                    step = max(1, nframes // max(1, min(nframes, max_frames)))
                    idxs = list(range(0, nframes, step))[:max_frames]
                    for i in idxs:
                        try:
                            im.seek(i)
                            _add(im.copy())
                        except Exception:
                            continue
                else:
                    _add(im)
                if out:
                    return out
        except Exception:
            pass
    # Fallback: imageio
    if imageio:
        try:
            rdr = imageio.get_reader(io.BytesIO(data), format='WEBP')
            c = 0
            for frm in rdr:
                try:
                    if Image:
                        _add(Image.fromarray(frm))
                    c += 1
                    if c >= max_frames:
                        break
                except Exception:
                    continue
            if out:
                return out
        except Exception:
            try:
                img = imageio.imread(io.BytesIO(data))
                if Image:
                    _add(Image.fromarray(img))
            except Exception:
                pass
    return out

def phash_hit(hashes: Iterable[str], db: Iterable[str], max_distance: int = 0) -> Optional[str]:
    S = list(db) if not isinstance(db, (set, list, tuple)) else db
    for h in hashes:
        if not h:
            continue
        if h in S:
            return h
    if max_distance > 0:
        for h in hashes:
            for d in S:
                if _hamming_hex(h, d) <= max_distance:
                    return d
    return None


# ---------- Tile pHash (grid-based) ----------
def tile_phash_from_image(img: Image.Image, grid: int = 3) -> List[str]:
    """Return list of hex pHashes for grid*grid tiles of the image."""
    if not img or not Image:
        return []
    try:
        W, H = img.size
        tiles = []
        for gy in range(grid):
            for gx in range(grid):
                x0 = int(gx * W / grid); x1 = int((gx+1) * W / grid)
                y0 = int(gy * H / grid); y1 = int((gy+1) * H / grid)
                tile = img.crop((x0, y0, x1, y1))
                tiles.append(phash_hex(tile))
        return tiles
    except Exception:
        return []

def tile_phash_list_from_bytes(data: bytes, grid: int = 3, max_frames: int = 4, augment: bool = True, augment_per_frame: int = 3) -> List[str]:
    """
    Returns list of tile-signatures. Each signature is 'h1|h2|...|hN' for grid*grid tiles.
    """
    out: List[str] = []
    if not data or not Image:
        return out
    try:
        im = Image.open(io.BytesIO(data))
        frames = ImageSequence.Iterator(im) if getattr(im, "is_animated", False) else [im]
        c = 0
        for frame in frames:
            try:
                base = frame.copy().convert("RGB")
                sig = tile_phash_from_image(base, grid=grid)
                if sig:
                    out.append("|".join(sig))
                if augment:
                    k = 0
                    for v in _augment_variants(base, max_extra=augment_per_frame):
                        sig2 = tile_phash_from_image(v, grid=grid)
                        if sig2:
                            out.append("|".join(sig2))
                        k += 1
                        if k >= augment_per_frame:
                            break
                c += 1
                if c >= max_frames:
                    break
            except Exception:
                continue
    except Exception:
        pass
    return out

def tile_match_best(candidate_sigs: List[str], db_sigs: Iterable[str], grid: int, min_tiles: int, per_tile_max_distance: int) -> int:
    """
    Return best tile match count between candidate signatures and DB signatures.
    Two tile strings match on a tile if hamming(p,q) <= per_tile_max_distance.
    """
    if not candidate_sigs or not db_sigs:
        return 0
    def split_sig(sig: str) -> List[str]:
        return [x for x in sig.split("|") if x]
    best = 0
    DB = list(db_sigs) if not isinstance(db_sigs, (list, set, tuple)) else db_sigs
    for cand in candidate_sigs:
        C = split_sig(cand)
        for db in DB:
            D = split_sig(db)
            if len(C) != len(D):
                continue
            hit = 0
            for a, b in zip(C, D):
                try:
                    if _hamming_hex(a, b) <= per_tile_max_distance:
                        hit += 1
                except Exception:
                    pass
            if hit > best:
                best = hit
            if best >= min_tiles:
                return best
    return best


# ---------- ORB descriptors (optional, requires cv2) ----------
try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

def _orb_compute(img):
    if cv2 is None:
        return None
    try:
        g = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
        orb = cv2.ORB_create(nfeatures=600)
        kps, des = orb.detectAndCompute(g, None)
        return des  # shape (N, 32) uint8 or None
    except Exception:
        return None

def orb_descriptors_from_bytes(data: bytes, max_frames: int = 2, augment: bool = True, augment_per_frame: int = 2, keep_per_frame: int = 64) -> List[List[int]]:
    """
    Return a compact list of ORB descriptors (as lists of ints) limited for storage.
    """
    out: List[List[int]] = []
    if not data or cv2 is None or not Image:
        return out
    try:
        im = Image.open(io.BytesIO(data))
        frames = ImageSequence.Iterator(im) if getattr(im, "is_animated", False) else [im]
        c = 0
        for frame in frames:
            try:
                base = frame.copy().convert("RGB")
                des = _orb_compute(base)
                if des is not None and len(des) > 0:
                    out.extend([list(map(int, row)) for row in des[:keep_per_frame]])
                if augment:
                    k = 0
                    for v in _augment_variants(base, max_extra=augment_per_frame):
                        des2 = _orb_compute(v)
                        if des2 is not None and len(des2) > 0:
                            out.extend([list(map(int, row)) for row in des2[:keep_per_frame]])
                        k += 1
                        if k >= augment_per_frame:
                            break
                c += 1
                if c >= max_frames:
                    break
            except Exception:
                continue
    except Exception:
        pass
    return out

def orb_match_count(descA: List[List[int]], descB: List[List[int]], ratio: float = 0.75) -> int:
    if cv2 is None or not descA or not descB:
        return 0
    try:
        A = np.array(descA, dtype=np.uint8)
        B = np.array(descB, dtype=np.uint8)
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(A, B, k=2)
        good = 0
        for m,n in matches:
            if m.distance < ratio * n.distance:
                good += 1
        return int(good)
    except Exception:
        return 0


def dhash_list_from_bytes(data: bytes, max_frames: int = 6, augment: bool = False, augment_per_frame: int = 4) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    if not data or not Image:
        return out
    def _dhash(img):
        try:
            g = img.convert("L").resize((9, 8))
            px = list(g.getdata())
            w, h = g.size
            bits = []
            for y in range(h):
                row = px[y*w:(y+1)*w]
                for x in range(w-1):
                    bits.append(1 if row[x] < row[x+1] else 0)
            v = 0
            for b in bits:
                v = (v << 1) | b
            return f"{v:0{len(bits)//4}x}"
        except Exception:
            return None
    try:
        im = Image.open(io.BytesIO(data))
        frames = ImageSequence.Iterator(im) if getattr(im, "is_animated", False) else [im]
        c = 0
        for frame in frames:
            try:
                base = frame.copy()
                hs = _dhash(base)
                if hs and hs not in seen:
                    seen.add(hs); out.append(hs)
                if augment:
                    k = 0
                    for v in _augment_variants(base, max_extra=augment_per_frame):
                        d = _dhash(v)
                        if d and d not in seen:
                            seen.add(d); out.append(d)
                        k += 1
                        if k >= augment_per_frame:
                            break
                c += 1
                if c >= max_frames:
                    break
            except Exception:
                continue
    except Exception:
        pass
    return out

def hex_hit(hashes: Iterable[str], db: Iterable[str], max_distance: int) -> Optional[str]:
    if max_distance <= 0 or not hashes or not db:
        return None
    DB = list(db) if not isinstance(db, (list, set, tuple)) else db
    for h in hashes:
        for d in DB:
            try:
                if _hamming_hex(h, d) <= max_distance:
                    return d
            except Exception:
                pass
    return None
