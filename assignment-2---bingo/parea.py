import ast
import json
import socket
import selectors
import sys

from utils import *
from logs import *

LOG       = []
PLAYER_ID = 1 

GAME_OBJECTS = {
    "Main_Deck": 20, 
    "Caller": (), 
    "Players": [], 
    "Cards": {},
    "Decks": {},
    "Keys": {},
}

def assign_playerId():
    global PLAYER_ID

    PLAYER_ID = PLAYER_ID + 1
    return PLAYER_ID - 1

def get_player_with_sock(sock):
    for player in GAME_OBJECTS["Players"]:
        if player[0] == sock:
            return player
    return None


def dispatch(srv_socket):
    (public_key, private_key) = generate_asym_keys()

    selector = selectors.DefaultSelector()

    srv_socket.setblocking(False)
    selector.register(srv_socket, selectors.EVENT_READ, data=None)

    while True:
        events = selector.select(timeout=None)
        for key, mask in events:

            # Check for a new client connection

            if key.fileobj == srv_socket:
                clt_socket, clt_addr = srv_socket.accept()
                clt_socket.setblocking(True)

                # Add it to the sockets under scrutiny

                selector.register(clt_socket, selectors.EVENT_READ, data=None)
                print('Client added')

            # Client data is available for reading

            else:
                data = recv_msg(key.fileobj)
                # cada mensagem recebida tem um type
                # none fecha a conexão com o servidor (é enviada pelos players no fim de cada jogo)
                if data == None: # Socket closed
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    print('Client removed')
                    continue

                data = json.loads(data.decode('utf-8'))
                print(json.dumps(data, indent=2))
                # se for register, validar a assinatura
                if (data["type"] == "register"):
                    # Validate registration 
                    response = validate_msg_integrity(data, "nickname", data["public_key"])
                    # se a assinatura for válida
                    if (response["status"] == "success"):
                        # adicionar o player à lista de players
                        player_id = assign_playerId()
                        GAME_OBJECTS["Players"].append(
                            (key.fileobj, player_id, data["nickname"], data["public_key"])
                        )

                        response["id"] = player_id
                        public_key_to_pem = public_key.public_bytes(
                            encoding = serialization.Encoding.PEM,
                            format = serialization.PublicFormat.SubjectPublicKeyInfo
                        )
                        response["public_key"] = public_key_to_pem.decode("utf-8")
                    # responder ao player com a sua id e a sua chave pública
                    send_msg(key.fileobj, json.dumps(response).encode("utf-8"))
                    new_log(LOG, f"player {player_id} registered with {response['status']}", private_key)

                elif (data["type"] == "card"):
                    # Validate card
                    player = get_player_with_sock(key.fileobj) # ir buscar o player que enviou a carta
                    response = validate_msg_integrity(data, "card", player[3])
                    send_msg(key.fileobj, json.dumps(response).encode("utf-8"))

                    GAME_OBJECTS["Cards"][player[1]] = ast.literal_eval(data["card"])
                    new_log(LOG, f"player {player[1]} sent his cards with {response['status']}", private_key)

                elif (data["type"] == "caller"):
                    response = validate_msg_integrity(data, "nickname", data["public_key"])

                    new_log(LOG, f"caller registered with {response['status']}", private_key)

                    if response["status"] == "success":
                        public_key_to_pem = public_key.public_bytes(
                            encoding = serialization.Encoding.PEM,
                            format = serialization.PublicFormat.SubjectPublicKeyInfo
                        )
                        response["public_key"] = public_key_to_pem.decode("utf-8")
                        send_msg(key.fileobj, json.dumps(response).encode("utf-8"))

                        GAME_OBJECTS["Caller"] = (key.fileobj, 0, "caller", data["public_key"])

                        # send cards to caller
                        cards = [(_id, card) for _id, card in GAME_OBJECTS["Cards"].items()]
                        sign_and_send(key.fileobj, "cards", "cards", 
                            json.dumps(cards), private_key
                        )
                        new_log(LOG, f"cards were sent to caller", private_key)

                        response = { "player_count": len(GAME_OBJECTS["Players"]) }
                        send_msg(key.fileobj, json.dumps(response).encode("utf-8"))
                        new_log(LOG, f"player count was sent to caller", private_key)

                        if len(GAME_OBJECTS["Cards"]) == len(GAME_OBJECTS["Players"]):
                            for player in GAME_OBJECTS["Players"]:
                                cards = [(_id, card) for _id, card in GAME_OBJECTS["Cards"].items()]
                                sign_and_send(player[0], "cards", "cards", 
                                    json.dumps(cards), private_key
                                )
                                new_log(LOG, f"cards were sent to player", private_key)
                    else:
                        send_msg(key.fileobj, json.dumps(response).encode("utf-8"))


                elif (data["type"] == "caller_deck"):
                    response = validate_msg_integrity(data, "deck", GAME_OBJECTS["Caller"][3])
                    send_msg(key.fileobj, json.dumps(response).encode("utf-8"))
                    new_log(LOG, f"caller sent his deck", private_key)

                    if response["status"] == "success":
                        for player in GAME_OBJECTS["Players"]:
                            sign_and_send(player[0], "deck", "deck", data["deck"], private_key)
                            new_log(LOG, f"caller's deck was sent to player {player[1]}", private_key)
                
                elif (data["type"] == "player_deck"):
                    deck_msg    = json.loads(data["deck_msg"])
                    player_id   = deck_msg["id"]
                    player_deck = ast.literal_eval(deck_msg["deck"])

                    response = validate_msg_integrity(
                        data, "deck_msg", GAME_OBJECTS["Players"][player_id-1][3]
                    )

                    send_msg(key.fileobj, json.dumps(response).encode("utf-8"))
                    new_log(LOG, f"player {player_id} sent his deck.", private_key)

                    GAME_OBJECTS["Decks"][player_id] = player_deck

                    if len(GAME_OBJECTS["Players"]) == len(GAME_OBJECTS["Decks"]):
                        response = { "player_count": len(GAME_OBJECTS["Players"]) }

                        for player in GAME_OBJECTS["Players"]:
                            send_msg(player[0], json.dumps(response).encode("utf-8"))
                            new_log(LOG, f"player count was sent to player {player[1]}", private_key)

                        for _id in GAME_OBJECTS["Decks"]:
                            _deck = GAME_OBJECTS["Decks"][_id]

                            encrypted_deck_msg = {
                                "id": _id,
                                "deck": str(_deck)
                            }

                            sign_and_send(GAME_OBJECTS["Caller"][0], "player_deck", "deck_msg", 
                                json.dumps(encrypted_deck_msg), private_key
                            )
                            new_log(LOG, f"player {_id} deck was sent to caller", private_key)

                            for player in GAME_OBJECTS["Players"]:
                                sign_and_send(player[0], "player_deck", "deck_msg", 
                                    json.dumps(encrypted_deck_msg), private_key
                                )
                                new_log(LOG, f"player {_id} deck was sent to player {player[1]}", private_key)
                
                elif (data["type"] == "play_deck"):
                    response = validate_msg_integrity(data, "msg", GAME_OBJECTS["Caller"][3])
                    send_msg(key.fileobj, json.dumps(response).encode("utf-8"))

                    msg             = json.loads(data["msg"])
                    play_deck_id    = msg["id"]
                    play_deck       = msg["deck"]

                    new_log(LOG, f"caller sent the deck that will be played - play_deck_id: {play_deck_id}", private_key)

                    if response["status"] == "success":
                        for player in GAME_OBJECTS["Players"]:
                            msg = {
                                "id": play_deck_id,
                                "deck": play_deck 
                            }
                            sign_and_send(player[0], "play_deck", "msg", json.dumps(msg), private_key)
                            new_log(LOG, f"play deck was sent to player {player[1]})", private_key)

                elif (data["type"] == "sym_key"):
                    key_msg = json.loads(data["key_msg"])

                    response = validate_msg_integrity(data, "key_msg", 
                        get_player_with_sock(key.fileobj)[3] if key_msg["id"] != 0 else GAME_OBJECTS["Caller"][3]
                    )
                    send_msg(key.fileobj, json.dumps(response).encode("utf-8"))
                    new_log(LOG, f"player {get_player_with_sock(key.fileobj)[1] if key_msg['id'] != 0 else 0} sent his sym key", private_key)

                    GAME_OBJECTS["Keys"][key_msg["id"]] = (key_msg["key"], key_msg["iv"])

                    if len(GAME_OBJECTS["Players"]) + 1 == len(GAME_OBJECTS["Keys"]):
                        keys = [(_id, key, iv) for _id, (key, iv) in GAME_OBJECTS["Keys"].items()]

                        sign_and_send(GAME_OBJECTS["Caller"][0], "sym_key", "keys", 
                            json.dumps(keys), private_key
                        )
                        new_log(LOG, f"keys were sent to caller", private_key)

                        for player in GAME_OBJECTS["Players"]:
                            sign_and_send(player[0], "sym_key", "keys", 
                                json.dumps(keys), private_key
                            )
                            new_log(LOG, f"keys were sent to player {player[1]}", private_key)
                
                elif (data["type"] == "winner"):
                    winner = data["winner"]

                    winner_msg = {
                        "id": get_player_with_sock(key.fileobj)[1],
                        "winner": winner
                    }
                    sign_and_send(GAME_OBJECTS["Caller"][0], "winner_msg", "winner_msg", 
                        json.dumps(winner_msg), private_key
                    )
                    new_log(LOG, f"player {get_player_with_sock(key.fileobj)[1]} says player {winner} wins", private_key)
                
                elif (data["type"] == "cheaters"):
                    cheaters = data["cheaters"]

                    for player in GAME_OBJECTS["Players"]:
                        sign_and_send(player[0], "cheaters", "cheaters", 
                            cheaters, private_key
                        )
                        new_log(LOG, f"cheaters list was sent to player {player[1]}", private_key)

                elif (data["type"] == "request_log"):
                    player = get_player_with_sock(key.fileobj) if get_player_with_sock(key.fileobj) else GAME_OBJECTS["Caller"]
                    response = validate_msg_integrity(data, "msg", player[3])
                    if player[1] == 0:
                         new_log(LOG, f"Caller requested audit logs | Validation status: {response['status']}", private_key)
                    else:
                        new_log(LOG, f"player {player[1]} requested audit logs | Validation status: {response['status']}", private_key)
                    
                    if response["status"] == "success":
                        sign_and_send(key.fileobj, "log", "log", 
                            str(LOG), private_key
                        )
                        new_log(LOG, f"Logs sent to player {player[1]}", private_key)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 server.py <port>")
        exit(1)
    port = int(sys.argv[1])
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', port))
        s.listen()
        print("Server is listening on port", port)
        dispatch(s)

if __name__ == '__main__':
    main()