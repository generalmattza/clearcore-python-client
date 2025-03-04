import logging
import logging.config
import yaml


def setup_logging():
    with open("config/logger.yaml", "r") as f:
        config = yaml.safe_load(f)

    logging.config.dictConfig(config)


class StringFilter(logging.Filter):
    def __init__(self, match: str):
        super().__init__()
        self.match = match

    def filter(self, record: logging.LogRecord) -> bool:
        # Return True if the match string is in the log message
        return self.match in record.getMessage()
