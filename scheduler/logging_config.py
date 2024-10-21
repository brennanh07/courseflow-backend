import logging
import os

def setup_logging():
    log_directory = 'logs'
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_directory, 'scheduler.log')),
            logging.StreamHandler()
        ]
    )

    # Create loggers for different modules
    loggers = {
        'fetch_sections': logging.getLogger('fetch_sections'),
        'schedule_generator': logging.getLogger('schedule_generator'),
        'schedule_scoring': logging.getLogger('schedule_scoring'),
        'main': logging.getLogger('main'),
        'views': logging.getLogger('views'),
        'schedule_formatter': logging.getLogger('schedule_formatter'),
    }

    for logger in loggers.values():
        logger.setLevel(logging.DEBUG)

    return loggers

loggers = setup_logging()