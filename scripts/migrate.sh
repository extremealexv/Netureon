#!/bin/bash

# Migrate from NetGuard to Netureon
cp /home/orangepi/NetGuard/scripts/migrate_linux.sh /home/orangepi/NetGuard/scripts/migrate_linux.sh.bak
curl -o /home/orangepi/NetGuard/scripts/migrate_linux.sh https://raw.githubusercontent.com/extremealexv/Netureon/v1.3.1/scripts/migrate_linux.sh
chmod +x /home/orangepi/NetGuard/scripts/migrate_linux.sh
sudo /home/orangepi/NetGuard/scripts/migrate_linux.sh
