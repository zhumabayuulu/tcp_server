from django.db import models
from django.utils import timezone
import json


class LockBoard(models.Model):
    """Модель платы управления замками"""
    device_id = models.CharField(max_length=8, unique=True, verbose_name="ID устройства")
    device_type = models.CharField(max_length=4, default="0025", verbose_name="Тип устройства")
    ccid = models.CharField(max_length=20, blank=True, verbose_name="CCID SIM карты")
    board_address = models.IntegerField(default=0, verbose_name="Адрес платы")
    total_channels = models.IntegerField(default=25, verbose_name="Количество каналов")
    is_online = models.BooleanField(default=False, verbose_name="Онлайн")
    last_heartbeat = models.DateTimeField(null=True, blank=True, verbose_name="Последний heartbeat")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP адрес")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Плата управления замками"
        verbose_name_plural = "Платы управления замками"

    def __str__(self):
        return f"Board {self.device_id} ({self.total_channels} channels)"


class Lock(models.Model):
    """Модель отдельного замка"""
    LOCK_STATUS_CHOICES = [
        (0, 'Открыт'),
        (1, 'Закрыт'),
    ]

    board = models.ForeignKey(LockBoard, on_delete=models.CASCADE, related_name='locks')
    channel = models.IntegerField(verbose_name="Номер канала")
    name = models.CharField(max_length=100, blank=True, verbose_name="Название")
    status = models.IntegerField(choices=LOCK_STATUS_CHOICES, default=1, verbose_name="Статус")
    last_status_change = models.DateTimeField(auto_now=True, verbose_name="Последнее изменение статуса")

    class Meta:
        unique_together = ['board', 'channel']
        verbose_name = "Замок"
        verbose_name_plural = "Замки"

    def __str__(self):
        return f"Lock {self.board.device_id}-{self.channel} ({self.get_status_display()})"


class LockOperation(models.Model):
    """Журнал операций с замками"""
    OPERATION_TYPES = [
        ('open_single', 'Открытие одного замка'),
        ('open_all', 'Открытие всех замков'),
        ('open_multiple', 'Открытие нескольких замков'),
        ('read_status', 'Чтение статуса'),
        ('read_all_status', 'Чтение всех статусов'),
        ('keep_open', 'Постоянное открытие'),
        ('close_channel', 'Закрытие канала'),
    ]

    board = models.ForeignKey(LockBoard, on_delete=models.CASCADE)
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES)
    channels = models.JSONField(default=list, verbose_name="Каналы")
    order_number = models.CharField(max_length=24, blank=True, verbose_name="Номер заказа")
    success = models.BooleanField(default=False, verbose_name="Успешно")
    error_message = models.TextField(blank=True, verbose_name="Сообщение об ошибке")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Операция с замком"
        verbose_name_plural = "Операции с замками"
        ordering = ['-created_at']