import pygame
import random
import time
import os
from pygame import gfxdraw

pygame.init()
pygame.mixer.init()

WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Retro Racing")

ASPHALT = (50, 50, 50)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
RED = (255, 40, 40)
BLUE = (30, 144, 255)
GREEN = (0, 200, 0)
GRAY = (128, 128, 128)

def load_sound(name):
    try:
        sound = pygame.mixer.Sound(name)
        return sound
    except pygame.error:
        print(f"Couldn't load sound {name}")
        return None

engine_sound = load_sound("modern_engine.wav")
#crash_sound = load_sound("modern_crash.wav")
crash_sound = load_sound("crash.wav")
drift_sound = load_sound("drift.wav")
nitro_sound = load_sound("nitro.wav")


if engine_sound:
    engine_sound.set_volume(0.3)
    engine_sound.play(-1)

def load_image(name, width, height):
    try:
        image = pygame.image.load(name)
        image = pygame.transform.scale(image, (width, height))
        reflection = pygame.transform.flip(image, False, True)
        reflection.set_alpha(50) 
        
        mask = pygame.mask.from_surface(image)
        bbox = mask.get_bounding_rects()
        
        if bbox:
            real_rect = bbox[0].unionall(bbox)
            collision_rect = pygame.Rect(real_rect)
            offset_x = collision_rect.x
            offset_y = collision_rect.y
            actual_width = collision_rect.width
            actual_height = collision_rect.height
        else:
            offset_x = 0
            offset_y = 0
            actual_width = width
            actual_height = height
            
        return image, reflection, actual_width, actual_height, offset_x, offset_y
    except pygame.error:
        print(f"Couldn't load image {name}")
        surface = pygame.Surface((width, height))
        surface.fill(BLUE if "player" in name else RED)
        return surface, surface, width, height, 0, 0

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.size = random.randint(2, 5)
        self.speed = random.randint(2, 6)
        self.life = random.randint(20, 40)

    def update(self):
        self.y += self.speed
        self.life -= 1
        self.size = max(0, self.size - 0.1)

    def draw(self, surface):
        alpha = int((self.life / 40) * 255)
        particle_surface = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(particle_surface, (*self.color, alpha), (self.size, self.size), self.size)
        surface.blit(particle_surface, (self.x - self.size, self.y - self.size))

class ModernCar:
    def __init__(self, x, y, width, height, is_player=False):
        self.width = width
        self.height = height
        self.x = x
        self.y = y
        self.base_speed = 5 if is_player else random.uniform(3, 7)
        self.speed = self.base_speed
        self.acceleration = 0
        self.max_speed = 12 if is_player else 8
        self.is_player = is_player
        
        image_name = "player_car.png" if is_player else f"enemy_car_{random.randint(1,4)}.png"
        self.image, self.reflection, self.actual_width, self.actual_height, self.offset_x, self.offset_y = load_image(
            image_name, width, height
        )
        
        self.nitro = 100 if is_player else 0
        self.is_drifting = False
        self.drift_angle = 0
        self.particles = []

    def update(self):
        if self.is_player:
            if self.nitro < 100:
                self.nitro += 0.1
                
            for particle in self.particles[:]:
                particle.update()
                if particle.life <= 0:
                    self.particles.remove(particle)
                    
            if random.random() < 0.3:
                self.particles.append(Particle(
                    self.x + self.width // 2,
                    self.y + self.height,
                    (100, 100, 100)
                ))
        else:
            self.y += self.speed

    def draw(self, surface):
        for particle in self.particles:
            particle.draw(surface)
            
        if self.is_drifting:
            rotated_image = pygame.transform.rotate(self.image, self.drift_angle)
            surface.blit(rotated_image, (self.x, self.y))
        else:
            surface.blit(self.image, (self.x, self.y))
            
        if self.is_player and self.nitro > 0:
            pygame.draw.rect(surface, (50, 50, 50), (self.x, self.y - 10, self.width, 5))
            pygame.draw.rect(surface, BLUE, (self.x, self.y - 10, self.width * (self.nitro/100), 5))

class ModernRacingGame:
    def __init__(self):
        self.reset_game()
        
    def reset_game(self):
        self.score = 0
        self.game_over = False
        self.player = ModernCar(
            WINDOW_WIDTH // 2,
            WINDOW_HEIGHT - 150,
            80,
            140,
            True
        )
        self.enemies = []
        self.particles = []
        self.start_time = time.time()
        self.last_speed_increase = self.start_time 
        self.speed_multiplier = 1.0 
        self.distance = 0
        
        self.boost_available = True
        self.boost_cooldown = 0
        self.lane_markings = [(WINDOW_WIDTH//4, 0), (WINDOW_WIDTH//2, 0), (3*WINDOW_WIDTH//4, 0)]

    def handle_input(self):
        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_LEFT] and self.player.x > 0:
            self.player.x -= self.player.speed
            self.player.is_drifting = True
            self.player.drift_angle = 15
            if drift_sound:
                drift_sound.play()
        elif keys[pygame.K_RIGHT] and self.player.x < WINDOW_WIDTH - self.player.width:
            self.player.x += self.player.speed
            self.player.is_drifting = True
            self.player.drift_angle = -15
            if drift_sound:
                drift_sound.play()
        else:
            self.player.is_drifting = False
            if drift_sound:
                drift_sound.stop()
            self.player.drift_angle = 0
            
        if keys[pygame.K_SPACE] and self.player.nitro > 0:
            self.player.speed = self.player.max_speed * 1.5
            self.player.nitro -= 1
            if nitro_sound:
                nitro_sound.play()
            for _ in range(3):
                self.particles.append(Particle(
                    self.player.x + random.randint(0, self.player.width),
                    self.player.y + self.player.height,
                    (255, 165, 0)
                ))
        else:
            self.player.speed = self.player.max_speed

    def update(self):
        if self.game_over:
            return

        current_time = time.time()
        
        if current_time - self.last_speed_increase >= 5:
            self.speed_multiplier += 0.2 
            self.last_speed_increase = current_time
            
            for enemy in self.enemies:
                enemy.speed = enemy.base_speed * self.speed_multiplier

        self.handle_input()
        self.player.update()
        
        self.distance += self.player.speed
        for i, marking in enumerate(self.lane_markings):
            new_y = (marking[1] + self.player.speed) % WINDOW_HEIGHT
            self.lane_markings[i] = (marking[0], new_y)
            
        if random.random() < 0.02:
            enemy = ModernCar(
                random.randint(0, WINDOW_WIDTH - 80),
                -150,
                160,
                160
            )
            enemy.speed = enemy.base_speed * self.speed_multiplier
            self.enemies.append(enemy)
            
        for enemy in self.enemies[:]:
            enemy.update()
            if enemy.y > WINDOW_HEIGHT:
                self.enemies.remove(enemy)
                self.score += 1
            elif self.check_collision(self.player, enemy):
                self.game_over = True
                if crash_sound:
                    crash_sound.play()
                if engine_sound:
                    engine_sound.stop()

        for particle in self.particles[:]:
            particle.update()
            if particle.life <= 0:
                self.particles.remove(particle)

    def check_collision(self, car1, car2):
        rect1 = pygame.Rect(
            car1.x + car1.offset_x,
            car1.y + car1.offset_y,
            car1.actual_width,
            car1.actual_height
        )
        rect2 = pygame.Rect(
            car2.x + car2.offset_x,
            car2.y + car2.offset_y,
            car2.actual_width,
            car2.actual_height
        )
        return rect1.colliderect(rect2)

    def draw(self):
        window.fill(ASPHALT)
        
        for x, y in self.lane_markings:
            pygame.draw.rect(window, WHITE, (x - 5, y, 10, 40))
            
        for particle in self.particles:
            particle.draw(window)
            
        self.player.draw(window)
        for enemy in self.enemies:
            enemy.draw(window)
            
        self.draw_hud()
        
        if self.game_over:
            self.draw_game_over()
            
        pygame.display.flip()

    def draw_hud(self):
        font = pygame.font.Font(None, 48)

        score_text = font.render(f"Score: {self.score}", True, WHITE)
        window.blit(score_text, (20, 20))
        
        speed_text = font.render(f"Speed: {self.speed_multiplier:.1f}x", True, WHITE)
        window.blit(speed_text, (20, 70))
        
        speed = int((self.player.speed / self.player.max_speed) * 200)
        pygame.draw.rect(window, GRAY, (20, WINDOW_HEIGHT - 40, 200, 20))
        pygame.draw.rect(window, GREEN, (20, WINDOW_HEIGHT - 40, speed, 20))
        
        nitro_text = font.render("NITRO", True, BLUE)
        window.blit(nitro_text, (WINDOW_WIDTH - 120, 20))
        pygame.draw.rect(window, GRAY, (WINDOW_WIDTH - 120, 50, 100, 10))
        pygame.draw.rect(window, BLUE, (WINDOW_WIDTH - 120, 50, self.player.nitro, 10))

    def draw_game_over(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        window.blit(overlay, (0, 0))
        
        font = pygame.font.Font(None, 72)
        game_over_text = font.render("GAME OVER (JATT DON'T CARE)", True, WHITE)
        score_text = font.render(f"Final Score: {self.score}", True, WHITE)
        restart_text = font.render("Press SPACE to restart", True, WHITE)
        
        window.blit(game_over_text, (WINDOW_WIDTH//2 - game_over_text.get_width()//2, WINDOW_HEIGHT//2 - 100))
        window.blit(score_text, (WINDOW_WIDTH//2 - score_text.get_width()//2, WINDOW_HEIGHT//2))
        window.blit(restart_text, (WINDOW_WIDTH//2 - restart_text.get_width()//2, WINDOW_HEIGHT//2 + 100))

def main():
    clock = pygame.time.Clock()
    game = ModernRacingGame()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and game.game_over:
                if event.key == pygame.K_SPACE:
                    game = ModernRacingGame()
                    if engine_sound:
                        engine_sound.play(-1)
                        
        game.update()
        game.draw()
        clock.tick(60)

    pygame.mixer.quit()
    pygame.quit()

if __name__ == "__main__":
    main()