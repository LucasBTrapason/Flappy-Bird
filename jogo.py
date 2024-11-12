import pygame
import random
import os
import tkinter as tk
from tkinter import simpledialog

# Inicializa o mixer de áudio
pygame.mixer.init()

# Configurações do Pygame
pygame.init()

# Carregar sons - com tratamento de erros
def load_sound(filename):
    try:
        sound = pygame.mixer.Sound(os.path.join('', filename))
        return sound
    except pygame.error as e:
        print(f"Erro ao carregar o som '{filename}': {e}")
        return None

sounds = {
    'wing': load_sound('sfx_wing.wav'),
    'hit': load_sound('sfx_hit.wav'),
    'point': load_sound('sfx_point.wav'),
    'die': load_sound('sfx_die.wav'),
    #'background': load_sound('background_music.mp3')  # Música de fundo removida
}

# Configurações do Pygame
pygame.init()

# Definições de constantes
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
FPS = 60

# Cores
WHITE = (255, 255, 255)

# Carregar imagens
def load_image(filename, size):
    image = pygame.image.load(os.path.join('', filename))  # Ajuste o diretório se necessário
    return pygame.transform.scale(image, size)

# Tamanhos ajustados das imagens
SIZES = {
    'cano': (40, 400),  # Novo tamanho do cano
    'chao': (SCREEN_WIDTH, 56),  # O chão cobrirá toda a largura
    'fundo': (SCREEN_WIDTH, SCREEN_HEIGHT),  # O fundo cobrirá toda a tela
    'comecar': (104, 58),
    'jogador_1': (34, 24),  # Aumentando o jogador proporcionalmente
    'jogador_2': (34, 24),
    'logo': (89 * 2, 24 * 2)
}

# Carregar todas as imagens
images = {
    'cano': load_image('sp_cano.png', SIZES['cano']),
    'cano2': load_image('sp_cano2.png', SIZES['cano']),
    'chao': load_image('sp_chao.png', SIZES['chao']),
    'fundo': load_image('sp_fundo.png', SIZES['fundo']),
    'comecar': load_image('sp_comecar.png', SIZES['comecar']),
    'jogador_1': load_image('sp_jogador_1.png', SIZES['jogador_1']),
    'jogador_2': load_image('sp_jogador_2.png', SIZES['jogador_2']),
    'logo': load_image('sp_logo.png', SIZES['logo'])
}

# Classe do jogo
class FlappyBird:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Flappy Bird")
        self.clock = pygame.time.Clock()
        self.running = True
        self.gravity = 0.5
        self.velocity = 0
        self.score = 0
        self.player_y = SCREEN_HEIGHT // 2
        self.pipes = []
        self.pipe_speed = 2
        self.high_scores = self.load_scores()  # Carrega os placares ao iniciar
        self.load_pipes()
        self.player_images = [images['jogador_1'], images['jogador_1'], images['jogador_1'], images['jogador_1'],
                              images['jogador_1'], images['jogador_2'], images['jogador_2'], images['jogador_2'],
                              images['jogador_2'], images['jogador_2']]
        self.player_index = 0
        self.game_active = False
        self.paused = False  # Variável para controlar o estado de pausa
        self.background_x = 0
        self.ground_x = 0


    # Função para salvar placares em um arquivo txt
    def save_scores(self):
        with open("high_scores.txt", "w") as f:
            for score in self.high_scores:
                f.write(f"{score}\n")

    # Função para carregar placares do arquivo txt
    def load_scores(self):
        if os.path.exists("high_scores.txt"):
            with open("high_scores.txt", "r") as f:
                return [int(line.strip()) for line in f.readlines()]
        return [0] * 10  # Caso o arquivo não exista, inicializa com 10 zeros

    def load_pipes(self):
        x_pos = SCREEN_WIDTH
        for _ in range(100):  # Cria canos com distâncias aleatórias
            gap = 150
            pipe_height = random.randint(100, 400)
            x_pos += random.randint(220, 230)  # Aumentando a distância entre os canos
            self.pipes.append((x_pos, pipe_height, gap))

    def draw_pipes(self):
        for pipe in self.pipes:
            x, height, gap = pipe
            # Desenha o cano de cima
            self.screen.blit(images['cano2'], (x, height - images['cano'].get_height()))
            # Desenha o cano de baixo
            self.screen.blit(images['cano'], (x, height + gap))

    def update_pipes(self):
        for i, pipe in enumerate(self.pipes):
            self.pipes[i] = (pipe[0] - self.pipe_speed, pipe[1], pipe[2])
            if pipe[0] < -images['cano'].get_width():
                self.pipes.pop(i)
                self.score += 1
                sounds['point'].play()
                # Adiciona um novo cano com uma distância aleatória
                gap = 150
                pipe_height = random.randint(100, 400)
                x_pos = self.pipes[-1][0] + random.randint(120, 160)  # Aumentando a distância para os novos canos
                self.pipes.append((x_pos, pipe_height, gap))
                break

    def check_collision(self):
        for pipe in self.pipes:
            x, height, gap = pipe
            pipe_rect_top = pygame.Rect(x, height - images['cano'].get_height(), images['cano'].get_width(),
                                        images['cano'].get_height())
            pipe_rect_bottom = pygame.Rect(x, height + gap, images['cano'].get_width(), images['cano'].get_height())
            player_rect = pygame.Rect(50, self.player_y, images['jogador_1'].get_width(),
                                      images['jogador_1'].get_height())
            if pipe_rect_top.colliderect(player_rect) or pipe_rect_bottom.colliderect(player_rect):
                return True
        if self.player_y <= 0 or self.player_y >= SCREEN_HEIGHT - images['jogador_1'].get_height() - 50:
            return True
        return False

    def jump(self):
        sounds['wing'].play()
        self.velocity = -8

    def show_high_scores(self):
        root = tk.Tk()
        root.withdraw()  # Esconde a janela principal do tkinter

        score_string = "\n".join([f"{i + 1}. {score}" for i, score in enumerate(self.high_scores)])
        simpledialog.messagebox.showinfo("High Scores", score_string)
        root.destroy()

    def update_high_scores(self):
        self.high_scores.append(self.score)
        self.high_scores.sort(reverse=True)
        self.high_scores = self.high_scores[:10]
        self.save_scores()  # Salva os placares atualizados

    def reset_game(self):
        self.velocity = 0
        self.score = 0
        self.player_y = SCREEN_HEIGHT // 2
        self.pipes = []
        self.load_pipes()
        self.game_active = False
        self.paused = False  # Reseta a pausa ao reiniciar o jogo
        self.background_x = 0
        self.ground_x = 0

    def draw_start_message(self):
        font = pygame.font.Font(None, 36)
        # Desenha fundo cobrindo toda a tela
        self.screen.blit(images['fundo'], (0, 0))
        self.screen.blit(images['logo'], (SCREEN_WIDTH // 2 - 89, SCREEN_HEIGHT // 3))

        self.screen.blit(images['comecar'], (SCREEN_WIDTH // 2-52, SCREEN_HEIGHT // 3+90))



    def draw_pause_message(self):
        font = pygame.font.Font(None, 36)
        pause_surface = font.render("PAUSADO", True, (255, 255, 255))
        pause_rect = pause_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(pause_surface, pause_rect)

    def update_background_and_ground(self):
        self.background_x -= self.pipe_speed
        self.ground_x -= self.pipe_speed

        if self.background_x <= -SCREEN_WIDTH:
            self.background_x = 0
        if self.ground_x <= -SCREEN_WIDTH:
            self.ground_x = 0

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        if not self.paused and not self.game_active:
                            self.game_active = True
                        elif not self.paused:
                            self.jump()
                    if event.key == pygame.K_p:
                        self.paused = not self.paused  # Inverte o estado de pausa
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Botão esquerdo
                        if not self.paused and not self.game_active:
                            self.game_active = True
                        elif not self.paused:
                            self.jump()
                    elif event.button == 3:  # Botão direito
                        self.paused = not self.paused  # Inverte o estado de pausa

            if self.game_active and not self.paused:
                # Atualiza a física do jogador
                self.velocity += self.gravity
                self.player_y += self.velocity

                # Limita a altura do jogador
                if self.player_y < 0:
                    self.player_y = 0
                if self.player_y > SCREEN_HEIGHT - images['jogador_1'].get_height() - 50:
                    self.player_y = SCREEN_HEIGHT - images['jogador_1'].get_height() - 50

                # Limpa a tela
                self.screen.fill(WHITE)

                # Desenha o fundo com efeito infinito
                self.update_background_and_ground()
                self.screen.blit(images['fundo'], (self.background_x, 0))
                self.screen.blit(images['fundo'], (self.background_x + SCREEN_WIDTH, 0))

                # Desenha o jogador alternando entre as imagens
                self.player_index += 1
                if self.player_index >= len(self.player_images):
                    self.player_index = 0
                self.screen.blit(self.player_images[self.player_index], (50, self.player_y))

                # Desenha canos
                self.draw_pipes()

                # Atualiza canos
                self.update_pipes()

                # Verifica colisão
                if self.check_collision():
                    sounds['hit'].play()
                    self.update_high_scores()
                    self.show_high_scores()
                    self.reset_game()

                # Desenha HUD de pontos
                font = pygame.font.Font(None, 120)
                score_surface = font.render(f'{self.score}', True, (255, 255, 255))
                score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 50))
                self.screen.blit(score_surface, score_rect)

            elif self.paused:  # Mostra a mensagem de pausa
                self.screen.blit(images['fundo'], (0, 0))
                self.draw_pause_message()

            else:
                # Exibe mensagem de clique para começar quando não está ativo
                self.draw_start_message()

            # Desenha o chão com efeito infinito
            self.screen.blit(images['chao'], (self.ground_x, SCREEN_HEIGHT - SIZES['chao'][1]))
            self.screen.blit(images['chao'], (self.ground_x + SCREEN_WIDTH, SCREEN_HEIGHT - SIZES['chao'][1]))

            pygame.display.update()
            self.clock.tick(FPS)

        pygame.quit()

if __name__ == "__main__":
    game = FlappyBird()
    game.run()