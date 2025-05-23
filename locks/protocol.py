import struct
from typing import List, Tuple, Optional


class VoungProtocol:
    """Класс для работы с протоколом Voung"""

    START_CHARS = b'WKLY'

    # Команды
    CMD_HEARTBEAT = 0x80
    CMD_REGISTER = 0x81
    CMD_OPEN_SINGLE = 0x82
    CMD_READ_STATUS = 0x83
    CMD_READ_ALL_STATUS = 0x84
    CMD_STATUS_CHANGE = 0x85
    CMD_OPEN_ALL = 0x86
    CMD_OPEN_MULTIPLE = 0x87
    CMD_KEEP_OPEN = 0x88
    CMD_CLOSE_CHANNEL = 0x89
    CMD_SIGNAL_QUALITY = 0xD0

    @staticmethod
    def compute_xor(data: bytes) -> int:
        """Вычисление XOR контрольной суммы"""
        result = 0
        for byte in data:
            result ^= byte
        return result

    @staticmethod
    def create_frame(board_addr: int, cmd: int, data: bytes = b'') -> bytes:
        """Создание фрейма команды"""
        frame_length = 8 + len(data)  # 4 (start) + 1 (len) + 1 (addr) + 1 (cmd) + data + 1 (xor)

        frame = VoungProtocol.START_CHARS
        frame += struct.pack('B', frame_length)
        frame += struct.pack('B', board_addr)
        frame += struct.pack('B', cmd)
        frame += data

        xor_byte = VoungProtocol.compute_xor(frame)
        frame += struct.pack('B', xor_byte)

        return frame

    @staticmethod
    def parse_frame(data: bytes) -> Optional[dict]:
        """Парсинг фрейма"""
        if len(data) < 8:
            return None

        if data[:4] != VoungProtocol.START_CHARS:
            return None

        frame_length = data[4]
        if len(data) < frame_length:
            return None

        board_addr = data[5]
        cmd = data[6]
        data_field = data[7:frame_length - 1]
        xor_received = data[frame_length - 1]

        # Проверка контрольной суммы
        xor_calculated = VoungProtocol.compute_xor(data[:frame_length - 1])
        if xor_received != xor_calculated:
            return None

        return {
            'board_addr': board_addr,
            'cmd': cmd,
            'data': data_field,
            'valid': True
        }

    @staticmethod
    def create_response(board_addr: int, cmd: int, status: int = 0x00, data: bytes = b'') -> bytes:
        """Создание ответа"""
        response_data = struct.pack('B', status) + data
        return VoungProtocol.create_frame(board_addr, cmd, response_data)