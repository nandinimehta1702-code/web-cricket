#!/usr/bin/env python3
"""
Web Cricket — Flask + Tailwind + HTMX

v2 — Settings + Mobile + Better UX
- Start screen to choose: player name, overs (1–20), difficulty (Easy/Med/Hard)
- Live, friendly commentary ("Yay! You scored two")
- 5 shots + wicket/4/6 reactions; scorecard at end
- New Game button fixed (re-renders whole page)
- Mobile-friendly; header logo + batter SVG

Run locally:
  pip install flask
  python app.py
Open: http://127.0.0.1:5000

On phone (same Wi‑Fi):
  python app.py  (it prints your LAN URL), or set host="0.0.0.0" below.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
from flask import Flask, render_template_string, request, session
import random, uuid, socket

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"  # change if deploying

# ---------------------- Config ----------------------
DEFAULT_OVERS = 5
MAX_OVERS = 20

SHOT_LABELS = {
    'defend': 'Defend',
    'cover': 'Cover Drive',
    'pull': 'Pull Shot',
    'straight': 'Straight Drive',
    'glance': 'Glance',
    'slog': 'Slog Sweep',
}
BALL_OPTIONS = {'g': 'Good length','s': 'Short','y': 'Yorker'}

# Difficulty tweaks: weight multipliers per outcome type
DIFF = {
    'easy':  {'W': 0.7, 0: 0.9, 1: 1.1, 2: 1.1, 3: 1.1, 4: 1.2, 6: 1.25},
    'medium':{'W': 1.0, 0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0, 6: 1.0},
    'hard':  {'W': 1.25,0: 1.05,1: 0.95,2: 0.95,3: 0.95,4: 0.9, 6: 0.85},
}

AI_BALLING_MIX = ['g']*6 + ['s']*3 + ['y']*3

# Outcome weights per (shot, ball)
PROB = {
 ('defend','g'):[('W',1),(0,55),(1,38),(2,6)],
 ('defend','s'):[('W',2),(0,48),(1,38),(2,10),(4,1)],
 ('defend','y'):[('W',1),(0,60),(1,36),(2,3)],
 ('cover','g'):[('W',6),(0,20),(1,18),(2,12),(3,3),(4,30),(6,5)],
 ('cover','s'):[('W',7),(0,28),(1,20),(2,12),(3,3),(4,22),(6,3)],
 ('cover','y'):[('W',10),(0,30),(1,20),(2,9),(3,1),(4,18),(6,2)],
 ('pull','g'):[('W',10),(0,28),(1,16),(2,10),(3,4),(4,20),(6,12)],
 ('pull','s'):[('W',11),(0,20),(1,12),(2,10),(3,5),(4,22),(6,20)],
 ('pull','y'):[('W',14),(0,32),(1,14),(2,8),(3,2),(4,16),(6,6)],
 ('straight','g'):[('W',4),(0,22),(1,22),(2,22),(3,4),(4,22),(6,4)],
 ('straight','s'):[('W',6),(0,26),(1,24),(2,20),(3,3),(4,18),(6,3)],
 ('straight','y'):[('W',5),(0,24),(1,22),(2,20),(3,2),(4,20),(6,3)],
 ('glance','g'):[('W',3),(0,18),(1,46),(2,26),(3,2),(4,5)],
 ('glance','s'):[('W',5),(0,22),(1,44),(2,24),(3,3),(4,6)],
 ('glance','y'):[('W',4),(0,22),(1,48),(2,20),(3,1),(4,5)],
 ('slog','g'):[('W',14),(0,22),(1,10),(2,10),(3,6),(4,18),(6,20)],
 ('slog','s'):[('W',16),(0,20),(1,8),(2,8),(3,6),(4,18),(6,24)],
 ('slog','y'):[('W',18),(0,26),(1,8),(2,6),(3,2),(4,16),(6,22)],
}

# ---------------------- Models ----------------------
from dataclasses import dataclass
@dataclass
class Settings:
    player: str = "Player"
    overs: int = DEFAULT_OVERS
    difficulty: str = 'medium'  # easy/medium/hard

@dataclass
class Innings:
    runs: int = 0
    wickets: int = 0
    balls: int = 0

    def balls_left(self, overs:int) -> int:
        return overs*6 - self.balls
    def over_ball(self) -> str:
        return f"{self.balls//6 + 1}.{self.balls%6 + 1}"
    def overs_text(self) -> str:
        return f"{self.balls//6}.{self.balls%6}"

@dataclass
class Game:
    id: str
    settings: Settings
    inn: Innings = field(default_factory=Innings)
    commentary: List[str] = field(default_factory=list)
    over: bool = False

GAMES: Dict[str, Game] = {}

# ---------------------- Helpers ----------------------

def weighted_choice(pairs, diff:dict):
    # apply difficulty multipliers
    weighted = []
    for outcome, w in pairs:
        key = outcome if outcome=='W' else int(outcome)
        weighted.append((outcome, w * diff[key]))
    total = sum(w for _,w in weighted)
    r = random.uniform(0,total)
    upto = 0
    for outcome, w in weighted:
        if upto + w >= r:
            return outcome
        upto += w
    return weighted[-1][0]

# ---------------------- Templates ----------------------
BASE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Web Cricket</title>
  <script src="https://unpkg.com/htmx.org@2.0.2"></script>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-slate-50 text-slate-800">
  <div id="main" class="max-w-3xl mx-auto py-6 px-4">
    <div class="flex items-center gap-3">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M4 20l8-8" stroke="#ef4444" stroke-width="2"/><circle cx="14" cy="6" r="3" fill="#f59e0b"/></svg>
      <h1 class="text-3xl font-bold tracking-tight">Web Cricket</h1>
    </div>
    <p class="text-sm text-slate-500">Bat ball-by-ball. Pick overs, pick vibe, and play.</p>

    <div class="mt-5 grid gap-4">
      <div class="rounded-2xl bg-white shadow p-5">
        {{ scoreboard|safe }}
      </div>
      <div class="rounded-2xl bg-white shadow p-5">
        {{ controls|safe }}
      </div>
      <div class="rounded-2xl bg-white shadow p-5">
        <h2 class="font-semibold mb-2">Commentary</h2>
        <div id="feed" class="space-y-1 text-sm min-h-[64px]">
          {% for line in commentary %}<div>• {{ line }}</div>{% endfor %}
          {% if not commentary %}<div class="text-slate-500">No balls bowled yet. Play a shot!</div>{% endif %}
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

SCORE = """
<div id="scoreboard">
  <div class="flex items-center justify-between">
    <div>
      <div class="text-xl font-semibold">Score: {{ r }}/{{ w }}</div>
      <div class="text-sm text-slate-500">Overs: {{ otext }} • Balls left: {{ left }}</div>
      <div class="text-sm text-slate-500">Player: {{ player }} • Difficulty: {{ diff }}</div>
    </div>
    <div class="text-xs text-slate-500">Game {{ gid[:6] }}…</div>
  </div>
  {% if over %}<div class="mt-3 text-emerald-700 font-medium">Innings complete.</div>{% endif %}
</div>
"""

CONTROLS_SETTINGS = """
<div id="controls">
  <h2 class="font-semibold mb-3">Start a Game</h2>
  <form hx-post="/new" hx-target="#main" hx-swap="outerHTML" class="grid md:grid-cols-3 gap-3">
    <input class="border rounded-xl px-3 py-2" name="player" placeholder="Your name" />
    <select class="border rounded-xl px-3 py-2" name="overs">
      {% for i in range(1,21) %}<option value="{{i}}" {% if i==def_ov %}selected{% endif %}>{{i}} over{{'' if i==1 else 's'}}</option>{% endfor %}
    </select>
    <select class="border rounded-xl px-3 py-2" name="difficulty">
      <option value="easy">Easy</option>
      <option value="medium" selected>Medium</option>
      <option value="hard">Hard</option>
    </select>
    <button class="col-span-full md:col-span-1 px-4 py-2 rounded-xl border bg-slate-900 text-white">Start</button>
  </form>
</div>
"""

CONTROLS_SHOTS = """
<div id="controls">
  <div class="flex items-center justify-between mb-3">
    <h2 class="font-semibold">Select Your Shot</h2>
    <form hx-post="/new" hx-target="#main" hx-swap="outerHTML">
      <input type="hidden" name="player" value="{{ player }}" />
      <input type="hidden" name="overs" value="{{ overs }}" />
      <input type="hidden" name="difficulty" value="{{ difficulty }}" />
      <button class="px-3 py-2 rounded-xl border">New Game</button>
    </form>
  </div>
  <div class="flex flex-wrap gap-2">
    {% for key,label in shots %}
      <button class="px-4 py-2 rounded-xl border hover:shadow transition disabled:opacity-50"
              hx-post="/play" hx-include="#gid" hx-vals='{"shot":"{{key}}"}'
              hx-target="#main" hx-swap="outerHTML" {% if over %}disabled{% endif %}>{{label}}</button>
    {% endfor %}
  </div>
  <form id="gid" class="hidden"><input type="hidden" name="game_id" value="{{ gid }}" /></form>
</div>
"""

# ---------------------- Views ----------------------

def _scoreboard(game:Game):
    inn = game.inn; s = game.settings
    return render_template_string(SCORE,
        r=inn.runs, w=inn.wickets, otext=inn.overs_text(),
        left=inn.balls_left(s.overs), player=s.player, diff=s.difficulty.title(),
        gid=game.id, over=game.over)


def _controls_settings():
    return render_template_string(CONTROLS_SETTINGS, def_ov=DEFAULT_OVERS)


def _controls_shots(game:Game):
    s = game.settings
    return render_template_string(CONTROLS_SHOTS, shots=list(SHOT_LABELS.items()),
                                  gid=game.id, over=game.over,
                                  player=s.player, overs=s.overs, difficulty=s.difficulty)


def _render(game:Game|None, show_settings=False):
    if show_settings or game is None:
        scoreboard = render_template_string(SCORE, r=0,w=0,otext="0.0",left=0,player="-",diff="-",gid="-",over=False)
        controls = _controls_settings()
        commentary = []
    else:
        scoreboard = _scoreboard(game)
        controls = _controls_shots(game)
        commentary = game.commentary[-80:]
    return render_template_string(BASE, scoreboard=scoreboard, controls=controls, commentary=commentary)


def _new_game(player:str, overs:int, difficulty:str) -> Game:
    gid = str(uuid.uuid4())
    g = Game(id=gid, settings=Settings(player=player or 'Player', overs=max(1,min(MAX_OVERS,overs)), difficulty=difficulty))
    GAMES[gid] = g
    session['gid'] = gid
    return g

@app.route("/")
def index():
    gid = session.get('gid')
    game = GAMES.get(gid) if gid else None
    return _render(game, show_settings=(game is None))

@app.post("/new")
def new():
    player = (request.form.get('player') or '').strip() or 'Player'
    overs = int(request.form.get('overs', DEFAULT_OVERS))
    difficulty = request.form.get('difficulty','medium').lower()
    game = _new_game(player, overs, difficulty)
    return _render(game)

@app.post("/play")
def play():
    gid = request.form.get('game_id'); game = GAMES.get(gid)
    if not game: return _render(None, show_settings=True)
    if game.over: return _render(game)

    shot = request.form.get('shot')
    if shot not in SHOT_LABELS: return _render(game)

    ai_ball = random.choice(AI_BALLING_MIX)
    matrix = PROB[(shot, ai_ball)]
    outcome = weighted_choice(matrix, DIFF[game.settings.difficulty])

    msg_base = f"Ball {game.inn.over_ball()} — {game.settings.player} plays {SHOT_LABELS[shot]} to a {BALL_OPTIONS[ai_ball]}: "
    if outcome == 'W':
        game.inn.wickets += 1
        game.commentary.append(msg_base + random.choice(["Gone!","Bowled!","Edged and taken.","Cleaned up."]))
    else:
        r = int(outcome)
        game.inn.runs += r
        phrases = {0:"dot ball.",1:"Yay! You scored one.",2:"Nice! You scored two.",3:"Three runs, well run!",4:"FOUR! Gorgeous timing.",6:"SIX! Out of the park!"}
        game.commentary.append(msg_base + phrases.get(r, f"{r} run(s)."))

    game.inn.balls += 1
    if game.inn.balls >= game.settings.overs*6 or game.inn.wickets >= 10:
        game.over = True
        game.commentary.append(f"Innings complete — {game.inn.runs}/{game.inn.wickets} in {game.inn.overs_text()} overs.")

    return _render(game)

if __name__ == "__main__":
    # Print LAN URL so you can open on your phone (same Wi‑Fi)
    try:
        host_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        host_ip = "127.0.0.1"
    print(f"Web Cricket running → http://127.0.0.1:5000  (LAN: http://{host_ip}:5000)")
    app.run(host="0.0.0.0", port=5000, debug=True)
