
# SIO - Projeto 2 - Recurso

## Run
1º Iniciar o servidor

`python3 parea.py <port>`

2º Conectar alguns players ao servidor

`python3 player.py <port> nickname`

3º Depois de conectar os players, conectar o Caller (vai iniciar o jogo automaticamente)

`python3 caller.py <port> nickname`

## Stated Changes
Este relatório apresenta as alterações realizadas no projeto. Devido ao alto número de erros na entrega anterior, o projeto foi refeito quase que completamente, incluindo mudanças significativas no seguinte:
- encriptação das mensagens;
- alteração no método de adicionar e pedir os logs;
- maneira como se inícia e decorre o jogo;
- criação de um "mini" protocolo  (`utils.py` e `logs.py`) para auxiliar na implementação de métodos globais para os diferentes tipos de usuários;
- implementação de cheating.

### **Encriptação** 
Para cifrar os dados estavamos a utilizar o algoritmo de Fernet, mas este foi-nos desaconselhado na altura da defesa do projeto. Então, trocamos para o AES com modo CBC.
`function encrypt`: Recebe três parâmetros - key (chave), iv (vetor de inicialização) e data (dados que vão ser cifrados). A função usa o algoritmo AES com modo CBC para cifrar os dados. Primeiro, o padder PKCS7 é usado para preencher os dados antes de serem cifrados. Em seguida, o encryptor cifra os dados e retorna o texto cifrado.

`function decrypt`: Recebe três parâmetros - key (chave), iv (vetor de inicialização) e ciphertext (texto cifrado). A função usa o algoritmo AES com modo CBC para decifrar o texto cifrado. O decryptor decifra os dados e, em seguida, o unpadder PKCS7 é usado para remover o preenchimento adicionado durante a cifragem. Finalmente, a função retorna o texto decifrado.

### **Logs**
Na nossa entrega anterior, fazer o request dos logs não estava funcional e a assinar as mensagens não estava a funcionar. Corrigimos isso e adicionámos uma função para verificar a integridade dos logs através do hash(prev_entry).

A cada nova mensagem enviada para o servidor, através do respetivo id do último log, texto da mensagem enviada e private_key do usuário que mandou, é criado um novo log e adicionado à list LOG (salva na playing area e acessível por todos).

`function new_log`
Ao adicionar-mos um novo log, na altura da sua criação utilizamos o id do log para criar o hash e verificar a integridade dos logs mais tarde.
```python
entry  = {"sequence": len(log) +  1,"timestamp": time.time(),}
entry["hash"] =  hashlib.sha256(str(entry['sequence']).encode("utf-8")).hexdigest()
entry["text"] =  text
entry["signature"] =  base64.b64encode(sign_msg(private_key, text)).decode("utf-8"))
```

`function verify_integrity`
Por cada entrada nos logs, comparamos o entry_hash do log com um hash gerado a partir da posição+1 do log na list LOG. No fim, validamos a assinatura feita sobre o text com a public_key.
Se a integridade dos logs não tiver sido comprometida, dá return a True.
```python
for  entry  in  log:
	sequence, timestamp, entry_hash, text, 								signature  =  entry
	prev_hash  =  	hashlib.sha256(str(sequence).encode("utf-8")).hexdigest()
	if  prev_hash  !=  entry_hash:
		return  False
if  validate_msg({"signature": signature, "text": text}, "text", public_key)["status"] !=  "success":
	return  False
return  True
```
### **Jogo**
Relativamente à mecânica do jogo, na nossa primeira entrega não conseguimos aplicar quase nada. Desta vez, conseguimos implementar várias coisas:
- O **caller** entra e define o seu nickname, são geradas as suas chaves assimétricas, coleta as cartas de todos os jogadores, gera o deck, baralha-o, cifra-o, assina-o e manda para o primeiro jogador. Quando o deck volta a si, o caller volta a assiná-lo e por fim recebe todos os cartões de todos os jogadores e verifica quem ganha e se houve batota.
- O **jogador** (player) entra e define o seu nickname, são geradas as suas chaves assimétricas, é criado o seu cartão, que assina e envia para os restantes jogadores. Recebe também os cartões do outros jogadores. Recebe o deck cifrado e assinado pelo caller e por todos os jogadores que entraram antes dele, que cifra, assina e envia para o próximo jogador(envia para o caller se for o último jogador). Por fim recebe todas as chaves públicas dos jogadores e caller que usará para decifrar e verificar o deck final, a fim de definir o vencedor.
- A **área de jogo** (playing area) é responsável por verificar a conecção de cada jogador/caller e expor todos os acontecimentos ao longo do jogo como quando um jogador recebe o deck, quando os jogadores enviam as suas chaves ou até qual o vencedor. 

### Cheating
Na primeira versão deste projeto, a única batota que podia ser feita era o jogador poder ter no seu cartão números repetidos, uma vez que era tudo implementado manualmente. Nesta versão isto ainda acontece, mas também foram implementadas outras formas de fazer batota.

A função generate_card gera uma lista de 5 números com base em uma probabilidade de cheating. Com uma probabilidade de 8/9, a função gera uma lista de 5 números aleatórios entre 1 e N. Caso contrário, com uma probabilidade de 1/9, a função seleciona 2 números distintos de 1 a N e distribui-os ao longo da lista. A ideia é que, caso esses 2 números sejam sorteados, o usuário será o vencedor, pois a sua mão, teoricamente, será "menor" que a dos outros jogadores e, portanto, validará menos números para a vitória.
```python
def generate_card(N):
    if random.randint(1, 9) <= 8:
        return [random.randint(1, N) for i in range(5)]
    else:
        number1, number2 = random.sample(range(1, N+1), 2)
        distribution = random.choice([[number1, number1, number2, number2, number2], 
                                      [number1, number2, number2, number2, number2],
                                      [number1, number1, number1, number1, number2]])
        return distribution
```

O código abaixo implementa uma probabilidade de cheating durante uma rodada do jogo. A variável "winner" armazena o verdadeiro vencedor do jogo, mas há uma possibilidade de um jogador apontar para si próprio como o vencedor, mesmo que ele não tenha vencido na realidade.

Isso é feito através de uma chamada ao método "random.randint(1, 10)" que gera um número aleatório entre 1 e 10. Se o resultado gerado for menor ou igual a 8, o vencedor verdadeiro é mantido, caso contrário o jogador "fingirá" ter vencido o jogo.

```python
# Probability of cheating
#  if random.randint(1, 10) <= 8: o winner = winner
# else: players says he won (even if he didn't)
winner = winner if random.randint(1, 10) <= 8 else player_id
sign_and_send(s, "winner", "winner", str(winner), private_key)
```
Cada jogador verá a seguinte mensagem na sua consola: "My player id is: [id do jogador]", "winner: [id do vencedor verdadeiro]", "cheaters: [lista de cheaters]".

Caso haja um cheater no jogo, isso será registrado no Audit Logs, através da mensagem "player [id do jogador] says player [id do vencedor apontado] wins". Por exemplo, caso hajam 3 jogadores e 1 deles seja o cheater, ele irá apontar para si próprio no log enquanto que os outros dois irão apontar para o verdadeiro vencedor.

### **Protocolo**
Na versão anterior deste projeto, havia um ficheiro em casa pasta chamado _"messages.py"_ que apenas definia as funções de envio e receção de mensagens.
Agora temos um ficheiro chamado _"utils.py"_ onde são definidas não só as funções relativas ao envio e receção de mensagens, mas também as funções relativas às gerações de chaves, a cifrar, assinar, verificar e também as funções que determinam qual jogador ganha.


## Autores

|NMEC 	|Name 	       |email                 |
|-------|--------------|----------------------|
|103415 |João Sousa 	 |jsousa11@ua.pt        |
|102383 |Vânia Morais  |vania.morais@ua.pt    |
|102690 |João Monteiro |joao.mont@ua.pt       |