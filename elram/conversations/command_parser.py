import re

from elram.repository.services import CommandException


class CommandParser:

    _commands_mapping = {
        'add_attendee': (
            r'^(?P<nickname>\w+) vino$',
            r'^(?P<nickname>\w+) viene$',
            r'^(?P<nickname>\w+) va$',
            r'^(?P<nickname>\w+) fue$',
            r'^vino (?P<nickname>\w+)$',
            r'^viene (?P<nickname>\w+)$',
            r'^va (?P<nickname>\w+)$',
            r'^fue (?P<nickname>\w+)$',
        ),
        'remove_attendee': (
            r'^(?P<nickname>\w+) no vino$',
            r'^(?P<nickname>\w+) falto$',
            r'^(?P<nickname>\w+) no viene$',
            r'^(?P<nickname>\w+) no va$',
            r'^(?P<nickname>\w+) no fue$',
            r'^no vino (?P<nickname>\w+)$',
            r'^no viene (?P<nickname>\w+)$',
            r'^no va (?P<nickname>\w+)$',
            r'^no fue (?P<nickname>\w+)$',
        ),
        'replace_host': (
            r'^organiza (?P<nickname>\w+)$',
            r'^organizó (?P<nickname>\w+)$',
            r'^la hizo (?P<nickname>\w+)$',
            r'^la hace (?P<nickname>\w+)$',
            r'^es de (?P<nickname>\w+)$',
        ),
        'add_expense': (
            r'^(?P<nickname>\w+) gastó (?P<amount>([1-9][0-9]*\.?[0-9]*)|(\.[0-9]+))$',
            r'^(?P<nickname>\w+) gasto (?P<amount>([1-9][0-9]*\.?[0-9]*)|(\.[0-9]+))$',
            r'^(?P<nickname>\w+) gastó (?P<amount>([1-9][0-9]*\.?[0-9]*)|(\.[0-9]+)) en (?P<description>.+)$',
            r'^(?P<nickname>\w+) gasto (?P<amount>([1-9][0-9]*\.?[0-9]*)|(\.[0-9]+)) en (?P<description>.+)$',
        ),
        'add_payment': (
            r'^(?P<nickname>\w+) pagó (?P<amount>([1-9][0-9]*\.?[0-9]*)|(\.[0-9]+))$',
            r'^(?P<nickname>\w+) pago (?P<amount>([1-9][0-9]*\.?[0-9]*)|(\.[0-9]+))$',
            r'^(?P<nickname>\w+) pagó (?P<amount>([1-9][0-9]*\.?[0-9]*)|(\.[0-9]+))$',
            r'^(?P<nickname>\w+) pago (?P<amount>([1-9][0-9]*\.?[0-9]*)|(\.[0-9]+))$',
        ),
        'add_refund': (
            r'^(?P<nickname>\w+) recibió (?P<amount>([1-9][0-9]*\.?[0-9]*)|(\.[0-9]+))$',
            r'^(?P<nickname>\w+) recibio (?P<amount>([1-9][0-9]*\.?[0-9]*)|(\.[0-9]+))$',
            r'^(?P<nickname>\w+) recuperó (?P<amount>([1-9][0-9]*\.?[0-9]*)|(\.[0-9]+))$',
            r'^(?P<nickname>\w+) recupero (?P<amount>([1-9][0-9]*\.?[0-9]*)|(\.[0-9]+))$',
        ),
        'next_event': (
            r'proxima peña$',
            r'próxima peña$',
            r'proxima pena$',
            r'próxima pena$',
        ),
        'previous_event': (
            r'peña anterior$',
            r'pena anterior$',
        ),
        'find_event': (
            r'^mostrame la peña (?P<event_code>\d+)$',
            r'^quiero ver la peña (?P<event_code>\d+)$',
            r'^ver peña (?P<event_code>\d+)$',
            r'^mostrame la pena (?P<event_code>\d+)$',
            r'^quiero ver la pena (?P<event_code>\d+)$',
            r'^ver pena (?P<event_code>\d+)$',
        ),
        'active_event': (
            r'proxima peña$',
            r'próxima peña$',
            r'proxima pena$',
            r'próxima pena$',
        )
    }

    def __call__(self, message):
        message = self._clean_message(message)
        for command in self._commands_mapping.keys():
            result = self._is_command(command, message)
            if result is not None:
                return result
        raise CommandException('mmmm no entendí')

    @staticmethod
    def _clean_message(message):
        return message.lower().strip()

    def _is_command(self, command, message):
        for patter in self._commands_mapping[command]:
            regex = re.compile(patter)
            match = regex.search(message)
            if not match:
                continue
            kwargs = {key: match.group(key) for key in regex.groupindex.keys()}
            return command, kwargs
