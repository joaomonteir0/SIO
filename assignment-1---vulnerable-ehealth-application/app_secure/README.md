# How To Run

1.
```bash
docker-compose build
```

2.
```bash
docker-compose up
```

3.
http://localhost:8000/

-------
Em caso de ter este erro: 
```
f'Error while fetching server API version: {e}'
docker.errors.DockerException: Error while fetching server API version: ('Connection aborted.', PermissionError(13, 'Permission denied'))
```

Faça isto: 
``` 
sudo chmod 666 /var/run/docker.sock 
```

------
No caso de não ter Docker ou este não estar a funcionar no momento, pode fazer:

1. Criar um ambiente virtual:
```
python3 -m venv venv
```

2.  Ativar o ambiente virtual
```
source venv/bin/activate
```

3. Intalar o pip:
```
python -m pip install --upgrade pip
```

4. Instalar os requisitos
```
pip install -r requirements.txt
```

5. E corre a aplicação
```
python3 app.py
```

Por fim, no terminal, aparece o link que o encaminhará para a app