import time
from fabric import Connection
from civo import Civo

# Configuration - Update these values
hostname_default = 'fastapi-hello-world.example.com'  # Change this to your desired hostname
ssh_key_name = 'default'  # Change this to your SSH key name in Civo

# Initialize Civo client
civo = Civo()

try:
    # Get available resources with error handling
    print("Getting available instance sizes...")
    sizes = civo.size.all()
    print(f"Available sizes: {[s['name'] for s in sizes[:5]]}")  # Show first 5
    
    # Try to find a suitable size (prefer small sizes for testing)
    size_candidates = ['g3.xsmall', 'g2.xsmall', 'g1.xsmall', 'xsmall']
    size_id = None
    
    for candidate in size_candidates:
        matching_sizes = [s for s in sizes if s['name'] == candidate]
        if matching_sizes:
            size_id = matching_sizes[0]['name']
            print(f"Using size: {size_id}")
            break
    
    if not size_id:
        # Fallback to first available size
        size_id = sizes[0]['name']
        print(f"Using fallback size: {size_id}")
    
    print("Getting available templates...")
    templates = civo.templates.all()
    print(f"Available templates: {[t['code'] for t in templates[:5]]}")  # Show first 5
    
    # Try to find a suitable Ubuntu template
    template_candidates = ['ubuntu-jammy', 'ubuntu-focal', 'ubuntu-20-04', 'ubuntu-22-04', 'ubuntu']
    template_id = None
    
    for candidate in template_candidates:
        matching_templates = [t for t in templates if candidate in t['code'].lower()]
        if matching_templates:
            template_id = matching_templates[0]['id']
            print(f"Using template: {matching_templates[0]['code']} (ID: {template_id})")
            break
    
    if not template_id:
        # Fallback to first available template
        template_id = templates[0]['id']
        print(f"Using fallback template: {templates[0]['code']} (ID: {template_id})")

    # Search for existing instance
    search_hostname = civo.instances.search(filter='hostname:{}'.format(hostname_default))
    
    # Get SSH key
    print("Getting SSH keys...")
    ssh_keys = civo.ssh.all()
    print(f"Available SSH keys: {[k['name'] for k in ssh_keys]}")
    
    ssh_key_matches = [k for k in ssh_keys if k['name'] == ssh_key_name]
    if not ssh_key_matches:
        print(f"SSH key '{ssh_key_name}' not found. Available keys: {[k['name'] for k in ssh_keys]}")
        if ssh_keys:
            ssh_id = ssh_keys[0]['id']
            print(f"Using first available SSH key: {ssh_keys[0]['name']}")
        else:
            raise Exception("No SSH keys found. Please add an SSH key to your Civo account first.")
    else:
        ssh_id = ssh_key_matches[0]['id']
        print(f"Using SSH key: {ssh_key_name}")

except Exception as e:
    print(f"Error getting Civo resources: {e}")
    print("This might be due to:")
    print("1. Invalid CIVO_TOKEN")
    print("2. API changes in Civo")
    print("3. Network connectivity issues")
    raise

# Create instance if it doesn't exist
if not search_hostname:
    print(f"Creating new instance: {hostname_default}")
    try:
        instance = civo.instances.create(
            hostname=hostname_default, 
            size=size_id, 
            region='lon1', 
            template_id=template_id,
            public_ip='true', 
            ssh_key_id=ssh_id
        )
        status = instance['status']
        print(f"Instance creation initiated. Status: {status}")

        # Wait for instance to be active
        while status != 'ACTIVE':
            status = civo.instances.search(filter='hostname:{}'.format(hostname_default))[0]['status']
            print(f"Instance status: {status}")
            time.sleep(10)
        
        # Wait additional time for SSH daemon to start
        print("Waiting for SSH daemon to start...")
        time.sleep(30)  # Increased wait time
    except Exception as e:
        print(f"Error creating instance: {e}")
        raise
else:
    print(f"Instance {hostname_default} already exists")

# Get instance IP and deploy
try:
    instance_info = civo.instances.search(filter='hostname:{}'.format(hostname_default))[0]
    ip_server = instance_info['public_ip']
    print(f"Instance IP: {ip_server}")
    
    # Determine username based on template (Ubuntu uses 'ubuntu', some others use 'root')
    username = 'ubuntu'  # Default for Ubuntu
    if 'debian' in template_id.lower():
        username = 'root'
    elif 'centos' in template_id.lower() or 'rhel' in template_id.lower():
        username = 'centos'
    
    print(f"Connecting to {username}@{ip_server}")

    # Connect and deploy
    c = Connection(f'{username}@{ip_server}')
    
    # Test connection first
    print("Testing SSH connection...")
    c.run('echo "SSH connection successful"')
    
    # Upload webroot
    result = c.put('webroot.gz', remote='/tmp')
    print(f"Uploaded {result.local} to {result.remote}")

    # Install and configure nginx
    print("Installing nginx...")
    c.sudo('apt update')
    c.sudo('apt install -qy nginx')
    c.sudo('systemctl enable nginx')
    c.sudo('systemctl start nginx')

    # Deploy the application
    print("Deploying application...")
    c.sudo('rm -rf /var/www/html/*')
    c.sudo('tar -C /var/www/html/ -xzvf /tmp/webroot.gz')

    # Set proper permissions
    c.sudo('chown -R www-data:www-data /var/www/html/')
    c.sudo('chmod -R 755 /var/www/html/')

    print(f"✅ Deployment completed successfully!")
    print(f"🌐 Your site should be available at: http://{ip_server}")
    
except Exception as e:
    print(f"Error during deployment: {e}")
    raise 