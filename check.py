import time
import os
import json
from fabric import Connection
from civo import Civo

# Configuration - Update these values
hostname_default = 'fastapi-hello-world.example.com'  # Change this to your desired hostname
ssh_key_name = 'default'  # Change this to your SSH key name in Civo

# Get token from environment
civo_token = os.environ.get('CIVO_TOKEN')
if not civo_token:
    raise Exception("CIVO_TOKEN environment variable not set")

# Initialize Civo client with token and region
print("Initializing Civo client...")
try:
    # Try different initialization approaches
    civo = Civo(civo_token, region='LON1')  # Explicit token and region
    print("Civo client initialized successfully")
except Exception as init_error:
    print(f"Error initializing Civo client: {init_error}")
    # Fallback to default initialization
    civo = Civo()

try:
    print("Getting available instance sizes...")
    
    # Add debugging to see what we're actually getting
    try:
        sizes_response = civo.size.search()
        print(f"Sizes API response type: {type(sizes_response)}")
        if hasattr(sizes_response, 'json'):
            print("Response has json() method, trying to parse...")
            sizes = sizes_response.json()
        else:
            sizes = sizes_response
        
        print(f"Sizes data type: {type(sizes)}")
        if isinstance(sizes, dict) and 'items' in sizes:
            sizes = sizes['items']
        elif isinstance(sizes, dict) and 'data' in sizes:
            sizes = sizes['data']
        
        print(f"Available sizes: {[s['name'] for s in sizes[:5]] if sizes else 'No sizes found'}")
        
    except Exception as size_error:
        print(f"Error getting sizes: {size_error}")
        print("Trying alternative API call...")
        # Try different approach
        import requests
        headers = {'Authorization': f'bearer {civo_token}'}
        response = requests.get('https://api.civo.com/v2/sizes', headers=headers)
        print(f"Direct API status: {response.status_code}")
        print(f"Direct API response preview: {response.text[:200]}...")
        if response.status_code == 200:
            sizes = response.json()
            if isinstance(sizes, dict) and 'items' in sizes:
                sizes = sizes['items']
        else:
            raise Exception(f"API returned status {response.status_code}: {response.text}")
    
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
    try:
        # Try the templates API with debugging
        templates_response = civo.templates.search()
        print(f"Templates API response type: {type(templates_response)}")
        if hasattr(templates_response, 'json'):
            templates = templates_response.json()
        else:
            templates = templates_response
            
        if isinstance(templates, dict) and 'items' in templates:
            templates = templates['items']
        elif isinstance(templates, dict) and 'data' in templates:
            templates = templates['data']
            
    except Exception as template_error:
        print(f"Error with templates API: {template_error}")
        print("Trying direct API call...")
        import requests
        headers = {'Authorization': f'bearer {civo_token}'}
        response = requests.get('https://api.civo.com/v2/disk_images', headers=headers)
        print(f"Templates API status: {response.status_code}")
        print(f"Templates API response preview: {response.text[:200]}...")
        if response.status_code == 200:
            templates = response.json()
            if isinstance(templates, dict) and 'items' in templates:
                templates = templates['items']
        else:
            raise Exception(f"Templates API returned status {response.status_code}: {response.text}")
    
    # Filter OUT k3s templates and keep only OS templates
    os_templates = [t for t in templates if t.get('distribution') not in ['civo-k3s-alpine', 'civo-k3s']]
    k3s_templates = [t for t in templates if t.get('distribution') in ['civo-k3s-alpine', 'civo-k3s']]
    
    print(f"Total templates found: {len(templates)}")
    print(f"K3s templates (filtered out): {len(k3s_templates)} - {[t['name'] for t in k3s_templates[:3]]}")
    print(f"OS templates available: {len(os_templates)} - {[t['name'] for t in os_templates[:5]]}")
    
    # Try to find a suitable OS template (prioritize Ubuntu)
    template_candidates = ['ubuntu-noble', 'ubuntu-jammy', 'ubuntu-focal', 'debian-12', 'debian-11', 'rocky-10', 'rocky-9']
    template_id = None
    template_name = None
    
    for candidate in template_candidates:
        matching_templates = [t for t in os_templates if t['name'] == candidate]
        if matching_templates:
            template_id = matching_templates[0]['id']
            template_name = candidate
            template_distribution = matching_templates[0].get('distribution', 'unknown')
            print(f"✅ Using template: {template_name} (ID: {template_id}) - Distribution: {template_distribution}")
            break
    
    if not template_id and os_templates:
        # Fallback to first available OS template (not k3s)
        template_id = os_templates[0]['id']
        template_name = os_templates[0]['name']
        template_distribution = os_templates[0].get('distribution', 'unknown')
        print(f"⚠️ Using fallback OS template: {template_name} (ID: {template_id}) - Distribution: {template_distribution}")
    elif not template_id:
        # Last resort: use any template (this shouldn't happen with proper filtering)
        template_id = templates[0]['id'] if templates else None
        template_name = templates[0].get('name', 'unknown') if templates else 'unknown'
        print(f"❌ FALLBACK: Using any available template: {template_name} (ID: {template_id})")
    
    if not template_id:
        raise Exception("No suitable template found")
    
    print("Getting SSH keys...")
    try:
        ssh_keys_response = civo.ssh.search()
        if hasattr(ssh_keys_response, 'json'):
            ssh_keys = ssh_keys_response.json()
        else:
            ssh_keys = ssh_keys_response
            
        if isinstance(ssh_keys, dict) and 'items' in ssh_keys:
            ssh_keys = ssh_keys['items']
        elif isinstance(ssh_keys, dict) and 'data' in ssh_keys:
            ssh_keys = ssh_keys['data']
            
    except Exception as ssh_error:
        print(f"Error with SSH keys API: {ssh_error}")
        print("Trying direct API call...")
        import requests
        headers = {'Authorization': f'bearer {civo_token}'}
        response = requests.get('https://api.civo.com/v2/sshkeys', headers=headers)
        print(f"SSH keys API status: {response.status_code}")
        if response.status_code == 200:
            ssh_keys = response.json()
            if isinstance(ssh_keys, dict) and 'items' in ssh_keys:
                ssh_keys = ssh_keys['items']
        else:
            print(f"SSH keys API returned status {response.status_code}: {response.text}")
            ssh_keys = []
    
    print(f"Available SSH keys: {[key['name'] for key in ssh_keys] if ssh_keys else 'No SSH keys found'}")
    
    # Find SSH key
    ssh_id = None
    if ssh_keys:
        matching_keys = [key for key in ssh_keys if key['name'] == ssh_key_name]
        if matching_keys:
            ssh_id = matching_keys[0]['id']
            print(f"Using SSH key: {ssh_key_name} (ID: {ssh_id})")
        else:
            print(f"SSH key '{ssh_key_name}' not found!")
            ssh_id = ssh_keys[0]['id']
            print(f"Using first available SSH key: {ssh_keys[0]['name']} (ID: {ssh_id})")
    else:
        print("No SSH keys found - proceeding without SSH key")
    
    # Check if instance already exists
    print(f"Checking if instance '{hostname_default}' already exists...")
    try:
        instances_response = civo.instances.search()
        if hasattr(instances_response, 'json'):
            existing_instances = instances_response.json()
        else:
            existing_instances = instances_response
            
        if isinstance(existing_instances, dict) and 'items' in existing_instances:
            existing_instances = existing_instances['items']
        elif isinstance(existing_instances, dict) and 'data' in existing_instances:
            existing_instances = existing_instances['data']
            
    except Exception as instances_error:
        print(f"Error getting instances: {instances_error}")
        print("Trying direct API call...")
        import requests
        headers = {'Authorization': f'bearer {civo_token}'}
        response = requests.get('https://api.civo.com/v2/instances', headers=headers)
        if response.status_code == 200:
            existing_instances = response.json()
            if isinstance(existing_instances, dict) and 'items' in existing_instances:
                existing_instances = existing_instances['items']
        else:
            existing_instances = []
    
    search_hostname = [instance for instance in existing_instances if instance['hostname'] == hostname_default]
    
    if not search_hostname:
        print(f"Creating new instance: {hostname_default}")
        # Use direct API call for creation since the library seems to have issues
        import requests
        headers = {'Authorization': f'bearer {civo_token}', 'Content-Type': 'application/json'}
        create_data = {
            'hostname': hostname_default,
            'size': size_id,
            'disk_image': template_id,
            'public_ip': 'create'
        }
        if ssh_id:
            create_data['ssh_key'] = ssh_id
            
        response = requests.post('https://api.civo.com/v2/instances', 
                               headers=headers, 
                               json=create_data)
        
        if response.status_code in [200, 201]:
            instance_data = response.json()
            print(f"Instance creation initiated: {instance_data}")
            
            # Wait for instance to be ready
            print("Waiting for instance to be ready...")
            for i in range(60):  # Wait up to 10 minutes
                time.sleep(10)
                response = requests.get('https://api.civo.com/v2/instances', headers={'Authorization': f'bearer {civo_token}'})
                if response.status_code == 200:
                    instances_data = response.json()
                    if isinstance(instances_data, dict) and 'items' in instances_data:
                        instances = instances_data['items']
                    else:
                        instances = instances_data
                    
                    current_instance = [inst for inst in instances if inst['hostname'] == hostname_default]
                    if current_instance and current_instance[0]['status'] == 'ACTIVE':
                        instance = current_instance[0]
                        print(f"Instance is ready! Status: {instance['status']}")
                        break
                print(f"Waiting... (attempt {i+1}/60)")
            else:
                print("Warning: Timeout waiting for instance to be ready")
        else:
            raise Exception(f"Failed to create instance: {response.status_code} - {response.text}")
    else:
        instance = search_hostname[0]
        print(f"Instance already exists: {instance['hostname']} (Status: {instance['status']})")
    
    # Get the current instance details
    response = requests.get('https://api.civo.com/v2/instances', headers={'Authorization': f'bearer {civo_token}'})
    if response.status_code == 200:
        instances_data = response.json()
        if isinstance(instances_data, dict) and 'items' in instances_data:
            instances = instances_data['items']
        else:
            instances = instances_data
            
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
                    
                    # Determine the correct user based on the template
                    user = 'root'  # Default fallback
                    if template_name and 'ubuntu' in template_name.lower():
                        user = 'ubuntu'
                    elif template_name and 'debian' in template_name.lower():
                        user = 'admin'
                    elif template_name and 'rocky' in template_name.lower():
                        user = 'rocky'
                    
                    print(f"Connecting as user: {user}")
                    
                    conn = Connection(
                        host=instance['public_ip'],
                        user=user,
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
                        if template_name and ('ubuntu' in template_name.lower() or 'debian' in template_name.lower()):
                            # Debian/Ubuntu
                            conn.run('apt-get update')
                            conn.run('apt-get install -y nginx')
                        elif template_name and 'rocky' in template_name.lower():
                            # Rocky Linux
                            conn.run('dnf update -y')
                            conn.run('dnf install -y nginx')
                        else:
                            # Fallback to apt (most common)
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
    token = os.environ.get('CIVO_TOKEN', 'NOT_SET')
    print(f"CIVO_TOKEN status: {'SET' if token != 'NOT_SET' else 'NOT_SET'}")
    if token != 'NOT_SET':
        print(f"Token length: {len(token)} characters")
        print(f"Token prefix: {token[:10]}...")
        
    # Try a simple API test
    print("\nTesting direct API access...")
    try:
        import requests
        headers = {'Authorization': f'bearer {token}'}
        response = requests.get('https://api.civo.com/v2/quota', headers=headers)
        print(f"Quota API status: {response.status_code}")
        if response.status_code == 200:
            print("✅ API authentication is working!")
            quota_data = response.json()
            print(f"Quota response: {quota_data}")
        else:
            print(f"❌ API authentication failed: {response.text}")
    except Exception as api_test_error:
        print(f"API test error: {api_test_error}") 