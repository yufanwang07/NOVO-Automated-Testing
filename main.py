import http.client
import json
import random
from datetime import datetime

conn = http.client.HTTPConnection("tripmocksvc.stg-qa.k8s.mypna.com")

prob_per_mile = {
    "hard_acceleration": 0.1,
    "hard_brake": 0.1,
    "speeding": 0.8,
}
multiplier = {
    "hard_acceleration": 1,
    "hard_brake": 1,
    "speeding": 1,
}

bay_area_coords = [
    # San Francisco
    (37.774929, -122.419416),  # SF - Civic Center
    (37.807999, -122.417743),  # SF - Fisherman's Wharf
    (37.759703, -122.428093),  # SF - Mission District
    (37.802139, -122.41874),   # SF - North Beach

    # Peninsula
    (37.441883, -122.143019),  # Palo Alto
    (37.457409, -122.170292),  # Menlo Park
    (37.562991, -122.325525),  # San Mateo
    (37.486316, -122.232523),  # Redwood City
    (37.600869, -122.391675),  # SFO Airport

    # South Bay
    (37.386050, -122.083850),  # Mountain View
    (37.331820, -122.030710),  # Cupertino
    (37.354107, -121.955238),  # Santa Clara
    (37.341414, -121.893005),  # Downtown San Jose

    # East Bay
    (37.804363, -122.271111),  # Oakland
    (37.871593, -122.272743),  # Berkeley
    (37.765207, -122.241635),  # Alameda
    (37.695111, -122.126495),  # Hayward
    (37.702152, -121.935791),  # Dublin
    (37.668820, -122.080796),  # Fremont
    (37.783460, -122.211460),  # San Leandro
]

def distance_miles(lat1, lon1, lat2, lon2):
    dlat = (lat2 - lat1) * 69.0
    dlon = (lon2 - lon1) * 55.5
    return (dlat**2 + dlon**2) ** 0.5

def generate_events(distance_miles):
    return {
        event: sum(random.random() < prob for prob in [prob_per_mile[event]] * int(distance_miles) * multiplier[event])
        for event in prob_per_mile
    }


start_coord, end_coord = random.sample(bay_area_coords, 2)
trip_start_time_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

distance = distance_miles(*start_coord, *end_coord)
event_counts = generate_events(distance)

payload = json.dumps({
    "desired_trips": [
        {
            "mock_vin": "5797d88a-27dc-43bb-8193-788aa6c2765d",
            "mock_telematics_user_id": "52e7e9e9-1eea-4f28-a89a-a20e049be2a7",
            "trip_start_point": f"{start_coord[0]},{start_coord[1]}",
            "trip_end_point": f"{end_coord[0]},{end_coord[1]}",
            "trip_start_time_local": trip_start_time_local,
            "job_creator": "TTTEST",
            "target_trip_format": "pipeline-novo_mobile_bt",
            "desired_drive_events": event_counts,
            "job_options": {
                "match_device_id": "5797d88a-27dc-43bb-8193-788aa6c2765d"
            }
        }
    ]
})

headers = {
  'Content-Type': 'application/json'
}

conn.request("POST", "/mock/trip/rapid", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
