import os
import json
import shutil
import logging
import sqlite3
import textwrap
import requests
from typing import Dict, Optional
from selenium import webdriver
from selenium_stealth import stealth
from fake_useragent import UserAgent
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium_authenticated_proxy import SeleniumAuthenticatedProxy


def setup_logging(logs_path: str) -> logging.Logger:
    """Configuring the application logger."""
    log_file = os.path.join(logs_path, 'app.log')

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    # Console output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File output (ERROR and higher)
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.ERROR)
        file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(module)s: %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning("Couldn't set up logging to a file: %s", e)

    return logger


def read_config(config_path='config.json', logger=None):
    """
    Reading the configuration from the config.json file.
    """
    logger = logger or logging.getLogger(__name__)
    config_path = os.path.join(os.path.dirname(__file__), '..', config_path)
    with open(config_path, 'r', encoding='utf-8') as file:
        try:
            config_content = file.read()
            return json.loads(config_content)
        except Exception as e:
            logger.exception('Unexpected error when reading the config: %s', e)
            return {}

def init_driver(user, config, users_directory='user_data/', headless=False) -> webdriver:
    """
    Initiates a selenium driver session.
    """
    service = Service()
    options = Options()
    options.add_argument('start-maximized')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    base_directory = os.path.join(os.getcwd(), users_directory)
    user_directory = os.path.join(base_directory, user)
    webdriver_config = config.get('webdriver', {}).get(user, {})

    proxy_directory = os.path.join(base_directory, 'proxy', user)
    if webdriver_config.get('use_proxy'):
        proxy_config = webdriver_config.get('proxy', {})
        os.makedirs(proxy_directory, exist_ok=True)
        # Initialize SeleniumAuthenticatedProxy
        proxy_login = proxy_config.get('login')
        proxy_password = proxy_config.get('password')
        proxy_host = proxy_config.get('host')
        proxy_port = proxy_config.get('port')
        proxy_url = f'http://{proxy_login}:{proxy_password}@{proxy_host}:{proxy_port}'
        proxy_helper = SeleniumAuthenticatedProxy(proxy_url=proxy_url, tmp_folder=proxy_directory)
        # Enrich Chrome options with proxy authentication
        proxy_helper.enrich_chrome_options(options)
    else:
        if os.path.isdir(proxy_directory):
            shutil.rmtree(proxy_directory, ignore_errors=True)

    if config.get('user_dir'):
        options.add_argument(f'user-data-dir={user_directory}')

    options.add_argument('--enable-unsafe-swiftshader')
    # SSL error fix
    options.add_argument('--ignore-certificate-errors-spki-list')
    options.add_argument('--ignore-ssl-errors')
    #
    options.add_argument('--mute-audio')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-session-restore')
    options.add_argument('--no-sandbox')
    if headless:
        options.add_argument('--headless')

    driver = webdriver.Chrome(service=service, options=options)
    stealth(driver=driver,
            user_agent=webdriver_config.get('ua', ''),
            languages=['ru-RU', 'ru'],
            vendor='Google Inc.',
            platform='Win32',
            webgl_vendor='Intel Inc.',
            renderer='Intel Iris OpenGL Engine',
            fix_hairline=True,
            run_on_insecure_origins=True
            )

    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
      '''
    })
    return driver


def user_agents_to_file(quantity: int = 1000, output_file: str = 'user_agents.json'):
    """
    Saves the json of a random user agent to a file.
    """
    accounts = {}
    for acc in range(0, quantity):
        user_agent = UserAgent(
            browsers=['chrome', 'firefox', 'safari'],
            os=['windows', 'macos', 'linux', 'android', 'ios'],
            platforms=['mobile', 'tablet'],
        )
        accounts[acc] = {'ua': user_agent.random}
    with open(output_file, 'w+', encoding='utf-8') as f:
        json.dump(accounts, f)


def filter_encar_links(file_path: str) -> list[str]:
    """Returns a list of strings starting with encar.com"""
    encar_links = []
    with open(file_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith((
                'http://encar.com',
                'https://encar.com',
                'http://www.encar.com',
                'https://www.encar.com'
            )):
                encar_links.append(line)
    return encar_links


def init_db(db_path: str = 'user_data/cars.db') -> None:
    """Creates a table if there is none."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS encar_searches (
                link TEXT NOT NULL,
                car_id TEXT NOT NULL,
                title TEXT,
                details TEXT,
                year TEXT,
                km TEXT,
                price TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                seen INTEGER DEFAULT 0,
                PRIMARY KEY (car_id)
            )
        ''')
        conn.commit()


def add_cars_to_db(
        cars: Dict,
        link: str,
        table_name:str,
        db_path: str = 'user_data/cars.db',
        logger: Optional[logging.Logger] = None
    ) -> None:
    """Adds cars to the database."""
    logger = logger or logging.getLogger(__name__)

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            for car_id, car_fields in cars.items():
                cursor.execute(f'''
                    INSERT OR IGNORE INTO {table_name}
                    (link, car_id, title, details, year, km, price)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    link,
                    car_id,
                    car_fields.get('title'),
                    car_fields.get('details'),
                    car_fields.get('year'),
                    car_fields.get('km'),
                    car_fields.get('price')
                ))
            conn.commit()
    except Exception as e:
        logger.error('Error when adding an entry: %s', e, exc_info=True)


def get_existing_cars(link: str, table_name: str, db_path: str = 'user_data/cars.db') -> set[str]:
    """Returns a set of car_ids for a given link."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT car_id FROM {table_name}
                WHERE link = ?
            ''', (link,))
            return {row[0] for row in cursor.fetchall()}
    except Exception as e:
        print(f"[ERROR] Couldn't get existing records: {e}")
        return set()


def car_to_telegram(
        car: tuple,
        api_token: str,
        chat_id: str,
        logger: Optional[logging.Logger] = None
    ) -> None:
    """Sends a message about the added car to the telegram chat."""
    logger = logger or logging.getLogger(__name__)
    api_url = f'https://api.telegram.org/bot{api_token}/sendMessage'
    car_id, car_data = car
    message = textwrap.dedent(f"""
        🚗 New ad Encar.com!
        ID: {car_id}
        Model: {car_data.get('title', 'неизвестно')}
        Price: {car_data.get('price', 'не указана')} ₩
        Mileage: {car_data.get('km', 'не указан')}
        Release date: {car_data.get('year', 'не указан')}
        Link: https://fem.encar.com/cars/detail/{car_id}
    """).strip()
    try:
        response = requests.post(api_url, json={'chat_id': chat_id, 'text': message})
        response.raise_for_status()
    except Exception as e:
        logger.error('Error sending telegram message: %s', e, exc_info=True)


def translate_word(
        word: str,
        dictionary: str = 'dictionary.json',
        logger: Optional[logging.Logger] = None
    ) -> str:
    """Translate word from user dictionary."""
    logger = logger or logging.getLogger(__name__)
    translated = word
    try:
        with open(dictionary, 'r', encoding='utf-8') as f:
            dict_data = json.load(f)
            translated = dict_data.get(word, word)
            return translated
    except Exception as e:
        logger.error('Word translation error: %s', e, exc_info=True)
    return translated


def get_text(row, selector: str) -> str:
    """Gets text from an element using the CSS selector."""
    try:
        els = row.find_elements(By.CSS_SELECTOR, selector)
        return els[0].text.strip() if els else ''
    except Exception:
        return ''
