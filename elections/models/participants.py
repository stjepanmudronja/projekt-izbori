from django.db import models


class Person(models.Model):
    first_name = models.CharField(max_length=200)
    last_name = models.CharField(max_length=200)
    normalized_name = models.CharField(max_length=400, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Party(models.Model):
    name = models.CharField(max_length=500, unique=True)
    short_name = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name_plural = 'parties'

    def __str__(self):
        return self.short_name or self.name


class ElectoralList(models.Model):
    election_round = models.ForeignKey(
        'ElectionRound', on_delete=models.CASCADE, related_name='electoral_lists'
    )
    district = models.ForeignKey(
        'ElectoralDistrict', on_delete=models.CASCADE, null=True, blank=True, related_name='electoral_lists'
    )
    name = models.CharField(max_length=1000)
    parties = models.ManyToManyField(Party, blank=True, related_name='electoral_lists')

    class Meta:
        indexes = [
            models.Index(fields=['election_round', 'district']),
        ]

    def __str__(self):
        return self.name[:100]


class Candidacy(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='candidacies')
    electoral_list = models.ForeignKey(ElectoralList, on_delete=models.CASCADE, related_name='candidacies')
    position_on_list = models.IntegerField()

    class Meta:
        verbose_name_plural = 'candidacies'
        unique_together = ['electoral_list', 'position_on_list']

    def __str__(self):
        return f"{self.person} - #{self.position_on_list} on {self.electoral_list}"


class ElectedMandate(models.Model):
    """A candidacy that actually took a seat/mandate.

    Recorded explicitly for outcomes that can't be derived from vote totals —
    e.g. EU MEPs who were seated only after higher-placed candidates ceded
    their seat (dual office). `group` optionally holds extra context such as
    the European Parliament political group.
    """
    candidacy = models.OneToOneField(
        Candidacy, on_delete=models.CASCADE, related_name='elected_mandate'
    )
    group = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"Mandate: {self.candidacy.person}"
