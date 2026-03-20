#!/bin/bash
# Eseguire UNA VOLTA sul server come root dopo aver clonato il repo in /opt/visura-api
set -e

REPO_DIR="/opt/visura-api"
DOMAIN="visura.malerba.info"

echo "==> 1. Copia config nginx"
cp "$REPO_DIR/deploy/$DOMAIN.nginx" "/etc/nginx/sites-available/$DOMAIN"
ln -sf "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"

echo "==> 2. Test e reload nginx"
nginx -t && systemctl reload nginx

echo "==> 3. Build e avvio container"
cd "$REPO_DIR"
docker compose up -d --build

echo "==> 4. Attendi health check (max 90s)"
for i in $(seq 1 18); do
  sleep 5
  STATUS=$(curl -s http://127.0.0.1:8001/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
  echo "   [$i] $STATUS"
  if [ "$STATUS" = "healthy" ]; then
    echo "==> Servizio avviato correttamente"
    break
  fi
done

echo ""
echo "==> 5. Ottieni certificato SSL"
echo "   certbot --nginx -d $DOMAIN"
echo ""
echo "Done. Testa: curl http://$DOMAIN/health"
