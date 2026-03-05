import os
from collections import Counter
from operator import attrgetter
import random as rand
from dataclasses import dataclass, field
from ascii_cards.cards import get_card

QUIT_COMMANDS = {"exit", "Exit", "quit", "q", "Quit"}
FIGURES = {"J", "Q", "K", "JK"}
DEBITO_VALUES = {"A": 1, "2": 2, "3": 3, "4": 4, "5": 5,
                 "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
                 "J": 5, "Q": 6, "K": 0
                 }
q_set = {str(r) for r in range(10) if r % 2 == 0}
q_set.add("J")
SPECIAL_WINS = {"J": {str(r) for r in range(10) if r % 2 != 0}, "Q": q_set}

HAND_SIZE = 4
TABLE_HAND_SIZE = 4
INITIAL_DEBITO = 11
CARD_WIDTH = 11

@dataclass 
class Card: 
    rank: str
    suit: str
    is_faceup: bool = True

    def __repr__(self):
        return f"{self.rank}{self.suit}"

    def get_card(self): # Wrapper for ascii_cards get_card() function
        return get_card(self.rank, self.suit, self.is_faceup)

@dataclass
class Player:
    hand: list = field(default_factory = list)
    table_hand: list = field(default_factory = list)
    exchanged_card: Card = None
    played_cards: list = field(default_factory = list)
    debito: int = INITIAL_DEBITO
    bonus_discard: int = 0




@dataclass
class GameState:
    deck: list
    p1: Player
    p2: Player
    discarded_pile: list = field(default_factory = list)
    turn: int = 0

    def layout_print(self, player, player_tag):
        print(player_tag + f"Current table card(s): {len(player.table_hand)}")

        card_viz = [c.get_card().splitlines() for c in player.table_hand]  
        for i, card_lines in enumerate(card_viz):
            card_lines.append(f" {i+1+HAND_SIZE} ".center(CARD_WIDTH, "-"))
        for row in zip(*card_viz):
            print(" ".join(row))
        print()

        print(player_tag + f"Current hand card(s): {len(player.hand)}")   

        card_viz = [c.get_card().splitlines() for c in player.hand]
        for i, card_lines in enumerate(card_viz):
            card_lines.append(f" {i+1} ".center(CARD_WIDTH, "-"))
        for row in zip(*card_viz):
            print(" ".join(row))
        print()

        print(player_tag + f"Current DEBITO: {player.debito}")
        print(player_tag + f"Card(s) left in the Deck: {len(self.deck)}")
        print(player_tag + f"Discard pile size: {len(self.discarded_pile)}\n")

    def showdown_print(self):
        print("\n" + " SHOWDOWN RESULT: ".center(30, "*") + "\n")

        print("PLAYER 2")
        card_viz = [c.get_card().splitlines() for c in self.p2.played_cards] 
        for row in zip(*card_viz):
            print(" ".join(row))

        sep_line_len = (CARD_WIDTH+1) * max(len(self.p2.played_cards), len(self.p1.played_cards))
        print("x".center(sep_line_len, "-"))

        card_viz = [c.get_card().splitlines() for c in self.p1.played_cards] 
        for row in zip(*card_viz):
            print(" ".join(row))
        print("PLAYER 1\n")


    def turn_init(self):
        self.turn += 1
        print(f"\n***** TURN {self.turn}:\n")

        for i in range(2):
            if i == 0:
                player = self.p1
            else:
                player = self.p2

            player_tag = f"(Player {i+1}) "
    
            print(player_tag + f"PLAYER {i+1}'S TURN: PRESS A KEY TO START.")
            #TODO: input manager function   
            input(">> ")

            # Draw
            draw_count = 0
            if len(player.hand) + len(player.table_hand) < HAND_SIZE:
                while len(player.hand) < HAND_SIZE:
                    player.hand.append(self.deck.pop())
                    draw_count += 1
                print(player_tag + f"Drawn {draw_count} card(s) from the Deck.\n")

            #TODO: LAYOUT PRINT (TEXTUALIZE)  
            self.layout_print(player, player_tag)

            # Exchange cards
            print(player_tag + f"Choose a card to give to your opponent: [1-{len(player.hand)}]")

            #TODO: input manager function
            while True:
                ex_choice = int(input(">> ")) - 1
                if get_card_by_pos(player.hand, ex_choice) != None:
                    break 
                print(player_tag + "Card not present in your hand. Try again:")

            player.exchanged_card = player.hand.pop(ex_choice)

            clear_terminal()

        self.p1.table_hand.append(self.p2.exchanged_card)
        self.p2.table_hand.append(self.p1.exchanged_card)


    def play_selection(self, player, pos, joker_ex = False):  

        player_tag = f"(Player {pos}) "

        print("\n" + player_tag + f"PLAYER {pos}'S TURN: PRESS A KEY TO START.")
        #TODO: input manager function   
        input(">> ")
        
        #TODO: LAYOUT PRINT (TEXTUALIZE)  
        self.layout_print(player, player_tag)

        total_hand = player.hand + [None] * (HAND_SIZE - len(player.hand)) + player.table_hand

        # Card-to-play selection
        print(player_tag + f"Choose a card to play:")
        #TODO: input manager function
        while True:
            sel_card = [get_card_by_pos(total_hand, int(input(">> ")) - 1)]
            if sel_card[0] != None:
                break 
            print(player_tag + "Card not present in your hand. Try again:")
        
        # Check if the player has duplicates (numericals only)
        if sel_card[0].rank not in FIGURES:
            counts = Counter(card.rank for card in total_hand if card != None)
            dupe_dict = {rank: count for rank, count in counts.items() if count > 1}

            if sel_card[0].rank in dupe_dict: 
                print(player_tag + f"There are multiple copy of {sel_card[0].rank} in your hand." + 
                    "choose the exact card(s) you'd like to play (even multiples):")
                mul_cards = input(">> ").split(" ")
                sel_card += [card for pos in mul_cards 
                             if (card := get_card_by_pos(total_hand, int(pos))) is not None
                                and card.rank == sel_card[0].rank]

        if joker_ex:
            for c in sel_card:
                    player.played_cards.append(c)
        else:
            for c in sel_card:
                try:
                    player.hand.remove(c)
                    player.played_cards.append(c)
                except ValueError:
                    player.table_hand.remove(c)
                    player.played_cards.append(c)
                    player.bonus_discard += 1

        clear_terminal()


    def debito_calculation(self):

        #TODO: LAYOUT PRINT (TEXTUALIZE)
        self.showdown_print()

        # Joker exception
        if self.p1.played_cards[0].rank == "JK":
            print("Player 1 has played a Joker card. They must choose a card in their hand to copy.")
            self.play_selection(self.p1, 1, joker_ex=True)

        if self.p2.played_cards[0].rank == "JK":
            print("Player 2 has played a Joker card. They must choose a card in their hand to copy.")
            self.play_selection(self.p2, 2, joker_ex=True)     

        m_result = debito_calc(self.p1.played_cards, self.p2.played_cards)

        print("\n***** RESULT: ")
        if m_result[0] == "TIE":
            print("The hand was a TIE! No one loses DEBITO™.")
        elif m_result[0] == "P1":
            print(f"P1 wins the hand! P1 DEBITO™ decreases by {m_result[1]}.")
            self.p2.debito += m_result[1]
            self.p1.debito -= m_result[1]
        else:
            print(f"P2 wins the hand! P2 DEBITO™ decreases by {m_result[1]}.")
            self.p1.debito += m_result[1]
            self.p2.debito -= m_result[1]
        print(f"\nP1's new DEBITO™: {self.p1.debito}")
        print(f"\nP2's new DEBITO™: {self.p2.debito}")

        # Discard bonus
        if self.p1.bonus_discard != 0:
            #TODO:
            print()
        if self.p2.bonus_discard != 0:
            #TODO:
            print()

        # Clean up
        self.discarded_pile.append("".join(map(str, self.p1.played_cards)) + " x " + "".join(map(str, self.p2.played_cards)))

        self.p1.played_cards.clear()
        self.p2.played_cards.clear()

        print("Input \"log\" to check the discard pile or press any key to move to the next turn.")
        if input(">> ") == "log":
            self.turn_log()


    def turn_log(self):
        print("TURN\t\tP1 x P2")
        for i, turn in enumerate(self.discarded_pile):
            print(f"\t{i+1}\t\t{discard.pile[turn]}")



def clear_terminal(): # OS invariant
    os.system('cls' if os.name == "nt" else 'clear')


def rules(): 
    rules = open("./../../.assets/rules.txt")
    print(rules.read())


def deck_generation():
    SUITS = ["♠", "♥", "♦", "♣"] 
    RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

    deck = [Card(rank = r, suit = s) for r in RANKS for s in SUITS] 
    # Add the Jokers
    deck.append(Card(rank = "JK", suit = "☆")) 
    deck.append(Card(rank = "JK", suit = "★"))

    return deck


def get_card_by_pos(hand, pos):
    if 0 <= pos < len(hand):
        return hand[pos]

    return None


def debito_calc(c_list1, c_list2):
    # King exception:
    if (c_list1[0].rank == "K" and c_list2[0].rank != "K"):
        if(c_list2[0].rank == "A"):
            return ("P2", 7)
        else:
            return ("P1", DEBITO_VALUES["K"])

    elif (c_list2[0].rank == "K" and c_list1[0].rank != "K"):
        if(c_list1[0].rank == "A"):
            return ("P1", 7)
        else:
            return ("P2", DEBITO_VALUES["K"])

    is_num1 = False
    is_num2 = False
    if c_list1[0].rank not in FIGURES:
        if c_list1[0].rank == "A": # Ace exception
            l1_tot = len(c_list1)
        else:
            l1_tot = int(c_list1[0].rank) * len(c_list1) 
        is_num1 = True
    if c_list2[0].rank not in FIGURES:
        if c_list2[0].rank == "A": # Ace exception
            l2_tot = len(c_list2)
        else:
            l2_tot = int(c_list2[0].rank) * len(c_list2) 
        is_num2 = True

    if not is_num1 and not is_num2: # Both figures
        if c_list1[0].rank == c_list2[0].rank:
            return ("TIE", 0)
        elif c_list1[0].rank == "J":
            return ("P2", DEBITO_VALUES["J"])
        else:
            return ("P1", DEBITO_VALUES["J"])

    elif is_num1 and not is_num2: # Only player 1 with figure
        if c_list2[0].rank in SPECIAL_WINS:
            return ("P1", DEBITO_VALUES[c_list2[0].rank])
        else:
            return ("P2", DEBITO_VALUES[c_list2[0].rank])

    elif is_num2 and not is_num1: # Only player 2 with figure
        if c_list1[0].rank in SPECIAL_WINS:
            return ("P2", DEBITO_VALUES[c_list1[0].rank])
        else:
            return ("P1", DEBITO_VALUES[c_list2[0].rank])

    elif is_num1 and is_num2: # Both numerals
        if l1_tot == l2_tot:
            return ("TIE", 0)
        elif l1_tot > l2_tot:
            return ("P1", DEBITO_VALUES[c_list2[0].rank])
        else:
            return ("P2", DEBITO_VALUES[c_list1[0].rank])


def clamp_debito(debito):
    if debito < 0:
        return 0
    elif debito > 2 * INITIAL_DEBITO:
        return 2 * INITIAL_DEBITO
    else:
        return debito


def pvp_game():
    # Game generation
    game_state = GameState(deck = deck_generation(), p1 = Player(), p2 = Player()) 
    rand.shuffle(game_state.deck)

    # Card distribution
    count = 0
    for i in range(2 * HAND_SIZE):
        if i % 2 == 0:
            game_state.p1.hand.append(game_state.deck.pop())
        else:      
            game_state.p2.hand.append(game_state.deck.pop())

    print("\n" + " GAME START ".center(50, "*") + "\n")
    
    # Game flow 
    while game_state.p1.debito > 0 or game_state.p2.debito > 0:
        if HAND_SIZE * 2 - (len(game_state.p1.hand) + len(game_state.p2.hand)) > len(game_state.deck):
            print("The Deck is out of cards. The game ends now!")
            break

        game_state.turn_init()
        game_state.play_selection(game_state.p1, 1)
        game_state.play_selection(game_state.p2, 2)
        game_state.debito_calculation()

    # End game
    d1 = clamp_debito(game_state.p1.debito)
    d2 = clamp_debito(game_state.p2.debito)

    if d1 > d2:
        winner = "PLAYER 1"
    elif d2 > d1:
        winner = "PLAYER 2"
    else:
        winner = "TIE"

    print("\n***** GAME RESULT: ")
    print(f"Player 1: {d1} DEBITO™")
    print(f"Player 2: {d2} DEBITO™")

    print(f"WINNER: {winner}!")
    print("\nPress \"1\" to play a new game or quit with \"3\".")


def main():
    title = open("./../../.assets/title-art.txt")
    print(title.read())

    start_opts = "1 -> Play", "2 -> Rules", "3 -> quit"

    print("  Welcome to DEBITO™ card game!  ".center(50, "*") + "\n")
    print("------ Please choose an option:\n\n" 
          + start_opts[0] + "\n"
          + start_opts[1] + "\n"
          + start_opts[2] + "\n"
          )

    while True:
        command = input(">> ")
        if command == "3" or command in QUIT_COMMANDS:  
            break
        elif command == "1":
            pvp_game()
        elif command == "2":
            rules()
        elif command == "":
            continue
        elif command == "help" or command == "h":
            print("TO BE ADDED.")
        else:
            print("Command not recognized. type \"help\" for command list.")

if __name__ == "__main__":
    main()
