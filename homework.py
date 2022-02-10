import logging
import os
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=None)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляем сообщение в Telegramm."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Бот отправил сообщение {message}')
    except Exception as error:
        logger.exception(
            'Ошибка при отправке сообщения ботом!',
            exc_info=error
        )


def get_api_answer(current_timestamp):
    """Делаем запрос к API и возвращаем JSON."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logger.error(f'Эндпоинт {ENDPOINT} недоступен.')
            raise Exception
        return response.json()
    except Exception as error:
        msg = (f'Эндпоинт {ENDPOINT} недоступен. '
               f'Код ответа API: {response.status_code}')
        logger.exception(msg, exc_info=error)
        raise Exception


def check_response(response):
    """Возвращаем список работ."""
    try:
        response['homeworks']
    except Exception as error:
        logger.exception('Некорректный ключ словаря', exc_info=error)
    if not isinstance(response['homeworks'], list):
        logger.error('Некорректные данные от API')
        raise Exception
    return response['homeworks']


def parse_status(homework):
    """Получаем статус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name == 'None' or homework_status == 'None':
        logger.error('Ошибка ключей словаря')
    if homework_status not in VERDICTS.keys():
        logger.error('Недокументированный статус домашней работы')
    verdict = VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем наличие всех токенов."""
    list_var = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(list_var)


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Нет необходимых токенов!')
        raise Exception
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            list_homeworks = check_response(response)
            if len(list_homeworks) != 0:
                for homework in list_homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
