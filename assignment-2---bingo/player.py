import ast
import json
import socket
import random
import sys

from utils import *
from logs import *

N = 20

GAME_OBJECTS = {
    "Cards": {},
    "Decks": {},
    "Keys": {}
}

def generate_card(N):
    if random.randint(1, 9) <= 8:
        return [random.randint(1, N) for i in range(5)]
    else:
        number1, number2 = random.sample(range(1, N+1), 2)
        distribution = random.choice([[number1, number1, number2, number2, number2], 
                                      [number1, number2, number2, number2, number2],
                                      [number1, number1, number1, number1, number2]])
        return distribution

def run(ADDR, nickname, private_key, public_key):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(ADDR)
        print(f"Connected to {ADDR}...")
        sign_and_send(s, "register", "nickname", nickname, private_key, public_key)
        response = json.loads(recv_msg(s).decode("utf-8"))

        if (response["status"] == "success"):
            player_id = response["id"] 
            parea_public_key = response["public_key"]
        print(f"My player id is: {player_id}")
        card = generate_card(N)
        # assinar e mandar as cartas
        sign_and_send(s, "card", "card", str(card), private_key)
        status_msg = json.loads(recv_msg(s).decode("utf-8"))

        # fetch other's cards
        cards_msg = json.loads(recv_msg(s).decode("utf-8"))
        cards = ast.literal_eval(cards_msg["cards"])
        for card in cards:
            GAME_OBJECTS["Cards"][card[0]] = card[1]
            if not check_card(card[1]):
                print(f"player {card[0]} cheated!")

        # caller's deck
        encrypted_deck = ast.literal_eval(json.loads(recv_msg(s).decode("utf-8"))["deck"])
        random.shuffle(encrypted_deck)
        key, iv, encrypted_deck = encrypt_deck(encrypted_deck)
        GAME_OBJECTS["Decks"][player_id] = encrypted_deck
        encrypted_deck_msg = {
            "id": player_id,
            "deck": str(encrypted_deck)
        }
        sign_and_send(
            s, "player_deck", "deck_msg", 
            json.dumps(encrypted_deck_msg),
            private_key
        )

        status_message = json.loads(recv_msg(s).decode("utf-8"))
        player_count = json.loads(recv_msg(s).decode("utf-8"))["player_count"]

        for _ in range(1, player_count + 1):
            data        = json.loads(recv_msg(s).decode("utf-8"))
            deck_msg    = json.loads(data["deck_msg"])
            _id         = deck_msg["id"]
            player_deck = ast.literal_eval(deck_msg["deck"])

            GAME_OBJECTS["Decks"][_id] = player_deck
        

        response        = json.loads(recv_msg(s).decode("utf-8"))
        msg             = json.loads(response["msg"])
        play_deck_id    = msg["id"]
        play_deck       = ast.literal_eval(msg["deck"])

        # Send the sym key to playing area
        GAME_OBJECTS["Keys"][player_id] = (key, iv)

        key_msg = {
            "id": player_id,
            "key": str(key),
            "iv": str(iv)
        }

        sign_and_send(
            s, "sym_key", "key_msg", 
            json.dumps(key_msg),
            private_key
        )

        status_msg = json.loads(recv_msg(s).decode("utf-8"))

        # Wait for all keys
        keys = ast.literal_eval(json.loads(recv_msg(s).decode("utf-8"))["keys"])
        for key in keys:
            GAME_OBJECTS["Keys"][key[0]] = (ast.literal_eval(key[1]), ast.literal_eval(key[2]))

        # calculate the winner
        winner = calculate_winner(GAME_OBJECTS["Cards"], GAME_OBJECTS["Keys"][play_deck_id], GAME_OBJECTS["Keys"][0], play_deck)
        print(f"Winner: {winner}")

        # Probability of cheating
        #  if random.randint(1, 10) <= 8: o winner = winner
        #  else: players says he won (even if he didn't)
        winner = winner if random.randint(1, 10) <= 8 else player_id
        sign_and_send(s, "winner", "winner", str(winner), private_key)

        cheaters_msg = json.loads(recv_msg(s).decode("utf-8"))
        print(f"\nCheaters: {cheaters_msg['cheaters']}")

        sign_and_send(s, "request_log", "msg", "msg", private_key)
        log = ast.literal_eval(json.loads(recv_msg(s).decode("utf-8"))["log"])
        for entry in log:
            print(f"\n{entry}")

        print(f"\nLog integrity was maintained? {verify_log_integrity(log, parea_public_key)}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 player.py <port> nickname")
        exit(1)
    port = int(sys.argv[1])
    nickname = sys.argv[2]
    ADDR = ("localhost", port)
    # Generate asym key
    (public_key, private_key) = generate_asym_keys()
    run(ADDR, nickname, private_key, public_key)

if __name__ == "__main__":
    main()
