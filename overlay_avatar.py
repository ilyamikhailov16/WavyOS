import math
import random
import sys
import time

import pygame

from avatar_controller import AvatarController
from audio_engine import AudioEngine


W, H = 560, 560
FPS = 60

BG_TOP    = (16, 18, 28)
BG_BOTTOM = (28, 30, 46)
FACE      = (255, 218, 185)
FACE_DARK = (220, 178, 150)
INK       = (28, 28, 36)
ACCENT    = (120, 200, 255)
BLUSH     = (255, 150, 160)
WHITE     = (240, 240, 240)

SILENT_IN   = 0.035   
SILENT_OUT  = 0.055   
SPEAK_IN    = 0.080   
SPEAK_OUT   = 0.060   
HIGH_ENERGY = 0.18    

EMOTION_HOLD = 0.25

OVERLAY_MODE = False  



pygame.init()

flags = pygame.NOFRAME if OVERLAY_MODE else 0
screen = pygame.display.set_mode((W, H), flags)
pygame.display.set_caption("Wavy Avatar")
clock = pygame.time.Clock()

font_lg = pygame.font.SysFont("Segoe UI", 20, bold=True)
font_md = pygame.font.SysFont("Segoe UI", 16)
font_sm = pygame.font.SysFont("Segoe UI", 13)

if OVERLAY_MODE:
    try:
        import win32gui
        import win32con

        hwnd = pygame.display.get_wm_info()["window"]
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 1000, 100, W, H, 0)
    except Exception as e:
        print(f"[overlay] topmost disabled: {e}", file=sys.stderr)



avatar = AvatarController()
audio = AudioEngine()

raw_volume = 0.0
raw_energy = 0.0


def on_audio(volume, energy):
    global raw_volume, raw_energy
    raw_volume = volume
    raw_energy = energy


audio.subscribe(on_audio)

audio_ok = True
try:
    audio.start()
except Exception as e:
    audio_ok = False
    print(f"[overlay] microphone unavailable: {e}", file=sys.stderr)



class Smoother:
    def __init__(self, value=0.0, speed=8.0):
        self.value = float(value)
        self.speed = speed

    def update(self, target, dt):
        a = 1.0 - math.exp(-self.speed * dt)
        self.value += (float(target) - self.value) * a
        return self.value


vol_smooth = Smoother(0.0, speed=14.0)   
vol_avg    = Smoother(0.0, speed=3.5)    
energy_avg = Smoother(0.0, speed=4.0)

current_state = "idle"        
current_emotion = "neutral"   

pending_emotion = current_emotion
pending_since = time.time()


def decide_state(v_avg):
    global current_state
    if current_state == "idle":
        if v_avg > SILENT_OUT:
            current_state = "listening"
    elif current_state == "listening":
        if v_avg < SILENT_IN:
            current_state = "idle"
        elif v_avg > SPEAK_IN:
            current_state = "speaking"
    elif current_state == "speaking":
        if v_avg < SPEAK_OUT:
            current_state = "listening"
    return current_state


def decide_emotion(state, v_avg, e_avg, now):
    global pending_emotion, pending_since, current_emotion

    if state == "idle":
        target = "neutral"
    elif e_avg > HIGH_ENERGY and state == "speaking":
        target = "surprised"
    elif state == "speaking":
        target = "happy"
    else: 
        target = "neutral"

    if target != pending_emotion:
        pending_emotion = target
        pending_since = now

    if (now - pending_since) >= EMOTION_HOLD and current_emotion != pending_emotion:
        current_emotion = pending_emotion

    return current_emotion



class Blink:
    def __init__(self):
        self.next_blink = time.time() + random.uniform(2.5, 5.0)
        self.active_until = 0.0
        self.duration = 0.13

    def factor(self, now):
        if now < self.active_until:
            t = 1.0 - (self.active_until - now) / self.duration
            return abs(math.cos(t * math.pi))
        if now >= self.next_blink:
            self.active_until = now + self.duration
            self.next_blink = now + random.uniform(2.5, 5.5)
        return 1.0


class EyeDrift:
    def __init__(self):
        self.tx = 0.0
        self.ty = 0.0
        self.next_change = 0.0

    def get(self, now, dt, active):
        if active and now >= self.next_change:
            self.tx = random.uniform(-3.0, 3.0)
            self.ty = random.uniform(-2.0, 2.0)
            self.next_change = now + random.uniform(1.4, 3.2)
        if not active:
            self.tx *= math.exp(-dt * 4)
            self.ty *= math.exp(-dt * 4)
        return self.tx, self.ty


blink = Blink()
drift = EyeDrift()
mouth_open = Smoother(0.0, speed=18.0)  



def draw_background(surf):
    for y in range(H):
        t = y / (H - 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (W, y))


def draw_aura(surf, cx, cy, base_r, intensity):
    if intensity <= 0.01:
        return
    layers = 5
    max_extra = 60 * intensity
    for i in range(layers, 0, -1):
        f = i / layers
        radius = int(base_r + max_extra * f + 8)
        alpha = int(70 * intensity * (1 - f))
        if alpha <= 0:
            continue
        s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*ACCENT, alpha), (radius, radius), radius)
        surf.blit(s, (cx - radius, cy - radius))


def draw_face(surf, cx, cy, r):
    shadow = pygame.Surface((r * 2 + 20, r * 2 + 20), pygame.SRCALPHA)
    pygame.draw.circle(shadow, (0, 0, 0, 60), (r + 10, r + 14), r + 6)
    surf.blit(shadow, (cx - r - 10, cy - r - 10))
    pygame.draw.circle(surf, FACE, (cx, cy), r)
    pygame.draw.circle(surf, FACE_DARK, (cx, cy), r, 3)


def draw_blush(surf, cx, cy, r, alpha):
    if alpha <= 0:
        return
    blush_r = 18
    s = pygame.Surface((blush_r * 2, blush_r * 2), pygame.SRCALPHA)
    pygame.draw.circle(s, (*BLUSH, alpha), (blush_r, blush_r), blush_r)
    surf.blit(s, (cx - r * 0.55 - blush_r, cy + r * 0.15 - blush_r))
    surf.blit(s, (cx + r * 0.55 - blush_r, cy + r * 0.15 - blush_r))


def draw_eyes(surf, cx, cy, emotion, blink_factor, drift_x, drift_y):
    eye_dx = 55
    eye_y = cy - 25
    left = (cx - eye_dx, eye_y)
    right = (cx + eye_dx, eye_y)

    base_r = 16
    open_r = max(1, int(base_r * blink_factor))

    if emotion == "sad":
        for (ex, ey) in (left, right):
            pygame.draw.line(surf, INK,
                             (ex - 14, ey + 4),
                             (ex + 14, ey - 5), 4)
        return

    if emotion == "surprised":
        for (ex, ey) in (left, right):
            r_outer = int(18 * blink_factor) or 1
            pygame.draw.circle(surf, WHITE, (ex, ey), r_outer)
            pygame.draw.circle(surf, INK, (ex, ey), r_outer, 3)
            if blink_factor > 0.3:
                pygame.draw.circle(
                    surf, INK,
                    (int(ex + drift_x * 0.6), int(ey + drift_y * 0.6)),
                    max(2, int(6 * blink_factor)),
                )
        return

    if emotion == "happy":
        for (ex, ey) in (left, right):
            if blink_factor < 0.25:
                pygame.draw.line(surf, INK, (ex - 12, ey), (ex + 12, ey), 4)
            else:
                rect = pygame.Rect(ex - 14, ey - int(10 * blink_factor),
                                   28, int(20 * blink_factor))
                pygame.draw.arc(surf, INK, rect, math.pi, 2 * math.pi, 4)
        return

    for (ex, ey) in (left, right):
        if blink_factor < 0.15:
            pygame.draw.line(surf, INK, (ex - 12, ey), (ex + 12, ey), 4)
            continue
        pygame.draw.circle(surf, WHITE, (ex, ey), open_r)
        pygame.draw.circle(surf, INK, (ex, ey), open_r, 2)
        px = int(ex + drift_x)
        py = int(ey + drift_y)
        pygame.draw.circle(surf, INK, (px, py), max(2, int(6 * blink_factor)))
        pygame.draw.circle(surf, WHITE, (px - 2, py - 3), 2)


def draw_mouth(surf, cx, cy, openness, emotion):
    mouth_y = cy + 50

    if emotion == "sad" and openness < 0.15:
        rect = pygame.Rect(cx - 30, mouth_y - 4, 60, 22)
        pygame.draw.arc(surf, INK, rect, 0, math.pi, 4)
        return

    if openness < 0.05:
        if emotion == "happy":
            rect = pygame.Rect(cx - 32, mouth_y - 12, 64, 28)
            pygame.draw.arc(surf, INK, rect, math.pi, 2 * math.pi, 4)
        else:
            pygame.draw.line(surf, INK, (cx - 22, mouth_y), (cx + 22, mouth_y), 4)
        return

    h = int(8 + 44 * openness)
    w = int(46 + 24 * openness)
    rect = pygame.Rect(cx - w // 2, mouth_y - h // 4, w, h)
    pygame.draw.ellipse(surf, INK, rect)
    if openness > 0.4:
        tongue = pygame.Rect(rect.x + 8, rect.y + h // 2, w - 16, h // 3)
        pygame.draw.ellipse(surf, BLUSH, tongue)


def draw_hud(surf, state, emotion, vol, eng, mic_ok):
    pad = 16

    label = state.upper()
    txt = font_lg.render(label, True, WHITE)
    pill_w = txt.get_width() + 24
    pill_h = txt.get_height() + 10
    pill = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
    pygame.draw.rect(pill, (*ACCENT, 50), pill.get_rect(), border_radius=pill_h // 2)
    pygame.draw.rect(pill, (*ACCENT, 180), pill.get_rect(), 2, border_radius=pill_h // 2)
    pill.blit(txt, (12, 5))
    surf.blit(pill, (pad, pad))

    e_txt = font_md.render(f"emotion: {emotion}", True, WHITE)
    surf.blit(e_txt, (pad + 4, pad + pill_h + 6))

    bar_x, bar_y, bar_w, bar_h = pad, H - pad - 14, 200, 8
    pygame.draw.rect(surf, (255, 255, 255, 40),
                     pygame.Rect(bar_x, bar_y, bar_w, bar_h),
                     border_radius=4)
    fill = max(0, min(1.0, vol)) * bar_w
    if fill > 0:
        pygame.draw.rect(surf, ACCENT,
                         pygame.Rect(bar_x, bar_y, int(fill), bar_h),
                         border_radius=4)
    surf.blit(font_sm.render(f"vol {vol:.2f}  energy {eng:.2f}", True, WHITE),
              (bar_x, bar_y - 18))

    if not mic_ok:
        warn = font_sm.render("microphone unavailable", True, BLUSH)
        surf.blit(warn, (W - warn.get_width() - pad, pad))

    # quit hint
    hint = font_sm.render("ESC to quit", True, WHITE)
    surf.blit(hint, (W - hint.get_width() - pad, H - hint.get_height() - pad))


running = True
last_t = time.time()

try:
    while running:
        clock.tick(FPS)
        now = time.time()
        dt = max(1e-3, now - last_t)
        last_t = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        v_fast = vol_smooth.update(raw_volume, dt)
        v_avg = vol_avg.update(raw_volume, dt)
        e_avg = energy_avg.update(raw_energy, dt)

        state = decide_state(v_avg)
        emotion = decide_emotion(state, v_avg, e_avg, now)

        avatar.set_state(state)
        avatar.set_expression(emotion)
        avatar.speak_level(v_fast)
        avatar.set_energy(e_avg)

        breath = math.sin(now * 1.4) * 0.012  
        face_r = int(150 * (1 + breath))
        cx, cy = W // 2, H // 2 + 10

        is_idle = state == "idle"
        bf = blink.factor(now)
        dx, dy = drift.get(now, dt, is_idle)

        target_open = 0.0 if state == "idle" else min(1.0, v_fast * 5.5)
        mo = mouth_open.update(target_open, dt)

        aura_intensity = 0.0
        if state == "speaking":
            aura_intensity = min(1.0, v_fast * 4.0)
        elif state == "listening":
            aura_intensity = 0.18

        blush_alpha = 0
        if emotion == "happy":
            blush_alpha = 90
        elif emotion == "surprised":
            blush_alpha = 40

        draw_background(screen)
        draw_aura(screen, cx, cy, face_r, aura_intensity)
        draw_face(screen, cx, cy, face_r)
        draw_blush(screen, cx, cy, face_r, blush_alpha)
        draw_eyes(screen, cx, cy, emotion, bf, dx, dy)
        draw_mouth(screen, cx, cy, mo, emotion)
        draw_hud(screen, state, emotion, v_fast, e_avg, audio_ok)

        pygame.display.flip()
finally:
    audio.stop()
    pygame.quit()
