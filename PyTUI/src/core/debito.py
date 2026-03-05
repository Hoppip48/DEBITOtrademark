"""
debit_game.py — DEBITO™ Card Game (PvP)

A two-player card game where players exchange cards, reveal their plays,
and accumulate or reduce "DEBITO™" points based on hand outcomes.
"""

import os
import random
from collections import Counter
from dataclasses import dataclass, field

from ascii_cards.cards import get_card

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

QUIT_COMMANDS = {"exit", "Exit", "quit", "q", "Quit"}

# Figure (non-numeric) card ranks, including Joker
FIGURES = {"J", "Q", "K", "JK"}

# DEBITO™ point values for each rank
DEBITO_VALUES = {
    "A": 1, "2": 2, "3": 3, "4": 4, "5": 5,
    "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 5, "Q": 6, "K": 0,
}

# Ranks that Q beats (even numerals + J), and ranks that J beats (odd numerals)
_q_beats = {str(r) for r in range(10) if r % 2 == 0}
_q_beats.add("J")
SPECIAL_WINS = {
    "J": {str(r) for r in range(10) if r % 2 != 0},  # J beats odd numerals
    "Q": _q_beats,                                     # Q beats even numerals + J
}

HAND_SIZE = 4           # Maximum cards a player holds in their hand
TABLE_HAND_SIZE = 4     # Maximum cards a player can have on the table
INITIAL_DEBITO = 11     # Starting DEBITO™ for each player
CARD_WIDTH = 11         # Width of a single ASCII card (used for alignment)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Card:
    """Represents a single playing card."""
    rank: str
    suit: str
    is_faceup: bool = True

    def __repr__(self):
        return f"{self.rank}{self.suit}"

    def get_card(self):
        """Return the ASCII art representation via the ascii_cards library."""
        return get_card(self.rank, self.suit, self.is_faceup)


@dataclass
class Player:
    """Holds all mutable state for one player during a game."""
    hand: list = field(default_factory=list)          # Cards in hand
    table_hand: list = field(default_factory=list)    # Cards on the table
    exchanged_card: Card = None                        # Card chosen to give away this turn
    played_cards: list = field(default_factory=list)  # Cards played this round
    debito: int = INITIAL_DEBITO                       # Current DEBITO™ score
    bonus_discard: int = 0                             # Extra discards earned from table cards


# ---------------------------------------------------------------------------
# Game State
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    """
    Central object containing the full state of an ongoing game:
    the deck, both players, the discard pile, and the turn counter.
    """
    deck: list
    p1: Player
    p2: Player
    discarded_pile: list = field(default_factory=list)
    turn: int = 0

    # --- Display Helpers ----------------------------------------------------

    def layout_print(self, player: Player, player_tag: str):
        """Print a player's current table cards, hand cards, and game stats."""

        # Table cards (positions HAND_SIZE+1 … HAND_SIZE+n)
        print(player_tag + f"Current table card(s): {len(player.table_hand)}")
        card_viz = [c.get_card().splitlines() for c in player.table_hand]
        for i, card_lines in enumerate(card_viz):
            card_lines.append(f" {i + 1 + HAND_SIZE} ".center(CARD_WIDTH, "-"))
        if card_viz:
            for row in zip(*card_viz):
                print(" ".join(row))
        print()

        # Hand cards (positions 1 … n)
        print(player_tag + f"Current hand card(s): {len(player.hand)}")
        card_viz = [c.get_card().splitlines() for c in player.hand]
        for i, card_lines in enumerate(card_viz):
            card_lines.append(f" {i + 1} ".center(CARD_WIDTH, "-"))
        if card_viz:
            for row in zip(*card_viz):
                print(" ".join(row))
        print()

        # Score / deck info
        print(player_tag + f"Current DEBITO™: {player.debito}")
        print(player_tag + f"Card(s) left in the Deck: {len(self.deck)}")
        print(player_tag + f"Discard pile size: {len(self.discarded_pile)}\n")

    def showdown_print(self):
        """Print both players' played cards face-to-face for the showdown."""
        print("\n" + " SHOWDOWN RESULT: ".center(30, "*") + "\n")

        print("PLAYER 2")
        p2_viz = [c.get_card().splitlines() for c in self.p2.played_cards]
        if p2_viz:
            for row in zip(*p2_viz):
                print(" ".join(row))

        sep_len = (CARD_WIDTH + 1) * max(
            len(self.p2.played_cards), len(self.p1.played_cards), 1
        )
        print("x".center(sep_len, "-"))

        p1_viz = [c.get_card().splitlines() for c in self.p1.played_cards]
        if p1_viz:
            for row in zip(*p1_viz):
                print(" ".join(row))
        print("PLAYER 1\n")

    def turn_log(self):
        """Print the full discard history (turn-by-turn played cards)."""
        print("TURN\t\tP1 x P2")
        for i, entry in enumerate(self.discarded_pile):
            print(f"\t{i + 1}\t\t{entry}")

    # --- Turn Logic ---------------------------------------------------------

    def turn_init(self):
        """
        Run the setup phase for a new turn:
          1. Increment turn counter.
          2. For each player (in order): draw up to HAND_SIZE cards, display
             the layout, and ask them to choose a card to exchange.
          3. Swap the two chosen cards onto the opponents' table hands.
        """
        self.turn += 1
        print(f"\n***** TURN {self.turn}:\n")

        for i, player in enumerate([self.p1, self.p2]):
            player_tag = f"(Player {i + 1}) "

            print(player_tag + f"PLAYER {i + 1}'S TURN: PRESS A KEY TO START.")
            input(">> ")

            # Draw cards until the hand is full (up to HAND_SIZE)
            draw_count = 0
            while len(player.hand) < HAND_SIZE and self.deck:
                player.hand.append(self.deck.pop())
                draw_count += 1
            if draw_count:
                print(player_tag + f"Drawn {draw_count} card(s) from the Deck.\n")

            self.layout_print(player, player_tag)

            # Ask the player to pick a card from their hand to give away
            print(player_tag + f"Choose a card to give to your opponent: [1-{len(player.hand)}]")
            while True:
                raw = input(">> ").strip()
                if not raw.isdigit():
                    print(player_tag + "Please enter a number.")
                    continue
                choice = int(raw) - 1
                if get_card_by_pos(player.hand, choice) is not None:
                    break
                print(player_tag + "Card not present in your hand. Try again:")

            player.exchanged_card = player.hand.pop(choice)
            clear_terminal()

        # Deliver the exchanged cards to each opponent's table
        self.p1.table_hand.append(self.p2.exchanged_card)
        self.p2.table_hand.append(self.p1.exchanged_card)

    def play_selection(self, player: Player, pos: int, joker_ex: bool = False):
        """
        Ask `player` (displayed as "Player {pos}") to choose a card (or cards,
        when they hold duplicates) to play this round.

        Args:
            player:    The Player instance making the selection.
            pos:       Display number for this player (1 or 2).
            joker_ex:  If True, the card is added to played_cards without
                       removing it from hand/table (Joker copy mechanic).
        """
        player_tag = f"(Player {pos}) "

        print("\n" + player_tag + f"PLAYER {pos}'S TURN: PRESS A KEY TO START.")
        input(">> ")

        self.layout_print(player, player_tag)

        # Build a unified positional list: [hand cards…, None padding…, table cards…]
        total_hand = (
            player.hand
            + [None] * (HAND_SIZE - len(player.hand))
            + player.table_hand
        )

        # Primary card selection
        print(player_tag + "Choose a card to play:")
        while True:
            raw = input(">> ").strip()
            if not raw.isdigit():
                print(player_tag + "Please enter a number.")
                continue
            sel_card = [get_card_by_pos(total_hand, int(raw) - 1)]
            if sel_card[0] is not None:
                break
            print(player_tag + "Card not present in your hand. Try again:")

        # If the chosen card is a numeral, check for duplicates and allow
        # the player to play multiple copies at once
        if sel_card[0].rank not in FIGURES:
            counts = Counter(card.rank for card in total_hand if card is not None)
            if counts[sel_card[0].rank] > 1:
                print(
                    player_tag
                    + f"There are multiple copies of {sel_card[0].rank} in your hand. "
                    + "Choose the exact card(s) you'd like to play (space-separated positions):"
                )
                extras = input(">> ").split()
                for raw_pos in extras:
                    if not raw_pos.isdigit():
                        continue
                    card = get_card_by_pos(total_hand, int(raw_pos) - 1)
                    if card is not None and card.rank == sel_card[0].rank:
                        sel_card.append(card)

        if joker_ex:
            # Joker copy: record the card without consuming it from the hand
            player.played_cards.extend(sel_card)
        else:
            # Normal play: remove from hand or table, tracking table-card plays
            for card in sel_card:
                if card in player.hand:
                    player.hand.remove(card)
                else:
                    player.table_hand.remove(card)
                    player.bonus_discard += 1  # Playing a table card grants a bonus discard
                player.played_cards.append(card)

        clear_terminal()

    # --- Round Resolution ---------------------------------------------------

    def debito_calculation(self):
        """
        Resolve the current round:
          1. Show the showdown.
          2. Handle Joker copy selections if needed.
          3. Calculate which player wins and by how much.
          4. Apply DEBITO™ changes.
          5. Record the round in the discard pile.
          6. Clean up played cards.
        """
        self.showdown_print()

        # Joker exception: the Joker player picks a card in hand to "copy"
        if self.p1.played_cards[0].rank == "JK":
            print("Player 1 played a Joker! They must choose a card in their hand to copy.")
            self.play_selection(self.p1, 1, joker_ex=True)

        if self.p2.played_cards[0].rank == "JK":
            print("Player 2 played a Joker! They must choose a card in their hand to copy.")
            self.play_selection(self.p2, 2, joker_ex=True)

        result, delta = debito_calc(self.p1.played_cards, self.p2.played_cards)

        print("\n***** RESULT:")
        if result == "TIE":
            print("The hand was a TIE! No one loses DEBITO™.")
        elif result == "P1":
            print(f"P1 wins the hand! P2 DEBITO™ increases by {delta}.")
            self.p2.debito += delta
            self.p1.debito -= delta
        else:  # P2
            print(f"P2 wins the hand! P1 DEBITO™ increases by {delta}.")
            self.p1.debito += delta
            self.p2.debito -= delta

        print(f"\nP1's new DEBITO™: {self.p1.debito}")
        print(f"P2's new DEBITO™: {self.p2.debito}")

        # TODO: implement bonus discard logic (award extra discards)
        if self.p1.bonus_discard:
            pass
        if self.p2.bonus_discard:
            pass

        # Record this round as "P1cards x P2cards" in the discard pile
        p1_str = "".join(map(str, self.p1.played_cards))
        p2_str = "".join(map(str, self.p2.played_cards))
        self.discarded_pile.append(f"{p1_str} x {p2_str}")

        # Clear played cards for the next round
        self.p1.played_cards.clear()
        self.p2.played_cards.clear()

        print('\nInput "log" to check the discard pile or press any key to continue.')
        if input(">> ").strip().lower() == "log":
            self.turn_log()


# ---------------------------------------------------------------------------
# Standalone Helper Functions
# ---------------------------------------------------------------------------

def clear_terminal():
    """Clear the terminal screen (works on both Windows and Unix-like OSes)."""
    os.system("cls" if os.name == "nt" else "clear")


def rules():
    """Read and print the rules from the assets file."""
    with open("./../../.assets/rules.txt") as f:
        print(f.read())


def deck_generation() -> list:
    """
    Build and return a standard 52-card deck plus two Jokers (54 cards total).
    Each card is a Card dataclass instance.
    """
    SUITS = ["♠", "♥", "♦", "♣"]
    RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

    deck = [Card(rank=r, suit=s) for r in RANKS for s in SUITS]
    deck.append(Card(rank="JK", suit="☆"))  # Standard Joker
    deck.append(Card(rank="JK", suit="★"))  # Wild Joker
    return deck


def get_card_by_pos(hand: list, pos: int):
    """
    Return the card at index `pos` in `hand`, or None if out of range or None slot.

    Args:
        hand: List of Card objects (may contain None padding slots).
        pos:  Zero-based index.

    Returns:
        The Card at that position, or None.
    """
    if 0 <= pos < len(hand):
        return hand[pos]
    return None


def debito_calc(c_list1: list, c_list2: list) -> tuple:
    """
    Determine the winner of a round and the DEBITO™ delta.

    Evaluation order:
      1. King special rules (K beats everything except A, which beats K for 7pts).
      2. Both figures  → J always loses to Q; identical figures → TIE.
      3. Figure vs. numeral → check SPECIAL_WINS to see if the figure beats it.
      4. Both numerals → compare totals (rank × count); higher total wins.

    Args:
        c_list1: Cards played by Player 1 (index 0 is the primary card).
        c_list2: Cards played by Player 2 (index 0 is the primary card).

    Returns:
        ("P1" | "P2" | "TIE", delta: int)
    """
    r1 = c_list1[0].rank
    r2 = c_list2[0].rank

    # --- King special rule ---
    # K beats everything; if the opponent played A, the Ace beats K for 7 pts.
    if r1 == "K" and r2 != "K":
        return ("P2", 7) if r2 == "A" else ("P1", DEBITO_VALUES["K"])
    if r2 == "K" and r1 != "K":
        return ("P1", 7) if r1 == "A" else ("P2", DEBITO_VALUES["K"])

    # Determine whether each player played a numeral
    is_num1 = r1 not in FIGURES
    is_num2 = r2 not in FIGURES

    # Calculate numeral totals (Ace counts as 1 per copy)
    if is_num1:
        l1_tot = len(c_list1) if r1 == "A" else int(r1) * len(c_list1)
    if is_num2:
        l2_tot = len(c_list2) if r2 == "A" else int(r2) * len(c_list2)

    if not is_num1 and not is_num2:
        # --- Both figures ---
        if r1 == r2:
            return ("TIE", 0)
        # J always loses when facing any other figure
        if r1 == "J":
            return ("P2", DEBITO_VALUES["J"])
        return ("P1", DEBITO_VALUES["J"])

    elif is_num1 and not is_num2:
        # --- P1 numeral vs P2 figure ---
        # Special-win figures beat their designated numeral ranks
        if r1 in SPECIAL_WINS.get(r2, set()):
            return ("P2", DEBITO_VALUES[r2])
        return ("P1", DEBITO_VALUES[r2])

    elif is_num2 and not is_num1:
        # --- P2 numeral vs P1 figure ---
        if r2 in SPECIAL_WINS.get(r1, set()):
            return ("P1", DEBITO_VALUES[r1])
        return ("P2", DEBITO_VALUES[r1])

    else:
        # --- Both numerals: compare totals ---
        if l1_tot == l2_tot:
            return ("TIE", 0)
        if l1_tot > l2_tot:
            return ("P1", DEBITO_VALUES[r2])
        return ("P2", DEBITO_VALUES[r1])


def clamp_debito(debito: int) -> int:
    """
    Clamp a DEBITO™ value to the valid range [0, 2 * INITIAL_DEBITO].

    Args:
        debito: Raw DEBITO™ score to clamp.

    Returns:
        Clamped integer value.
    """
    return max(0, min(debito, 2 * INITIAL_DEBITO))


# ---------------------------------------------------------------------------
# Game Entry Points
# ---------------------------------------------------------------------------

def pvp_game():
    """
    Run a full Player-vs-Player game:
      - Generate and shuffle the deck.
      - Deal HAND_SIZE cards to each player.
      - Loop turns until one player reaches 0 DEBITO™ or the deck runs out.
      - Announce the winner.
    """
    # Initialise game state
    game_state = GameState(deck=deck_generation(), p1=Player(), p2=Player())
    random.shuffle(game_state.deck)

    # Deal initial hands, alternating between players
    for i in range(2 * HAND_SIZE):
        if i % 2 == 0:
            game_state.p1.hand.append(game_state.deck.pop())
        else:
            game_state.p2.hand.append(game_state.deck.pop())

    print("\n" + " GAME START ".center(50, "*") + "\n")

    # Main game loop: continue while both players have DEBITO™ remaining
    while game_state.p1.debito > 0 and game_state.p2.debito > 0:
        cards_needed = HAND_SIZE * 2 - (
            len(game_state.p1.hand) + len(game_state.p2.hand)
        )
        if cards_needed > len(game_state.deck):
            print("The Deck is out of cards. The game ends now!")
            break

        game_state.turn_init()
        game_state.play_selection(game_state.p1, 1)
        game_state.play_selection(game_state.p2, 2)
        game_state.debito_calculation()

    # Determine and announce the winner
    d1 = clamp_debito(game_state.p1.debito)
    d2 = clamp_debito(game_state.p2.debito)

    if d1 > d2:
        winner = "PLAYER 1"
    elif d2 > d1:
        winner = "PLAYER 2"
    else:
        winner = "TIE"

    print("\n***** GAME RESULT:")
    print(f"Player 1: {d1} DEBITO™")
    print(f"Player 2: {d2} DEBITO™")
    print(f"WINNER: {winner}!")
    print('\nPress "1" to play a new game or "3" to quit.')


def main():
    """
    Entry point: display the title screen and main menu, then
    dispatch to game modes or quit based on player input.
    """
    with open("./../../.assets/title-art.txt") as f:
        print(f.read())

    print("  Welcome to DEBITO™ card game!  ".center(50, "*") + "\n")
    print(
        "------ Please choose an option:\n\n"
        "1 -> Play\n"
        "2 -> Rules\n"
        "3 -> Quit\n"
    )

    while True:
        command = input(">> ").strip()

        if command == "3" or command in QUIT_COMMANDS:
            print("Thanks for playing DEBITO™. Goodbye!")
            break
        elif command == "1":
            pvp_game()
        elif command == "2":
            rules()
        elif command == "":
            continue
        elif command in {"help", "h"}:
            print("TO BE ADDED.")
        else:
            print('Command not recognised. Type "help" for the command list.')


if __name__ == "__main__":
    main()
