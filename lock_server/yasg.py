from drf_yasg import openapi
from drf_yasg.views import get_schema_view

# Swagger schema view
schema_view = get_schema_view(
   openapi.Info(
      title="Your API",
      default_version='v1',
      description="API Documentation",
   ),
   public=True,
   # permission_classes=(permissions.AllowAny,),
)