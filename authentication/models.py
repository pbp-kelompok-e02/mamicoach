from django.conf import settings
from django.db import models


class FcmDeviceToken(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	token = models.CharField(max_length=255, unique=True)
	platform = models.CharField(max_length=32, default="android")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		indexes = [
			models.Index(fields=["user", "platform"]),
		]

	def __str__(self) -> str:
		return f"{self.user_id}:{self.platform}"
