from django.db import models
from django.contrib.auth.models import User


class NutritionImage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    result = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Analysis by {self.user.username}"