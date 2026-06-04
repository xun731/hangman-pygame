"""
Hangman - Pygame Edition
從原本 console 版改寫，保留所有玩法：
  - 兩種類別（Animals / Countries）
  - 三種難度（依單字長度過濾）
  - 開局亮出母音
  - 提示功能（會消耗一次失誤）
  - 計時
  - 11 階段吊人圖（用 pygame primitives 畫）

操作：
  - 直接打鍵盤 A-Z 猜字母，或滑鼠點下方按鈕
  - 按 ? 或點 Hint 鈕使用提示
  - ESC 回主選單
"""

import pygame # 記得安裝> pip install pygame
import random
import sys
import time

pygame.init()

# ============ 基本設定 ============
WIDTH, HEIGHT = 900, 680
FPS = 60

# 配色（取代原本的 ANSI 代碼）
BG          = (28, 32, 44)
PANEL       = (40, 46, 62)
PANEL_LIGHT = (54, 60, 78)
FG          = (235, 235, 240)
MUTED       = (140, 145, 160)
GREEN       = (110, 220, 130)
RED         = (230, 100, 110)
YELLOW      = (240, 200, 90)
ACCENT      = (110, 180, 230)
ACCENT_HOVER= (140, 200, 240)

VOWELS = set('AEIOU')
MAX_MISSES = 10  # 失誤達 10 次（第 11 階段）即輸

WORD_CATEGORIES = {
    'Animals': (
        'ALLIGATOR ANT BABOON BADGER BAT BEAR BEAVER CAMEL CAT CLAM COBRA COUGAR '
        'COYOTE CROW DEER DOG DONKEY DUCK EAGLE ELEPHANT FERRET FOX FROG GIRAFFE '
        'GOAT GOOSE GORILLA HAWK HIPPOPOTAMUS JELLYFISH KANGAROO LEOPARD LION '
        'LIZARD LLAMA MOLE MONKEY MOOSE MOUSE MULE NARWHAL NEWT OCTOPUS OTTER OWL '
        'PANDA PARROT PENGUIN PIGEON PYTHON RABBIT RAM RAT RAVEN RHINO RHINOCEROS '
        'SALMON SEAL SHARK SHEEP SKUNK SLOTH SNAKE SPIDER SQUIRREL STORK SWAN '
        'TIGER TOAD TROUT TURKEY TURTLE WEASEL WHALE WOLF WOMBAT ZEBRA'
    ).split(),
    'Countries': (
        'TAIWAN JAPAN CANADA BRAZIL FRANCE GERMANY EGYPT CHILE KENYA NORWAY '
        'SWEDEN FINLAND POLAND TURKEY INDIA CHINA KOREA MEXICO SPAIN ITALY '
        'KYRGYZSTAN NETHERLANDS UZBEKISTAN TURKMENISTAN PHILIPPINES SEYCHELLES '
        'LIECHTENSTEIN LUXEMBOURG'
    ).split(),
}

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Hangman - Pygame Edition')
clock = pygame.time.Clock()

font_title = pygame.font.SysFont('arial', 56, bold=True)
font_h1    = pygame.font.SysFont('arial', 36, bold=True)
font_h2    = pygame.font.SysFont('arial', 24, bold=True)
font_body  = pygame.font.SysFont('arial', 20)
font_word  = pygame.font.SysFont('couriernew', 40, bold=True)
font_btn   = pygame.font.SysFont('arial', 22, bold=True)


# ============ Button 元件 ============
class Button:
    def __init__(self, rect, text, callback, *, color=ACCENT, text_color=FG, font=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.color = color
        self.text_color = text_color
        self.font = font or font_btn
        self.enabled = True

    def draw(self, surface, mouse_pos):
        if not self.enabled:
            color, tc = PANEL, MUTED
        else:
            hovered = self.rect.collidepoint(mouse_pos)
            color = ACCENT_HOVER if (hovered and self.color == ACCENT) else self.color
            tc = self.text_color
            if hovered and self.color != ACCENT:
                # 一般淡淡的 hover 效果：稍微提亮
                color = tuple(min(255, c + 20) for c in self.color)
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, PANEL_LIGHT, self.rect, width=2, border_radius=8)
        text_surf = self.font.render(self.text, True, tc)
        surface.blit(text_surf, text_surf.get_rect(center=self.rect.center))

    def handle_click(self, pos):
        if self.enabled and self.rect.collidepoint(pos):
            self.callback()
            return True
        return False


# ============ 吊人圖繪製 ============
def draw_hangman(surface, stage):
    """根據 stage (0~10) 在左半部畫出吊人圖。"""
    ox, oy = 80, 480  # 底座左端基準點
    color = FG
    w = 4

    # 永遠存在：底座 + 立柱 + 橫樑 + 繩
    pygame.draw.line(surface, color, (ox, oy), (ox + 200, oy), w)                       # 地面
    pygame.draw.line(surface, color, (ox + 40, oy), (ox + 40, oy - 340), w)             # 立柱
    pygame.draw.line(surface, color, (ox + 40, oy - 340), (ox + 180, oy - 340), w)      # 橫樑
    pygame.draw.line(surface, color, (ox + 180, oy - 340), (ox + 180, oy - 300), w)     # 繩

    body_top = (ox + 180, oy - 240)
    body_bot = (ox + 180, oy - 140)

    if stage >= 1:  # 頭
        pygame.draw.circle(surface, color, (ox + 180, oy - 270), 30, w)
    if stage >= 2:  # 身體
        pygame.draw.line(surface, color, body_top, body_bot, w)
    if stage >= 3:  # 左手
        pygame.draw.line(surface, color, (ox + 180, oy - 220), (ox + 135, oy - 185), w)
    if stage >= 4:  # 右手
        pygame.draw.line(surface, color, (ox + 180, oy - 220), (ox + 225, oy - 185), w)
    if stage >= 5:  # 左腳
        pygame.draw.line(surface, color, body_bot, (ox + 145, oy - 80), w)
    if stage >= 6:  # 右腳
        pygame.draw.line(surface, color, body_bot, (ox + 215, oy - 80), w)
    # 7~10 是「死亡裝飾」：棺材框 + 腳下橫線（用紅色強調危險）
    if stage >= 7:  # 左棺框 [
        pygame.draw.line(surface, RED, (ox + 130, oy - 305), (ox + 130, oy - 235), w)
        pygame.draw.line(surface, RED, (ox + 130, oy - 305), (ox + 145, oy - 305), w)
        pygame.draw.line(surface, RED, (ox + 130, oy - 235), (ox + 145, oy - 235), w)
    if stage >= 8:  # 右棺框 ]
        pygame.draw.line(surface, RED, (ox + 230, oy - 305), (ox + 230, oy - 235), w)
        pygame.draw.line(surface, RED, (ox + 230, oy - 305), (ox + 215, oy - 305), w)
        pygame.draw.line(surface, RED, (ox + 230, oy - 235), (ox + 215, oy - 235), w)
    if stage >= 9:  # 左腳底線
        pygame.draw.line(surface, RED, (ox + 125, oy - 75), (ox + 155, oy - 75), w)
    if stage >= 10:  # 右腳底線（GAME OVER）
        pygame.draw.line(surface, RED, (ox + 205, oy - 75), (ox + 235, oy - 75), w)


# ============ 主遊戲類別 ============
class Game:
    def __init__(self):
        self.state = 'category'   # 'category' | 'difficulty' | 'playing' | 'win' | 'lose'
        self.category = None
        self.difficulty = None
        self.secret_word = ''
        self.missed_letters = []   # 含 '?' 表示提示用過
        self.correct_letters = []
        self.guessed = set()       # 鍵盤上「已使用」的字母（含開局母音）
        self.hint_used = False
        self.start_time = 0
        self.end_time = 0
        self.message = ''
        self.message_until = 0

        self.buttons = []
        self.letter_buttons = {}
        self.hint_button = None
        self._build_category_screen()

    # ---------- flash 訊息 ----------
    def flash(self, text, seconds=1.8):
        self.message = text
        self.message_until = time.time() + seconds

    # ---------- 建構各畫面按鈕 ----------
    def _clear_buttons(self):
        self.buttons = []
        self.letter_buttons = {}
        self.hint_button = None

    def _back_to_menu(self):
        self.state = 'category'
        self._build_category_screen()

    def _build_category_screen(self):
        self._clear_buttons()
        cats = list(WORD_CATEGORIES.keys())
        bw, bh = 280, 70
        for i, cat in enumerate(cats):
            x = (WIDTH - bw) // 2
            y = 300 + i * (bh + 20)
            self.buttons.append(Button((x, y, bw, bh), cat,
                                       lambda c=cat: self.choose_category(c)))

    def _build_difficulty_screen(self):
        self._clear_buttons()
        labels = [('Easy  (≤5)', 1), ('Medium  (6-7)', 2), ('Hard  (>7)', 3)]
        bw, bh = 220, 70
        total = bw * 3 + 40 * 2
        start_x = (WIDTH - total) // 2
        for i, (label, val) in enumerate(labels):
            x = start_x + i * (bw + 40)
            self.buttons.append(Button((x, 340, bw, bh), label,
                                       lambda d=val: self.choose_difficulty(d)))
        self.buttons.append(Button((30, 30, 110, 40), '< Back',
                                   self._back_to_menu, color=PANEL, font=font_body))

    def _build_play_screen(self):
        self._clear_buttons()
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        row1, row2 = letters[:13], letters[13:]
        bw, bh, gap = 56, 56, 8
        row_w = bw * 13 + gap * 12
        x0 = (WIDTH - row_w) // 2
        y1, y2 = 500, 500 + bh + gap

        for i, ch in enumerate(row1):
            btn = Button((x0 + i * (bw + gap), y1, bw, bh), ch,
                         lambda c=ch: self.guess(c),
                         color=PANEL_LIGHT, font=font_h2)
            self.buttons.append(btn)
            self.letter_buttons[ch] = btn
        for i, ch in enumerate(row2):
            btn = Button((x0 + i * (bw + gap), y2, bw, bh), ch,
                         lambda c=ch: self.guess(c),
                         color=PANEL_LIGHT, font=font_h2)
            self.buttons.append(btn)
            self.letter_buttons[ch] = btn

        # 提示按鈕（右上）
        self.hint_button = Button((WIDTH - 180, 90, 140, 50), '? Hint',
                                  self.use_hint, color=YELLOW, text_color=BG)
        self.buttons.append(self.hint_button)

        self.buttons.append(Button((30, 30, 110, 40), '< Menu',
                                   self._back_to_menu, color=PANEL, font=font_body))
        self._sync_letter_buttons()

    def _sync_letter_buttons(self):
        for ch, btn in self.letter_buttons.items():
            if ch in self.guessed:
                btn.enabled = False
                if ch in self.correct_letters:
                    btn.color = GREEN
                    btn.text_color = BG
                else:
                    btn.color = RED
                    btn.text_color = FG
        if self.hint_button is not None:
            self.hint_button.enabled = (
                not self.hint_used and len(self.missed_letters) < MAX_MISSES - 1
            )

    def _build_end_screen(self, won):
        self._clear_buttons()
        self.state = 'win' if won else 'lose'
        bw, bh, gap = 200, 60, 30
        total = bw * 2 + gap
        x0 = (WIDTH - total) // 2
        self.buttons.append(Button((x0, 560, bw, bh), 'Play Again',
                                   self._restart_same))
        self.buttons.append(Button((x0 + bw + gap, 560, bw, bh), 'Main Menu',
                                   self._back_to_menu, color=PANEL))

    # ---------- 流程 ----------
    def choose_category(self, cat):
        self.category = cat
        self.state = 'difficulty'
        self._build_difficulty_screen()

    def choose_difficulty(self, d):
        self.difficulty = d
        if not self._words_for_difficulty():
            self.flash('No words match this difficulty — try another.')
            return
        self._start_round()

    def _words_for_difficulty(self):
        words = WORD_CATEGORIES[self.category]
        if self.difficulty == 1: return [w for w in words if len(w) <= 5]
        if self.difficulty == 2: return [w for w in words if 5 < len(w) <= 7]
        return [w for w in words if len(w) > 7]

    def _start_round(self):
        words = self._words_for_difficulty()
        self.secret_word = random.choice(words)
        self.missed_letters = []
        self.correct_letters = [l for l in set(self.secret_word) if l in VOWELS] # 判定母音
        self.guessed = set(l for l in VOWELS)
        self.hint_used = False
        self.start_time = time.time()
        self.state = 'playing'
        self._build_play_screen()

        # 母音已經判定過了，所有母音都不能點了
        # for ch, btn in self.letter_buttons.items(): 
        #     if ch in VOWELS:
        #         btn.enabled = False

        # 極少數情況：母音直接全中 → 立刻獲勝
        if all(l in self.correct_letters for l in self.secret_word):
            self.end_time = time.time()
            self._build_end_screen(won=True)

    def _restart_same(self):
        self._start_round()

    def guess(self, ch):
        if self.state != 'playing':
            return
        if ch in self.guessed:
            self.flash(f'Already guessed "{ch}"')
            return
        self.guessed.add(ch)
        if ch in self.secret_word:
            self.correct_letters.append(ch)
        else:
            self.missed_letters.append(ch)
        self._sync_letter_buttons()
        self._check_end()

    def use_hint(self):
        if self.state != 'playing':
            return
        if self.hint_used:
            self.flash('Hint already used.')
            return
        if len(self.missed_letters) >= MAX_MISSES - 1:
            self.flash('Too risky to use a hint now.')
            return
        ungussed = [l for l in set(self.secret_word) if l not in self.correct_letters]
        if not ungussed:
            return
        letter = random.choice(ungussed)
        self.correct_letters.append(letter)
        self.guessed.add(letter)
        self.missed_letters.append('?')  # 代表用了一次 hint（也算一次失誤）
        self.hint_used = True
        self.flash(f'Hint: the word contains "{letter}"', 2.5)
        self._sync_letter_buttons()
        self._check_end()

    def _check_end(self):
        if all(l in self.correct_letters for l in self.secret_word):
            self.end_time = time.time()
            self._build_end_screen(won=True)
            return
        if len(self.missed_letters) >= MAX_MISSES:
            self.end_time = time.time()
            self._build_end_screen(won=False)

    # ---------- 事件 ----------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state == 'category':
                    return False
                self._back_to_menu()
            elif self.state == 'playing':
                ch = (event.unicode or '').upper()
                if ch.isalpha() and len(ch) == 1:
                    self.guess(ch)
                elif event.unicode == '?':
                    self.use_hint()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.buttons:
                if btn.handle_click(event.pos):
                    break
        return True

    # ---------- 繪製 ----------
    def draw(self):
        screen.fill(BG)
        if self.state == 'category':
            self._draw_category()
        elif self.state == 'difficulty':
            self._draw_difficulty()
        elif self.state == 'playing':
            self._draw_playing()
        else:
            self._draw_end()

        # flash 訊息
        if self.message and time.time() < self.message_until:
            surf = font_body.render(self.message, True, YELLOW)
            screen.blit(surf, surf.get_rect(midbottom=(WIDTH // 2, HEIGHT - 8)))

        mouse = pygame.mouse.get_pos()
        for btn in self.buttons:
            btn.draw(screen, mouse)
        pygame.display.flip()

    def _draw_category(self):
        title = font_title.render('HANGMAN', True, FG)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 150)))
        sub = font_h2.render('Choose a category', True, MUTED)
        screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 230)))

    def _draw_difficulty(self):
        title = font_h1.render(f'Category: {self.category}', True, FG)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 200)))
        sub = font_h2.render('Choose a difficulty', True, MUTED)
        screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 270)))

    def _draw_playing(self):
        draw_hangman(screen, len(self.missed_letters))

        # 類別 + 計時
        cat_surf = font_h2.render(f'Category: {self.category}', True, ACCENT)
        screen.blit(cat_surf, (380, 100))
        elapsed = int(time.time() - self.start_time)
        screen.blit(font_body.render(f'Time: {elapsed}s', True, MUTED), (380, 140))

        # 單字（_/字母 並排）
        self._draw_word(380, 220)

        # 失誤字母
        screen.blit(font_body.render('Missed:', True, MUTED), (380, 340))
        for i, ch in enumerate(self.missed_letters):
            color = YELLOW if ch == '?' else RED
            s = font_h2.render(ch, True, color)
            screen.blit(s, (470 + i * 32, 335))

    def _draw_word(self, x, y):
        word = self.secret_word
        n = max(1, len(word))
        available = WIDTH - x - 30
        spacing = min(44, available // n)
        for ch in word:
            if ch in self.correct_letters:
                txt = font_word.render(ch, True, GREEN)
            else:
                txt = font_word.render('_', True, FG)
            screen.blit(txt, (x + (spacing - txt.get_width()) // 2, y))
            x += spacing

    def _draw_end(self):
        won = self.state == 'win'
        draw_hangman(screen, len(self.missed_letters))

        title_text = 'YOU WON!' if won else 'YOU LOST!'
        color = GREEN if won else RED
        title = font_title.render(title_text, True, color)
        screen.blit(title, title.get_rect(center=(WIDTH // 2 + 130, 160)))

        reveal = font_h1.render(f'The word was: {self.secret_word}', True, FG)
        screen.blit(reveal, reveal.get_rect(center=(WIDTH // 2 + 130, 260)))

        elapsed = int(self.end_time - self.start_time)
        info = font_body.render(
            f'Time: {elapsed}s   |   Category: {self.category}   |   Difficulty: {self.difficulty}',
            True, MUTED
        )
        screen.blit(info, info.get_rect(center=(WIDTH // 2 + 130, 320)))


def main():
    game = Game()
    running = True
    while running:
        for event in pygame.event.get():
            if game.handle_event(event) is False:
                running = False
                break
        game.draw()
        clock.tick(FPS)
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
