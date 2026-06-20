# Fix Report: SEC_002_A07_AUTH - OAuth Session Fixation

## Vulnerabilidade
**Arquivo:** `backend/endpoints/auth_endpoints.py:564-582`
**Severidade:** CRITICAL
**OWASP:** A07:2021 - Authentication Failures

## Problema
Quando usuário autenticava via Google OAuth, a conta era criada com `status='ativo'` diretamente, ignorando confirmação de email. Atacante podia sequestrar conta de vítima linkando ao Google do atacante.

## Correção Aplicada
1. Criar conta com `status='pendente'` e `email_confirmado=false`
2. Gerar token de confirmação de email
3. Enviar email de confirmação
4. Retornar status `email_confirmation_required` se email não confirmado

```python
# Antes: status='ativo'
user_id = db.execute(text("""
    INSERT INTO users (email, nome, status, plano, ...)
    VALUES (:email, :nome, 'ativo', 'trial', ...)
"""), {...}).fetchone()[0]

# Depois: status='pendente' com confirmação
user_id = db.execute(text("""
    INSERT INTO users (email, nome, status, plano, ..., email_confirmado, confirm_token, confirm_expires)
    VALUES (:email, :nome, 'pendente', 'trial', ..., false, :confirm_token, :confirm_expires)
"""), {...}).fetchone()[0]
```

## Validação
- [x] Email confirmação obrigatório para novos usuários OAuth
- [x] Status inicial = 'pendente' (não 'ativo')
- [x] Token de confirmação gerado
- [x] Compilação Python OK

## Commits
```
fix: corrige A07 - OAuth cria conta pendente de confirmação de email
```
