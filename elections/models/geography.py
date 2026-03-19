from django.db import models


class County(models.Model):
    code = models.CharField(max_length=5, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'counties'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Municipality(models.Model):
    county = models.ForeignKey(County, on_delete=models.CASCADE, related_name='municipalities')
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=[
        ('grad', 'Grad'),
        ('općina', 'Općina'),
        ('država', 'Država'),
    ])

    class Meta:
        verbose_name_plural = 'municipalities'
        unique_together = ['county', 'name']
        ordering = ['county', 'name']

    def __str__(self):
        return f"{self.name} ({self.county.code})"


class PollingStation(models.Model):
    municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, related_name='polling_stations')
    number = models.CharField(max_length=10)
    name = models.CharField(max_length=300)
    location = models.CharField(max_length=500, blank=True)
    address = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = ['municipality', 'number']
        ordering = ['municipality', 'number']

    def __str__(self):
        return f"{self.municipality.name} - {self.number} {self.name}"
