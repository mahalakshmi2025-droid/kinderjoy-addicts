import pygame
import math
import sys

# CONFIG

WIDTH, HEIGHT = 1024, 768
FPS = 60

TILE_SIZE = 64  

FOV = math.pi / 3
NUM_RAYS = 300 
MAX_DEPTH = 1000

PLAYER_SPEED = 2.5
MOUSE_SENSITIVITY = 0.003  
FLASHLIGHT_RADIUS = 300

INSANITY_RATE = 0.005      
INSANITY_IN_DARK = 0.02
INSANITY_NEAR_MONSTER = 0.05
INSANITY_OBJECTIVE_REDUCTION = 15

MONSTER_SPEED = 1.5

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_GRAY = (10, 10, 10)
GRAY = (100, 100, 100)
RED = (255, 0, 0)
GREEN = (0, 200, 0)
YELLOW = (255, 255, 0)
DARK_YELLOW = (100, 100, 0)
DARK_GREEN = (0, 100, 0)
BLUE = (0, 0, 255)

# 0 = empty space
# 1 = wall
# 2 = light switch
# 3 = objective

GAME_MAP = [
    [1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,3,0,2,1],
    [1,0,1,0,1,1,1,0,1,0,0,1],
    [1,0,1,0,0,0,1,0,1,0,0,1],
    [1,0,1,1,1,0,1,0,1,1,0,1],
    [1,0,0,0,1,0,0,0,0,1,0,1],
    [1,0,1,0,1,1,1,1,0,1,0,1],
    [1,0,1,0,0,0,0,1,0,1,3,1],
    [1,0,1,1,1,1,0,1,0,1,0,1],
    [1,0,0,0,0,0,0,1,0,0,0,1],
    [1,2,0,1,1,1,0,0,0,2,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1],
]

MAP_WIDTH = len(GAME_MAP[0])
MAP_HEIGHT = len(GAME_MAP)
MAP_PIX_WIDTH = MAP_WIDTH * TILE_SIZE
MAP_PIX_HEIGHT = MAP_HEIGHT * TILE_SIZE

pygame.init()
infoObject = pygame.display.Info()
infoObject = pygame.display.Info()
WIDTH, HEIGHT = infoObject.current_w, infoObject.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Haunted Mansion 3D")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 24)
pygame.event.set_grab(True)
pygame.mouse.set_visible(False)

player_x = TILE_SIZE * 1.5
player_y = TILE_SIZE * 1.5
player_angle = 0.0

flashlight_on = False
lights_on = False

insanity = 0.0

def find_objectives_and_switches():
    objs = []
    switches = []
    for y,row in enumerate(GAME_MAP):
        for x,tile in enumerate(row):
            if tile == 3:
                objs.append((x, y))
            elif tile == 2:
                switches.append((x, y))
    return objs, switches

objectives, light_switches = find_objectives_and_switches()

collected_objectives = set()

monster_pos = [TILE_SIZE * (MAP_WIDTH - 2) + TILE_SIZE // 2,
               TILE_SIZE * (MAP_HEIGHT - 2) + TILE_SIZE // 2]
monster_active = True


def is_wall(x, y):
    if x < 0 or x >= MAP_WIDTH or y < 0 or y >= MAP_HEIGHT:
        return True
    return GAME_MAP[y][x] == 1

def is_switch(x, y):
    if x < 0 or x >= MAP_WIDTH or y < 0 or y >= MAP_HEIGHT:
        return False
    return GAME_MAP[y][x] == 2

def is_objective(x, y):
    if x < 0 or x >= MAP_WIDTH or y < 0 or y >= MAP_HEIGHT:
        return False
    return GAME_MAP[y][x] == 3

def distance(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)

def cast_rays():
    rays = []
    start_angle = player_angle - FOV / 2
    for ray in range(NUM_RAYS):
        ray_angle = start_angle + ray * (FOV / NUM_RAYS)
        sin_a = math.sin(ray_angle)
        cos_a = math.cos(ray_angle)

        depth = 0
        x_hit, y_hit = 0, 0
        hit = False

        delta_dist_x = abs(1 / cos_a) if cos_a != 0 else 1e30
        delta_dist_y = abs(1 / sin_a) if sin_a != 0 else 1e30

        map_x = int(player_x // TILE_SIZE)
        map_y = int(player_y // TILE_SIZE)

        if cos_a < 0:
            step_x = -1
            side_dist_x = (player_x - map_x * TILE_SIZE) * delta_dist_x / TILE_SIZE
        else:
            step_x = 1
            side_dist_x = ((map_x + 1) * TILE_SIZE - player_x) * delta_dist_x / TILE_SIZE

        if sin_a < 0:
            step_y = -1
            side_dist_y = (player_y - map_y * TILE_SIZE) * delta_dist_y / TILE_SIZE
        else:
            step_y = 1
            side_dist_y = ((map_y + 1) * TILE_SIZE - player_y) * delta_dist_y / TILE_SIZE

        side = 0  

        while not hit and depth < MAX_DEPTH:
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x
                map_x += step_x
                side = 0
            else:
                side_dist_y += delta_dist_y
                map_y += step_y
                side = 1
            if is_wall(map_x, map_y):
                hit = True

        if side == 0:
            depth = (map_x - player_x / TILE_SIZE + (1 - step_x) / 2) / cos_a
        else:
            depth = (map_y - player_y / TILE_SIZE + (1 - step_y) / 2) / sin_a

        depth *= TILE_SIZE
        depth_corrected = depth * math.cos(player_angle - ray_angle)

        rays.append((depth_corrected, ray_angle, map_x, map_y, side))

    return rays

def draw_3d_scene():
    floor_color = (30, 30, 30) if not lights_on else (80, 80, 80)
    ceiling_color = (10, 10, 10) if not lights_on else (120, 120, 120)
    pygame.draw.rect(screen, ceiling_color, (0, 0, WIDTH, HEIGHT // 2))
    pygame.draw.rect(screen, floor_color, (0, HEIGHT // 2, WIDTH, HEIGHT // 2))

    rays = cast_rays()
    for i, (depth, ray_angle, map_x, map_y, side) in enumerate(rays):
        if depth == 0:
            continue
        wall_height = (TILE_SIZE * 1000) / (depth + 0.0001)
        shade = 255 / (1 + depth * depth * 0.00002)
        if side == 1:
            shade *= 0.7  

        if not lights_on and not flashlight_on:
            shade *= 0.25 

        shade = max(0, min(255, shade))
        color = (shade, shade, shade)

        rect = pygame.Rect(i * (WIDTH // NUM_RAYS),
                           HEIGHT // 2 - wall_height // 2,
                           (WIDTH // NUM_RAYS) + 1,
                           wall_height)
        pygame.draw.rect(screen, color, rect)

    return rays

def move_player(dx, dy):
    global player_x, player_y
    new_x = player_x + dx
    new_y = player_y + dy

    if not is_wall(int(new_x // TILE_SIZE), int(player_y // TILE_SIZE)):
        player_x = new_x
    if not is_wall(int(player_x // TILE_SIZE), int(new_y // TILE_SIZE)):
        player_y = new_y

def check_objectives():
    global insanity, collected_objectives
    px_tile = int(player_x // TILE_SIZE)
    py_tile = int(player_y // TILE_SIZE)
    if is_objective(px_tile, py_tile) and (px_tile, py_tile) not in collected_objectives:
        collected_objectives.add((px_tile, py_tile))
        insanity = max(0, insanity - INSANITY_OBJECTIVE_REDUCTION)
        print(f"Objective collected at ({px_tile}, {py_tile})!")

def check_light_switch():
    global lights_on
    px_tile = int(player_x // TILE_SIZE)
    py_tile = int(player_y // TILE_SIZE)
    if is_switch(px_tile, py_tile):
        lights_on = True

def move_monster(rays):
    global monster_pos

    if not monster_active:
        return

    dx = player_x - monster_pos[0]
    dy = player_y - monster_pos[1]
    dist = math.hypot(dx, dy)
    if dist == 0:
        return

    nx = dx / dist
    ny = dy / dist

    new_x = monster_pos[0] + nx * MONSTER_SPEED
    new_y = monster_pos[1] + ny * MONSTER_SPEED

    if not is_wall(int(new_x // TILE_SIZE), int(monster_pos[1] // TILE_SIZE)):
        monster_pos[0] = new_x
    if not is_wall(int(monster_pos[0] // TILE_SIZE), int(new_y // TILE_SIZE)):
        monster_pos[1] = new_y

def check_monster_proximity():
    global insanity
    dist = distance(player_x, player_y, monster_pos[0], monster_pos[1])
    if dist < 150:
        insanity += INSANITY_NEAR_MONSTER
    if dist < 25:
        print("Monster caught you! Restarting level...")
        reset_game()

def reset_game():
    global player_x, player_y, player_angle, insanity, collected_objectives, monster_pos, lights_on, flashlight_on
    player_x = TILE_SIZE * 1.5
    player_y = TILE_SIZE * 1.5
    player_angle = 0.0
    insanity = 0.0
    collected_objectives = set()
    monster_pos[0] = TILE_SIZE * (MAP_WIDTH - 2) + TILE_SIZE // 2
    monster_pos[1] = TILE_SIZE * (MAP_HEIGHT - 2) + TILE_SIZE // 2
    lights_on = False
    flashlight_on = False

UI_X = 50
UI_Y = 25

def draw_ui():
    pygame.draw.rect(screen, DARK_GRAY, (UI_X, UI_Y, 250, 25))
    fill_width = (insanity / 100) * 250
    pygame.draw.rect(screen, RED, (UI_X, UI_Y, fill_width, 25))
    insanity_text = font.render(f"Insanity: {int(insanity)}%", True, WHITE)
    screen.blit(insanity_text, (UI_X + 5, UI_Y))

    left = len(objectives) - len(collected_objectives)
    obj_text = font.render(f"Sanity potions: {left}", True, WHITE)
    screen.blit(obj_text, (UI_X, UI_Y + 35))

    lights_text = font.render(f"Lights: {'ON' if lights_on else 'OFF'}", True, WHITE)
    screen.blit(lights_text, (UI_X, UI_Y + 65))

    flash_text = font.render(f"Flashlight: {'ON' if flashlight_on else 'OFF'}", True, WHITE)
    screen.blit(flash_text, (UI_X, UI_Y + 95))

def draw_flashlight_effect():
    if flashlight_on:
        flashlight_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(flashlight_surface, (255, 255, 200, 120), (WIDTH // 2, HEIGHT // 2), FLASHLIGHT_RADIUS)
        screen.blit(flashlight_surface, (0, 0))

def can_see_monster(rays):
    dx = monster_pos[0] - player_x
    dy = monster_pos[1] - player_y
    angle_to_monster = math.atan2(dy, dx)

    def normalize_angle(angle):
        while angle < -math.pi:
            angle += 2 * math.pi
        while angle > math.pi:
            angle -= 2 * math.pi
        return angle

    angle_diff = normalize_angle(angle_to_monster - player_angle)
    half_fov = FOV / 2
    if abs(angle_diff) > half_fov:
        return False  

    ray_index = int((angle_diff + half_fov) / FOV * NUM_RAYS)
    if ray_index < 0 or ray_index >= len(rays):
        return False

    depth_to_monster = distance(player_x, player_y, monster_pos[0], monster_pos[1])
    ray_depth = rays[ray_index][0]

    return depth_to_monster < ray_depth + 10 

def draw_monster(rays):
    if not monster_active:
        return

    if can_see_monster(rays):
        dist = distance(player_x, player_y, monster_pos[0], monster_pos[1])
        size = (TILE_SIZE * 800) / (dist + 0.0001)
        shade = 255 / (1 + dist * dist * 0.00002)
        shade = max(50, min(255, shade))

        monster_color = (shade, 0, 0)

        dx = monster_pos[0] - player_x
        dy = monster_pos[1] - player_y
        angle_to_monster = math.atan2(dy, dx)
        angle_diff = angle_to_monster - player_angle
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi

        half_fov = FOV / 2
        screen_x = int((0.5 + angle_diff / FOV) * WIDTH)

        rect = pygame.Rect(screen_x - size // 2, HEIGHT // 2 - size // 2, size, size)
        pygame.draw.rect(screen, monster_color, rect)

def draw_objectives_and_switches(rays):
    for (ox, oy) in objectives:
        if (ox, oy) in collected_objectives:
            continue  
        draw_sprite(ox, oy, GREEN, rays)

    for (sx, sy) in light_switches:
        draw_sprite(sx, sy, YELLOW, rays)

def draw_sprite(mx, my, color, rays):
    sprite_x = (mx + 0.5) * TILE_SIZE
    sprite_y = (my + 0.5) * TILE_SIZE
    dist = distance(player_x, player_y, sprite_x, sprite_y)
    if dist > MAX_DEPTH:
        return  

    dx = sprite_x - player_x
    dy = sprite_y - player_y
    angle_to_sprite = math.atan2(dy, dx)
    angle_diff = angle_to_sprite - player_angle
    while angle_diff < -math.pi:
        angle_diff += 2 * math.pi
    while angle_diff > math.pi:
        angle_diff -= 2 * math.pi

    if abs(angle_diff) > FOV / 2:
        return
    
    ray_index = int((angle_diff + FOV / 2) / FOV * NUM_RAYS)
    if ray_index < 0 or ray_index >= len(rays):
        return

    if dist > rays[ray_index][0]:
        return

    size = (TILE_SIZE * 800) / (dist + 0.0001)
    screen_x = int((0.5 + angle_diff / FOV) * WIDTH)
    rect = pygame.Rect(screen_x - size // 4, HEIGHT // 2 - size // 4, size // 2, size // 2)
    pygame.draw.rect(screen, color, rect)

def main():
    global player_angle, flashlight_on, insanity

    reset_game()

    alt_pressed = False

    while True:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.VIDEORESIZE:
                global WIDTH, HEIGHT, screen
                WIDTH, HEIGHT = event.w, event.h
                screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LALT or event.key == pygame.K_RALT:
                    alt_pressed = True
                    pygame.mouse.set_visible(True)
                    pygame.event.set_grab(False)
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_LALT or event.key == pygame.K_RALT:
                    alt_pressed = False
                    pygame.mouse.set_visible(False)
                    pygame.event.set_grab(True)


        mx, my = pygame.mouse.get_rel()
        player_angle += mx * MOUSE_SENSITIVITY
        player_angle %= 2 * math.pi

        keys = pygame.key.get_pressed()
        dx = 0
        dy = 0

        if keys[pygame.K_w]:
            dx += math.cos(player_angle) * PLAYER_SPEED
            dy += math.sin(player_angle) * PLAYER_SPEED
        if keys[pygame.K_s]:
            dx -= math.cos(player_angle) * PLAYER_SPEED
            dy -= math.sin(player_angle) * PLAYER_SPEED
        if keys[pygame.K_d]:
            dx -= math.sin(player_angle) * PLAYER_SPEED  
            dy += math.cos(player_angle) * PLAYER_SPEED  
        if keys[pygame.K_a]:
            dx += math.sin(player_angle) * PLAYER_SPEED  
            dy -= math.cos(player_angle) * PLAYER_SPEED  

        move_player(dx, dy)

        if keys[pygame.K_f]:
            flashlight_on = not flashlight_on
            pygame.time.wait(150)  

        insanity += INSANITY_RATE


        px_tile = int(player_x // TILE_SIZE)
        py_tile = int(player_y // TILE_SIZE)

        if not lights_on and not flashlight_on:
            insanity += INSANITY_IN_DARK


        check_light_switch()
        check_objectives()
        rays = cast_rays()
        move_monster(rays)
        check_monster_proximity()

        if (len(collected_objectives) == len(objectives) and lights_on) or lights_on:

            screen.fill(BLACK)
            win_text = font.render("Level Complete! You turned on the lights and collected all objectives!", True, GREEN)
            screen.blit(win_text, (WIDTH // 2 - win_text.get_width() // 2, HEIGHT // 2))
            pygame.display.flip()
            pygame.time.wait(5000)
            reset_game()
            continue

        if insanity >= 100:

            screen.fill(BLACK)
            lose_text = font.render("You passed out from insanity! Restarting level...", True, RED)
            screen.blit(lose_text, (WIDTH // 2 - lose_text.get_width() // 2, HEIGHT // 2))
            pygame.display.flip()
            pygame.time.wait(3000)
            reset_game()
            continue


        rays = cast_rays()
        draw_3d_scene()
        draw_objectives_and_switches(rays)
        draw_monster(rays)
        draw_flashlight_effect()
        draw_ui()

        pygame.display.flip()

if __name__ == "__main__":
    main()
