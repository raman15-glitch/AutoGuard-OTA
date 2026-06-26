FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# We don't copy the code here. We will "mount" it live using docker-compose 
# so you don't have to rebuild the container every time you change a line of code!

CMD ["python3", "server/src/server.py"]