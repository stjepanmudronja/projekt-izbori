from django.db import models


class ElectionType(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subtypes')

    def __str__(self):
        return self.name


class Election(models.Model):
    election_type = models.ForeignKey(ElectionType, on_delete=models.CASCADE, related_name='elections')
    year = models.IntegerField()
    name = models.CharField(max_length=300)
    date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ['election_type', 'year', 'name']

    def __str__(self):
        return self.name


class ElectionRound(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='rounds')
    round_number = models.IntegerField()

    class Meta:
        unique_together = ['election', 'round_number']

    def __str__(self):
        return f"{self.election.name} - Krug {self.round_number}"


class ElectoralDistrict(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='districts')
    number = models.IntegerField()
    name = models.CharField(max_length=200)

    class Meta:
        unique_together = ['election', 'number']

    def __str__(self):
        return f"{self.name} ({self.election.name})"
