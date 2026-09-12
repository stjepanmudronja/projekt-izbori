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


class ParliamentMember(models.Model):
    """A person who held a Sabor seat in the convocation elected at `election`.

    Complements ElectedMandate, which hangs off a Candidacy and so only works
    where DIP published candidate names. Before preferential voting (2015) it
    published list totals only for districts I-XI, so no Candidacy exists for
    the 2007/2011 MPs and there is nothing for an ElectedMandate to point at.
    This table also carries mid-term replacements, who never appear in the
    election-day result at all — hence a roster per convocation rather than a
    flag on the election result.

    `party` holds the full "<NAME> - <ABBR>" form the results pages show, not a
    Party FK: the roster names the party a member sat for, which need not be
    one of the ElectoralList names they were elected on (a coalition list
    returns members of several parties). `set_sabor_members` expands the
    abbreviation its rosters are written with. It is blank where the published
    roster records no affiliation, as for the 2003 saziv.
    `candidacy` is filled in where the person does have one (district XII).
    """
    election = models.ForeignKey(
        'Election', on_delete=models.CASCADE, related_name='parliament_members'
    )
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name='parliament_memberships'
    )
    party = models.CharField(max_length=200, blank=True)
    minority = models.BooleanField(
        default=False, help_text='Elected in district XII (nacionalne manjine)'
    )
    note = models.CharField(
        max_length=300, blank=True,
        help_text='Mandate start/end, reactivation after mirovanje, etc.'
    )
    candidacy = models.ForeignKey(
        Candidacy, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='parliament_members'
    )

    class Meta:
        unique_together = ['election', 'person']
        ordering = ['person__last_name', 'person__first_name']
        indexes = [
            models.Index(fields=['election']),
        ]

    def __str__(self):
        return f"{self.person} ({self.party}) — {self.election}"
