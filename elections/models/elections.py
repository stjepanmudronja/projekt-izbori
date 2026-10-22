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
    # Rounds of the same election are held weeks apart and can fall in
    # different calendar years — the 2019 presidential first round was
    # 22 Dec 2019, its runoff 5 Jan 2020 — so `Election.date` (the first
    # round) can't label round 2. Set by `set_election_dates`.
    date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ['election', 'round_number']

    def __str__(self):
        return f"{self.election.name} - Krug {self.round_number}"


class ElectoralDistrict(models.Model):
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='districts')
    number = models.IntegerField()
    name = models.CharField(max_length=200)
    # The contest's own published electorate, for districts whose voters
    # TurnoutData already counts elsewhere: 1992's and 1995's single-member
    # districts and minority units, where the same electors also cast the
    # national-list ballot. Display only — never summed into turnout, or the
    # electorate doubles. Null wherever TurnoutData is the record.
    registered_voters = models.IntegerField(null=True, blank=True)
    ballots_cast = models.IntegerField(null=True, blank=True)
    invalid_ballots = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ['election', 'number']

    def __str__(self):
        return f"{self.name} ({self.election.name})"
