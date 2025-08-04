#!/usr/bin/env python3

import os
import requests

# Configuration
firewall_id = 'fcd22c7c-93b5-4c04-af63-f14faf1e1151'  # The firewall we just created
hostname_to_find = 'fastapi-hello-world.example.com'

# Get token from environment
civo_token = os.environ.get('CIVO_TOKEN')
if not civo_token:
    raise Exception("CIVO_TOKEN environment variable not set")

headers = {'Authorization': f'bearer {civo_token}', 'Content-Type': 'application/json'}

print("Getting existing instances...")
response = requests.get('https://api.civo.com/v2/instances', headers={'Authorization': f'bearer {civo_token}'})

if response.status_code == 200:
    instances_data = response.json()
    if isinstance(instances_data, dict) and 'items' in instances_data:
        instances = instances_data['items']
    else:
        instances = instances_data
    
    # Find our instance
    target_instance = None
    for instance in instances:
        if hostname_to_find in instance.get('hostname', ''):
            target_instance = instance
            break
    
    if target_instance:
        print(f"Found instance: {target_instance['hostname']} (ID: {target_instance['id']})")
        print(f"Current status: {target_instance['status']}")
        print(f"Public IP: {target_instance.get('public_ip', 'None')}")
        print(f"Current firewall: {target_instance.get('firewall_id', 'None')}")
        
        # Update the firewall
        print(f"Applying firewall {firewall_id} to instance...")
        firewall_update = {'firewall_id': firewall_id}
        update_response = requests.put(f'https://api.civo.com/v2/instances/{target_instance["id"]}', 
                                     headers=headers, 
                                     json=firewall_update)
        
        if update_response.status_code == 200:
            print("✅ Firewall applied successfully!")
            print(f"🎉 Your instance should now be accessible at: http://{target_instance['public_ip']}")
            print("\nTry accessing:")
            print(f"🌐 Main site: http://{target_instance['public_ip']}")
            print(f"📚 API docs: http://{target_instance['public_ip']}/docs")
            print(f"❤️  Health check: http://{target_instance['public_ip']}/health")
        else:
            print(f"❌ Failed to apply firewall: {update_response.text}")
    else:
        print("❌ Could not find the target instance")
        print("Available instances:")
        for instance in instances:
            print(f"  - {instance['hostname']} ({instance['id']})")
else:
    print(f"❌ Failed to get instances: {response.text}")