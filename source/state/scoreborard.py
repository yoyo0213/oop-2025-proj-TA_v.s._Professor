# scoreboard.py
import json
import os
from datetime import datetime
from .. import constants as c

class Scoreboard:
    def __init__(self):
        self.scores = self.load_scores()

    def load_scores(self):
        if os.path.exists(c.SCORE_FILE):
            with open(c.SCORE_FILE, "r") as f:
                return json.load(f)
        return []

    def save_scores(self):
        with open(c.SCORE_FILE, "w") as f:
            json.dump(self.scores, f, indent=4)

    def add_score(self, name, score):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.scores.append({"name": name,"survival time": score  ,"time": timestamp})
        self.scores = sorted(self.scores, key=lambda x: x["survival time"], reverse=True)[:c.MAX_ENTRIES]
        self.save_scores()

    def get_top_scores(self):
        return self.scores
    def clear_scores(self):
        """Clear all scores from the scoreboard."""
        self.scores = []
        self.save_scores()