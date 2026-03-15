# Mari-Olivier Reality Hub

MVP premium em Flask + PostgreSQL pronto para GitHub e Railway.

## Stack
- Flask
- Jinja2
- SQLAlchemy
- Flask-Login
- PostgreSQL
- Railway Volume para uploads

## Funcionalidades incluídas
- Home premium inspirada em streaming
- Login, cadastro e logout
- Perfil do usuário com avatar e dados extras
- Player de episódio com retomada automática
- Progresso salvo no banco
- Comentários e likes em episódios
- Notificações internas
- Área de bônus e extras
- Painel administrativo básico
- Seed automática com conteúdo demo

## Variáveis de ambiente
Copie `.env.example` e configure:

- `SECRET_KEY`
- `DATABASE_URL`
- `AUTO_INIT_DB=true`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

## Subida no Railway
1. Envie o projeto para o GitHub.
2. Crie um projeto no Railway.
3. Adicione PostgreSQL.
4. Monte um volume e aponte para `/data` se quiser persistir uploads.
5. Configure as variáveis de ambiente.
6. Deploy.

## Comportamento de bootstrap
Se `AUTO_INIT_DB=true`, o app cria as tabelas no primeiro boot e insere dados demo se o banco estiver vazio.

## Login admin demo
- Email: valor de `ADMIN_EMAIL`
- Senha: valor de `ADMIN_PASSWORD`

## Observação
Para produção, troque o player demo por vídeos hospedados em CDN/streaming e substitua o upload local por um fluxo de mídia próprio.
