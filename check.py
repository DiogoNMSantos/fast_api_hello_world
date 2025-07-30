import time
from fabric import Connection
from civo import Civo

# Configuration - Update these values
hostname_default = 'fastapi-hello-world.example.com'  # Change this to your desired hostname
ssh_key_name = 'default'  # Change this to your SSH key name in Civo

# Initialize Civo client
civo = Civo()

# Get available resources
size_id = civo.size.search(filter='name:g3.xsmall')[0]['name']  # Updated to newer size
template = civo.templates.search(filter='code:ubuntu-focal')[0]['id']  # Updated to Ubuntu 20.04
search_hostname = civo.instances.search(filter='hostname:{}'.format(hostname_default))
ssh_id = civo.ssh.search(filter='name:{}'.format(ssh_key_name))[0]['id']

# Create instance if it doesn't exist
if not search_hostname:
    print(f"Creating new instance: {hostname_default}")
    instance = civo.instances.create(
        hostname=hostname_default, 
        size=size_id, 
        region='lon1', 
        template_id=template,
        public_ip='true', 
        ssh_key_id=ssh_id
    )
    status = instance['status']

    # Wait for instance to be active
    while status != 'ACTIVE':
        status = civo.instances.search(filter='hostname:{}'.format(hostname_default))[0]['status']
        print(f"Instance status: {status}")
        time.sleep(10)
    
    # Wait additional time for SSH daemon to start
    print("Waiting for SSH daemon to start...")
    time.sleep(20)
else:
    print(f"Instance {hostname_default} already exists")

# Get instance IP and deploy
ip_server = civo.instances.search(filter='hostname:{}'.format(hostname_default))[0]['public_ip']
username = 'ubuntu'  # Updated for Ubuntu

print(f"Connecting to {username}@{ip_server}")

# Connect and deploy
c = Connection(f'{username}@{ip_server}')
result = c.put('webroot.gz', remote='/tmp')
print(f"Uploaded {result.local} to {result.remote}")

# Install and configure nginx
c.sudo('apt update')
c.sudo('apt install -qy nginx')
c.sudo('systemctl enable nginx')
c.sudo('systemctl start nginx')

# Deploy the application
c.sudo('rm -rf /var/www/html/*')
c.sudo('tar -C /var/www/html/ -xzvf /tmp/webroot.gz')

# Set proper permissions
c.sudo('chown -R www-data:www-data /var/www/html/')
c.sudo('chmod -R 755 /var/www/html/')

print(f"Deployment completed! Your site should be available at: http://{ip_server}") 