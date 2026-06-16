import sys
import pygame 

from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, TIME_SPEEDS, DEFAULT_SPEED_INDEX, GAME_MINUTES_PER_SECOND_BASE,
)
from node import Node
from ui import DashboardUI

def main():
    pygame.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    node = Node()
    ui = DashboardUI(screen)
    speed_index = DEFAULT_SPEED_INDEX

    running = True
    while running:
        dt_real = clock.tick(FPS) / 1000.0 

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            result = ui.handle_event(event, node)
            if result == "restart":
                node = Node()
                ui = DashboardUI(screen)
                speed_index = DEFAULT_SPEED_INDEX
            elif result and result.startswith("speed:"):
                idx = int(result.split(":")[1])
                speed_index = idx

        # Simulation update:
        speed_mult = TIME_SPEEDS[speed_index] * GAME_MINUTES_PER_SECOND_BASE
        node.update(dt_real, speed_mult)

        # Render:
        ui.draw(node, speed_index)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()