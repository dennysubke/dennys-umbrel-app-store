export APP_COOLIFY_APP_ID="$(derive_entropy "${app_entropy_identifier}-app-id" | cut -c1-32)"
export APP_COOLIFY_DB_PASSWORD="$(derive_entropy "${app_entropy_identifier}-postgres-password")"
export APP_COOLIFY_REDIS_PASSWORD="$(derive_entropy "${app_entropy_identifier}-redis-password")"
export APP_COOLIFY_PUSHER_ID="$(derive_entropy "${app_entropy_identifier}-pusher-id" | cut -c1-32)"
export APP_COOLIFY_PUSHER_KEY="$(derive_entropy "${app_entropy_identifier}-pusher-key")"
export APP_COOLIFY_PUSHER_SECRET="$(derive_entropy "${app_entropy_identifier}-pusher-secret")"

_coolify_key_material="$(derive_entropy "${app_entropy_identifier}-laravel-app-key")"
export APP_COOLIFY_APP_KEY="base64:$(printf '%.32s' "${_coolify_key_material}" | base64 | tr -d '\n')"
unset _coolify_key_material
