import os
from typing import Any
from time import sleep

from src.core import EncarBot
from src.utils import (
    filter_encar_links,
    read_config,
    get_existing_cars,
    init_db,
    add_cars_to_db,
    setup_logging,
    car_to_telegram
)


def initialize_app() -> Any:
    """Application initialization"""
    try:
        for dir_ in ['logs', 'user_data']:
            os.makedirs(dir_, exist_ok=True)
        log = setup_logging('logs')
        return log

    except Exception as e:
        print(f'[FATAL] Failed to initialize the system: {e}')
        raise RuntimeError('Critical initialization error') from e


def main(logger):
    """Main function"""
    try:
        config = read_config()
        if 'tg_api_token' not in config or 'tg_chat_id' not in config:
            logger.critical('Telegram API token or chat ID not found in the config')
            raise RuntimeError('Missing data in config.json')

    except Exception as e:
        logger.critical('Error loading the configuration or accounts: %s', e, exc_info=True)
        raise

    init_db()

    for encar_link in filter_encar_links('encar_links.txt'):
        bot = EncarBot(
            user_id='bot1',
            config=config,
            logger=logger
        )
        logger.info('The link is being processed: %s', encar_link)
        bot.get_url(encar_link)
        parsed_cars = bot.search_cars()

        if not parsed_cars:
            logger.warning('Ads not found!')
            bot.quit_driver()
            sleep(3)
            continue

        existing_cars = get_existing_cars(encar_link, 'encar_searches')
        new_car_ids = set(parsed_cars.keys()) - existing_cars

        if new_car_ids:
            cars_to_add = {car_id: parsed_cars[car_id] for car_id in new_car_ids}
            for car_id, car_data in cars_to_add.items():
                car_to_telegram(
                    (car_id, car_data),
                    config.get('tg_api_token'),
                    config.get('tg_chat_id'),
                    logger
                )
                sleep(1)

            add_cars_to_db(cars_to_add, encar_link, 'encar_searches')

        else:
            logger.info('There are no new ads')

        bot.quit_driver()
        sleep(3)


if __name__ == '__main__':
    logger = initialize_app()
    while True:
        try:
            main(logger)
            sleep(5)
        except Exception as e:
            logger.error('Program execution error: %s', e, exc_info=True)
            logger.error('An attempt to continue executing the program...')
            sleep(5)
            continue
