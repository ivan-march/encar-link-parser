# Encar.com link parser
This script monitors new car listings on [Encar.com](https://www.encar.com ) — a Korean used car marketplace.
When new listings appear, it sends notifications to Telegram.

🛠 It works using Selenium and supports:
- Using proxies (including authenticated ones)
- Anti-detection browser settings
- Translating car model name
- Sending alerts via Telegram

#### `main.py`
Main executable file. Contains: 

- Monitoring loop
- Logging setup
- Config handling
     
#### `src/core.py`
Contains the main class `EncarBot` — responsible for parsing advertisements from `encar.com`.

#### `src/utils.py`
Utility functions: 
- Logging
- Working with SQLite database
- Sending messages to Telegram
- Translating words
- Launching the browser

## 📦 Requirements
To run this project, you need: 
- Python 3.9+
- Selenium
- Chrome browser
     
`requirements.txt`
```txt
requests==2.32.3
selenium==4.32.0
selenium-stealth==1.0.6
fake-useragent==2.2.0
selenium-authenticated-proxy==1.1.2
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```


## 🔧 Setup
**1. config.json** 

Create a `config.json` file like this:

```json
{
  "tg_api_token": "ваш_telegram_бот_токен",
  "tg_chat_id": "ваш_chat_id",
  "webdriver": {
    "bot1": {
      "headless": true,
      "use_proxy": true,
      "proxy": {
        "host": "your.proxy.host",
        "port": "8080",
        "login": "user",
        "password": "pass"
      },
      "ua": "Mozilla/5.0 ..."
    }
  }
}
```

**2. encar_links.txt**

Add links from `encar.com` that you want to monitor:

    https://www.encar.com/dc/dc_carsearch_list.html?cate_id=... 
    https://fem.encar.com/fem/fem_search_list.html?... 

## 🚀 How to Run
```bash
python main.py
```
 
The script will: 

- Periodically check specified links
- Parse new car listings
- Send them to Telegram
- Save results in a database to avoid duplicates
     
## 📬 Setting Up Telegram Notifications
To receive notifications:

- Create a new Telegram bot using @BotFather 
- Get your tg_api_token
- Find out your chat_id

## 📁 Example dictionary.json for translation
     
```json
{
  "쏘렌토": "Sorento",
  "싼타페": "Santa Fe",
  "투싼": "Tucson",
  "팰리세이드": "Palisade"
}
```

## 🤝 Author 

👤 Ivan Marchenko

🔗 [GitHub Project](https://github.com/ivan-march)

🔗 [GitVerse Project](https://gitverse.ru/ivan-march)

📬 [Telegram](https://t.me/ivanumarch): @ivanumarch

## 💡 Want Custom Features?

I can help implement:

- Telegram MiniApp to view results
- Web interface with filters
- Price tracking
- Notifications via WhatsApp, Email or SMS
     
Contact me on Telegram: 👉 [@ivanumarch](https://t.me/ivanumarch)

## 📜 License 

MIT License