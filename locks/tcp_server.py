import asyncio
import logging
from django.utils import timezone
from django.db import transaction
from .models import LockBoard, Lock, LockOperation
from .protocol import VoungProtocol

logger = logging.getLogger(__name__)


class LockControlServer:
    """TCP сервер для управления замками"""

    def __init__(self, host='0.0.0.0', port=8585):
        self.host = host
        self.port = port
        self.clients = {}  # device_id -> (writer, board_instance)

    async def handle_client(self, reader, writer):
        """Обработка подключения клиента"""
        client_addr = writer.get_extra_info('peername')
        logger.info(f"Новое подключение от {client_addr}")

        try:
            while True:
                # Читаем данные
                data = await reader.read(1024)
                if not data:
                    break

                # Парсим фрейм
                frame = VoungProtocol.parse_frame(data)
                if not frame:
                    logger.warning(f"Неверный фрейм от {client_addr}: {data.hex()}")
                    continue

                # Обрабатываем команду
                response = await self.process_command(frame, client_addr)
                if response:
                    writer.write(response)
                    await writer.drain()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Ошибка при обработке клиента {client_addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            # Убираем клиента из списка активных
            for device_id, (w, board) in list(self.clients.items()):
                if w == writer:
                    del self.clients[device_id]
                    await self.set_board_offline(board)
                    break

    async def process_command(self, frame: dict, client_addr) -> bytes:
        """Обработка команды от устройства"""
        cmd = frame['cmd']
        board_addr = frame['board_addr']
        data = frame['data']

        if cmd == VoungProtocol.CMD_HEARTBEAT:
            return await self.handle_heartbeat(board_addr, data)
        elif cmd == VoungProtocol.CMD_REGISTER:
            return await self.handle_register(board_addr, data, client_addr)
        elif cmd == VoungProtocol.CMD_STATUS_CHANGE:
            await self.handle_status_change(board_addr, data)
            return None  # Сервер не отвечает на это сообщение
        else:
            logger.warning(f"Неизвестная команда: 0x{cmd:02X}")
            return None

    async def handle_heartbeat(self, board_addr: int, data: bytes) -> bytes:
        """Обработка heartbeat"""
        if len(data) >= 8:
            device_id = data[:8].decode('ascii', errors='ignore')

            # Обновляем время последнего heartbeat
            try:
                board = await LockBoard.objects.filter(device_id=device_id).afirst()
                if board:
                    board.last_heartbeat = timezone.now()
                    board.is_online = True
                    await board.asave()
            except Exception as e:
                logger.error(f"Ошибка при обновлении heartbeat: {e}")

        return VoungProtocol.create_response(board_addr, VoungProtocol.CMD_HEARTBEAT, 0x00)

    async def handle_register(self, board_addr: int, data: bytes, client_addr) -> bytes:
        """Обработка регистрации устройства"""
        if len(data) < 10:
            return VoungProtocol.create_response(board_addr, VoungProtocol.CMD_REGISTER, 0xFF)

        device_id = data[:8].decode('ascii', errors='ignore')
        device_type = data[8:10].hex()
        ccid = data[10:30].decode('ascii', errors='ignore') if len(data) >= 30 else ''

        try:
            # Создаем или обновляем плату
            board, created = await LockBoard.objects.aupdate_or_create(
                device_id=device_id,
                defaults={
                    'device_type': device_type,
                    'ccid': ccid,
                    'board_address': board_addr,
                    'is_online': True,
                    'last_heartbeat': timezone.now(),
                    'ip_address': client_addr[0] if client_addr else None
                }
            )

            # Создаем замки для новой платы
            if created:
                await self.create_locks_for_board(board)

            # Сохраняем соединение
            # В Django async views нужно использовать sync_to_async для writer
            # self.clients[device_id] = (writer, board) # Это нужно адаптировать

            logger.info(f"Устройство {device_id} зарегистрировано")
            return VoungProtocol.create_response(board_addr, VoungProtocol.CMD_REGISTER, 0x00)

        except Exception as e:
            logger.error(f"Ошибка регистрации устройства {device_id}: {e}")
            return VoungProtocol.create_response(board_addr, VoungProtocol.CMD_REGISTER, 0xFF)

    async def handle_status_change(self, board_addr: int, data: bytes):
        """Обработка изменения статуса замка"""
        if len(data) < 2:
            return

        channel = data[0]
        status = data[1]

        try:
            board = await LockBoard.objects.filter(board_address=board_addr).afirst()
            if board:
                lock = await Lock.objects.filter(board=board, channel=channel).afirst()
                if lock:
                    lock.status = status
                    lock.last_status_change = timezone.now()
                    await lock.asave()
                    logger.info(f"Статус замка {board.device_id}-{channel} изменен на {status}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса замка: {e}")

    async def create_locks_for_board(self, board: LockBoard):
        """Создание замков для новой платы"""
        locks_to_create = []
        for channel in range(1, board.total_channels + 1):
            locks_to_create.append(Lock(
                board=board,
                channel=channel,
                name=f"Lock {channel}",
                status=1  # Закрыт по умолчанию
            ))

        await Lock.objects.abulk_create(locks_to_create)

    async def set_board_offline(self, board: LockBoard):
        """Установка платы в оффлайн режим"""
        board.is_online = False
        await board.asave()
        logger.info(f"Плата {board.device_id} отключена")

    async def send_command_to_board(self, device_id: str, cmd: int, data: bytes = b'') -> bool:
        """Отправка команды на плату"""
        if device_id not in self.clients:
            return False

        writer, board = self.clients[device_id]
        try:
            frame = VoungProtocol.create_frame(board.board_address, cmd, data)
            writer.write(frame)
            await writer.drain()
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке команды на {device_id}: {e}")
            return False

    async def start_server(self):
        """Запуск TCP сервера"""
        server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )

        logger.info(f"TCP сервер запущен на {self.host}:{self.port}")

        async with server:
            await server.serve_forever()
lock_server = LockControlServer()
