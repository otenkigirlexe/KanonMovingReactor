import pygame
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import json
import threading
import math
import time
import random

# --- Configuration ---
WIDTH, HEIGHT = 854, 480
FPS = 60
IMAGE_PATH = "images/00_shibuyakanon_normal.png"
NEW_IMAGE_PATH = "images/10_shibuyakanon_hajimari_ha_kiminosora_normal.png"
BG_NORMAL_PATH = "images/20_backimage_normal.png"
BG_HAJIMARI_PATH = "images/30_backimage_hajimari_ha_kiminosora.png"
AMPLITUDE_SCALE = 2000
SAMPLE_RATE = 44100
BUFFER_SIZE = 4000
VOLUME_THRESHOLD = 0.01
TEXT_LOCK_DURATION = 3  # Seconds to lock the text after update

# --- Spring physics parameters ---
stiffness = 0.8
damping = 0.2
vy = 0
base_y = HEIGHT // 2 + 50
y = base_y


# --- Speech bubble texts ---
first_text = "こんにちは！"
text_10 = "私も大好きだよ！"
text_00_options = [
    "こんにちは！",
    "こんばんは！",
    "今日はいい天気だね！",
    "私やっぱり…歌が好きだ…！",
    "作曲の続きを頑張ろうかな！",
    "どうしたの？"
]
current_text = first_text
text_lock_timer = None

# --- Background music setup ---
import pygame.mixer
pygame.mixer.init()
pygame.mixer.music.load("audio/liella_bgm.opus")
pygame.mixer.music.set_volume(0.1)   # Volume adjustment
pygame.mixer.music.play(loops=-1, fade_ms=500)  # Loop with 0.5s fade-in

# --- Vosk speech recognition setup ---
model = Model("model")
rec = KaldiRecognizer(model, SAMPLE_RATE)
trigger_change = False

# --- State management flags ---
rotating = False          # Rotation from 00 → 10
rotating_back = False     # Rotation from 10 → 00
bg_fading = False
return_timer = None
is_state_00 = True        # Tracks whether the current state is 00

# --- Speech recognition thread ---
def listen_for_love():
    global trigger_change
    with sd.InputStream(channels=1, samplerate=SAMPLE_RATE, dtype='int16') as stream:
        while True:
            data, _ = stream.read(BUFFER_SIZE)
            if rec.AcceptWaveform(data.tobytes()):
                result = json.loads(rec.Result())
                text = result.get("text", "")
                if "大好き" in text and not (rotating or rotating_back or bg_fading):
                    trigger_change = True

listener_thread = threading.Thread(target=listen_for_love, daemon=True)
listener_thread.start()

# --- Audio level acquisition ---
prev_level = 0.0
def get_audio_level():
    global prev_level
    audio = sd.rec(int(0.1 * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32', blocking=True)
    rms = float(np.sqrt(np.mean(np.square(audio))))
    # Apply simple smoothing
    level = 0.8 * prev_level + 0.2 * rms
    prev_level = level
    return level

# --- Initialize Pygame ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("kanonchan!")
clock = pygame.time.Clock()

# --- Font setup ---
font = pygame.font.SysFont("meiryo", 20)
name_font = pygame.font.SysFont("meiryo", 18)

# --- Load and scale images ---
def load_and_scale(path):
    img = pygame.image.load(path).convert_alpha()
    max_width = WIDTH * 1.25
    max_height = HEIGHT * 1.25
    scale_factor = min(max_width / img.get_width(), max_height / img.get_height())
    new_width = int(img.get_width() * scale_factor)
    new_height = int(img.get_height() * scale_factor)
    return pygame.transform.scale(img, (new_width, new_height))

img_00 = load_and_scale(IMAGE_PATH)
img_10 = load_and_scale(NEW_IMAGE_PATH)
current_img = img_00
next_img = None
img_rect = current_img.get_rect(center=(WIDTH // 2, y))

# --- Background images ---
bg_normal = pygame.image.load(BG_NORMAL_PATH).convert()
bg_hajimari = pygame.image.load(BG_HAJIMARI_PATH).convert()
bg_current = bg_normal
bg_target = bg_normal
bg_alpha = 0
fade_speed = 20

rotation_angle = 0
rotation_speed = 45

# --- Main loop ---
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- Spring animation ---
    level = get_audio_level()
    target_y = base_y - level * AMPLITUDE_SCALE
    force = (target_y - y) * stiffness
    vy = vy * damping + force
    y += vy

    # --- Update text based on audio volume (00 state only) ---
    if is_state_00 and not (rotating or rotating_back or bg_fading):
        if text_lock_timer is None or time.time() - text_lock_timer > TEXT_LOCK_DURATION:
            if level > VOLUME_THRESHOLD:
                current_text = random.choice(text_00_options)
                text_lock_timer = time.time()

    # --- Trigger rotation on "I love you" recognition ---
    if trigger_change and not (rotating or rotating_back or bg_fading):
        rotating = True
        rotation_angle = 0
        next_img = img_10
        bg_target = bg_hajimari
        trigger_change = False
        bg_fading = True
        return_timer = None
        current_text = text_10
        text_lock_timer = time.time()

    # --- Rotation animation 00 → 10 ---
    if rotating:
        rotation_angle += rotation_speed
        if rotation_angle >= 360:
            rotation_angle = 0
            rotating = False
            return_timer = time.time()
            is_state_00 = False
        angle_rad = math.radians(rotation_angle)
        scale_x = max(1, abs(math.cos(angle_rad)) * current_img.get_width())
        img_to_draw = current_img if rotation_angle < 180 else next_img
        if rotation_angle >= 180 and current_img != next_img:
            current_img = next_img
        scaled_img = pygame.transform.scale(img_to_draw, (int(scale_x), img_to_draw.get_height()))
        img_rect = scaled_img.get_rect(center=(WIDTH // 2, int(y)))
        screen_img = scaled_img

    # --- After 3 seconds, rotate back 10 → 00 ---
    elif return_timer and time.time() - return_timer >= 3 and not rotating_back:
        rotating_back = True
        rotation_angle = 0
        next_img = img_00
        bg_target = bg_normal
        bg_fading = True
        return_timer = None
        current_text = random.choice(text_00_options)
        text_lock_timer = time.time()

    # --- Rotation animation 10 → 00 ---
    elif rotating_back:
        rotation_angle += rotation_speed
        if rotation_angle >= 360:
            rotation_angle = 0
            rotating_back = False
            is_state_00 = True
        angle_rad = math.radians(rotation_angle)
        scale_x = max(1, abs(math.cos(angle_rad)) * current_img.get_width())
        img_to_draw = current_img if rotation_angle < 180 else next_img
        if rotation_angle >= 180 and current_img != next_img:
            current_img = next_img
        scaled_img = pygame.transform.scale(img_to_draw, (int(scale_x), img_to_draw.get_height()))
        img_rect = scaled_img.get_rect(center=(WIDTH // 2, int(y)))
        screen_img = scaled_img
    else:
        screen_img = current_img
        img_rect.centery = int(y)

    # --- Background fade effect ---
    if bg_current != bg_target:
        if bg_alpha < 255:
            bg_alpha += fade_speed
        if bg_alpha > 255:
            bg_alpha = 255
        tmp_bg = bg_current.copy()
        tmp_bg.set_alpha(255 - bg_alpha)
        screen.blit(bg_target, (0, 0))
        screen.blit(tmp_bg, (0, 0))
        if bg_alpha >= 255:
            bg_current = bg_target
            bg_alpha = 0
            bg_fading = False
    else:
        screen.blit(bg_current, (0, 0))

    # --- Draw character ---
    screen.blit(screen_img, img_rect)

    # --- Draw speech bubble (top-right) ---
    bubble_width, bubble_height = 400, 65
    bubble_rect = pygame.Rect(WIDTH - bubble_width - 20, 20, bubble_width, bubble_height)
    pygame.draw.rect(screen, (255, 165, 0), bubble_rect, border_radius=15)
    pygame.draw.rect(screen, (0, 0, 0), bubble_rect, width=2, border_radius=15)

    # --- Name plate (overlapping the speech bubble) ---
    name_bubble_width, name_bubble_height = 140, 35
    name_rect = pygame.Rect(
        bubble_rect.left + 15,
        bubble_rect.top - name_bubble_height // 2,
        name_bubble_width,
        name_bubble_height
    )
    pygame.draw.rect(screen, (255, 220, 120), name_rect, border_radius=10)
    pygame.draw.rect(screen, (0, 0, 0), name_rect, width=2, border_radius=10)

    name_surface = name_font.render("かのん", True, (0, 0, 0))
    name_text_rect = name_surface.get_rect(center=name_rect.center)
    screen.blit(name_surface, name_text_rect)

    # --- Render speech text (bottom-aligned in the bubble) ---
    text_surface = font.render(current_text, True, (0, 0, 0))
    text_rect = text_surface.get_rect(midbottom=(bubble_rect.centerx, bubble_rect.bottom - 10))
    screen.blit(text_surface, text_rect)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()