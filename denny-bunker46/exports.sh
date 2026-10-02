export APP_BUNKER46_PORT="8466"

export APP_BUNKER46_DB_PASSWORD="$(derive_entropy "env-${app_entropy_identifier}-DB_PASSWORD" | head -c32)"
export APP_BUNKER46_JWT_SECRET="$(derive_entropy "env-${app_entropy_identifier}-JWT_SECRET")"
export APP_BUNKER46_JWT_REFRESH_SECRET="$(derive_entropy "env-${app_entropy_identifier}-JWT_REFRESH_SECRET")"
export APP_BUNKER46_ENCRYPTION_KEY="$(derive_entropy "env-${app_entropy_identifier}-ENCRYPTION_KEY")"

local_ips=$(hostname --all-ip-addresses 2> /dev/null) || local_ips=""
local_origins=$(for ip in $local_ips; do
  if [[ "$ip" == *:* ]]; then
    echo -n "http://[$ip]:$APP_BUNKER46_PORT,https://[$ip]:$APP_BUNKER46_PORT,"
  else
    echo -n "http://$ip:$APP_BUNKER46_PORT,https://$ip:$APP_BUNKER46_PORT,"
  fi
done | sed 's/,$//')

export APP_BUNKER46_LOCAL_ORIGINS="${local_origins}"
