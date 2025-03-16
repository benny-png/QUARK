#!/bin/bash

# Start Nginx
nginx

# Start Huey worker
huey_consumer.py app.tasks.deployment.huey &

# Start FastAPI application with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 