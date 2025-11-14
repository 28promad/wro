# python
# rover_simulation_improved.py

import pygame
import randomw
import math

# --- Constants ---
WIDTH, HEIGHT = 800, 600
ROVER_RADIUS = 15
SPEED = 2.0
TURN_ANGLE = 25
SENSOR_RANGE = 50

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Rover Simulation")
clock = pygame.time.Clock()

# --- Environment ---
walls = [
    pygame.Rect(100, 100, 600, 20),
    pygame.Rect(100, 480, 600, 20),
    pygame.Rect(100, 120, 20, 360),
    pygame.Rect(680, 120, 20, 360),
]
for _ in range(5):
    x, y = random.randint(150, 650), random.randint(150, 450)
    walls.append(pygame.Rect(x, y, 40, 40))

# --- Rover ---
x, y = WIDTH // 2, HEIGHT // 2
angle = 0
stuck_counter = 0  # counts how long rover’s been stuck
backing_up = False
backup_steps = 0

def move_forward(x, y, angle, speed):
    x += speed * math.cos(math.radians(angle))
    y -= speed * math.sin(math.radians(angle))
    return x, y

def sense_obstacle(x, y, angle):
    """Ultrasonic-like ray"""
    for dist in range(SENSOR_RANGE):
        test_x = x + dist * math.cos(math.radians(angle))
        test_y = y - dist * math.sin(math.radians(angle))
        for wall in walls:
            if wall.collidepoint(test_x, test_y):
                return True
    return False

running = True
while running:
    screen.fill((20, 20, 30))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    obstacle_detected = sense_obstacle(x, y, angle)
    rover_rect = pygame.Rect(x - ROVER_RADIUS, y - ROVER_RADIUS, ROVER_RADIUS*2, ROVER_RADIUS*2)

    # --- Behavior Logic ---
    if backing_up:
        # Reverse for a few frames
        x, y = move_forward(x, y, angle + 180, SPEED)
        backup_steps -= 1
        if backup_steps <= 0:
            # Done backing up — now turn away randomly
            angle += random.choice([-TURN_ANGLE*2, TURN_ANGLE*2])
            backing_up = False
    elif obstacle_detected:
        # If obstacle is too close, initiate reverse
        stuck_counter += 1
        if stuck_counter > 10:
            backing_up = True
            backup_steps = 20
            stuck_counter = 0
        else:
            # Minor angle adjustment if just lightly blocked
            angle += random.choice([-TURN_ANGLE, TURN_ANGLE])
    else:
        # Move forward normally
        x, y = move_forward(x, y, angle, SPEED)
        stuck_counter = 0

    # Collision check
    for wall in walls:
        if rover_rect.colliderect(wall):
            backing_up = True
            backup_steps = 20

    # --- Drawing ---
    for wall in walls:
        pygame.draw.rect(screen, (120, 120, 120), wall)
    pygame.draw.circle(screen, (0, 200, 255), (int(x), int(y)), ROVER_RADIUS)

    # Sensor ray
    sensor_end = (
        x + SENSOR_RANGE * math.cos(math.radians(angle)),
        y - SENSOR_RANGE * math.sin(math.radians(angle)),
    )
    pygame.draw.line(screen, (255, 100, 100), (x, y), sensor_end, 2)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
