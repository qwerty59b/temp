# todus-up-bot-ultimate

[![Formatted With Isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://github.com/PyCQA/isort) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


## Comandos

    queue - shows the queue
    reset - resets the bot
    token - shows token
    verbose - on | off (spam)
    silent_mode - on | off (grupo en paz)
    uptime - show time online of bot
    s3 - la magia
    log - show the log

## env vars

    API_ID=
    API_HASH=
    ADMIN=
    BOT_TOKEN=
    UPSTREAM_REPO=
    UPSTREAM_BRANCH=
    
    
## Tips

UPSTREAM_REPO: Tu enlace al repositorio de github, si tu repositorio es privado añade con el sig formato https://username:{githubtoken}@github.com/{username}/{reponame} . Obten token desde el sig enlace [Github settings](https://github.com/settings/tokens). Así podrás actualizar tu bot desde el repositorio en cada reinicio sin necesidad de redeploy ## NOTA casos en los que es necesario hacer redeploy > cambios en el requirements.txt o en el Dockerfile

Ejemplo de url con token para env var UPSTREAM_REPO  https://pedrito:gh_idsfhudddhdfhudfhduf@github.com/pedrito/repo-subesube

UPSTREAM_BRANCH: aqui va main, master, dev o el name que le hallan puesto a la rama.

forkear cada cual este repo no hacer deploy desde aqui ni usar el token de gh para halar el repo directo de la organizacion


[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)
