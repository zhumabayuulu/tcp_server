from django.urls import path, include
from . import views

urlpatterns = [
    # Board URLs
    path('api/boards/', views.LockBoardListView.as_view(), name='board-list'),
    path('api/boards/create/', views.LockBoardCreateView.as_view(), name='board-create'),
    path('api/boards/<int:pk>/', views.LockBoardDetailView.as_view(), name='board-detail'),
    path('api/boards/<int:pk>/update/', views.LockBoardUpdateView.as_view(), name='board-update'),
    path('api/boards/<int:pk>/delete/', views.LockBoardDeleteView.as_view(), name='board-delete'),

    # Lock Operation URLs
    path('api/boards/<int:board_id>/open-lock/', views.OpenSingleLockView.as_view(), name='open-single-lock'),
    path('api/boards/<int:board_id>/open-all/', views.OpenAllLocksView.as_view(), name='open-all-locks'),
    path('api/boards/<int:board_id>/open-multiple/', views.OpenMultipleLocksView.as_view(), name='open-multiple-locks'),
    path('api/boards/<int:board_id>/read-status/', views.ReadLockStatusView.as_view(), name='read-lock-status'),
    path('api/boards/<int:board_id>/read-all-status/', views.ReadAllStatusView.as_view(), name='read-all-status'),
    path('api/boards/<int:board_id>/keep-open/', views.KeepChannelOpenView.as_view(), name='keep-channel-open'),
    path('api/boards/<int:board_id>/close-channel/', views.CloseChannelView.as_view(), name='close-channel'),

    # Lock URLs
    path('api/locks/', views.LockListView.as_view(), name='lock-list'),
    path('api/locks/<int:pk>/', views.LockDetailView.as_view(), name='lock-detail'),
    path('api/locks/<int:pk>/update/', views.LockUpdateView.as_view(), name='lock-update'),

    # Operation URLs
    path('api/operations/', views.LockOperationListView.as_view(), name='operation-list'),
    path('api/operations/<int:pk>/', views.LockOperationDetailView.as_view(), name='operation-detail'),

    # Statistics URLs
    path('api/statistics/', views.BoardStatisticsView.as_view(), name='board-statistics'),
]
