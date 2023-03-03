import os
import json
import base64

from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ( rsa, padding )
from cryptography.hazmat.primitives.ciphers import ( Cipher, algorithms, modes )



########## GIVEN MESSAGES METHODS##########
def send_msg( dst, msg ):
    length = len(msg).to_bytes( 4, 'big' )# 4-byte integer, network byte order (Big Endian)
    dst.send( length )
    dst.send( msg )

def exact_recv( src, length ):
    data = bytearray( 0 )

    while len(data) != length:
        more_data = src.recv( length - len(data) )
        if len(more_data) == 0: # End-of-File
            return None
        data.extend( more_data )
    return data

def recv_msg( src ):
    data = exact_recv( src, 4 ) # 4-byte integer, network byte order (Big Endian)
    if data == None:
        return None

    length = int.from_bytes( data, 'big' )
    return exact_recv( src, length )

########## KEYS GENERATION AND SIGNING FUNCTIONS ##########
# gerar o par de chaves assimetricas
# com RSA e valores tipicos/default no public_exponent, key_size e backend
def generate_asym_keys():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    # tuplo com a chave publica e privada
    return (public_key, private_key)


# assinar processo:
# codificar como utf-8
# assinar com a chave privada usando sign()
# assinado com PSS com MGF1 e SHA256
# salt_length é o comprimento do salt da assinatura
# o comprimento max do salt deve ser o máximo permitido pelo algoritmo PSS
# isto é a quantidade adicional de dados que são adicionados ao final da mensagem para a deixar mais segura
def sign_msg(private_key, msg):
    signature = private_key.sign(
        msg.encode("utf-8"),
        padding.PSS(mgf = padding.MGF1(hashes.SHA256()),
            salt_length = padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    return signature

########## GENERAL ENCRYPTION AND DECRYPTION METHODS ##########
def encrypt(key, iv, data):
    encryptor = Cipher(
        algorithms.AES(key),
        modes.CBC(iv)
    ).encryptor()

    padder = PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()

    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    return ciphertext

def decrypt(key, iv, ciphertext):
    decryptor = Cipher(
        algorithms.AES(key),
        modes.CBC(iv)
    ).decryptor()

    decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = PKCS7(128).unpadder()
    plain_text = unpadder.update(decrypted_data) + unpadder.finalize()

    return plain_text 


########## DECK ENCRYPTION AND DECRYPTION ##########
# encrypt_deck: usa cifra AES no modo CBC
# Gera chave secreta (aleatória): key
# Gera vetor de inicialização (aleatório): iv
# Cifra cada número do baralho com a chave e o vetor de inicialização
# Retorna a chave, o vetor de inicialização e o baralho cifrado
def encrypt_deck(deck):
    key = os.urandom(32)
    iv = os.urandom(16)

    encrypted_deck = []
    for number in deck:
        encrypted_num = encrypt(key, iv, str(number).encode())
        encrypted_deck.append(encrypted_num)

    return key, iv, encrypted_deck

# decrypt_deck: descifra o baralho cifrado
# usa a chave e o vetor de inicialização para descifrar cada número do baralho
# antes de dar append ao decrypted deck : eval() para converter o número descifrado de bytes para int
# retorna o baralho descifrado
def decrypt_deck(key, iv, deck):
    decrypted_deck = []
    for num in deck:
        decrypted_deck.append(eval(decrypt(key, iv, num).decode()))
    return decrypted_deck


# assinar e mandar to socket target (sock)
# msg_type: valor que vai no campo "type" da request
# msg_field: campo que queremos enviar
# msg: valor que vai no campo msg_field da request
# public_key: chave publica normal (nao necessaria)
# private_key: chave privada normal
def sign_and_send(sock, msg_type, msg_field, msg, private_key, public_key=None):
    signature = sign_msg(private_key, msg)
    signature_b64 = base64.b64encode(signature).decode("utf-8")

    request = {
        "type": msg_type,
        msg_field: msg,
        "signature": signature_b64
    }

    if public_key:
        public_key_to_pem = public_key.public_bytes(
            encoding = serialization.Encoding.PEM,
            format = serialization.PublicFormat.SubjectPublicKeyInfo
        )
        public_key_pem = public_key_to_pem.decode("utf-8")
        request["public_key"] = public_key_pem

    send_msg(sock, json.dumps(request).encode("utf-8"))

# verificar a assinatura com a public_key
def verify_signature(public_key_pem, message, signature):
    public_key = serialization.load_pem_public_key(
        public_key_pem,
        backend = default_backend()
    )

    public_key.verify(signature, message,
        padding.PSS(
            mgf = padding.MGF1(hashes.SHA256()),
            salt_length = padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )


# se estiver mal assinada, retorna "fail"
# se estiver bem assinada, retorna "success"
def validate_msg_integrity(data, msg_field, public_key_pem):
    response = {"status": ""}
    signature = base64.b64decode(data["signature"])

    try:
        verify_signature(public_key_pem.encode("utf-8"),
            data[msg_field].encode("utf-8"), 
            signature
        )

        response["status"] = "success"
    except:
        response["status"] = "fail"

    return response

# verificar se não há elementos repetidos
# retorna true se sim, false se não
def check_card(card):
    return len(set(card)) == len(card)



def calculate_winner(cards, key, caller_key, deck):
    decrypted_deck = decrypt_deck(key[0], key[1], deck)
    plaintext_deck = decrypt_deck(caller_key[0], caller_key[1], decrypted_deck)

    player_cards = cards.copy()
    for num in plaintext_deck:
        for i in range(1, len(player_cards) + 1):
            if num in cards[i]:
                cards[i].remove(num)
            if cards[i] == []:
                return i
    return None