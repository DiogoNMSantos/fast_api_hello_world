import time
from fabric import Connection
from civo import Civo

# Configuration - Update these values
hostname_default = 'fastapi-hello-world.example.com'  # Change this to your desired hostname
ssh_key_name = 'default'  # Change this to your SSH key name in Civo

# Initialize Civo client
civo = Civo()

try:
    print("Getting available instance sizes...")
    # Get available sizes using search method
    sizes = civo.size.search()
    print(f"Available sizes: {[s['name'] for s in sizes[:5]]}")  # Show first 5
    
    # Try to find a suitable size (prefer small sizes for testing)
    size_candidates = ['g3.xsmall', 'g4s.xsmall', 'g2.xsmall', 'xsmall']
    size_id = None
    
    for candidate in size_candidates:
        matching_sizes = [s for s in sizes if s['name'] == candidate]
        if matching_sizes:
            size_id = matching_sizes[0]['name']
            print(f"Using size: {size_id}")
            break
    
    if not size_id:
        # Fallback to first available size
        size_id = sizes[0]['name'] if sizes else None
        print(f"Using fallback size: {size_id}")
    
    if not size_id:
        raise Exception("No suitable instance size found")
    
    print("Getting available templates...")
    # Get available templates
    templates = civo.templates.search()
    print(f"Available templates: {[t.get('code', t.get('name', 'unknown')) for t in templates[:5]]}")
    
    # Try to find a suitable template
    template_candidates = ['ubuntu-focal', 'ubuntu-jammy', 'ubuntu-bionic', 'debian-11', 'debian-10']
    template_id = None
    
    for candidate in template_candidates:
        matching_templates = [t for t in templates if t.get('code') == candidate]
        if matching_templates:
            template_id = matching_templates[0]['id']
            print(f"Using template: {candidate} (ID: {template_id})")
            break
    
    if not template_id:
        # Fallback to first available template
        template_id = templates[0]['id'] if templates else None
        template_name = templates[0].get('code', templates[0].get('name', 'unknown')) if templates else 'unknown'
        print(f"Using fallback template: {template_name} (ID: {template_id})")
    
    if not template_id:
        raise Exception("No suitable template found")
    
    print("Getting SSH keys...")
    # Get SSH keys
    ssh_keys = civo.ssh.search()
    print(f"Available SSH keys: {[key['name'] for key in ssh_keys]}")
    
    # Find SSH key
    ssh_id = None
    matching_keys = [key for key in ssh_keys if key['name'] == ssh_key_name]
    if matching_keys:
        ssh_id = matching_keys[0]['id']
        print(f"Using SSH key: {ssh_key_name} (ID: {ssh_id})")
    else:
        print(f"SSH key '{ssh_key_name}' not found!")
        if ssh_keys:
            ssh_id = ssh_keys[0]['id']
            print(f"Using first available SSH key: {ssh_keys[0]['name']} (ID: {ssh_id})")
        else:
            print("No SSH keys found - proceeding without SSH key")
    
    # Check if instance already exists
    print(f"Checking if instance '{hostname_default}' already exists...")
    existing_instances = civo.instances.search()
    search_hostname = [instance for instance in existing_instances if instance['hostname'] == hostname_default]
    
    if not search_hostname:
        print(f"Creating new instance: {hostname_default}")
        instance = civo.instances.create(
            hostname=hostname_default,
            size=size_id,
            template_id=template_id,
            public_ip='true',
            ssh_key=ssh_id
        )
        print(f"Instance creation initiated: {instance}")
        
        # Wait for instance to be ready
        print("Waiting for instance to be ready...")
        for i in range(60):  # Wait up to 10 minutes
            instances = civo.instances.search()
            current_instance = [inst for inst in instances if inst['hostname'] == hostname_default]
            if current_instance and current_instance[0]['status'] == 'ACTIVE':
                instance = current_instance[0]
                print(f"Instance is ready! Status: {instance['status']}")
                break
            print(f"Waiting... (attempt {i+1}/60)")
            time.sleep(10)
        else:
            print("Warning: Timeout waiting for instance to be ready")
    else:
        instance = search_hostname[0]
        print(f"Instance already exists: {instance['hostname']} (Status: {instance['status']})")
    
    # Get the current instance details
    instances = civo.instances.search()
    current_instance = [inst for inst in instances if inst['hostname'] == hostname_default]
    if current_instance:
        instance = current_instance[0]
        print(f"Instance details:")
        print(f"  Hostname: {instance['hostname']}")
        print(f"  Status: {instance['status']}")
        print(f"  Size: {instance['size']}")
        print(f"  Public IP: {instance.get('public_ip', 'None')}")
        print(f"  Private IP: {instance.get('private_ip', 'None')}")
        
        # Deploy the webroot files if instance has a public IP
        if instance.get('public_ip') and instance['status'] == 'ACTIVE':
            print(f"Deploying files to {instance['public_ip']}...")
            try:
                # Give the instance a bit more time to fully boot
                time.sleep(30)
                
                conn = Connection(
                    host=instance['public_ip'],
                    user='root',  # Adjust user as needed
                    connect_kwargs={
                        "key_filename": "~/.ssh/id_rsa",  # Adjust path as needed
                    },
                )
                
                # Upload and extract webroot
                conn.put('webroot.gz', '/tmp/webroot.gz')
                conn.run('cd /tmp && tar -xzvf webroot.gz')
                conn.run('mkdir -p /var/www/html')
                conn.run('cp -r /tmp/webroot/* /var/www/html/')
                
                # Install nginx if not present
                try:
                    conn.run('which nginx', hide=True)
                    print("nginx already installed")
                except:
                    print("Installing nginx...")
                    conn.run('apt-get update')
                    conn.run('apt-get install -y nginx')
                
                # Start nginx
                conn.run('systemctl enable nginx')
                conn.run('systemctl start nginx')
                
                print(f"Deployment complete! Visit http://{instance['public_ip']}")
                
            except Exception as deploy_error:
                print(f"Deployment error (this is normal for new instances): {deploy_error}")
                print("You may need to wait longer for the instance to fully boot, then run the deployment manually.")
        else:
            print("Instance doesn't have a public IP or isn't ready for deployment")
    else:
        print("Could not find the created instance")
        
except Exception as e:
    print(f"Error getting Civo resources: {e}")
    print("This might be due to:")
    print("1. Invalid CIVO_TOKEN")
    print("2. API changes in Civo")
    print("3. Network connectivity issues")
    print("4. Region availability issues")
    
    # Additional debug info
    import os
    token = os.environ.get('CIVO_TOKEN', 'NOT_SET')
    print(f"CIVO_TOKEN status: {'SET' if token != 'NOT_SET' else 'NOT_SET'}")
    if token != 'NOT_SET':
        print(f"Token length: {len(token)} characters") 