# ---- Base image ----
FROM python:3.10-slim

# ---- Working directory ----
WORKDIR /app

# ---- Install dependencies ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy project files ----
COPY bot.py .

# ---- Environment variables (runtime pe set karein) ----
ENV BOT_TOKEN=""
ENV ADMIN_ID="5770911041 5048189981 7829941642"

# ---- Run the bot ----
CMD ["python", "bot.py"]
