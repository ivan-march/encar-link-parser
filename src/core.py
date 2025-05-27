import logging
from abc import ABC
from typing import Dict, Any
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from src.utils import get_text, init_driver, translate_word


class WebBot(ABC):
    def __init__(self, user_id: str, config: dict, logger=None):
        self.user = user_id
        self.config = config
        self.driver = init_driver(
            self.user,
            self.config,
            headless=self.config.get('headless', False)
        )
        self.driver.implicitly_wait(10)
        self.logger = logger or logging.getLogger(__name__)

    def quit_driver(self):
        """Closing the webdriver."""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info('The web driver is closed')
        except Exception as e:
            self.logger.error('Error when trying to close the driver: %s', e, exc_info=True)

    def get_url(self, url: str):
        """Opening an URL"""
        self.driver.get(url)

    def make_screenshot(self, screenshot_path: str):
        """Saves a screenshot of the page."""
        try:
            self.driver.save_screenshot(screenshot_path)
        except Exception as e:
            self.logger.error('Error when creating a screenshot: %s', e, exc_info=True )


class EncarBot(WebBot):
    def search_cars(self) -> Dict[str, Any]:
        """Search for cars on the page."""
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'table.car_list'))
            )
        except TimeoutException:
            self.logger.warning('The car_list table failed to load in 30 seconds')
            return
        except Exception as e:
            self.logger.error('Error: %s', e, exc_info=True)
            return

        tables = self.driver.find_elements(By.CSS_SELECTOR, 'table.car_list')
        cars_data = {}

        for table in tables:
            try:
                WebDriverWait(table, 30).until(
                    EC.presence_of_all_elements_located((By.TAG_NAME, 'tr'))
                )
            except TimeoutException:
                self.logger.warning('The car_list table failed to load in 30 seconds')
                return
            except Exception as e:
                self.logger.error('Error: %s', e, exc_info=True)
                return

            rows = table.find_elements(By.CSS_SELECTOR, 'tr')
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, 'td')

                    if len(cells) == 0:
                        continue
                    link_elements = row.find_elements(By.CSS_SELECTOR, 'a.newLink._link')

                    if len(link_elements) == 0:
                        continue
                    car_link = link_elements[0].get_attribute('href')

                    query_params = parse_qs(urlparse(car_link).query)
                    car_id = query_params.get('carid', [None])[0]
                    cars_data[car_id] = {}

                    title = get_text(row, 'span.cls')
                    cars_data[car_id]['title'] = translate_word(title)

                    cars_data[car_id]['details'] = get_text(row, 'span.dtl')

                    year =  get_text(row, 'span.yer')
                    cars_data[car_id]['year'] = year[:-1] if year else ''

                    cars_data[car_id]['km'] = get_text(row, 'span.km')

                    cars_data[car_id]['price'] = get_text(row, 'td.prc_hs strong')

                except Exception as e:
                    self.logger.error('Error: %s', e, exc_info=True)
                    continue

        return cars_data
