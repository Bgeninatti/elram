import logging
import logging.config


class ContextLogger(logging.Logger):
    def _log(self, level, msg, args, exc_info=None, extra=None, **kwargs):
        msg = f"{msg} - "
        if extra:
            msg = f"{msg}{'; '.join((f'{k}={v}' for k, v in extra.items()))}"
        super()._log(level, msg, args, exc_info, extra, **kwargs)


logging.setLoggerClass(ContextLogger)


def setup_logger(lvl="info"):

    LOGGING_CONFIG = {
        "version": 1,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(module)s:%(funcName)s %(message)s"
            },
        },
        "handlers": {
            "default": {
                "level": lvl.upper(),
                "formatter": "standard",
                "class": "logging.StreamHandler",
            },
        },
        "loggers": {
            "main": {
                "handlers": ["default"],
                "level": lvl.upper(),
            },
        },
    }

    logging.config.dictConfig(LOGGING_CONFIG)
