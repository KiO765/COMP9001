import pygame
import random
import sys
from enum import Enum

# initialize pygame
pygame.init()

# set the game screen
WIDTH, HEIGHT = 1100, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Force_Grey")

# define colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 120, 255)
PURPLE = (128, 0, 128)
GOLD = (255, 215, 0)
ORANGE = (255, 165, 0)
YELLOW = (255, 255, 0)
BROWN = (165, 42, 42)

# type of words
font_large = pygame.font.SysFont('simhei', 36)
font_medium = pygame.font.SysFont('simhei', 28)
font_small = pygame.font.SysFont('simhei', 22)
font_tiny = pygame.font.SysFont('simhei', 18)

# II-magic
class MagicType(Enum):
    FIRE = 1      # burn
    BREAK = 2     # rupture
    SHOCK = 3     # tremor

# I-magic
class MagicAttackMode(Enum):
    NORMAL = 1    # normal attack
    DOUBLE = 2    # double attack
    CHARGE = 3    # charge attack

# state
class StatusEffect:
    def __init__(self, name, duration=0, stacks=0):
        self.name = name
        self.duration = duration  # state duration, 0 means forever-lasting until it triggered
        self.stacks = stacks      # state stacks
    
    def __str__(self):
        return f"{self.name}({self.stacks})"

class Character:
    def __init__(self, name, max_hp, attack, defense, magic_power, physical_resistance=1.0, magic_resistance=1.0):
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self.attack = attack
        self.defense = defense
        self.magic_power = magic_power
        self.physical_resistance = physical_resistance  # physical damage multiplier
        self.magic_resistance = magic_resistance        # magical damage multiplier
        self.alive = True
        self.status_effects = {}  # dictionary of all state
        self.stunned = False      # is shocked or not
    
    def take_damage(self, damage, damage_type="physical"):
        # applying damage based on different damage multiplier
        resistance = self.physical_resistance if damage_type == "physical" else self.magic_resistance
        actual_damage = max(1, int((damage - self.defense) * resistance))
        self.hp -= actual_damage
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return actual_damage
    
    def heal(self, amount):
        heal_amount = min(self.max_hp - self.hp, amount)
        self.hp += heal_amount
        return heal_amount
    
    def is_alive(self):
        return self.alive
    
    def add_status_effect(self, effect_name, duration=0, stacks=1):
        if effect_name in self.status_effects:
            self.status_effects[effect_name].stacks += stacks
            if duration > 0:
                self.status_effects[effect_name].duration = max(
                    self.status_effects[effect_name].duration, duration
                )
        else:
            self.status_effects[effect_name] = StatusEffect(effect_name, duration, stacks)
    
    def remove_status_effect(self, effect_name, stacks=1):
        if effect_name in self.status_effects:
            self.status_effects[effect_name].stacks -= stacks
            if self.status_effects[effect_name].stacks <= 0:
                del self.status_effects[effect_name]
                return True
        return False
    
    def process_status_effects(self):
        effects_log = []
        damage_taken = 0
        
        # dealing with burn state
        if "burn" in self.status_effects:
            burn_stacks = self.status_effects["burn"].stacks
            burn_damage = int(self.max_hp * (burn_stacks * 0.01))
            self.hp -= burn_damage
            damage_taken += burn_damage
            # burn state stacks(s) - 1
            self.remove_status_effect("burn", 1)
            effects_log.append(f"{self.name}affected by the burn，lost{burn_damage}heal points")
            
            if self.hp <= 0:
                self.hp = 0
                self.alive = False
        
        # dealing with state duration
        effects_to_remove = []
        for effect_name, effect in self.status_effects.items():
            if effect.duration > 0:
                effect.duration -= 1
                if effect.duration <= 0:
                    effects_to_remove.append(effect_name)
        
        for effect_name in effects_to_remove:
            del self.status_effects[effect_name]
            effects_log.append(f"{self.name}'s{effect_name}ends.")
        
        return effects_log, damage_taken
    
    def apply_break_effect(self, damage):
        # rupture: every time when getting attcked, lost 1 rupture stack and increase this attack damage based on the rupture state stacks
        if "break" in self.status_effects:
            break_stacks = self.status_effects["break"].stacks
            bonus_damage = break_stacks
            self.remove_status_effect("break", 1)
            return damage + bonus_damage
        return damage
    
    def apply_shock_effect(self, damage, attack_count):
        # tremor: every time when getting attacked, the stack of tremor buff increase 1 
        if "shock" in self.status_effects:
            self.status_effects["shock"].stacks += 1
            # if the stack of tremor buff equal or over 10, the enemy get shocked, next turn it can not do any action and will get double damage
            if self.status_effects["shock"].stacks >= 10:
                self.stunned = True
                return damage * 2
        else:
            self.add_status_effect("shock", 0, 1)
        return damage

class Player(Character):
    def __init__(self):
        super().__init__("Element Master", 120, 15, 5, 25)
        self.magic_points = 60
        self.max_magic_points = 60
        self.charging = False  # is charging or not
        self.charge_turn = 0   # rest of the charging turn
        self.magic_attack_mode = MagicAttackMode.NORMAL  # default magical attack mode
    
    def use_magic(self, cost):
        if self.magic_points >= cost:
            self.magic_points -= cost
            return True
        return False
    
    def restore_magic(self, amount):
        self.magic_points = min(self.max_magic_points, self.magic_points + amount)

class Enemy(Character):
    def __init__(self, name, max_hp, attack, defense, magic_power, physical_resistance=1.0, magic_resistance=1.0):
        super().__init__(name, max_hp, attack, defense, magic_power, physical_resistance, magic_resistance)

class Game:
    def __init__(self):
        self.player = Player()
        # create enemies, each enemy has their own damage multiplier
        self.enemies = [
            Enemy("Goblin", 40, 10, 2, 5, 1.2, 0.8),  # high physical multiplier but low magical multiplier
            Enemy("Orc", 70, 15, 5, 8, 0.8, 1.2),    # low physical multiplier but high magical multiplier
            Enemy("Dragon", 150, 25, 10, 15, 0.7, 0.7)  # both magical and physical multiplier are low but has high heal points
        ]
        self.current_enemy = None
        self.game_state = "start"  # start, battle, player_turn, enemy_turn, victory, defeat
        self.message = ""
        self.battle_log = []
        self.enemy_index = 0
        self.attack_count = 0  # for the count of tremor buff
        self.new_enemy()
    
    def new_enemy(self):
        if self.enemy_index < len(self.enemies):
            self.current_enemy = self.enemies[self.enemy_index]
            self.enemy_index += 1
            self.game_state = "battle"
            self.add_message(f"fall in battle with {self.current_enemy.name}！")
            self.add_message(f"{self.current_enemy.name}'s physical multiplier:{self.current_enemy.physical_resistance}, magical multiplier:{self.current_enemy.magic_resistance}")
        else:
            self.game_state = "victory"
    
    def player_attack(self):
        damage = self.player.attack + random.randint(-3, 3)
        
        # applying rupture buff
        damage = self.current_enemy.apply_break_effect(damage)
        
        # applying tremor buff
        self.attack_count += 1
        damage = self.current_enemy.apply_shock_effect(damage, self.attack_count)
        
        actual_damage = self.current_enemy.take_damage(damage, "physical")
        self.add_message(f"You dealt {actual_damage} points of physical damage to {self.current_enemy.name}！")
        
        # check the buff
        if "break" in self.current_enemy.status_effects:
            self.add_message(f"{self.current_enemy.name}'s rupture buff decrease 1 stack!")
        
        if not self.current_enemy.is_alive():
            self.add_message(f"you have beat {self.current_enemy.name}！")
            self.player.restore_magic(15)
            self.game_state = "enemy_defeated"
        else:
            self.game_state = "enemy_turn"
    
    def player_magic_attack(self, magic_type=None):
        if magic_type is None:
            magic_type = self.player.magic_attack_mode
        
        if magic_type == MagicAttackMode.NORMAL:
            self._normal_magic_attack()
        elif magic_type == MagicAttackMode.DOUBLE:
            self._double_magic_attack()
        elif magic_type == MagicAttackMode.CHARGE:
            self._charge_magic_attack()
    
    def _normal_magic_attack(self):
        if self.player.use_magic(10):
            damage = self.player.magic_power + random.randint(5, 10)
            actual_damage = self.current_enemy.take_damage(damage, "magic")
            self.add_message(f"You dealt {actual_damage} points of magical damage to {self.current_enemy.name}！")
            
            if not self.current_enemy.is_alive():
                self.add_message(f"you have beat {self.current_enemy.name}！")
                self.player.restore_magic(15)
                self.game_state = "enemy_defeated"
            else:
                self.game_state = "enemy_turn"
        else:
            self.add_message("No enough mana！")
            self.game_state = "player_turn"
    
    def _double_magic_attack(self):
        if self.player.use_magic(15):
            total_damage = 0
            for i in range(2):
                damage = int((self.player.magic_power + random.randint(3, 7)) * 0.4)
                actual_damage = self.current_enemy.take_damage(damage, "magic")
                total_damage += actual_damage
                self.add_message(f"Your magic attack {i+1} dealt {actual_damage} points of magical damage！")
            
            self.add_message(f"The double magic dealt total damage: {total_damage}！")
            
            if not self.current_enemy.is_alive():
                self.add_message(f"you have beat {self.current_enemy.name}！")
                self.player.restore_magic(15)
                self.game_state = "enemy_defeated"
            else:
                self.game_state = "enemy_turn"
        else:
            self.add_message("No enough mana！")
            self.game_state = "player_turn"
    
    def _charge_magic_attack(self):
        if self.player.charging:
            # charging ends, deal powerful attack
            damage = int((self.player.magic_power + random.randint(10, 15)) * 3.0)
            actual_damage = self.current_enemy.take_damage(damage, "magic")
            self.add_message(f"Charging ends！you dealt {actual_damage} points of magical damage to {self.current_enemy.name}！")
            self.player.charging = False
            self.player.charge_turn = 0
            
            if not self.current_enemy.is_alive():
                self.add_message(f"you have beat {self.current_enemy.name}！")
                self.player.restore_magic(15)
                self.game_state = "enemy_defeated"
            else:
                self.game_state = "enemy_turn"
        else:
            # start to charge
            if self.player.use_magic(20):
                self.player.charging = True
                self.player.charge_turn = 1
                self.add_message("Start to charge, the charge is going to ends at next turn！")
                self.game_state = "enemy_turn"
            else:
                self.add_message("No enough mana！")
                self.game_state = "player_turn"
    
    def apply_magic_effect(self, magic_type):
        cost = 12
        if self.player.use_magic(cost):
            if magic_type == MagicType.FIRE:
                self.current_enemy.add_status_effect("burn", 0, 2)
                self.add_message(f"You dealt (2) Burn to {self.current_enemy.name}！")
            elif magic_type == MagicType.BREAK:
                self.current_enemy.add_status_effect("break", 0, 10)
                self.add_message(f"You dealt (10) Rupture to {self.current_enemy.name}！")
            elif magic_type == MagicType.SHOCK:
                self.current_enemy.add_status_effect("shock", 0, 1)
                self.add_message(f"You dealt (1) Tremor to {self.current_enemy.name}！")
            
            self.game_state = "enemy_turn"
        else:
            self.add_message("No enough mana！")
            self.game_state = "player_turn"
    
    def player_heal(self):
        if self.player.use_magic(15):
            heal_amount = self.player.heal(30 + random.randint(5, 15))
            self.add_message(f"You heal yourself {heal_amount} points of heal points！")
            self.game_state = "enemy_turn"
        else:
            self.add_message("No enough mana！")
            self.game_state = "player_turn"
    
    def enemy_attack(self):
        # check enemy is shocked or not
        if self.current_enemy.stunned:
            self.add_message(f"{self.current_enemy.name} is shocked, can't move this turn！")
            self.current_enemy.stunned = False
            if "shock" in self.current_enemy.status_effects:
                self.current_enemy.remove_status_effect("shock")  # if shock triggered, remove the buff of tremor
            self.game_state = "player_turn"
            return
        
        damage = self.current_enemy.attack + random.randint(-2, 2)
        actual_damage = self.player.take_damage(damage, "physical")
        self.add_message(f"{self.current_enemy.name} dealt {actual_damage} points of physical damage to you！")
        
        if not self.player.is_alive():
            self.game_state = "defeat"
        else:
            self.game_state = "player_turn"
    
    def add_message(self, msg):
        self.battle_log.append(msg)
        if len(self.battle_log) > 8:
            self.battle_log.pop(0)
    
    def update(self):
        if self.game_state == "enemy_turn":
            # dealing with the enemy's state
            effects_log, damage_taken = self.current_enemy.process_status_effects()
            for log in effects_log:
                self.add_message(log)
            
            if damage_taken > 0 and not self.current_enemy.is_alive():
                self.add_message(f"{self.current_enemy.name} is bitten down due to the negative buff！")
                self.player.restore_magic(15)
                self.game_state = "enemy_defeated"
                return
            
            pygame.time.delay(1000)
            self.enemy_attack()
        elif self.game_state == "enemy_defeated":
            pygame.time.delay(1500)
            self.new_enemy()
            self.attack_count = 0  # reset the attack count

def draw_button(surface, x, y, width, height, color, text, text_color=WHITE, enabled=True):
    if not enabled:
        color = (color[0]//2, color[1]//2, color[2]//2)
    
    pygame.draw.rect(surface, color, (x, y, width, height), border_radius=10)
    pygame.draw.rect(surface, BLACK, (x, y, width, height), 2, border_radius=10)
    
    text_surf = font_small.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=(x + width/2, y + height/2))
    surface.blit(text_surf, text_rect)
    
    return pygame.Rect(x, y, width, height)

def draw_health_bar(surface, x, y, width, height, current, maximum, color):
    ratio = current / maximum
    pygame.draw.rect(surface, BLACK, (x-2, y-2, width+4, height+4), border_radius=5)
    pygame.draw.rect(surface, (50, 50, 50), (x, y, width, height), border_radius=5)
    pygame.draw.rect(surface, color, (x, y, width * ratio, height), border_radius=5)

def draw_magic_bar(surface, x, y, width, height, current, maximum):
    ratio = current / maximum
    pygame.draw.rect(surface, BLACK, (x-2, y-2, width+4, height+4), border_radius=5)
    pygame.draw.rect(surface, (30, 30, 60), (x, y, width, height), border_radius=5)
    pygame.draw.rect(surface, BLUE, (x, y, width * ratio, height), border_radius=5)

def draw_status_effects(surface, x, y, character):
    if not character.status_effects:
        return
    
    title_text = font_tiny.render("magic buff:", True, WHITE)            #  hfajfhioagu
    surface.blit(title_text, (x, y))
    
    y_offset = 25
    for effect_name, effect in character.status_effects.items():
        color = WHITE
        if effect_name == "burn":
            color = RED
        elif effect_name == "break":
            color = ORANGE
        elif effect_name == "shock":
            color = YELLOW
            
        effect_text = font_tiny.render(f"{effect_name}: {effect.stacks} stack(s)", True, color)
        surface.blit(effect_text, (x, y + y_offset))
        y_offset += 20

def main():
    clock = pygame.time.Clock()
    game = Game()
    
    # bottom area
    attack_button_rect = pygame.Rect(50, 500, 150, 40)
    magic_button_rect = pygame.Rect(210, 500, 150, 40)
    magic_effect_button_rect = pygame.Rect(370, 500, 150, 40)
    heal_button_rect = pygame.Rect(530, 500, 150, 40)
    
    # magical attack mode selecton bottom area
    magic_normal_rect = pygame.Rect(50, 550, 120, 30)
    magic_double_rect = pygame.Rect(180, 550, 120, 30)
    magic_charge_rect = pygame.Rect(310, 550, 120, 30)
    
    # magical attack type selection area
    fire_effect_rect = pygame.Rect(50, 590, 120, 30)
    break_effect_rect = pygame.Rect(180, 590, 120, 30)
    shock_effect_rect = pygame.Rect(310, 590, 120, 30)

    running = True
    while running:
        screen.fill((30, 30, 50))
        
        # event execution
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                
                if game.game_state == "battle":
                    game.game_state = "player_turn"
                
                elif game.game_state == "player_turn":
                    if attack_button_rect.collidepoint(mouse_pos):
                        game.player_attack()
                    elif magic_button_rect.collidepoint(mouse_pos):
                        if game.player.charging:
                            game.player_magic_attack(MagicAttackMode.CHARGE)
                        else:
                            game.player_magic_attack()
                    elif heal_button_rect.collidepoint(mouse_pos):
                        game.player_heal()
                    elif magic_effect_button_rect.collidepoint(mouse_pos):
                        # select the magic type
                        pass
                    elif magic_normal_rect.collidepoint(mouse_pos):
                        game.player.magic_attack_mode = MagicAttackMode.NORMAL
                    elif magic_double_rect.collidepoint(mouse_pos):
                        game.player.magic_attack_mode = MagicAttackMode.DOUBLE
                    elif magic_charge_rect.collidepoint(mouse_pos):
                        game.player.magic_attack_mode = MagicAttackMode.CHARGE
                    elif fire_effect_rect.collidepoint(mouse_pos):
                        game.apply_magic_effect(MagicType.FIRE)
                    elif break_effect_rect.collidepoint(mouse_pos):
                        game.apply_magic_effect(MagicType.BREAK)
                    elif shock_effect_rect.collidepoint(mouse_pos):
                        game.apply_magic_effect(MagicType.SHOCK)
                
                elif game.game_state in ["victory", "defeat"]:
                    # restart the game
                    game = Game()
        
        # draw the game start page
        if game.game_state == "start":
            # stary page
            title_text = font_large.render("Force_Grey", True, GOLD)
            screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, 150))
            
            start_text = font_medium.render("Click to start...", True, WHITE)
            screen.blit(start_text, (WIDTH//2 - start_text.get_width()//2, 250))
            
            instruction_text = font_small.render("Use your power to clear the dunguen！", True, GREEN)
            screen.blit(instruction_text, (WIDTH//2 - instruction_text.get_width()//2, 320))
            
            features_text = [
                'waiting for new version...'
            ]
            
            for i, text in enumerate(features_text):
                feature_text = font_small.render(text, True, WHITE)
                screen.blit(feature_text, (WIDTH//2 - feature_text.get_width()//2, 370 + i * 30))
        
        else:
            # draw the info of player
            player_text = font_medium.render(game.player.name, True, WHITE)
            screen.blit(player_text, (100, 50))
            
            draw_health_bar(screen, 100, 90, 250, 20, game.player.hp, game.player.max_hp, GREEN)
            hp_text = font_small.render(f"HP: {game.player.hp}/{game.player.max_hp}", True, WHITE)
            screen.blit(hp_text, (360, 90))
            
            draw_magic_bar(screen, 100, 120, 250, 15, game.player.magic_points, game.player.max_magic_points)
            mp_text = font_small.render(f"MP: {game.player.magic_points}/{game.player.max_magic_points}", True, WHITE)
            screen.blit(mp_text, (360, 120))
            
            # draw player's state
            draw_status_effects(screen, 100, 150, game.player)
            
            # draw the info of enemy
            if game.current_enemy:
                enemy_text = font_medium.render(game.current_enemy.name, True, WHITE)
                screen.blit(enemy_text, (600, 50))
                
                draw_health_bar(screen, 600, 90, 250, 20, game.current_enemy.hp, game.current_enemy.max_hp, RED)
                enemy_hp_text = font_small.render(f"HP: {game.current_enemy.hp}/{game.current_enemy.max_hp}", True, WHITE)
                screen.blit(enemy_hp_text, (860, 90))
                
                # show the multiplier of enemy
                resist_text = font_tiny.render(
                    f"physical multiplier: {game.current_enemy.physical_resistance} magical multiplier: {game.current_enemy.magic_resistance}", 
                    True, YELLOW
                )
                screen.blit(resist_text, (600, 115))
                
                # draw enemy's state
                draw_status_effects(screen, 600, 150, game.current_enemy)
            
            # draw the battle log
            log_bg = pygame.Rect(50, 200, 800, 250)
            pygame.draw.rect(screen, (20, 20, 40), log_bg, border_radius=10)
            pygame.draw.rect(screen, BLUE, log_bg, 2, border_radius=10)
            
            log_title = font_small.render("Battle Log:", True, GOLD)
            screen.blit(log_title, (70, 210))
            
            for i, message in enumerate(game.battle_log):
                log_text = font_small.render(message, True, WHITE)
                screen.blit(log_text, (70, 240 + i * 25))
            
            # draw bottoms
            if game.game_state == "player_turn":
                attack_button = draw_button(screen, 50, 500, 150, 40, RED, "physical ATK")
                
                magic_text = "charging ATK" if game.player.charging else "magical ATK"
                magic_color = PURPLE if game.player.charging else BLUE
                magic_button = draw_button(screen, 210, 500, 150, 40, magic_color, magic_text)
                
                magic_effect_button = draw_button(screen, 370, 500, 150, 40, GREEN, "magic effect")
                heal_button = draw_button(screen, 530, 500, 150, 40, GREEN, "healing")
                
                # draw the bottom of magic mode selection
                mode_normal_color = GOLD if game.player.magic_attack_mode == MagicAttackMode.NORMAL else BLUE
                mode_double_color = GOLD if game.player.magic_attack_mode == MagicAttackMode.DOUBLE else BLUE
                mode_charge_color = GOLD if game.player.magic_attack_mode == MagicAttackMode.CHARGE else BLUE
                
                magic_normal = draw_button(screen, 50, 550, 120, 30, mode_normal_color, "normal")
                magic_double = draw_button(screen, 180, 550, 120, 30, mode_double_color, "double")
                magic_charge = draw_button(screen, 310, 550, 120, 30, mode_charge_color, "charging")
                
                # draw the bottom of magic type selection
                fire_effect = draw_button(screen, 50, 590, 120, 30, RED, "BURN")
                break_effect = draw_button(screen, 180, 590, 120, 30, GREEN, "RUPTURE")
                shock_effect = draw_button(screen, 310, 590, 120, 30, ORANGE, "TREMOR")
            
            # show current state
            if game.game_state == "player_turn":
                if game.player.charging:
                    status_text = font_medium.render("charging... click magic attack to deal powerful attack! ", True, GOLD)
                else:
                    status_text = font_medium.render("your turn，choose your action", True, GOLD)
                screen.blit(status_text, (WIDTH//2 - status_text.get_width()//2, 650))
            elif game.game_state == "enemy_turn":
                status_text = font_medium.render("enemy's turn...", True, RED)
                screen.blit(status_text, (WIDTH//2 - status_text.get_width()//2, 650))
            elif game.game_state == "victory":
                status_text = font_large.render("congratulations！you win！", True, GOLD)
                screen.blit(status_text, (WIDTH//2 - status_text.get_width()//2, 350))
                restart_text = font_medium.render("click to restart", True, WHITE)
                screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, 420))
            elif game.game_state == "defeat":
                status_text = font_large.render("YOU DIED...", True, RED)
                screen.blit(status_text, (WIDTH//2 - status_text.get_width()//2, 350))
                restart_text = font_medium.render("click to restart", True, WHITE)
                screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, 420))
        
        pygame.display.flip()
        clock.tick(60)
        
        # reset the game state
        game.update()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
