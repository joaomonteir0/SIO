import ast
import json
import socket
import random
import sys

from utils import *
from logs import *


N = 20

GAME_OBJECTS = {
    "Decks": {},
    "Cards": {},
    "Keys": {}
}

def generate_deck():
    deck = list(range(N))
    random.shuffle(deck)
    return deck

def run(ADDR, nickname, private_key, public_key, cheaters):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(ADDR)
        print(f"Connected as caller to {ADDR}...")

        sign_and_send(s, "caller", "nickname", nickname, private_key, public_key)
        response = json.loads(recv_msg(s).decode("utf-8"))

        if (response["status"] == "success"):
            parea_public_key = response["public_key"]
        else:
            return 

        #print(f"register process: {status_msg}")

        # collect cards from players
        cards_msg = json.loads(recv_msg(s).decode("utf-8"))
        cards = ast.literal_eval(cards_msg["cards"])
        for card in cards:
            GAME_OBJECTS["Cards"][card[0]] = card[1]
            if not check_card(card[1]):
                print(f"player {card[0]} cheated!")
                cheaters.add(card[0])

        #print(f"cards: {GAME_OBJECTS['Cards']}")

        player_count = json.loads(recv_msg(s).decode("utf-8"))["player_count"]
        
        # deck generation and shuffling
        deck = generate_deck()
        key, iv, encrypted_deck = encrypt_deck(deck)
        #print(f"deck: {deck}")
        #print(f"encrypted deck: {encrypted_deck}")

        sign_and_send(s, "caller_deck", "deck", str(encrypted_deck), private_key)
        status_msg = json.loads(recv_msg(s).decode("utf-8"))
        #print(f"deck validation: {status_msg}")

        for _ in range(1, player_count + 1):
            data        = json.loads(recv_msg(s).decode("utf-8"))
            deck_msg    = json.loads(data["deck_msg"])
            player_id   = deck_msg["id"]
            player_deck = ast.literal_eval(deck_msg["deck"])

            GAME_OBJECTS["Decks"][player_id] = player_deck
        
        # Finished collecting all decks from players
        #print(f"finished: {GAME_OBJECTS['Decks']}")

        random_idx = random.randint(1, player_count)
        play_deck = GAME_OBJECTS["Decks"][random_idx]

        msg = {
            "id": random_idx,
            "deck": str(play_deck)
        }

        sign_and_send(s, "play_deck", "msg", json.dumps(msg), private_key)
        status_msg = json.loads(recv_msg(s).decode("utf-8"))
        #print(f"play_deck validation: {status_msg}")

        # send sym key to parea
        GAME_OBJECTS["Keys"][0] = (key, iv)

        key_msg = {
            "id": 0,
            "key": str(key),
            "iv": str(iv)
        }

        sign_and_send(
            s, "sym_key", "key_msg", 
            json.dumps(key_msg),
            private_key
        )

        status_msg = json.loads(recv_msg(s).decode("utf-8"))
        #print(f"sym key validation: {status_msg}")

        # Wait for all keys
        keys = ast.literal_eval(json.loads(recv_msg(s).decode("utf-8"))["keys"])
        for key in keys:
            GAME_OBJECTS["Keys"][key[0]] = (ast.literal_eval(key[1]), ast.literal_eval(key[2]))

        # Finished collecting all decks from players
        #print(f"\nfinished: {GAME_OBJECTS['Keys']}")

        # TODO(): Verify decks
        winner = calculate_winner(GAME_OBJECTS["Cards"], GAME_OBJECTS["Keys"][random_idx], GAME_OBJECTS["Keys"][0], play_deck)
        #print(f"winner: {winner}")

        for _ in range(player_count):
            msg = json.loads(recv_msg(s).decode("utf-8"))
            _winner = json.loads(msg["winner_msg"])["winner"] 
            _winner = int(_winner) if _winner != "None" else "0"
            _id = int(json.loads(msg["winner_msg"])["id"])

            if winner != _winner:
                cheaters.add(_id)

        # Broadcast cheater
        sign_and_send(s, "cheaters", "cheaters", str(list(cheaters)), private_key)

        sign_and_send(s, "request_log", "msg", "msg", private_key)
        log = ast.literal_eval(json.loads(recv_msg(s).decode("utf-8"))["log"])
        for entry in log:
            print(f"\n{entry}")

        print(f"\nLog integrity was maintained?? {verify_log_integrity(log, parea_public_key)}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 caller.py <port> nickname")
        exit(1)
    port = int(sys.argv[1])
    nickname = sys.argv[2]
   
    nickname = "Caller - "+nickname
    cheaters = set()
    ADDR = ("localhost", port)
    # Generate asym key
    (public_key, private_key) = generate_asym_keys()
    run(ADDR, nickname, private_key, public_key, cheaters)

if __name__ == "__main__":
    main()