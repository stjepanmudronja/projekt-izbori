from django.contrib import admin
from .models import (
    County, Municipality, PollingStation,
    ElectionType, Election, ElectionRound, ElectoralDistrict,
    Person, Party, ElectoralList, Candidacy,
    TurnoutData, ListResult, CandidateResult,
)


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['name']


@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'county']
    list_filter = ['type', 'county']
    search_fields = ['name']


@admin.register(PollingStation)
class PollingStationAdmin(admin.ModelAdmin):
    list_display = ['number', 'name', 'municipality']
    search_fields = ['name', 'municipality__name']
    list_filter = ['municipality__county']


@admin.register(ElectionType)
class ElectionTypeAdmin(admin.ModelAdmin):
    list_display = ['slug', 'name', 'parent']


@admin.register(Election)
class ElectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'year', 'election_type', 'date']
    list_filter = ['election_type', 'year']


@admin.register(ElectionRound)
class ElectionRoundAdmin(admin.ModelAdmin):
    list_display = ['election', 'round_number']
    list_filter = ['election']


@admin.register(ElectoralDistrict)
class ElectoralDistrictAdmin(admin.ModelAdmin):
    list_display = ['number', 'name', 'election']


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'normalized_name']
    search_fields = ['first_name', 'last_name', 'normalized_name']


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ['short_name', 'name']
    search_fields = ['name', 'short_name']


@admin.register(ElectoralList)
class ElectoralListAdmin(admin.ModelAdmin):
    list_display = ['name', 'election_round', 'district']
    list_filter = ['election_round__election']
    search_fields = ['name']


@admin.register(Candidacy)
class CandidacyAdmin(admin.ModelAdmin):
    list_display = ['person', 'electoral_list', 'position_on_list']
    search_fields = ['person__first_name', 'person__last_name']
    list_filter = ['electoral_list__election_round__election']


@admin.register(TurnoutData)
class TurnoutDataAdmin(admin.ModelAdmin):
    list_display = ['polling_station', 'election_round', 'registered_voters', 'ballots_cast']
    list_filter = ['election_round']


@admin.register(ListResult)
class ListResultAdmin(admin.ModelAdmin):
    list_display = ['electoral_list', 'polling_station', 'votes']
    list_filter = ['electoral_list__election_round__election']


@admin.register(CandidateResult)
class CandidateResultAdmin(admin.ModelAdmin):
    list_display = ['candidacy', 'polling_station', 'votes']
    list_filter = ['candidacy__electoral_list__election_round__election']
