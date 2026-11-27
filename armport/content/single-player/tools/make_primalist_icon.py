"""Draw the Primalist archetype badge (an original design: a paw with claws on a green disc) and
write it as a City of Heroes .texture (32x32, uncompressed, with mip levels).
usage: make_primalist_icon.py <out.texture> <preview.png>"""
import io, math, struct, sys
from PIL import Image, ImageDraw, ImageFilter

S = 512                                    # drawing size; the texture is 32 px

def badge():
    image = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    # Disc with a soft top-left light, like a lit enamel badge.
    disc = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    pixels = disc.load()
    cx = cy = S / 2; radius = S * 0.47
    for y in range(S):
        for x in range(S):
            d = math.hypot(x - cx, y - cy)
            if d > radius + 1: continue
            light = max(0.0, 1.0 - math.hypot(x - S * 0.36, y - S * 0.30) / (S * 0.70))
            edge = d / radius
            r = 20 + 70 * light; g = 78 + 120 * light; b = 38 + 60 * light
            shade = 1.0 - 0.45 * edge ** 3
            alpha = 255 if d <= radius else int(255 * max(0.0, radius + 1 - d))
            pixels[x, y] = (int(r * shade), int(g * shade), int(b * shade), alpha)
    image.alpha_composite(disc)
    draw = ImageDraw.Draw(image)
    # Rim: dark outer ring, thin light inner ring.
    draw.ellipse((S * 0.03, S * 0.03, S * 0.97, S * 0.97), outline=(12, 40, 20, 255), width=int(S * 0.045))
    draw.ellipse((S * 0.075, S * 0.075, S * 0.925, S * 0.925), outline=(150, 215, 140, 235), width=int(S * 0.018))
    # The paw: main pad, four toes, a claw on each toe.
    paw = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    p = ImageDraw.Draw(paw)
    cream = (248, 246, 228, 255)
    p.ellipse((S * 0.31, S * 0.50, S * 0.69, S * 0.80), fill=cream)                      # pad, lower lobe
    p.ellipse((S * 0.28, S * 0.56, S * 0.50, S * 0.80), fill=cream)
    p.ellipse((S * 0.50, S * 0.56, S * 0.72, S * 0.80), fill=cream)
    p.ellipse((S * 0.37, S * 0.47, S * 0.63, S * 0.68), fill=cream)
    toes = ((0.215, 0.405, -28), (0.385, 0.285, -9), (0.615, 0.285, 9), (0.785, 0.405, 28))
    for tx, ty, angle in toes:
        toe = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        t = ImageDraw.Draw(toe)
        w, h = S * 0.075, S * 0.105
        t.ellipse((S / 2 - w, S / 2 - h, S / 2 + w, S / 2 + h), fill=cream)
        # claw: a narrow spike above the toe
        t.polygon(((S / 2 - w * 0.42, S / 2 - h * 0.86), (S / 2 + w * 0.42, S / 2 - h * 0.86), (S / 2, S / 2 - h * 1.95)),
                  fill=cream)
        toe = toe.rotate(-angle, resample=Image.BICUBIC, center=(S / 2, S / 2))
        paw.alpha_composite(toe, (int(tx * S - S / 2), int(ty * S - S / 2)) if tx * S >= S / 2 and ty * S >= S / 2 else (0, 0)) \
            if False else None
        layer = Image.new('RGBA', (S, S), (0, 0, 0, 0))
        layer.paste(toe, (int(tx * S - S / 2), int(ty * S - S / 2)), toe)
        paw.alpha_composite(layer)
    # A dark edge under the paw so it reads on the light part of the disc.
    shadow = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    shadow.paste((8, 34, 16, 150), (0, 0, S, S), paw.split()[3].filter(ImageFilter.MaxFilter(13)))
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(3)))
    image.alpha_composite(paw)
    return image

def texture(master, name):
    """32x32 uncompressed BGRA with its mip levels (tex.c reads DDS_RGBA, 32 bits, alpha mask ff000000)."""
    levels, size = [], 32
    while size >= 1:
        level = master.resize((size, size), Image.LANCZOS)
        r, g, b, a = level.split()
        levels.append(Image.merge('RGBA', (b, g, r, a)).tobytes()); size //= 2
    assert [len(l) for l in levels] == [4096, 1024, 256, 64, 16, 4]
    header = struct.pack('<4s7I44x', b'DDS ', 124, 0x0002100F, 32, 32, 128, 0, len(levels))
    pixel_format = struct.pack('<2I4s5I', 32, 0x41, b'\0\0\0\0', 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    caps = struct.pack('<4I4x', 0x00401008, 0, 0, 0)
    assert len(header + pixel_format + caps) == 128
    dds = header + pixel_format + caps + b''.join(levels)
    stored = name.encode('ascii') + b'\0'
    head = struct.pack('<5i2fB3s', 32 + len(stored), len(dds), 32, 32, 0, 0.0, 0.0, 1, b'TX2')
    assert len(head) == 32
    return head + stored + dds, dds

if __name__ == '__main__':
    master = badge()
    data, dds = texture(master, 'texture_library/GUI/Icons/Archetype/archetypeicon_primalist.dds')
    open(sys.argv[1], 'wb').write(data)
    b, g, r, a = Image.frombytes('RGBA', (32, 32), dds[128:128 + 4096]).split()
    small = Image.merge('RGBA', (r, g, b, a))
    assert Image.open(io.BytesIO(dds)).size == (32, 32)
    sheet = Image.new('RGBA', (32 * 8 * 3 + 40, 32 * 8 + 20), (30, 44, 66, 255))
    sheet.alpha_composite(small.resize((256, 256), Image.NEAREST), (10, 10))
    light = Image.new('RGBA', (256, 256), (200, 205, 215, 255)); light.alpha_composite(small.resize((256, 256), Image.LANCZOS))
    sheet.paste(light, (276, 10))
    sheet.alpha_composite(master.resize((256, 256), Image.LANCZOS), (542, 10))
    for i, scale in enumerate((1, 2)):
        sheet.alpha_composite(small.resize((32 * scale, 32 * scale), Image.LANCZOS), (10 + i * 40, 10))
    sheet.save(sys.argv[2]); print(len(data), 'bytes;', small.size)
