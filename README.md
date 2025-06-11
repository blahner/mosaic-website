# mosaic-website
This repository contains a Flask web application for MOSAIC data management, providing user interfaces for downloading and uploading data to an Amazon S3 bucket. The application runs on an AWS EC2 instance (Amazon Linux) with data stored in AWS S3. AWS CloudFront provides content delivery for improved download performance.

### Set up website
This assumes you have already set up an Amazon EC2 instance and allocated an elastic IP address via the AWS console. This also assumes you have a domain name pointed to the IP address.

1. Install git, install miniconda, clone website repository
```
mkdir ~/projects
cd ~/projects

wget <your distro here> #example: https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh 

sudo yum update -y
sudo yum install git -y

git clone <mosaic-website repo>
cd mosaic-website
conda create -n mosaic-website python=3.11
conda activate mosaic-website
pip install -r requirements.txt
```

2. Test webapp locally
```
gunicorn --bind 127.0.0.1:5000 wsgi:app
```

3. Create Gunicorn config file
```
nano gunicorn.conf.py
```
In the file, put:
```
# gunicorn.conf.py
bind = "127.0.0.1:5000"
workers = 2 
worker_class = "sync"
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```
Make sure you can run the app with the config file now
```
gunicorn --config gunicorn.conf.py wsgi:app
```

4. Create systemd service for production
```
sudo nano /etc/systemd/system/webapp.service
```
In the file, put:
```
[Unit]
Description=MOSAIC web app server
After=network.target

[Service]
Type=notify
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/projects/mosaic-website
Environment=PATH=/home/ec2-user/miniconda3/bin:/home/ec2-user/miniconda3/envs/mosaic-website/bin
ExecStart=/home/ec2-user/miniconda3/envs/mosaic-website/bin/gunicorn --config gunicorn.conf.py wsgi:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

5. Start the service
```
sudo systemctl daemon-reload
sudo systemctl enable webapp
sudo systemctl start webapp
sudo systemctl status webapp
```

6. Set up nxinx
```
sudo yum update -y
sudo yum install nginx -y
sudo nano /etc/nginx/conf.d/mosaic.csail.mit.edu.conf
```
In the file, put:
```
server {
    listen 80;
    server_name mosaic.csail.mit.edu;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Serve static files directly (if you have any)
    location /static/ {
        alias /home/ec2-user/projects/mosaic-website/static/;
        expires -1;
        add_header Cache-Control "public, immutable";
    }
}
```
Test nxinx configuration
```
sudo nginx -t
```

Start and enable nginx
```
sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl status nginx
```

7. Set up SSL
```
sudo yum install python3-pip -y
sudo pip3 install certbot certbot-nginx
sudo certbot --nginx -d mosaic.csail.mit.edu
```

Test and check services
```
# Test HTTP
curl -I http://mosaic.csail.mit.edu

# Test HTTPS
curl -I https://mosaic.csail.mit.edu

# Check services
sudo systemctl status nginx
sudo systemctl status webapp
```

8. Set up automatic renewal and test
```
# Add to crontab
echo "0 12 * * * /usr/local/bin/certbot renew --quiet" | sudo tee -a /etc/crontab

# Test renewal
sudo certbot renew --dry-run
```

### Extra commands

test nginx configuration
```
sudo nginx -t
```

reload nginx
```
sudo systemctl reload nginx
```

restart webapp to propogate changes made to files in /templates/
```
sudo systemctl restart webapp.service
```

### Questions?
First check the FAQ page to see if your question is answered. Next, if the question is related to this project page itself (e.g., frontend or backend code, download bugs etc), raise a GitHub issue. If the question is related to the actual data that is downloaded, contact the "owner" for that data object and/or check the object's provided GitHub url.
