"""
ac's mc 0.1 — my take
Minecraft Indev / Infdev homage — 60 FPS software 3D, no external files.
"""
# import python 3.14. files = off
# pr
import math
import random
import sys
import time
from enum import IntEnum

import pygame

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
TITLE = "ac's mc 0.1 — my take"
W, H = 960, 540
RW, RH = 128, 72           # internal buffer — scaled to 960x540 for 60 FPS
FPS = 60
FOV = 70
CHUNK = 16
WORLD_H = 64
RENDER_DIST = 3
GRAVITY = 28.0
JUMP_V = 9.2
WALK = 4.3
RUN = 6.8
REACH = 5.5
SEED = 4041337
random.seed(SEED)

# ---------------------------------------------------------------------------
# BLOCKS
# ---------------------------------------------------------------------------
class Block(IntEnum):
    AIR = 0
    GRASS = 1
    DIRT = 2
    STONE = 3
    LOG = 4
    LEAVES = 5
    SAND = 6
    WATER = 7
    BEDROCK = 8
    COBBLE = 9
    PLANKS = 10
    GRAVEL = 11
    COAL = 12
    IRON = 13
    GOLD = 14
    MOSS = 15

BLOCK = {
    Block.AIR:     None,
    Block.GRASS:   ((90, 150, 60), (110, 85, 55), (100, 130, 55)),
    Block.DIRT:    ((110, 85, 55),) * 3,
    Block.STONE:   ((120, 120, 125),) * 3,
    Block.LOG:     ((100, 75, 45), (85, 60, 35), (100, 75, 45)),
    Block.LEAVES:  ((50, 110, 45),) * 3,
    Block.SAND:    ((210, 195, 120),) * 3,
    Block.WATER:   ((40, 80, 180),) * 3,
    Block.BEDROCK: ((55, 55, 55),) * 3,
    Block.COBBLE:  ((100, 100, 105),) * 3,
    Block.PLANKS:  ((160, 130, 80),) * 3,
    Block.GRAVEL:  ((130, 125, 120),) * 3,
    Block.COAL:    ((90, 90, 95), (40, 40, 45), (90, 90, 95)),
    Block.IRON:    ((150, 140, 130), (180, 160, 140), (150, 140, 130)),
    Block.GOLD:    ((150, 140, 130), (220, 190, 60), (150, 140, 130)),
    Block.MOSS:    ((70, 120, 60), (110, 85, 55), (70, 120, 60)),
}

BLOCK_NAMES = {
    Block.GRASS: "Grass", Block.DIRT: "Dirt", Block.STONE: "Stone",
    Block.LOG: "Log", Block.LEAVES: "Leaves", Block.SAND: "Sand",
    Block.WATER: "Water", Block.BEDROCK: "Bedrock", Block.COBBLE: "Cobblestone",
    Block.PLANKS: "Planks", Block.GRAVEL: "Gravel", Block.COAL: "Coal Ore",
    Block.IRON: "Iron Ore", Block.GOLD: "Gold Ore", Block.MOSS: "Moss Stone",
}

HOTBAR = [
    Block.GRASS, Block.DIRT, Block.STONE, Block.COBBLE, Block.PLANKS,
    Block.LOG, Block.LEAVES, Block.SAND, Block.GRAVEL,
]

SKY_TOP = (90, 155, 255)
SKY_BOT = (170, 210, 255)
FOG = (150, 195, 245)
CHAT_BG = (0, 0, 0, 120)

INFDEV_BOOT = [
    "Singleplayer mode enabled.",
    "Generating level...",
    "Building terrain...",
    "Simulating world for a bit...",
    "Preparing spawn area...",
    "Spawning player...",
    "Done.",
    "Welcome to Infdev — infinite worlds, finite RAM.",
    "Left click: dig. Right click: place. E: pick block.",
    "Scroll / 1-9: hotbar. F3: debug. T: chat.",
]

INFDEV_CHAT = [
    "Try the infinite world!",
    "The sun rises in the east and sets in the west.",
    "Don't dig straight down.",
    "Get wood!",
    "Saving level...",
    "Chunks saved.",
    "Can't keep up! Did the system time change?",
    "Level seed: {seed}",
    "Building terrain... still building terrain...",
    "Software renderer engaged — OpenGL is for other games.",
    "Block updated.",
    "Infinite horizontally. Still pretty finite vertically.",
    "Achievement get! [Software 3D]",
    "Press F3 to see how hard your CPU is coping.",
    "ac's mc 0.1 — my take on the before-times.",
    "60 FPS or bust.",
    "Procedural everything. files = off.",
]

FACE_SHADE = (0.95, 0.75, 1.0, 0.65, 0.85, 0.85)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def shade(c, m):
    return (int(c[0] * m), int(c[1] * m), int(c[2] * m))


def height_at(wx, wz):
    h = 34.0
    h += 10 * math.sin(wx * 0.041 + SEED * 0.001)
    h += 6 * math.cos(wz * 0.053 - SEED * 0.002)
    h += 4 * math.sin(wx * 0.11 + wz * 0.09)
    h += 2 * math.sin(wx * 0.27) * math.cos(wz * 0.31)
    h += 1.5 * math.sin((wx + wz) * 0.19)
    return int(h)


def cave_noise(wx, wy, wz):
    return (math.sin(wx * 0.31 + wy * 0.17) +
            math.sin(wz * 0.29 - wy * 0.23) +
            math.sin((wx + wz + wy) * 0.13)) / 3.0


def chunk_coord(v):
    return v // CHUNK if v >= 0 else (v + 1) // CHUNK - 1


# ---------------------------------------------------------------------------
# WORLD
# ---------------------------------------------------------------------------
class Chunk:
    __slots__ = ("cx", "cz", "blocks", "y_min", "y_max")

    def __init__(self, cx, cz):
        self.cx, self.cz = cx, cz
        self.blocks = bytearray(CHUNK * CHUNK * WORLD_H)
        self.y_min = WORLD_H
        self.y_max = 0

    def idx(self, x, y, z):
        return y * CHUNK * CHUNK + z * CHUNK + x

    def get(self, x, y, z):
        if x < 0 or x >= CHUNK or y < 0 or y >= WORLD_H or z < 0 or z >= CHUNK:
            return Block.AIR
        return Block(self.blocks[self.idx(x, y, z)])

    def set(self, x, y, z, bid):
        if 0 <= x < CHUNK and 0 <= y < WORLD_H and 0 <= z < CHUNK:
            self.blocks[self.idx(x, y, z)] = int(bid)
            if bid != Block.AIR:
                self.y_min = min(self.y_min, y)
                self.y_max = max(self.y_max, y)


class World:
    def __init__(self):
        self.chunks = {}

    def chunk(self, cx, cz, create=True):
        k = (cx, cz)
        if k not in self.chunks and create:
            self.chunks[k] = self._gen(cx, cz)
        return self.chunks.get(k)

    def wxz_to_chunk(self, wx, wz):
        return chunk_coord(wx), chunk_coord(wz)

    def get(self, wx, wy, wz):
        if wy < 0 or wy >= WORLD_H:
            return Block.AIR
        cx, cz = self.wxz_to_chunk(wx, wz)
        ch = self.chunk(cx, cz, create=False)
        if not ch:
            return Block.AIR
        return ch.get(wx - cx * CHUNK, wy, wz - cz * CHUNK)

    def set(self, wx, wy, wz, bid):
        if wy < 0 or wy >= WORLD_H:
            return
        cx, cz = self.wxz_to_chunk(wx, wz)
        ch = self.chunk(cx, cz)
        lx, lz = wx - cx * CHUNK, wz - cz * CHUNK
        ch.set(lx, wy, lz, bid)

    def get_fast(self, cache, wx, wy, wz):
        if wy < 0 or wy >= WORLD_H:
            return Block.AIR
        cx = wx // CHUNK if wx >= 0 else (wx + 1) // CHUNK - 1
        cz = wz // CHUNK if wz >= 0 else (wz + 1) // CHUNK - 1
        if cache[0] != cx or cache[1] != cz:
            cache[0], cache[1] = cx, cz
            cache[2] = self.chunks.get((cx, cz))
        ch = cache[2]
        if ch is None:
            return Block.AIR
        return ch.blocks[wy * CHUNK * CHUNK + (wz - cz * CHUNK) * CHUNK + (wx - cx * CHUNK)]

    def _gen(self, cx, cz):
        ch = Chunk(cx, cz)
        for lx in range(CHUNK):
            for lz in range(CHUNK):
                wx = cx * CHUNK + lx
                wz = cz * CHUNK + lz
                h = height_at(wx, wz)
                sand_line = 30 + int(3 * math.sin(wx * 0.02))
                for y in range(WORLD_H):
                    bid = Block.AIR
                    if y == 0:
                        bid = Block.BEDROCK
                    elif y < h - 4:
                        if cave_noise(wx, y, wz) > 0.72 and y > 8:
                            bid = Block.AIR
                        else:
                            bid = Block.STONE
                            r = random.random()
                            if r < 0.012 and y < h - 8:
                                bid = Block.COAL
                            elif r < 0.018 and y < h - 12:
                                bid = Block.IRON
                            elif r < 0.004 and y < h - 16:
                                bid = Block.GOLD
                    elif y < h:
                        bid = Block.DIRT
                    elif y == h:
                        bid = Block.SAND if h <= sand_line else Block.GRASS
                    elif y < sand_line + 2 and h <= sand_line:
                        bid = Block.WATER
                    if bid != Block.AIR:
                        ch.set(lx, y, lz, bid)
                if h > sand_line + 1 and random.random() < 0.018:
                    th = h + 1 + random.randint(3, 5)
                    for ty in range(h + 1, min(th, WORLD_H - 1)):
                        ch.set(lx, ty, lz, Block.LOG)
                    for dy in range(-2, 3):
                        for dx in range(-2, 3):
                            for dz in range(-2, 3):
                                if abs(dx) + abs(dy) + abs(dz) > 4:
                                    continue
                                tx, ty, tz = lx + dx, th - 2 + dy, lz + dz
                                if 0 <= tx < CHUNK and 0 <= ty < WORLD_H and 0 <= tz < CHUNK:
                                    if ch.get(tx, ty, tz) == Block.AIR:
                                        ch.set(tx, ty, tz, Block.LEAVES)
        return ch

    def ensure_around(self, px, pz):
        pcx, pcz = self.wxz_to_chunk(int(px), int(pz))
        r2 = RENDER_DIST * RENDER_DIST + 1
        for dx in range(-RENDER_DIST, RENDER_DIST + 1):
            for dz in range(-RENDER_DIST, RENDER_DIST + 1):
                if dx * dx + dz * dz <= r2:
                    self.chunk(pcx + dx, pcz + dz)


# ---------------------------------------------------------------------------
# CHAT
# ---------------------------------------------------------------------------
class Chat:
    def __init__(self, player_name="Player"):
        self.player = player_name
        self.lines = []
        self.scroll = 0
        self.open = False
        self.input = ""
        self._boot_i = 0
        self._boot_t = 0.0
        self._flavor_t = 8.0
        self._done_boot = False

    def add(self, text, color=(240, 240, 240)):
        self.lines.append((text, color, time.time()))
        if len(self.lines) > 200:
            self.lines.pop(0)

    def system(self, text):
        self.add(text, (170, 170, 170))

    def player_msg(self, text):
        self.add(f"<{self.player}> {text}", (255, 255, 255))

    def start_boot(self):
        self._boot_i = 0
        self._boot_t = 0.0
        self._done_boot = False

    def update(self, dt):
        if not self._done_boot:
            self._boot_t += dt
            while self._boot_i < len(INFDEV_BOOT) and self._boot_t >= self._boot_i * 0.45:
                self.system(INFDEV_BOOT[self._boot_i])
                self._boot_i += 1
            if self._boot_i >= len(INFDEV_BOOT):
                self._done_boot = True
                self.system(f"Level seed: {SEED}")
        else:
            self._flavor_t -= dt
            if self._flavor_t <= 0:
                msg = random.choice(INFDEV_CHAT).format(seed=SEED, player=self.player)
                self.system(msg)
                self._flavor_t = random.uniform(18.0, 45.0)

    def submit(self):
        t = self.input.strip()
        if t:
            self.player_msg(t)
        self.input = ""
        self.open = False

    def draw(self, surf, font, font_sm):
        visible = 12
        total = len(self.lines)
        start = max(0, total - visible - self.scroll)
        end = min(total, start + visible)
        if total == 0 and not self.open:
            return
        pad = 6
        line_h = 18
        box_h = visible * line_h + pad * 2 + (24 if self.open else 0)
        box = pygame.Surface((W - 40, box_h), pygame.SRCALPHA)
        box.fill(CHAT_BG)
        surf.blit(box, (8, H - box_h - 8))
        y = H - box_h - 8 + pad
        for i in range(start, end):
            text, color, _ = self.lines[i]
            surf.blit(font_sm.render(text, True, color), (14, y))
            y += line_h
        if self.open:
            cur = "_" if int(time.time() * 2) % 2 else " "
            surf.blit(font.render("> " + self.input + cur, True, (255, 255, 160)), (14, H - 32))


# ---------------------------------------------------------------------------
# RAYCAST — voxel DDA (mining + software 3D)
# ---------------------------------------------------------------------------
def _dda_setup(ox, oy, oz, dx, dy, dz):
    ln = math.sqrt(dx * dx + dy * dy + dz * dz)
    if ln < 1e-8:
        return None
    dx, dy, dz = dx / ln, dy / ln, dz / ln
    x = int(math.floor(ox))
    y = int(math.floor(oy))
    z = int(math.floor(oz))
    step_x = 1 if dx >= 0 else -1
    step_y = 1 if dy >= 0 else -1
    step_z = 1 if dz >= 0 else -1
    t_max_x = ((x + (1 if dx >= 0 else 0)) - ox) / (dx if abs(dx) > 1e-8 else 1e-8)
    t_max_y = ((y + (1 if dy >= 0 else 0)) - oy) / (dy if abs(dy) > 1e-8 else 1e-8)
    t_max_z = ((z + (1 if dz >= 0 else 0)) - oz) / (dz if abs(dz) > 1e-8 else 1e-8)
    t_delta_x = abs(1 / (dx if abs(dx) > 1e-8 else 1e-8))
    t_delta_y = abs(1 / (dy if abs(dy) > 1e-8 else 1e-8))
    t_delta_z = abs(1 / (dz if abs(dz) > 1e-8 else 1e-8))
    return (x, y, z, step_x, step_y, step_z,
            t_max_x, t_max_y, t_max_z, t_delta_x, t_delta_y, t_delta_z, dx, dy, dz)


def raycast(world: World, ox, oy, oz, dx, dy, dz, max_dist=REACH):
    st = _dda_setup(ox, oy, oz, dx, dy, dz)
    if st is None:
        return None
    (x, y, z, step_x, step_y, step_z,
     t_max_x, t_max_y, t_max_z, t_delta_x, t_delta_y, t_delta_z, _, _, _) = st
    prev = (x, y, z)
    dist = 0.0
    for _ in range(96):
        b = world.get(x, y, z)
        if b != Block.AIR and b != Block.WATER:
            return prev, (x, y, z), b
        prev = (x, y, z)
        if t_max_x < t_max_y:
            if t_max_x < t_max_z:
                x += step_x
                dist = t_max_x
                t_max_x += t_delta_x
            else:
                z += step_z
                dist = t_max_z
                t_max_z += t_delta_z
        else:
            if t_max_y < t_max_z:
                y += step_y
                dist = t_max_y
                t_max_y += t_delta_y
            else:
                z += step_z
                dist = t_max_z
                t_max_z += t_delta_z
        if dist > max_dist:
            break
    return None


def raycast_shade(world: World, cache, ox, oy, oz, dx, dy, dz, max_dist):
    return raycast_shade_fast(world.chunks, world.get_fast, cache, ox, oy, oz, dx, dy, dz, max_dist)


def raycast_shade_fast(chunks, getf, cache, ox, oy, oz, dx, dy, dz, max_dist):
    st = _dda_setup(ox, oy, oz, dx, dy, dz)
    if st is None:
        return None
    (x, y, z, step_x, step_y, step_z,
     t_max_x, t_max_y, t_max_z, t_delta_x, t_delta_y, t_delta_z, _, _, _) = st
    dist = 0.0
    face = 2
    b = getf(cache, x, y, z)
    if b != Block.AIR:
        return 0.0, b, face
    for _ in range(56):
        if t_max_x < t_max_y:
            if t_max_x < t_max_z:
                x += step_x
                dist = t_max_x
                face = 1 if step_x > 0 else 0
                t_max_x += t_delta_x
            else:
                z += step_z
                dist = t_max_z
                face = 5 if step_z > 0 else 4
                t_max_z += t_delta_z
        else:
            if t_max_y < t_max_z:
                y += step_y
                dist = t_max_y
                face = 3 if step_y > 0 else 2
                t_max_y += t_delta_y
            else:
                z += step_z
                dist = t_max_z
                face = 5 if step_z > 0 else 4
                t_max_z += t_delta_z
        if dist > max_dist:
            return None
        b = getf(cache, x, y, z)
        if b != Block.AIR:
            return dist, b, face
    return None


def fog_apply(col, dist, max_dist):
    t = clamp(dist / max_dist, 0.0, 1.0)
    if t <= 0.4:
        return col
    fog_t = (t - 0.4) / 0.6
    return (int(lerp(col[0], FOG[0], fog_t * 0.55)),
            int(lerp(col[1], FOG[1], fog_t * 0.55)),
            int(lerp(col[2], FOG[2], fog_t * 0.55)))


# ---------------------------------------------------------------------------
# CAMERA / RENDERER — fast voxel raycast (Indev-style software 3D)
# ---------------------------------------------------------------------------
class Camera:
    def __init__(self):
        self.x = 8.5
        self.y = 40.0
        self.z = 8.5
        self.yaw = 0.0
        self.pitch = 0.0
        self.vy = 0.0
        self.on_ground = False

    def forward(self):
        cp = math.cos(self.pitch)
        return math.sin(self.yaw) * cp, math.sin(self.pitch), math.cos(self.yaw) * cp

    def right(self):
        return math.cos(self.yaw), 0.0, -math.sin(self.yaw)


def camera_basis(cam):
    cp = math.cos(cam.pitch)
    sp = math.sin(cam.pitch)
    cy = math.cos(cam.yaw)
    sy = math.sin(cam.yaw)
    fx, fy, fz = sy * cp, sp, cy * cp
    rx, rz = cy, -sy
    upx, upy, upz = -sy * sp, cp, -cy * sp
    return fx, fy, fz, rx, rz, upx, upy, upz


class Renderer:
    def __init__(self, surf):
        self.surf = surf
        self.low = pygame.Surface((RW, RH)).convert()
        self.tan_f = math.tan(math.radians(FOV * 0.5))
        self.aspect = RW / RH
        self._rays = 0
        self._ray_cache_key = None
        self._ray_dirs = None
        self.sky_rows = []
        for py in range(RH):
            t = py / RH
            self.sky_rows.append((
                int(lerp(SKY_TOP[0], SKY_BOT[0], t)),
                int(lerp(SKY_TOP[1], SKY_BOT[1], t)),
                int(lerp(SKY_TOP[2], SKY_BOT[2], t)),
            ))
        if HAS_NUMPY:
            self.pixels = np.zeros((RH, RW, 3), dtype=np.uint8)

    def _ensure_rays(self, cam):
        key = (round(cam.yaw, 3), round(cam.pitch, 3))
        if key == self._ray_cache_key:
            return
        self._ray_cache_key = key
        fx, fy, fz, rx, rz, upx, upy, upz = camera_basis(cam)
        dirs = []
        for py in range(RH):
            ny = (0.5 - py / RH) * 2 * self.tan_f
            row = []
            for px in range(RW):
                nx = (px / RW - 0.5) * 2 * self.tan_f * self.aspect
                dx = fx + rx * nx + upx * ny
                dy = fy + upy * ny
                dz = fz + rz * nx + upz * ny
                ln = math.sqrt(dx * dx + dy * dy + dz * dz)
                row.append((dx / ln, dy / ln, dz / ln))
            dirs.append(row)
        self._ray_dirs = dirs

    def draw_world(self, world: World, cam: Camera):
        self._rays = 0
        world.ensure_around(cam.x, cam.z)
        self._ensure_rays(cam)
        cache = [None, None, None]
        max_dist = RENDER_DIST * CHUNK + 6
        ox, oy, oz = cam.x, cam.y + 0.05, cam.z
        chunks = world.chunks
        getf = world.get_fast

        if HAS_NUMPY:
            pxbuf = self.pixels
            for py, row in enumerate(self._ray_dirs):
                sky = self.sky_rows[py]
                for px, (dx, dy, dz) in enumerate(row):
                    hit = raycast_shade_fast(chunks, getf, cache, ox, oy, oz, dx, dy, dz, max_dist)
                    if hit is None:
                        pxbuf[py, px] = sky
                        continue
                    dist, bid, face = hit
                    cols = BLOCK[bid]
                    fi = min(face // 2, len(cols) - 1)
                    col = shade(cols[fi], FACE_SHADE[face])
                    if bid == Block.WATER:
                        col = shade(col, 0.82)
                    pxbuf[py, px] = fog_apply(col, dist, max_dist)
                    self._rays += 1
            pygame.surfarray.blit_array(self.low, np.transpose(pxbuf, (1, 0, 2)))
        else:
            for py, row in enumerate(self._ray_dirs):
                sky = self.sky_rows[py]
                for px, (dx, dy, dz) in enumerate(row):
                    hit = raycast_shade_fast(chunks, getf, cache, ox, oy, oz, dx, dy, dz, max_dist)
                    if hit is None:
                        self.low.set_at((px, py), sky)
                        continue
                    dist, bid, face = hit
                    cols = BLOCK[bid]
                    fi = min(face // 2, len(cols) - 1)
                    col = fog_apply(shade(cols[fi], FACE_SHADE[face]), dist, max_dist)
                    self.low.set_at((px, py), col)
                    self._rays += 1

        pygame.transform.scale(self.low, (W, H), self.surf)

    def draw_crosshair(self):
        cx, cy = W // 2, H // 2
        pygame.draw.line(self.surf, (255, 255, 255), (cx - 8, cy), (cx + 8, cy), 1)
        pygame.draw.line(self.surf, (255, 255, 255), (cx, cy - 8), (cx, cy + 8), 1)

    def draw_hud(self, font, hotbar_i, fps, debug, cam, world, target):
        s = self.surf
        bx = W // 2 - len(HOTBAR) * 22
        by = H - 44
        for i, bid in enumerate(HOTBAR):
            r = pygame.Rect(bx + i * 44, by, 40, 40)
            pygame.draw.rect(s, (30, 30, 30), r)
            pygame.draw.rect(s, (200, 200, 200) if i == hotbar_i else (80, 80, 80), r, 2)
            pygame.draw.rect(s, BLOCK[bid][0], r.inflate(-8, -8))
            s.blit(font.render(str(i + 1), True, (255, 255, 255)), (r.x + 2, r.y + 2))
        if debug:
            lines = [
                f"ac's mc 0.1 | {fps:.0f} FPS | raycast {RW}x{RH} | hits {self._rays}",
                f"XYZ: {cam.x:.2f} / {cam.y:.2f} / {cam.z:.2f}",
                f"Chunk: {world.wxz_to_chunk(int(cam.x), int(cam.z))} | Chunks: {len(world.chunks)}",
                f"Seed: {SEED} | Block: {BLOCK_NAMES.get(HOTBAR[hotbar_i], '?')}",
            ]
            if target:
                lines.append(f"Target: {BLOCK_NAMES.get(target[2], '?')} at {target[1]}")
            for i, ln in enumerate(lines):
                s.blit(font.render(ln, True, (255, 255, 0)), (4, 4 + i * 16))


# ---------------------------------------------------------------------------
# GAME
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        try:
            self.screen = pygame.display.set_mode((W, H))
        except pygame.error as e:
            print("Display error:", e, file=sys.stderr)
            sys.exit(1)
        pygame.display.set_caption(TITLE)
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas,monaco,monospace", 14)
        self.font_sm = pygame.font.SysFont("consolas,monaco,monospace", 15)
        self.world = World()
        self.cam = Camera()
        self.renderer = Renderer(self.screen)
        self.chat = Chat()
        self.hotbar_i = 0
        self.debug = False
        self.spawn_player()
        self.world.ensure_around(self.cam.x, self.cam.z)
        self.chat.start_boot()

    def spawn_player(self):
        wx, wz = 8, 8
        h = height_at(wx, wz) + 2
        self.cam.x = wx + 0.5
        self.cam.z = wz + 0.5
        self.cam.y = float(h)
        self.cam.vy = 0.0

    def solid_at(self, x, y, z):
        b = self.world.get(int(math.floor(x)), int(math.floor(y)), int(math.floor(z)))
        return b != Block.AIR and b != Block.WATER

    def collide(self, nx, ny, nz):
        hw, hh = 0.28, 0.92
        for ox in (-hw, hw):
            for oy in (0.0, hh * 0.5, hh):
                for oz in (-hw, hw):
                    if self.solid_at(nx + ox, ny + oy, nz + oz):
                        return True
        return False

    def update_physics(self, dt):
        c = self.cam
        keys = pygame.key.get_pressed()
        spd = RUN if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else WALK
        fx, _, fz = c.forward()
        mag = math.hypot(fx, fz) or 1.0
        fx, fz = fx / mag, fz / mag
        rx, _, rz = c.right()
        mx = (fx * (keys[pygame.K_w] - keys[pygame.K_s]) + rx * (keys[pygame.K_d] - keys[pygame.K_a])) * spd
        mz = (fz * (keys[pygame.K_w] - keys[pygame.K_s]) + rz * (keys[pygame.K_d] - keys[pygame.K_a])) * spd
        nx = c.x + mx * dt
        if not self.collide(nx, c.y, c.z):
            c.x = nx
        nz = c.z + mz * dt
        if not self.collide(c.x, c.y, nz):
            c.z = nz
        c.vy -= GRAVITY * dt
        ny = c.y + c.vy * dt
        if self.collide(c.x, ny, c.z):
            if c.vy < 0:
                steps = 0
                while not self.collide(c.x, c.y - 0.05, c.z) and steps < 64:
                    c.y -= 0.05
                    steps += 1
            c.vy = 0
            c.on_ground = True
        else:
            c.y = ny
            c.on_ground = False
        if keys[pygame.K_SPACE] and c.on_ground:
            c.vy = JUMP_V
            c.on_ground = False

    def target_block(self):
        fx, fy, fz = self.cam.forward()
        hit = raycast(self.world, self.cam.x, self.cam.y + 0.1, self.cam.z, fx, fy, fz, REACH)
        if not hit:
            return None
        prev, cur, bid = hit
        return prev, cur, bid

    def handle_event(self, e):
        if e.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if e.type == pygame.KEYDOWN:
            if self.chat.open:
                if e.key == pygame.K_RETURN:
                    self.chat.submit()
                elif e.key == pygame.K_ESCAPE:
                    self.chat.input = ""
                    self.chat.open = False
                elif e.key == pygame.K_BACKSPACE:
                    self.chat.input = self.chat.input[:-1]
                return
            if e.key == pygame.K_ESCAPE:
                grab = not pygame.event.get_grab()
                pygame.event.set_grab(grab)
                pygame.mouse.set_visible(not grab)
            elif e.key == pygame.K_F3:
                self.debug = not self.debug
            elif e.key == pygame.K_t:
                self.chat.open = True
            elif pygame.K_1 <= e.key <= pygame.K_9:
                i = e.key - pygame.K_1
                if i < len(HOTBAR):
                    self.hotbar_i = i
            elif e.key == pygame.K_e:
                hit = self.target_block()
                if hit:
                    _, _, bid = hit
                    if bid in HOTBAR:
                        self.hotbar_i = HOTBAR.index(bid)
                        self.chat.system(f"Picked {BLOCK_NAMES.get(bid, '?')}")
        if e.type == pygame.TEXTINPUT and self.chat.open:
            if len(self.chat.input) < 80:
                self.chat.input += e.text
        if e.type == pygame.MOUSEBUTTONDOWN and not self.chat.open and pygame.event.get_grab():
            hit = self.target_block()
            if not hit:
                return
            prev, cur, bid = hit
            if e.button == 1:
                self.world.set(*cur, Block.AIR)
                self.chat.system(f"Broke {BLOCK_NAMES.get(bid, 'block')}.")
            elif e.button == 3:
                px, py, pz = prev
                if not self.collide(px + 0.5, py + 0.5, pz + 0.5):
                    b = HOTBAR[self.hotbar_i]
                    self.world.set(px, py, pz, b)
                    self.chat.system(f"Placed {BLOCK_NAMES.get(b, '?')}.")
        if e.type == pygame.MOUSEWHEEL and not self.chat.open:
            self.hotbar_i = (self.hotbar_i - e.y) % len(HOTBAR)
        if e.type == pygame.MOUSEMOTION and pygame.event.get_grab() and not self.chat.open:
            self.cam.yaw += e.rel[0] * 0.003
            self.cam.pitch = clamp(self.cam.pitch - e.rel[1] * 0.003, -1.45, 1.45)

    def run(self):
        tgt = None
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 20)
            for e in pygame.event.get():
                self.handle_event(e)
            if not self.chat.open:
                self.update_physics(dt)
            self.chat.update(dt)
            if self.clock.get_fps() > 20 or self.debug:
                tgt = self.target_block()
            self.renderer.draw_world(self.world, self.cam)
            self.renderer.draw_crosshair()
            fps = self.clock.get_fps()
            self.renderer.draw_hud(self.font, self.hotbar_i, fps, self.debug, self.cam, self.world, tgt)
            self.chat.draw(self.screen, self.font, self.font_sm)
            title = self.font.render(TITLE + "  |  60 FPS  |  Infdev chat", True, (255, 255, 255))
            self.screen.blit(title, (W - title.get_width() - 8, 8))
            pygame.display.flip()


def main():
    Game().run()


if __name__ == "__main__":
    main()
