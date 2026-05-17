# Lokalni izbori — county-level kinds (Župan, Županijska skupština)

## What changed

The `/api/lokalni/station-results` endpoint and the Lokalni izbori UI
now support two new **county-level** election kinds in addition to
the existing muni-level ones:

| `kind`           | Razina    | Election type (DB)     |
| ---------------- | --------- | ---------------------- |
| `vijece`         | muni      | Gradsko / Općinsko vijeće |
| `nacelnik`       | muni      | Gradonačelnik / Načelnik  |
| `zupan`          | županija  | Župan                  |
| `zup_skupstina`  | županija  | Županijska skupština   |

For `zupan` / `zup_skupstina` the scope is the entire županija:
votes and turnout are aggregated across every polling station whose
municipality belongs to the chosen county, and the per-station
breakdown lists every BM in the county.

## Backend (`app.py`)

`/api/lokalni/station-results` now accepts a `county_id` parameter
and a new dispatch map:

```python
LOKALNI_COUNTY_KIND_TO_TYPE = {
    'zupan': 'Župan',
    'zup_skupstina': 'Županijska skupština',
}
```

The handler branches on `is_county_kind = kind in LOKALNI_COUNTY_KIND_TO_TYPE`:

- **County kind**: requires `county_id`; ignores `station_id` / `municipality_id`.
- **Muni kind**: requires `station_id` *or* `municipality_id`,
  and the muni must be `grad` or `općina` (unchanged behaviour).

The two parallel SQL paths for votes/turnout were collapsed into a
single `scope_stations` subquery covering all three scopes:

```python
if is_county_kind:
    scope_stations = db.session.query(PollingStation.id).join(
        Municipality, Municipality.id == PollingStation.municipality_id
    ).filter(Municipality.county_id == county.id)
elif station_id:
    scope_stations = db.session.query(PollingStation.id).filter(PollingStation.id == station_id)
else:
    scope_stations = db.session.query(PollingStation.id).filter(
        PollingStation.municipality_id == muni.id
    )
```

The vote query then joins via `ListResult.polling_station_id.in_(scope_stations)`,
and turnout aggregation runs the same join against `TurnoutData`.

`stations_breakdown` is returned for every non-single-station scope
(both `municipality` and `county`), so the UI gets a per-BM turnout
table for the whole županija.

### Request examples

```
GET /api/lokalni/station-results?county_id=7&kind=zupan&round=1
GET /api/lokalni/station-results?county_id=7&kind=zup_skupstina&round=1
GET /api/lokalni/station-results?municipality_id=42&kind=nacelnik&round=2
GET /api/lokalni/station-results?station_id=1234&kind=vijece&round=1
```

### Error cases

| Request                                           | HTTP | Body                                             |
| ------------------------------------------------- | ---- | ------------------------------------------------ |
| county-level kind without `county_id`             | 400  | `county_id required for county-level kind`       |
| unknown kind                                      | 400  | `kind must be one of [...]`                      |
| `county_id` not found                             | 404  | `county not found`                               |

## Frontend (`templates/index.html`)

### Dropdown

The **Vrsta izbora** select is split into two `<optgroup>`s so the
županijska razina is clearly separated from gradska / općinska:

```html
<optgroup label="Županijska razina">
  <option value="zupan">Župan</option>
  <option value="zup_skupstina">Županijska skupština</option>
</optgroup>
<optgroup label="Gradska / općinska razina">
  <option value="vijece">Gradsko / Općinsko vijeće</option>
  <option value="nacelnik">Gradonačelnik / Općinski načelnik</option>
</optgroup>
```

### Gating

The previous flow required `county → muni → kind`. Now `kind` is
enabled as soon as a county is picked:

- County-level kinds need: `county` + `kind` (muni/station ignored).
- Muni-level kinds still need: `county` + `muni` + `kind` (station optional).

The Add-to-compare button mirrors this:

```js
btn.disabled = LOK_COUNTY_KINDS.has(k) ? !cId : !mId;
```

### Scope model

Compare chips are keyed on `(type, id, kind)`. A new scope type was
added: `type: 'county'`. The chip type-badge shows `Žup` for county
scopes; `BM` / `Gr/Op` are unchanged. Kind labels are centralised:

```js
const LOK_KIND_LABELS = {
    vijece: 'Vijeće', nacelnik: 'Načelnik',
    zupan: 'Župan', zup_skupstina: 'Žup. skupština',
};
```

### Fetch

`fetchOne` picks the right query-string param per scope type:

```js
if (sc.type === 'station')      params.set('station_id', sc.id);
else if (sc.type === 'county')  params.set('county_id', sc.id);
else                             params.set('municipality_id', sc.id);
```

## Why this lives in one endpoint

All four kinds share the same response shape (items + total + turnout +
per-station breakdown), differ only in (a) which `ElectionType` row to
look up and (b) which stations are in scope. Keeping them in one
endpoint avoids duplicating the vote/turnout aggregation SQL and lets
the compare UI mix all four kinds in one set of side-by-side cards.
