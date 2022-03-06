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
