from django.db import models


class TurnoutData(models.Model):
    election_round = models.ForeignKey(
        'ElectionRound', on_delete=models.CASCADE, related_name='turnout_data'
    )
    polling_station = models.ForeignKey(
        'PollingStation', on_delete=models.CASCADE, related_name='turnout_data'
    )
    registered_voters = models.IntegerField(default=0)
    ballots_cast = models.IntegerField(default=0)
    valid_ballots = models.IntegerField(default=0)
    invalid_ballots = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = 'turnout data'
        unique_together = ['election_round', 'polling_station']

    def __str__(self):
        return f"Turnout: {self.polling_station} ({self.election_round})"


class ListResult(models.Model):
    electoral_list = models.ForeignKey(
        'ElectoralList', on_delete=models.CASCADE, related_name='results'
    )
    polling_station = models.ForeignKey(
        'PollingStation', on_delete=models.CASCADE, related_name='list_results'
    )
    votes = models.IntegerField(default=0)

    class Meta:
        unique_together = ['electoral_list', 'polling_station']

    def __str__(self):
        return f"{self.electoral_list}: {self.votes} votes at {self.polling_station}"


class CandidateResult(models.Model):
    candidacy = models.ForeignKey(
        'Candidacy', on_delete=models.CASCADE, related_name='results'
    )
    polling_station = models.ForeignKey(
        'PollingStation', on_delete=models.CASCADE, related_name='candidate_results'
    )
    votes = models.IntegerField(default=0)

    class Meta:
        unique_together = ['candidacy', 'polling_station']

    def __str__(self):
        return f"{self.candidacy.person}: {self.votes} votes at {self.polling_station}"
