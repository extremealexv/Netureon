import paramiko
from scp import SCPClient
import sys
import os

def create_ssh_client(server, port, user, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)
    return client

try:
    print("Connecting to 192.168.1.60...")
    ssh = create_ssh_client('192.168.1.60', 22, 'orangepi', 'orangepi')
    
    # Check directory
    stdin, stdout, stderr = ssh.exec_command('pwd')
    print("PWD:", stdout.read().decode().strip())
    
    # Check service file to find working directory
    stdin, stdout, stderr = ssh.exec_command('cat /etc/systemd/system/netureon_web.service | grep WorkingDirectory')
    working_dir = stdout.read().decode().strip().split('=')[-1]
    print("Working Directory from systemd:", working_dir)
    
    if not working_dir:
        working_dir = '/home/orangepi/Netureon'
        
    print(f"Deploying to {working_dir}...")
    
    print("Checking netureon_scan logs...")
    stdin, stdout, stderr = ssh.exec_command('journalctl -u netureon_scan.service -n 50 --no-pager')
    print("Logs:")
    print(stdout.read().decode())
    
    print("Checking netureon.log...")
    stdin, stdout, stderr = ssh.exec_command('cat /home/orangepi/Netureon/logs/netureon.log | tail -n 50')
    print("App Logs:")
    print(stdout.read().decode())
    
    ssh.close()
except Exception as e:
    print("Error:", e)
