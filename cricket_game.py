#!/usr/bin/env python3
"""
Text Cricket Game — Single Match (Limited Overs)
Author: ChatGPT

How to run:
    python cricket_game.py

What it has:
- Toss, choose to bat/bowl
- Choose number of overs (1–20)
- Ball‑by‑ball play for two innings
- You pick a shot when batting (Defend / Normal / Aggressive)
- You pick a delivery when bowling (Good length / Short / Yorker)
- Realistic-ish outcomes: dots, 1/2/3/4/6, wickets
- Strike rotation, over changes, wickets (out of 10)
- Target/Chase logic for the 2nd innings

Notes:
- Keep inputs short: d = defend, n = normal, a = aggressive, g = good, s = short, y = yorker
- Press Enter to accept defaults shown in [brackets].
- This is a simple probabilities-based game intended for fun, not a simulator.

Have fun!
"""

import random
from dataclasses import dataclass
from typing import Optional, Tuple

# ---------------------- Utility & Models ----------------------

SHOT_OPTIONS = {
    'd': 'Defend',
    'n': 'Normal',
    'a': 'Aggressive',
}

BALL_OPTIONS = {
    'g': 'Good length',
    's': 'Short',
    'y': 'Yorker',
}

@dataclass
class InningsState:
    runs: int = 0
    wickets: int = 0
    balls_bowled: int = 0  # total balls including completed overs
    overs_limit: int = 6   # default 1 over (6 balls); we will set later
    striker: str = "Striker"
    non_striker: str = "Non-striker"

    def balls_remaining(self) -> int:
        return self.overs_limit * 6 - self.balls_bowled

    def overs_as_text(self) -> str:
        return f"{self.balls_bowled // 6}.{self.balls_bowled % 6}"

# Outcome probabilities tuned by matchup of shot vs ball
# Each entry returns a list of (outcome, weight)
# Outcome is from {"W": wicket, 0,1,2,3,4,6}

# Baseline matrices — rough cricket feel
PROB_MATRIX = {
    ('d', 'g'): [('W', 2), (0, 55), (1, 30), (2, 10), (3, 1), (4, 2), (6, 0)],
    ('d', 's'): [('W', 3), (0, 50), (1, 30), (2, 10), (3, 2), (4, 4), (6, 1)],
    ('d', 'y'): [('W', 2), (0, 58), (1, 32), (2, 6),  (3, 0), (4, 2), (6, 0)],

    ('n', 'g'): [('W', 6), (0, 35), (1, 28), (2, 14), (3, 3), (4, 10), (6, 4)],
    ('n', 's'): [('W', 8), (0, 30), (1, 24), (2, 14), (3, 4), (4, 12), (6, 8)],
    ('n', 'y'): [('W', 7), (0, 38), (1, 27), (2, 9),  (3, 1), (4, 11), (6, 7)],

    ('a', 'g'): [('W', 12), (0, 22), (1, 18), (2, 12), (3, 5), (4, 16), (6, 15)],
    ('a', 's'): [('W', 14), (0, 20), (1, 14), (2, 10), (3, 6), (4, 18), (6, 18)],
    ('a', 'y'): [('W', 16), (0, 26), (1, 14), (2, 8),  (3, 2), (4, 16), (6, 18)],
}

AI_BALLING_MIX = ['g'] * 6 + ['s'] * 3 + ['y'] * 3  # bias to good length
AI_SHOT_MIX = ['n'] * 6 + ['a'] * 4 + ['d'] * 2      # bias to normal/aggressive


def weighted_choice(pairs):
    outcomes, weights = zip(*pairs)
    total = sum(weights)
    r = random.uniform(0, total)
    upto = 0
    for outcome, w in pairs:
        if upto + w >= r:
            return outcome
        upto += w
    return outcomes[-1]

# ---------------------- Core Engine ----------------------

def play_ball_batting(user_shot: str, ai_ball: str) -> Tuple[str, int]:
    matrix = PROB_MATRIX[(user_shot, ai_ball)]
    outcome = weighted_choice(matrix)
    if outcome == 'W':
        return ('W', 0)
    else:
        return ('R', int(outcome))


def play_ball_bowling(user_ball: str, ai_shot: str) -> Tuple[str, int]:
    matrix = PROB_MATRIX[(ai_shot, user_ball)]
    outcome = weighted_choice(matrix)
    if outcome == 'W':
        return ('W', 0)
    else:
        return ('R', int(outcome))


def rotate_strike_if_needed(state: InningsState, runs_scored: int):
    if runs_scored % 2 == 1:
        state.striker, state.non_striker = state.non_striker, state.striker


def end_of_over(state: InningsState):
    state.striker, state.non_striker = state.non_striker, state.striker


def print_score(state: InningsState, target: Optional[int] = None):
    need_txt = ""
    if target is not None:
        to_get = target - state.runs
        if to_get > 0:
            need_txt = f" | Target: {target} (need {to_get} off {state.balls_remaining()} balls)"
        else:
            need_txt = f" | Target: {target} (achieved)"
    print(f"Score: {state.runs}/{state.wickets} in {state.overs_as_text()} overs{need_txt}")

# ---------------------- Input Helpers ----------------------

def ask_choice(prompt: str, valid: dict, default_key: Optional[str] = None) -> str:
    keys = "/".join(valid.keys())
    default_br = f"[{default_key}]" if default_key else ""
    while True:
        raw = input(f"{prompt} ({keys}) {default_br}: ").strip().lower()
        if not raw and default_key:
            raw = default_key
        if raw in valid:
            return raw
        print(f"Invalid. Choose one of: {keys}")


def ask_int(prompt: str, lo: int, hi: int, default: Optional[int] = None) -> int:
    default_br = f"[{default}]" if default is not None else ""
    while True:
        raw = input(f"{prompt} {default_br}: ").strip()
        if not raw and default is not None:
            return default
        try:
            val = int(raw)
            if lo <= val <= hi:
                return val
        except ValueError:
            pass
        print(f"Enter a number between {lo} and {hi}.")

# ---------------------- Innings Loops ----------------------

def play_innings_user_batting(overs: int, target: Optional[int] = None) -> InningsState:
    state = InningsState(overs_limit=overs)
    print("\n--- Your Batting Innings ---")
    while state.balls_bowled < overs * 6 and state.wickets < 10:
        over_ball = f"{state.balls_bowled // 6 + 1}.{state.balls_bowled % 6 + 1}"
        ai_ball = random.choice(AI_BALLING_MIX)
        shot = ask_choice(f"Ball {over_ball} — choose shot: Defend(d)/Normal(n)/Aggressive(a)", SHOT_OPTIONS, 'n')
        code, runs = play_ball_batting(shot, ai_ball)
        if code == 'W':
            state.wickets += 1
            print(f"  Bowled {BALL_OPTIONS[ai_ball]} — OUT! {state.striker} gone.")
        else:
            state.runs += runs
            print(f"  Bowled {BALL_OPTIONS[ai_ball]} — You scored {runs}.")
            rotate_strike_if_needed(state, runs)
        state.balls_bowled += 1

        # Check chase
        if target is not None and state.runs > target:
            break

        if state.balls_bowled % 6 == 0 and state.balls_bowled < overs * 6:
            print("--- End of over ---")
            end_of_over(state)
        print_score(state, target)
    print("Innings complete.")
    print_score(state, target)
    return state


def play_innings_user_bowling(overs: int, target: Optional[int] = None) -> InningsState:
    state = InningsState(overs_limit=overs)
    print("\n--- Your Bowling Innings ---")
    while state.balls_bowled < overs * 6 and state.wickets < 10:
        over_ball = f"{state.balls_bowled // 6 + 1}.{state.balls_bowled % 6 + 1}"
        ball = ask_choice(f"Ball {over_ball} — bowl: Good(g)/Short(s)/Yorker(y)", BALL_OPTIONS, 'g')
        ai_shot = random.choice(AI_SHOT_MIX)
        code, runs = play_ball_bowling(ball, ai_shot)
        if code == 'W':
            state.wickets += 1
            print(f"  {BALL_OPTIONS[ball]} — WICKET! {state.striker} out.")
        else:
            state.runs += runs
            print(f"  {BALL_OPTIONS[ball]} — Batter scored {runs}.")
            rotate_strike_if_needed(state, runs)
        state.balls_bowled += 1

        # Check defense if you are bowling second
        if target is not None and state.runs > target:
            break

        if state.balls_bowled % 6 == 0 and state.balls_bowled < overs * 6:
            print("--- End of over ---")
            end_of_over(state)
        print_score(state, target)
    print("Innings complete.")
    print_score(state, target)
    return state

# ---------------------- Match Controller ----------------------

def toss() -> Tuple[str, str]:
    call = ask_choice("Toss time! Call Heads or Tails (h/t)", {'h': 'Heads', 't': 'Tails'}, 'h')
    flip = random.choice(['h', 't'])
    if call == flip:
        print(f"You won the toss (it was { 'Heads' if flip=='h' else 'Tails' }).")
        choice = ask_choice("Bat or Bowl first? (bowl=bl)", {'bat': 'Bat', 'bowl': 'Bowl', 'bl': 'Bowl'}, 'bat')
        if choice == 'bl':
            choice = 'bowl'
        return ('user', choice)
    else:
        print(f"You lost the toss (it was { 'Heads' if flip=='h' else 'Tails' }).")
        # Simple AI: prefers to bat first in short games, bowl first otherwise
        ai_choice = 'bat'
        print(f"AI chooses to {ai_choice} first.")
        return ('ai', ai_choice)


def play_match():
    print("\nWelcome to Text Cricket! 🏏")
    # Optional seed for reproducibility
    seed_ans = input("Enter a random seed for reproducibility (or press Enter to skip): ").strip()
    if seed_ans:
        try:
            random.seed(int(seed_ans))
        except ValueError:
            random.seed(seed_ans)
    overs = ask_int("How many overs per side? (1–20)", 1, 20, 2)

    winner, decision = toss()

    user_bats_first = (winner == 'user' and decision == 'bat') or (winner == 'ai' and decision != 'bat')

    if user_bats_first:
        first = play_innings_user_batting(overs)
        target = first.runs
        print("\n=== Innings Break ===")
        print(f"Target for AI: {target + 1}")
        second = play_innings_user_bowling(overs, target=target)
        user_score, ai_score = first.runs, second.runs
    else:
        first = play_innings_user_bowling(overs)
        target = first.runs
        print("\n=== Innings Break ===")
        print(f"Target for You: {target + 1}")
        second = play_innings_user_batting(overs, target=target)
        user_score, ai_score = second.runs, first.runs

    print("\n=== Match Result ===")
    if user_score > ai_score:
        margin = user_score - ai_score
        print(f"You win by {margin} runs! 🎉")
    elif user_score < ai_score:
        margin = 10 - second.wickets if user_bats_first else 10 - first.wickets
        # If chasing team wins, report wickets remaining if possible
        if (user_bats_first and ai_score > user_score) or (not user_bats_first and user_score > ai_score):
            wkts_in_hand = max(0, 10 - (second.wickets if user_bats_first else first.wickets))
            if user_bats_first:
                print(f"AI wins by {wkts_in_hand} wickets. 😑")
            else:
                print(f"You win by {wkts_in_hand} wickets! 🎉")
        else:
            print("They edge it. Tough luck!")
    else:
        print("It’s a tie! Rare scenes.")


if __name__ == "__main__":
    try:
        play_match()
    except KeyboardInterrupt:
        print("\nMatch abandoned (user quit).")
