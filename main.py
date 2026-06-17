"""
Mini Console Launcher UI
=========================
A PlayStation/Xbox-style dashboard built with pygame.
Boots straight into fullscreen, hides hints by default, and "launches"
apps by handing them the real game window to draw into.

Controls:
    LEFT / A         -> move selection left
    RIGHT / D        -> move selection right
    ENTER / SPACE    -> launch selected app
    H                -> show / hide control hints
    F11              -> toggle fullscreen / windowed
    ESC              -> quit (or exit an open app back to the dashboard)
    Gamepad (optional):
        D-pad / left stick X axis -> move selection
        Button A (button index 0) -> launch

How to extend:
    - Add a new entry to the `apps` list near the bottom of the file.
    - "on_open" is a real function that receives the live pygame `screen`
      surface, the shared `clock`, and `fonts` -- draw directly into the
      window, run your own loop, and return when you're done. The
      dashboard resumes exactly where it left off.

Run with:
    pip install pygame
    python console_launcher.py
"""

import sys
import math
import random
import pygame


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

DEFAULT_WINDOWED_SIZE = (1280, 720)   # used only if the user toggles OUT of fullscreen

BG_TOP_COLOR = (10, 10, 18)           # background gradient: deep navy/black
BG_BOTTOM_COLOR = (24, 16, 38)        # background gradient: dark violet
ACCENT_COLOR = (110, 190, 255)        # cyan-blue accent (glow, underline, header)
ACCENT_COLOR_2 = (190, 110, 255)      # violet accent used in gradients/particles
TEXT_COLOR = (240, 240, 248)
SUBTEXT_COLOR = (140, 145, 165)

TILE_WIDTH = 220
TILE_HEIGHT = 220
TILE_GAP = 46
TILE_CORNER_RADIUS = 22

SELECTED_SCALE = 1.15
ANIMATION_SPEED = 0.20                # easing factor, 0..1

PARTICLE_COUNT = 40

FPS = 60


# ---------------------------------------------------------------------------
# APP ACTIONS
# ---------------------------------------------------------------------------
# Each app's "on_open" is a real function wired directly to the live window.
# It receives the actual `screen` surface the dashboard was drawing into, so
# whatever you draw appears in the same window -- no separate popup. Run your
# own loop inside, and `return` (or break out) once you're done; the
# dashboard takes back control on the next frame exactly where it left off.

def make_demo_app(app_name):
    if app_name == "Steam":
        print("steam")


# ---------------------------------------------------------------------------
# APP DEFINITIONS
# ---------------------------------------------------------------------------
# The core data structure driving the whole UI. Add/remove apps here.
# "image" can be None or a path to an image file you own.

apps = [
    {
        "name": "Games",
        "color": (235, 64, 92),
        "image": "canieat.jpg",
        "on_open": make_demo_app("Games", (40, 12, 18)),
    },
    {
        "name": "Media",
        "color": (64, 160, 235),
        "image": None,
        "on_open": make_demo_app("Media", (10, 24, 40)),
    },
    {
        "name": "Store",
        "color": (72, 210, 150),
        "image": None,
        "on_open": make_demo_app("Store", (10, 32, 24)),
    },
    {
        "name": "Settings",
        "color": (180, 120, 235),
        "image": None,
        "on_open": make_demo_app("Settings", (24, 14, 40)),
    },
    {
        "name": "Friends",
        "color": (245, 180, 60),
        "image": None,
        "on_open": make_demo_app("Friends", (40, 28, 8)),
    },
]


# ---------------------------------------------------------------------------
# HELPER: load optional images safely
# ---------------------------------------------------------------------------

def load_app_images(app_list, target_size):
    """Loads each app's 'image' path into a pygame Surface, if provided.
    Falls back to no icon (plain color tile) if missing or fails to load."""
    for app in app_list:
        path = app.get("image")
        if path:
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.smoothscale(img, target_size)
                app["image_surface"] = img
            except Exception as e:
                print(f"[Launcher] Could not load image for '{app['name']}': {e}")
                app["image_surface"] = None
        else:
            app["image_surface"] = None


# ---------------------------------------------------------------------------
# HELPER: vertical gradient background
# ---------------------------------------------------------------------------

def draw_gradient_background(screen, top_color, bottom_color):
    """Draws a smooth vertical gradient by blitting a precomputed strip."""
    w, h = screen.get_size()
    gradient = pygame.Surface((1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
        gradient.set_at((0, y), (r, g, b))
    gradient = pygame.transform.scale(gradient, (w, h))
    screen.blit(gradient, (0, 0))


# ---------------------------------------------------------------------------
# HELPER: drifting ambient particles (purely cosmetic "cool factor")
# ---------------------------------------------------------------------------

def make_particles(width, height, count):
    particles = []
    for _ in range(count):
        particles.append(
            {
                "x": random.uniform(0, width),
                "y": random.uniform(0, height),
                "speed": random.uniform(6, 22),
                "size": random.uniform(1.0, 3.0),
                "alpha": random.uniform(40, 130),
            }
        )
    return particles


def update_and_draw_particles(screen, particles, dt_seconds, width, height):
    for p in particles:
        p["y"] -= p["speed"] * dt_seconds
        if p["y"] < -5:
            p["y"] = height + 5
            p["x"] = random.uniform(0, width)
        surf = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(
            surf, (*ACCENT_COLOR, int(p["alpha"])), (3, 3), p["size"]
        )
        screen.blit(surf, (p["x"] - 3, p["y"] - 3))


# ---------------------------------------------------------------------------
# HELPER: glow + tile rendering
# ---------------------------------------------------------------------------

def draw_tile(screen, rect, color, selected, glow_phase):
    """Draws a rounded tile with a soft drop shadow, and -- if selected --
    a pulsing colored glow ring plus a brighter border."""

    # Soft drop shadow for depth
    shadow_surf = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
    pygame.draw.rect(
        shadow_surf,
        (0, 0, 0, 90),
        shadow_surf.get_rect(),
        border_radius=TILE_CORNER_RADIUS + 6,
    )
    screen.blit(shadow_surf, (rect.x - 10, rect.y - 6))

    if selected:
        pulse = (math.sin(glow_phase) + 1) / 2  # 0..1 breathing
        glow_alpha = int(110 + pulse * 110)
        glow_size_boost = int(18 + pulse * 10)
        glow_surf = pygame.Surface(
            (rect.width + glow_size_boost * 2, rect.height + glow_size_boost * 2),
            pygame.SRCALPHA,
        )
        pygame.draw.rect(
            glow_surf,
            (*ACCENT_COLOR, glow_alpha),
            glow_surf.get_rect(),
            width=8,
            border_radius=TILE_CORNER_RADIUS + glow_size_boost,
        )
        screen.blit(glow_surf, (rect.x - glow_size_boost, rect.y - glow_size_boost))

    # Slight vertical gradient fill inside the tile for a "glassy" look
    tile_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    base_r, base_g, base_b = color
    lighter = tuple(min(255, c + 35) for c in (base_r, base_g, base_b))
    darker = tuple(max(0, c - 35) for c in (base_r, base_g, base_b))
    for y in range(rect.height):
        t = y / max(1, rect.height - 1)
        r = int(lighter[0] + (darker[0] - lighter[0]) * t)
        g = int(lighter[1] + (darker[1] - lighter[1]) * t)
        b = int(lighter[2] + (darker[2] - lighter[2]) * t)
        pygame.draw.line(tile_surf, (r, g, b), (0, y), (rect.width, y))

    # Mask the gradient into rounded-corner shape
    mask_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(
        mask_surf, (255, 255, 255), mask_surf.get_rect(), border_radius=TILE_CORNER_RADIUS
    )
    tile_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    screen.blit(tile_surf, rect.topleft)

    # Border
    border_color = (255, 255, 255) if selected else (255, 255, 255)
    border_width = 3 if selected else 1
    border_alpha = 255 if selected else 60
    border_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(
        border_surf,
        (*border_color, border_alpha),
        border_surf.get_rect(),
        width=border_width,
        border_radius=TILE_CORNER_RADIUS,
    )
    screen.blit(border_surf, rect.topleft)


def draw_selection_underline(screen, x_center, y, width, glow_phase):
    """A slim glowing bar beneath the selected tile that eases into
    position -- the 'console UI' signature touch."""
    pulse = (math.sin(glow_phase * 1.3) + 1) / 2
    alpha = int(160 + pulse * 80)
    bar_surf = pygame.Surface((width, 6), pygame.SRCALPHA)
    pygame.draw.rect(
        bar_surf, (*ACCENT_COLOR, alpha), bar_surf.get_rect(), border_radius=3
    )
    screen.blit(bar_surf, (x_center - width // 2, y))


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    pygame.init()
    pygame.display.set_caption("Console Launcher")

    # Optional joystick support -- safe even with no gamepad connected
    pygame.joystick.init()
    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for js in joysticks:
        js.init()

    # Boot straight into fullscreen, no windowed flash first
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    is_fullscreen = True

    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("arial", 30, bold=True)
    font_big = pygame.font.SysFont("arial", 56, bold=True)
    font_small = pygame.font.SysFont("arial", 22)
    font_hint = pygame.font.SysFont("arial", 18)
    fonts = (font_big, font_small, font_hint)

    # Optional click sound; stays silent if no audio device / file available.
    click_sound = None
    try:
        pygame.mixer.init()
        # Point this at a real .wav/.ogg you own to enable sound on click:
        # click_sound = pygame.mixer.Sound("click.wav")
    except Exception as e:
        print(f"[Launcher] Audio unavailable: {e}")

    load_app_images(apps, (TILE_WIDTH - 70, TILE_HEIGHT - 100))

    selected_index = 0
    tile_scales = [1.0 for _ in apps]          # animated per-tile scale
    underline_x = 0.0                          # animated underline position
    glow_phase = 0.0
    hints_visible = False                      # hidden by default per request

    particles = make_particles(*screen.get_size(), PARTICLE_COUNT)

    # Joystick axis needs a deadzone + cooldown so one tilt doesn't repeat-fire
    joystick_cooldown = 0
    JOYSTICK_DEADZONE = 0.5
    JOYSTICK_COOLDOWN_FRAMES = 12

    running = True
    while running:
        dt_ms = clock.tick(FPS)
        dt_seconds = dt_ms / 1000.0
        glow_phase += 0.10

        # ---------------- EVENT HANDLING ----------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_F11:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode(
                            DEFAULT_WINDOWED_SIZE, pygame.RESIZABLE
                        )
                    particles = make_particles(*screen.get_size(), PARTICLE_COUNT)

                elif event.key == pygame.K_h:
                    hints_visible = not hints_visible

                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    selected_index = (selected_index - 1) % len(apps)
                    if click_sound:
                        click_sound.play()

                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    selected_index = (selected_index + 1) % len(apps)
                    if click_sound:
                        click_sound.play()

                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if click_sound:
                        click_sound.play()
                    # Hand the live window straight to the app's own function.
                    apps[selected_index]["on_open"](screen, clock, fonts)

            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == 0:  # "A" on most Xbox/PS-style mappings
                    if click_sound:
                        click_sound.play()
                    apps[selected_index]["on_open"](screen, clock, fonts)

        # ---------------- JOYSTICK AXIS (continuous, polled) ----------------
        if joysticks and joystick_cooldown == 0:
            axis_x = joysticks[0].get_axis(0)
            if axis_x < -JOYSTICK_DEADZONE:
                selected_index = (selected_index - 1) % len(apps)
                joystick_cooldown = JOYSTICK_COOLDOWN_FRAMES
            elif axis_x > JOYSTICK_DEADZONE:
                selected_index = (selected_index + 1) % len(apps)
                joystick_cooldown = JOYSTICK_COOLDOWN_FRAMES
        if joystick_cooldown > 0:
            joystick_cooldown -= 1

        # ---------------- LAYOUT ----------------
        screen_w, screen_h = screen.get_size()
        total_row_width = len(apps) * TILE_WIDTH + (len(apps) - 1) * TILE_GAP
        row_start_x = (screen_w - total_row_width) // 2
        row_y = (screen_h - TILE_HEIGHT) // 2

        # ---------------- ANIMATION EASING ----------------
        for i in range(len(apps)):
            target_scale = SELECTED_SCALE if i == selected_index else 1.0
            tile_scales[i] += (target_scale - tile_scales[i]) * ANIMATION_SPEED

        target_underline_x = row_start_x + selected_index * (TILE_WIDTH + TILE_GAP) + TILE_WIDTH / 2
        underline_x += (target_underline_x - underline_x) * ANIMATION_SPEED

        # ---------------- DRAWING ----------------
        draw_gradient_background(screen, BG_TOP_COLOR, BG_BOTTOM_COLOR)
        update_and_draw_particles(screen, particles, dt_seconds, screen_w, screen_h)

        # Header with accent-colored accent dot
        header_surf = font_title.render("HOME", True, TEXT_COLOR)
        screen.blit(header_surf, (50, 40))
        pygame.draw.circle(screen, ACCENT_COLOR, (40, 54), 6)

        for i, app in enumerate(apps):
            base_x = row_start_x + i * (TILE_WIDTH + TILE_GAP)
            base_y = row_y

            scale = tile_scales[i]
            width = int(TILE_WIDTH * scale)
            height = int(TILE_HEIGHT * scale)
            x = base_x - (width - TILE_WIDTH) // 2
            y = base_y - (height - TILE_HEIGHT) // 2

            tile_rect = pygame.Rect(x, y, width, height)
            is_selected = i == selected_index

            draw_tile(screen, tile_rect, app["color"], is_selected, glow_phase)

            if app.get("image_surface") is not None:
                icon = app["image_surface"]
                icon_rect = icon.get_rect(center=(tile_rect.centerx, tile_rect.centery - 20))
                screen.blit(icon, icon_rect)

            name_surf = font_small.render(app["name"], True, TEXT_COLOR)
            name_rect = name_surf.get_rect(center=(tile_rect.centerx, tile_rect.bottom - 30))
            screen.blit(name_surf, name_rect)

        # Glowing underline indicator that glides to the selected tile
        draw_selection_underline(
            screen, int(underline_x), row_y + TILE_HEIGHT + 26, TILE_WIDTH - 40, glow_phase
        )

        # Hints -- hidden by default, toggle with H
        if hints_visible:
            hint_text = "<- A | D -> move    ENTER launch    H hints    F11 fullscreen    ESC quit"
            hint_surf = font_hint.render(hint_text, True, SUBTEXT_COLOR)
            screen.blit(hint_surf, (50, screen_h - 50))
        else:
            tiny_surf = font_hint.render("H", True, (90, 90, 100))
            screen.blit(tiny_surf, (50, screen_h - 36))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()