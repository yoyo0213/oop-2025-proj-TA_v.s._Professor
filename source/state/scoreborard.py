# scoreboard.py
import json
import os
from datetime import datetime

SCORE_FILE = "scores.json"
MAX_ENTRIES = 10
class Scoreboard:
    def __init__(self):
        self.scores = self.load_scores()

    def load_scores(self):
        if os.path.exists(SCORE_FILE):
            with open(SCORE_FILE, "r") as f:
                return json.load(f)
        return []

    def save_scores(self):
        with open(SCORE_FILE, "w") as f:
            json.dump(self.scores, f, indent=4)

    def add_score(self, name, score):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.scores.append({"name": name, "score": score, "time": timestamp})
        self.scores = sorted(self.scores, key=lambda x: x["score"], reverse=True)[:MAX_ENTRIES]
        self.save_scores()

    def get_top_scores(self):
        return self.scores
    def clear_scores(self):
        """Clear all scores from the scoreboard."""
        self.scores = []
        self.save_scores()
"""
    def display_scoreboard(screen, clock):
        scoreboard = Scoreboard()
        scores = scoreboard.get_top_scores()
        font = pygame.font.SysFont("Arial", 36)
        small_font = pygame.font.SysFont("Arial", 24)

        showing = True
        while showing:
            screen.fill((50, 50, 80))
            title = font.render("🏆 排行榜 🏆", True, (255, 255, 0))
            screen.blit(title, (300, 50))

            for i, entry in enumerate(scores):
                text = f"{i+1}. {entry['name']} - {entry['score']} 分 - {entry['time']}"
                text_surface = small_font.render(text, True, (255, 255, 255))
                screen.blit(text_surface, (100, 120 + i * 40))

            info = small_font.render("按任意鍵返回", True, (200, 200, 200))
            screen.blit(info, (280, 550))

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    showing = False
                elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    showing = False

            clock.tick(30)
"""
