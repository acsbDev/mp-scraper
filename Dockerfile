# 1) Start from a slim Python image
FROM python:3.12-slim-bookworm

# 2) Install all the apt packages Chrome needs
RUN apt-get update && apt-get install -y \
    wget unzip gnupg ca-certificates \
    fonts-liberation libgconf-2-4 libnss3 libx11-xcb1 \
    libxcomposite1 libxcursor1 libxdamage1 libxi6 libxtst6 \
    libpangocairo-1.0-0 libxrandr2 libpango-1.0-0 xdg-utils \
  && rm -rf /var/lib/apt/lists/*

# 3) Add Google’s signing key & repo, then install Chrome
RUN wget -qO - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
  && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
     > /etc/apt/sources.list.d/google-chrome.list \
  && apt-get update && apt-get install -y google-chrome-stable \
  && rm -rf /var/lib/apt/lists/*

# 4) Set your working directory
WORKDIR /app

# 5) Copy irequirements.txt
COPY requirements.txt ./

# 6) Install requirements
RUN pip install --no-cache-dir -r requirements.txt

# 7) Copy the rest of your code
COPY . .

# 8) Ensure the download folder exists
RUN mkdir -p mp_scraper

# 9) On container start, run main.py — when it finishes, the container will exit.
CMD ["python", "main.py"]