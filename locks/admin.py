from django.contrib import admin
from .models import LockBoard, Lock, LockOperation

@admin.register(LockBoard)
class LockBoardAdmin(admin.ModelAdmin):
    list_display = ['device_id', 'device_type', 'total_channels', 'is_online', 'last_heartbeat', 'ip_address']
    list_filter = ['is_online', 'device_type', 'created_at']
    search_fields = ['device_id', 'ccid']
    readonly_fields = ['created_at', 'updated_at', 'last_heartbeat']

@admin.register(Lock)
class LockAdmin(admin.ModelAdmin):
    list_display = ['board', 'channel', 'name', 'status', 'last_status_change']
    list_filter = ['status', 'board']
    search_fields = ['name', 'board__device_id']

@admin.register(LockOperation)
class LockOperationAdmin(admin.ModelAdmin):
    list_display = ['board', 'operation_type', 'channels', 'success', 'created_at']
    list_filter = ['operation_type', 'success', 'created_at']
    readonly_fields = ['created_at']