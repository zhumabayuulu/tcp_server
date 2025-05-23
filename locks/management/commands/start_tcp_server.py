from django.core.management.base import BaseCommand
from ...tcp_server import lock_server
import asyncio


class Command(BaseCommand):
    help = 'Запуск TCP сервера для управления замками'

    def add_arguments(self, parser):
        parser.add_argument('--host', default='0.0.0.0', help='IP адрес для привязки')
        parser.add_argument('--port', type=int, default=8585, help='Порт для прослушивания')

    def handle(self, *args, **options):
        lock_server.host = options['host']
        lock_server.port = options['port']

        self.stdout.write(f"Запуск TCP сервера на {options['host']}:{options['port']}")

        try:
            asyncio.run(lock_server.start_server())
        except KeyboardInterrupt:
            self.stdout.write("Сервер остановлен")
