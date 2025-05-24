from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import LockBoard, Lock, LockOperation
from .serializers import LockBoardSerializer, LockSerializer, LockOperationSerializer
from .tcp_server import lock_server
from .protocol import VoungProtocol
import struct
import asyncio
import logging

# Логгерди конфигурациялоо
logging.basicConfig(level=logging.INFO)

# Логгерди түзүү
logger = logging.getLogger(__name__)

# Lock Board Views
class LockBoardListView(generics.ListAPIView):
    """Список плат управления замками"""
    queryset = LockBoard.objects.all()
    serializer_class = LockBoardSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        is_online = self.request.query_params.get('is_online')
        device_type = self.request.query_params.get('device_type')
        search = self.request.query_params.get('search')

        if is_online is not None:
            queryset = queryset.filter(is_online=is_online.lower() == 'true')
        if device_type:
            queryset = queryset.filter(device_type=device_type)
        if search:
            queryset = queryset.filter(
                Q(device_id__icontains=search) |
                Q(ccid__icontains=search)
            )
        return queryset


class LockBoardDetailView(generics.RetrieveAPIView):
    """Детали платы управления замками"""
    queryset = LockBoard.objects.all()
    serializer_class = LockBoardSerializer


class LockBoardCreateView(generics.CreateAPIView):
    """Создание платы управления замками"""
    queryset = LockBoard.objects.all()
    serializer_class = LockBoardSerializer


class LockBoardUpdateView(generics.UpdateAPIView):
    """Обновление платы управления замками"""
    queryset = LockBoard.objects.all()
    serializer_class = LockBoardSerializer


class LockBoardDeleteView(generics.DestroyAPIView):
    """Удаление платы управления замками"""
    queryset = LockBoard.objects.all()
    serializer_class = LockBoardSerializer


# Lock Operation Views
class OpenSingleLockView(APIView):
    """Открытие одного замка"""

    def post(self, request, board_id):
        board = get_object_or_404(LockBoard, pk=board_id)
        channel = request.data.get('channel')
        order_number = request.data.get('order_number', '')

        if not channel or not isinstance(channel, int):
            return Response({'error': 'Укажите номер канала'}, status=status.HTTP_400_BAD_REQUEST)

        if channel < 1 or channel > board.total_channels:
            return Response({'error': 'Неверный номер канала'}, status=status.HTTP_400_BAD_REQUEST)

        # Формируем данные команды
        data = struct.pack('B', channel)
        if order_number:
            data += order_number.encode('ascii')[:24]

        # Отправляем команду (синхронно через asyncio)
        try:
            loop = asyncio.get_event_loop()
            success = loop.run_until_complete(
                lock_server.send_command_to_board(
                    board.device_id,
                    VoungProtocol.CMD_OPEN_SINGLE,
                    data
                )
            )
        except Exception as e:
            success = False

        # Записываем операцию
        LockOperation.objects.create(
            board=board,
            operation_type='open_single',
            channels=[channel],
            order_number=order_number,
            success=success
        )

        if success:
            return Response({
                'message': f'Команда открытия замка {channel} отправлена',
                'board_id': board.id,
                'channel': channel,
                'order_number': order_number
            })
        else:
            return Response({'error': 'Плата недоступна'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


from asgiref.sync import async_to_sync

class OpenAllLocksView(APIView):
    """Открытие всех замков"""

    def post(self, request, board_id):
        board = get_object_or_404(LockBoard, pk=board_id)

        try:
            success = async_to_sync(lock_server.send_command_to_board)(
                board.device_id,
                VoungProtocol.CMD_OPEN_ALL
            )
        except Exception as e:
            logger.error(f"Ошибка отправки команды открытия всех замков: {e}")
            success = False

        LockOperation.objects.create(
            board=board,
            operation_type='open_all',
            channels=list(range(1, board.total_channels + 1)),
            success=success
        )

        if success:
            return Response({
                'message': 'Команда открытия всех замков отправлена',
                'board_id': board.id,
                'total_channels': board.total_channels
            })
        else:
            return Response({'error': 'Плата недоступна'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class OpenMultipleLocksView(APIView):
    """Открытие нескольких замков"""

    def post(self, request, board_id):
        board = get_object_or_404(LockBoard, pk=board_id)
        channels = request.data.get('channels', [])

        if not channels or not isinstance(channels, list):
            return Response({'error': 'Укажите список каналов'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем корректность каналов
        for channel in channels:
            if not isinstance(channel, int) or channel < 1 or channel > board.total_channels:
                return Response({'error': f'Неверный номер канала: {channel}'}, status=status.HTTP_400_BAD_REQUEST)

        # Формируем данные команды
        data = struct.pack('B', len(channels))
        for channel in channels:
            data += struct.pack('B', channel)

        try:
            loop = asyncio.get_event_loop()
            success = loop.run_until_complete(
                lock_server.send_command_to_board(
                    board.device_id,
                    VoungProtocol.CMD_OPEN_MULTIPLE,
                    data
                )
            )
        except Exception as e:
            success = False

        LockOperation.objects.create(
            board=board,
            operation_type='open_multiple',
            channels=channels,
            success=success
        )

        if success:
            return Response({
                'message': f'Команда открытия замков {channels} отправлена',
                'board_id': board.id,
                'channels': channels
            })
        else:
            return Response({'error': 'Плата недоступна'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class ReadLockStatusView(APIView):
    """Чтение статуса замка"""

    def get(self, request, board_id):
        board = get_object_or_404(LockBoard, pk=board_id)
        channel = request.query_params.get('channel')

        if not channel:
            return Response({'error': 'Укажите номер канала'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            channel = int(channel)
        except ValueError:
            return Response({'error': 'Неверный номер канала'}, status=status.HTTP_400_BAD_REQUEST)

        if channel < 1 or channel > board.total_channels:
            return Response({'error': 'Неверный номер канала'}, status=status.HTTP_400_BAD_REQUEST)

        data = struct.pack('B', channel)

        try:
            loop = asyncio.get_event_loop()
            success = loop.run_until_complete(
                lock_server.send_command_to_board(
                    board.device_id,
                    VoungProtocol.CMD_READ_STATUS,
                    data
                )
            )
        except Exception as e:
            success = False

        # Получаем текущий статус из базы данных
        try:
            lock = Lock.objects.get(board=board, channel=channel)
            current_status = lock.get_status_display()
            last_change = lock.last_status_change
        except Lock.DoesNotExist:
            current_status = 'Неизвестно'
            last_change = None

        if success:
            return Response({
                'message': f'Запрос статуса замка {channel} отправлен',
                'board_id': board.id,
                'channel': channel,
                'current_status': current_status,
                'last_status_change': last_change
            })
        else:
            return Response({'error': 'Плата недоступна'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class ReadAllStatusView(APIView):
    """Чтение статуса всех замков"""

    def get(self, request, board_id):
        board = get_object_or_404(LockBoard, pk=board_id)

        try:
            loop = asyncio.get_event_loop()
            success = loop.run_until_complete(
                lock_server.send_command_to_board(
                    board.device_id,
                    VoungProtocol.CMD_READ_ALL_STATUS
                )
            )
        except Exception as e:
            success = False

        # Получаем текущие статусы из базы данных
        locks = Lock.objects.filter(board=board).order_by('channel')
        locks_data = []
        for lock in locks:
            locks_data.append({
                'channel': lock.channel,
                'name': lock.name,
                'status': lock.get_status_display(),
                'last_change': lock.last_status_change
            })

        if success:
            return Response({
                'message': 'Запрос статуса всех замков отправлен',
                'board_id': board.id,
                'locks': locks_data
            })
        else:
            return Response({'error': 'Плата недоступна'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class KeepChannelOpenView(APIView):
    """Постоянное открытие канала"""

    def post(self, request, board_id):
        board = get_object_or_404(LockBoard, pk=board_id)
        channel = request.data.get('channel')

        if not channel or not isinstance(channel, int):
            return Response({'error': 'Укажите номер канала'}, status=status.HTTP_400_BAD_REQUEST)

        if channel < 1 or channel > board.total_channels:
            return Response({'error': 'Неверный номер канала'}, status=status.HTTP_400_BAD_REQUEST)

        data = struct.pack('B', channel)

        try:
            loop = asyncio.get_event_loop()
            success = loop.run_until_complete(
                lock_server.send_command_to_board(
                    board.device_id,
                    VoungProtocol.CMD_KEEP_OPEN,
                    data
                )
            )
        except Exception as e:
            success = False

        LockOperation.objects.create(
            board=board,
            operation_type='keep_open',
            channels=[channel],
            success=success
        )

        if success:
            return Response({
                'message': f'Канал {channel} переведен в режим постоянного открытия',
                'board_id': board.id,
                'channel': channel
            })
        else:
            return Response({'error': 'Плата недоступна'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class CloseChannelView(APIView):
    """Закрытие канала"""

    def post(self, request, board_id):
        board = get_object_or_404(LockBoard, pk=board_id)
        channel = request.data.get('channel')

        if not channel or not isinstance(channel, int):
            return Response({'error': 'Укажите номер канала'}, status=status.HTTP_400_BAD_REQUEST)

        if channel < 1 or channel > board.total_channels:
            return Response({'error': 'Неверный номер канала'}, status=status.HTTP_400_BAD_REQUEST)

        data = struct.pack('B', channel)

        try:
            loop = asyncio.get_event_loop()
            success = loop.run_until_complete(
                lock_server.send_command_to_board(
                    board.device_id,
                    VoungProtocol.CMD_CLOSE_CHANNEL,
                    data
                )
            )
        except Exception as e:
            success = False

        LockOperation.objects.create(
            board=board,
            operation_type='close_channel',
            channels=[channel],
            success=success
        )

        if success:
            return Response({
                'message': f'Канал {channel} закрыт',
                'board_id': board.id,
                'channel': channel
            })
        else:
            return Response({'error': 'Плата недоступна'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# Lock Views
class LockListView(generics.ListAPIView):
    """Список замков"""
    queryset = Lock.objects.select_related('board')
    serializer_class = LockSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        board_id = self.request.query_params.get('board_id')
        status_filter = self.request.query_params.get('status')
        channel = self.request.query_params.get('channel')

        if board_id:
            queryset = queryset.filter(board_id=board_id)
        if status_filter is not None:
            queryset = queryset.filter(status=status_filter)
        if channel:
            queryset = queryset.filter(channel=channel)
        return queryset


class LockDetailView(generics.RetrieveAPIView):
    """Детали замка"""
    queryset = Lock.objects.select_related('board')
    serializer_class = LockSerializer


class LockUpdateView(generics.UpdateAPIView):
    """Обновление замка (только название)"""
    queryset = Lock.objects.all()
    serializer_class = LockSerializer

    def get_serializer_class(self):
        # Ограничиваем редактирование только названием
        class LockUpdateSerializer(LockSerializer):
            class Meta(LockSerializer.Meta):
                fields = ['name']

        return LockUpdateSerializer


# Lock Operation Views
class LockOperationListView(generics.ListAPIView):
    """Список операций с замками"""
    queryset = LockOperation.objects.select_related('board')
    serializer_class = LockOperationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        board_id = self.request.query_params.get('board_id')
        operation_type = self.request.query_params.get('operation_type')
        success = self.request.query_params.get('success')

        if board_id:
            queryset = queryset.filter(board_id=board_id)
        if operation_type:
            queryset = queryset.filter(operation_type=operation_type)
        if success is not None:
            queryset = queryset.filter(success=success.lower() == 'true')

        return queryset.order_by('-created_at')[:100]  # Последние 100 операций


class LockOperationDetailView(generics.RetrieveAPIView):
    """Детали операции с замком"""
    queryset = LockOperation.objects.select_related('board')
    serializer_class = LockOperationSerializer


# Statistics Views
class BoardStatisticsView(APIView):
    """Статистика по платам"""

    def get(self, request):
        total_boards = LockBoard.objects.count()
        online_boards = LockBoard.objects.filter(is_online=True).count()
        offline_boards = total_boards - online_boards

        total_locks = Lock.objects.count()
        open_locks = Lock.objects.filter(status=0).count()
        closed_locks = Lock.objects.filter(status=1).count()

        recent_operations = LockOperation.objects.count()
        success_operations = LockOperation.objects.filter(success=True).count()
        failed_operations = recent_operations - success_operations

        return Response({
            'boards': {
                'total': total_boards,
                'online': online_boards,
                'offline': offline_boards
            },
            'locks': {
                'total': total_locks,
                'open': open_locks,
                'closed': closed_locks
            },
            'operations': {
                'total': recent_operations,
                'success': success_operations,
                'failed': failed_operations
            }
        })

class DebugClientConnectionsView(APIView):
    def get(self, request):
        online_boards = LockBoard.objects.filter(is_online=True).values_list('device_id', flat=True)
        return Response({
            "connected_boards": list(online_boards)
        })
