import os
import time

import requests
from flask import Blueprint, request, jsonify

PROVIDER = "openmeteo"  # openmeteo | photon | geonames
GEONAMES_USER = ""

_CACHE = {}
TTL = 3600  # 1 час

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
UA = os.getenv("NOMINATIM_UA", "UnieTicket/1.0 (admin@yourdomain.tld)")

_ADDR_CACHE = {}
ADDR_TTL = 1800

places_bp = Blueprint("places_bp", __name__)


@places_bp.route("/api/cities")
def api_cities():
    q = (request.args.get("q") or "").strip()
    limit = int(request.args.get("limit", 15))
    if len(q) < 2:
        return jsonify([])

    key = f"{PROVIDER}::{q.lower()}::{limit}"
    now = time.time()
    if key in _CACHE and now - _CACHE[key][0] < TTL:
        return jsonify(_CACHE[key][1])

    try:
        if PROVIDER == "photon":
            data = _photon(q, limit)
        elif PROVIDER == "geonames":
            data = _geonames(q, limit)
        else:
            data = _openmeteo(q, limit)  # по умолчанию
    except Exception:
        data = []

    _CACHE[key] = (now, data)
    return jsonify(data)


def _openmeteo(q, limit):
    # https://geocoding-api.open-meteo.com/v1/search?name=Prague&count=10&type=city&language=en
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": q, "count": limit, "type": "city", "language": "en"}
    r = requests.get(url, params=params, timeout=6)
    r.raise_for_status()
    js = r.json()
    res = []
    for it in js.get("results", []) or []:
        res.append({
            "id": it.get("id") or f"om-{it.get('latitude')}-{it.get('longitude')}",
            "name": it.get("name", ""),
            "country": it.get("country", "") or "",
            "admin": it.get("admin1", "") or "",
            "lat": float(it["latitude"]),
            "lon": float(it["longitude"]),
            "source": "openmeteo",
        })
    return res[:limit]


def _photon(q, limit):
    # https://photon.komoot.io/api/?q=Prague&limit=10
    url = "https://photon.komoot.io/api"
    params = {"q": q, "limit": limit}
    r = requests.get(url, params=params, timeout=6)
    r.raise_for_status()
    js = r.json()
    res = []
    for f in js.get("features", []) or []:
        props = f.get("properties", {})
        if props.get("type") not in ("city", "town", "village", "municipality", "locality"):
            continue
        lon, lat = f["geometry"]["coordinates"]
        res.append({
            "id": props.get("osm_id") or props.get("osm_value") or props.get("countrycode") + "-" + props.get("name",
                                                                                                              ""),
            "name": props.get("name", ""),
            "country": props.get("country", "") or "",
            "admin": props.get("state", "") or props.get("county", "") or "",
            "lat": float(lat),
            "lon": float(lon),
            "source": "photon",
        })
    return res[:limit]


def _geonames(q, limit):
    # https://secure.geonames.org/searchJSON?q=Prague&featureClass=P&maxRows=15&lang=en&username=USER
    if not GEONAMES_USER:
        return []
    url = "https://secure.geonames.org/searchJSON"
    params = {
        "q": q,
        "maxRows": limit * 2,
        "featureClass": "P",  # только населённые пункты
        "orderby": "relevance",
        "lang": "en",
        "username": GEONAMES_USER,
    }
    r = requests.get(url, params=params, timeout=6)
    r.raise_for_status()
    js = r.json()
    res = []
    for it in js.get("geonames", []) or []:
        if not it.get("name"):
            continue
        res.append({
            "id": it.get("geonameId"),
            "name": it["name"],
            "country": it.get("countryName", "") or "",
            "admin": it.get("adminName1", "") or "",
            "lat": float(it["lat"]),
            "lon": float(it["lng"]),
            "source": "geonames",
        })
        if len(res) >= limit: break
    return res
