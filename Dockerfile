# 1. Start from a standard, stable Python 3.11 base image
FROM python:3.11-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy the requirements file first and install dependencies
# This step is cached, so it runs faster on subsequent builds
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy all of your application files into the container
COPY . .

# 5. Tell the container to listen on port 8080
EXPOSE 8080

# 6. The final command to run your app using Uvicorn (bypassing Gunicorn)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
