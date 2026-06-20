# Acesso Operacional a VPS FraLib

Guia para outras janelas/agentes operarem a VPS sem compartilhar segredos no Git.

## Conexao SSH

- Host: `187.77.37.72`
- Porta: `22`
- Usuario: `root`
- Comando: `ssh root@187.77.37.72`
- Projeto na VPS: `/root/fralib`
- Frontend publicado: `/var/www/fralib`

O cliente SSH local procura as chaves padrao em `~/.ssh`, incluindo
`id_ed25519` e `id_rsa`. Este documento nao armazena senha, token ou chave
privada. Uma nova janela precisa usar o mesmo perfil do Windows/SSH agent ou
uma chave publica previamente autorizada na VPS.

Teste de acesso sem alterar nada:

```powershell
ssh root@187.77.37.72 "hostname; cd /root/fralib && git status --short --branch"
```

## PostgreSQL

- Host visto da VPS: `localhost`
- Porta: `5433`
- Banco: `fralib_db`
- Usuario de manutencao local: `postgres`

Abrir o console pela VPS:

```powershell
ssh root@187.77.37.72
sudo -u postgres psql -p 5433 -d fralib_db -w -P pager=off
```

Executar uma consulta somente leitura em uma linha:

```powershell
ssh --% root@187.77.37.72 sudo -u postgres psql -p 5433 -d fralib_db -w -v ON_ERROR_STOP=1 -P pager=off -c "SELECT now(), current_database();"
```

No PowerShell, `--%` impede que variaveis e aspas do SQL sejam interpretadas
localmente. Para consultas potencialmente pesadas, comece com
`SET statement_timeout = '5s';`.

## Servicos

```bash
cd /root/fralib
pm2 status
pm2 logs fralib --lines 100 --nostream
pm2 logs fralib-worker --lines 100 --nostream
pm2 logs fralib-franz-worker --lines 100 --nostream
```

Portas principais:

- API FraLib: `8000`
- Meowhats/WhatsApp: `3001`
- PostgreSQL: `5433`

## Regras Obrigatorias

1. Nunca usar SCP ou rsync.
2. Nunca editar `/root/fralib`, `/var/www/fralib` ou Nginx diretamente.
3. Alterar apenas em `C:\fralib`.
4. Validar localmente e atualizar `AGENTS.md` quando aplicavel.
5. Publicar somente por `git add`, `git commit` e `git push`.
6. Nunca imprimir `.env`, tokens, senhas, URLs com credenciais ou chaves.
7. Consultas de diagnostico devem ser somente leitura salvo autorizacao clara.

## Verificacoes Seguras

```powershell
ssh root@187.77.37.72 "curl -fsS http://127.0.0.1:8000/health"
ssh root@187.77.37.72 "cd /root/fralib && pm2 status"
ssh root@187.77.37.72 "nginx -t"
```

Se aparecer `Permission denied`, confirme que a janela usa o mesmo usuario do
Windows e que a chave esta disponivel com `ssh-add -l`. Nao crie nem copie uma
chave privada para dentro do repositorio.
