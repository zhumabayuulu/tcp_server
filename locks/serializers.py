from rest_framework import serializers
from .models import LockBoard, Lock, LockOperation


class LockSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Lock
        fields = '__all__'
        ref_name = "test"


class LockBoardSerializer(serializers.ModelSerializer):
    locks = LockSerializer(many=True, read_only=True)

    class Meta:
        model = LockBoard
        fields = '__all__'
        ref_name = "test1"


class LockOperationSerializer(serializers.ModelSerializer):
    operation_type_display = serializers.CharField(source='get_operation_type_display', read_only=True)
    board_name = serializers.CharField(source='board.device_id', read_only=True)

    class Meta:
        model = LockOperation
        fields = '__all__'
