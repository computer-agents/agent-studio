#!/bin/bash

if [ -n "$VNC_PASSWORD" ]; then
    echo -n "$VNC_PASSWORD" > /.password1
    x11vnc -storepasswd "$(cat /.password1)" /.password2
    chmod 644 /.password*  # Change permissions to be readable
    sed -i 's/^command=x11vnc.*/& -rfbauth \/.password2/' /etc/supervisor/conf.d/supervisord.conf
    export VNC_PASSWORD=
fi

if [ -n "$X11VNC_ARGS" ]; then
    sed -i "s/^command=x11vnc.*/& ${X11VNC_ARGS}/" /etc/supervisor/conf.d/supervisord.conf
fi

if [ -n "$OPENBOX_ARGS" ]; then
    sed -i "s#^command=/usr/bin/openbox\$#& ${OPENBOX_ARGS}#" /etc/supervisor/conf.d/supervisord.conf
fi

if [ -n "$RESOLUTION" ]; then
    sed -i "s/1024x768/$RESOLUTION/" /usr/local/bin/xvfb.sh
fi

USER=ubuntu
HOME=/home/$USER
echo "* Setting up for user: $USER"
if [ -z "$PASSWORD" ]; then
    echo "  set default password to \"ubuntu\""
    PASSWORD=ubuntu
fi
echo "$USER:$PASSWORD" | chpasswd
usermod -aG sudo $USER
echo "$USER ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
cp -r /root/{.config,.gtkrc-2.0,.asoundrc} "${HOME}"
chown -R "$USER":"$USER" "${HOME}"
[ -d "/dev/snd" ] && chgrp -R adm /dev/snd

sed -i -e "s|%USER%|$USER|" -e "s|%HOME%|$HOME|" /etc/supervisor/conf.d/supervisord.conf

# Modify VNC server to run as ubuntu user
sed -i 's/^command=x11vnc.*/command=su - ubuntu -c "x11vnc -xkb -noxrecord -noxfixes -noxdamage -display :1 -rfbauth \/.password2 -shared -forever"/' /etc/supervisor/conf.d/supervisord.conf

# home folder
if [ ! -x "$HOME/.config/pcmanfm/LXDE/" ]; then
    mkdir -p "$HOME"/.config/pcmanfm/LXDE/
    ln -sf /usr/local/share/doro-lxde-wallpapers/desktop-items-0.conf "$HOME"/.config/pcmanfm/LXDE/
    chown -R "$USER":"$USER" "$HOME"
fi

# nginx workers
sed -i 's|worker_processes .*|worker_processes 1;|' /etc/nginx/nginx.conf

# nginx ssl
if [ -n "$SSL_PORT" ] && [ -e "/etc/nginx/ssl/nginx.key" ]; then
    echo "* enable SSL"
	sed -i 's|#_SSL_PORT_#\(.*\)443\(.*\)|\1'"$SSL_PORT"'\2|' /etc/nginx/sites-enabled/default
	sed -i 's|#_SSL_PORT_#||' /etc/nginx/sites-enabled/default
fi

# nginx http base authentication
if [ -n "$HTTP_PASSWORD" ]; then
    echo "* enable HTTP base authentication"
    htpasswd -bc /etc/nginx/.htpasswd "$USER" "$HTTP_PASSWORD"
	sed -i 's|#_HTTP_PASSWORD_#||' /etc/nginx/sites-enabled/default
fi

# dynamic prefix path renaming
if [ -n "$RELATIVE_URL_ROOT" ]; then
    echo "* enable RELATIVE_URL_ROOT: '$RELATIVE_URL_ROOT'"
	sed -i 's|#_RELATIVE_URL_ROOT_||' /etc/nginx/sites-enabled/default
	sed -i 's|_RELATIVE_URL_ROOT_|'"$RELATIVE_URL_ROOT"'|' /etc/nginx/sites-enabled/default
fi

# clearup
PASSWORD=
HTTP_PASSWORD=

# Add agent_server to supervisord under ubuntu user space
cat <<EOF > /etc/supervisor/conf.d/agent_server.conf
[program:agent_server]
command=python3.11 /home/ubuntu/agent_studio/scripts/agent_server.py
autostart=true
autorestart=true
user=ubuntu
stderr_logfile=/var/log/agent_server.err.log
stdout_logfile=/var/log/agent_server.out.log
environment=HOME="/home/ubuntu",USER="ubuntu",PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin",LOGNAME="ubuntu",DISPLAY=":1.0",DONT_PROMPT_WSL_INSTALL=True
EOF

exec /bin/tini -- supervisord -n -c /etc/supervisor/supervisord.conf
