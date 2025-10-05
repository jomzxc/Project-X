from django.db import models


class ClassificationJob(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    job_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    total_objects = models.IntegerField()
    processed_objects = models.IntegerField(default=0)
    file_path = models.CharField(max_length=500)
    file_name = models.CharField(max_length=255, default='N/A')

    def __str__(self):
        return f"Job {self.job_id} - {self.file_name}"


class TOIResult(models.Model):
    job = models.ForeignKey(ClassificationJob, on_delete=models.CASCADE, related_name='results')
    toi_id = models.CharField(max_length=50)
    tic_id = models.CharField(max_length=50, null=True, blank=True)  # Add this new line
    prediction = models.CharField(max_length=20)
    probability = models.FloatField()
    confidence = models.CharField(max_length=10)
    feature_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.toi_id} ({self.tic_id}) - {self.prediction}"