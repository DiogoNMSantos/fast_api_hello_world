#!/usr/bin/env python3

import os
import time
from fabric import Connection

# Configuration
instance_ip = '212.2.246.218'
template_name = 'ubuntu-noble'  # From the previous output

print(f"Deploying FastAPI application to {instance_ip}...")

try:
    # Determine the correct user based on the template
    user = 'ubuntu'  # Ubuntu Noble uses 'ubuntu' user
    print(f"Connecting as user: {user}")
    
    conn = Connection(
        host=instance_ip,
        user=user,
        connect_kwargs={
            "key_filename": "~/.ssh/id_rsa",  # Adjust path as needed
        },
    )
    
    # Upload FastAPI application files
    print("Uploading FastAPI application files...")
    conn.put('main.py', '/tmp/main.py')
    conn.put('requirements.txt', '/tmp/requirements.txt')
    
    # Upload and extract webroot for static files
    try:
        conn.put('webroot.gz', '/tmp/webroot.gz')
        conn.run('cd /tmp && tar -xzvf webroot.gz')
    except:
        print("webroot.gz not found, creating basic webroot...")
        conn.run('mkdir -p /tmp/webroot')
    
    # Install Python, pip and system dependencies
    print("Installing Python and system dependencies...")
    conn.run('sudo apt-get update')
    conn.run('sudo apt-get install -y python3 python3-pip python3-venv nginx curl')
    
    # Set up application directory
    conn.run('sudo mkdir -p /opt/fastapi-app')
    conn.run('sudo cp /tmp/main.py /opt/fastapi-app/')
    conn.run('sudo cp /tmp/requirements.txt /opt/fastapi-app/')
    
    # Create virtual environment and install dependencies
    print("Installing Python dependencies...")
    conn.run('cd /opt/fastapi-app && sudo python3 -m venv venv')
    conn.run('cd /opt/fastapi-app && sudo venv/bin/pip install --upgrade pip')
    conn.run('cd /opt/fastapi-app && sudo venv/bin/pip install -r requirements.txt')
    
    # Create systemd service for FastAPI
    print("Creating systemd service for FastAPI...")
    service_content = '''[Unit]
Description=FastAPI Hello World
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fastapi-app
Environment=PATH=/opt/fastapi-app/venv/bin
ExecStart=/opt/fastapi-app/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
'''
    conn.run(f'sudo bash -c "cat > /etc/systemd/system/fastapi-app.service << \'EOF\'\n{service_content}EOF"')
    
    # Configure nginx as reverse proxy
    print("Configuring nginx as reverse proxy...")
    nginx_config = '''server {
    listen 80;
    server_name _;
    
    # Serve static files for root path
    location = / {
        root /var/www/html;
        try_files /index.html =404;
    }
    
    # Serve static assets
    location /static/ {
        root /var/www/html;
    }
    
    # Proxy API requests to FastAPI
    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /info {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /test/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
'''
    conn.run(f'sudo bash -c "cat > /etc/nginx/sites-available/fastapi-app << \'EOF\'\n{nginx_config}EOF"')
    conn.run('sudo rm -f /etc/nginx/sites-enabled/default')
    conn.run('sudo ln -sf /etc/nginx/sites-available/fastapi-app /etc/nginx/sites-enabled/')
    
    # Set up webroot for static content
    conn.run('sudo mkdir -p /var/www/html')
    try:
        conn.run('sudo cp -r /tmp/webroot/* /var/www/html/')
    except:
        # Create a basic index.html if webroot doesn't exist
        basic_html = '''<!DOCTYPE html>
<html><head><title>FastAPI Hello World</title></head>
<body><h1>FastAPI Hello World</h1>
<p>API is running! Check <a href="/docs">/docs</a> for API documentation.</p>
</body></html>'''
        conn.run(f'sudo bash -c "cat > /var/www/html/index.html << \'EOF\'\n{basic_html}EOF"')
    
    # Start services
    print("Starting FastAPI application and nginx...")
    conn.run('sudo systemctl daemon-reload')
    conn.run('sudo systemctl enable fastapi-app')
    conn.run('sudo systemctl start fastapi-app')
    conn.run('sudo systemctl enable nginx')
    conn.run('sudo systemctl restart nginx')
    
    # Check service status and troubleshoot
    print("Checking service status...")
    try:
        result = conn.run('sudo systemctl is-active fastapi-app', hide=True)
        if 'active' in result.stdout:
            print("✅ FastAPI service is running")
        else:
            print("❌ FastAPI service is not active")
            conn.run('sudo systemctl status fastapi-app --no-pager')
    except Exception as e:
        print(f"❌ FastAPI service check failed: {e}")

    try:
        result = conn.run('sudo systemctl is-active nginx', hide=True)
        if 'active' in result.stdout:
            print("✅ Nginx service is running")
        else:
            print("❌ Nginx service is not active")
            conn.run('sudo systemctl status nginx --no-pager')
    except Exception as e:
        print(f"❌ Nginx service check failed: {e}")
    
    # Additional network checks
    try:
        print("Checking if services are listening on expected ports...")
        conn.run('sudo netstat -tlnp | grep -E ":(80|8000)"')
        print("Checking if FastAPI responds locally...")
        conn.run('curl -s http://localhost:8000/health || echo "FastAPI not responding"')
        print("Checking if nginx responds locally...")
        conn.run('curl -s http://localhost/health || echo "Nginx proxy not working"')
    except Exception as e:
        print(f"Network checks failed: {e}")
    
    print(f"🎉 Deployment complete!")
    print(f"🌐 Main site: http://{instance_ip}")
    print(f"📚 API docs: http://{instance_ip}/docs")
    print(f"❤️  Health check: http://{instance_ip}/health") 
    print(f"ℹ️  App info: http://{instance_ip}/info")
    print(f"🧪 Test endpoint: http://{instance_ip}/test/123")
    
except Exception as deploy_error:
    print(f"Deployment error: {deploy_error}")
    print("You may need to check SSH key configuration or wait for the instance to be fully ready.")