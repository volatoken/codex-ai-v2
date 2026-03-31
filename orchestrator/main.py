"""Entry point — start the Telegram bot orchestrator."""

import logging


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    from .telegram_bot import TelegramBot

    bot = TelegramBot()
    bot.run()


if __name__ == "__main__":
    main()
