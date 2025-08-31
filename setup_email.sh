#!/bin/bash

# Function to prompt for a value with a default
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local value

    read -p "$prompt [$default]: " value
    echo ${value:-$default}
}

# Create or update .env file
update_env() {
    local key="$1"
    local value="$2"
    if grep -q "^$key=" .env; then
        # Update existing value
        sed -i "s|^$key=.*|$key=$value|" .env
    else
        # Add new key-value pair
        echo "$key=$value" >> .env
    fi
}

echo "NetGuard Email Configuration Setup"
echo "--------------------------------"

# Email settings
EMAIL_FROM=$(prompt_with_default "Enter sender email address" "netguard@localhost")
EMAIL_TO=$(prompt_with_default "Enter recipient email address" "admin@localhost")
EMAIL_SUBJECT=$(prompt_with_default "Enter email subject" "NetGuard Security Alert")

# SMTP settings
SMTP_SERVER=$(prompt_with_default "Enter SMTP server" "localhost")
SMTP_PORT=$(prompt_with_default "Enter SMTP port" "587")
SMTP_USER=$(prompt_with_default "Enter SMTP username" "")
SMTP_PASSWORD=$(prompt_with_default "Enter SMTP password" "")

# Update .env file
update_env "EMAIL_FROM" "\"$EMAIL_FROM\""
update_env "EMAIL_TO" "\"$EMAIL_TO\""
update_env "EMAIL_SUBJECT" "\"$EMAIL_SUBJECT\""
update_env "SMTP_SERVER" "\"$SMTP_SERVER\""
update_env "SMTP_PORT" "$SMTP_PORT"
update_env "SMTP_USER" "\"$SMTP_USER\""
update_env "SMTP_PASSWORD" "\"$SMTP_PASSWORD\""

echo "Configuration updated successfully!"
