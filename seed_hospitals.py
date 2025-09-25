# seed_hospitals.py
import redis
import json

# Connect to Redis (talks to your Docker container)
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Alberta hospitals dataset
HOSPITALS = [
{
    "region": "Calgary",
    "category": "Emergency",
    "name": "Alberta Children's Hospital",
    "wait_time": "3 hr 20 min",
    "note": "Open 24 hours for patients 17 &amp; under (two adult family/support persons allowed)"
  },
  {
    "region": "Calgary",
    "category": "Emergency",
    "name": "Foothills Medical Centre",
    "wait_time": "6 hr 1 min",
    "note": "Open 24 hours<br />For patients 15 and older"
  },
  {
    "region": "Calgary",
    "category": "Emergency",
    "name": "Peter Lougheed Centre",
    "wait_time": "3 hr 7 min",
    "note": "Open 24 hours"
  },
  {
    "region": "Calgary",
    "category": "Emergency",
    "name": "Rockyview General Hospital",
    "wait_time": "3 hr 55 min",
    "note": "Open 24 hours<br />"
  },
  {
    "region": "Calgary",
    "category": "Emergency",
    "name": "South Health Campus",
    "wait_time": "4 hr 16 min",
    "note": "Open 24 hours for all patients with pediatrician specialty from 11 am – 11 pm"
  },
  {
    "region": "Calgary",
    "category": "Urgent",
    "name": "Airdrie Community Health Centre",
    "wait_time": "1 hr 7 min",
    "note": "Open 24 hours "
  },
  {
    "region": "Calgary",
    "category": "Urgent",
    "name": "Cochrane Community Health Centre",
    "wait_time": "0 hr 30 min",
    "note": "8 am – 10 pm"
  },
  {
    "region": "Calgary",
    "category": "Urgent",
    "name": "Okotoks Health and Wellness Centre",
    "wait_time": "0 hr 30 min",
    "note": "8 am – 10 pm"
  },
  {
    "region": "Calgary",
    "category": "Urgent",
    "name": "Sheldon M. Chumir Centre",
    "wait_time": "1 hr 18 min",
    "note": "Open 24 hours"
  },
  {
    "region": "Calgary",
    "category": "Urgent",
    "name": "South Calgary Health Centre",
    "wait_time": "0 hr 30 min",
    "note": "8 am – 8 pm"
  },
  {
    "region": "Edmonton",
    "category": "Emergency",
    "name": "Devon General Hospital",
    "wait_time": "0 hr 56 min",
    "note": "Open 24 hours"
  },
  {
    "region": "Edmonton",
    "category": "Emergency",
    "name": "Fort Sask Community Hospital",
    "wait_time": "2 hr 24 min",
    "note": "Open 24 hours"
  },
  {
    "region": "Edmonton",
    "category": "Emergency",
    "name": "Grey Nuns Community Hospital",
    "wait_time": "2 hr 45 min",
    "note": "Open 24 hours"
  },
  {
    "region": "Edmonton",
    "category": "Emergency",
    "name": "Leduc Community Hospital",
    "wait_time": "1 hr 38 min",
    "note": "Open 24 hours"
  },
  {
    "region": "Edmonton",
    "category": "Emergency",
    "name": "Misericordia Community Hospital",
    "wait_time": "1 hr 41 min",
    "note": "Open 24 hours"
  },
  {
    "region": "Edmonton",
    "category": "Emergency",
    "name": "Northeast Community Health Centre",
    "wait_time": "2 hr 25 min",
    "note": "Open 24 hours"
  },
  {
    "region": "Edmonton",
    "category": "Emergency",
    "name": "Royal Alexandra Hospital",
    "wait_time": "3 hr 53 min",
    "note": "Open 24 hours"
  },
  {
    "region": "Edmonton",
    "category": "Emergency",
    "name": "Stollery Children's Hospital",
    "wait_time": "0 hr 30 min",
    "note": "Open 24 hours for patients 17 &amp; under (one adult family/support person allowed)"
  },
  {
    "region": "Edmonton",
    "category": "Emergency",
    "name": "Strathcona Community Hospital",
    "wait_time": "0 hr 51 min",
    "note": "Open 24 hours<br />This location is in Sherwood Park"
  },
  {
    "region": "Edmonton",
    "category": "Emergency",
    "name": "Sturgeon Community Hospital",
    "wait_time": "2 hr 30 min",
    "note": "Open 24 hours<br />This location is in St. Albert"
  },
  {
    "region": "Edmonton",
    "category": "Emergency",
    "name": "University of Alberta Hospital",
    "wait_time": "6 hr 0 min",
    "note": "Open 24 hours"
  },
  {
    "region": "Edmonton",
    "category": "Emergency",
    "name": "WestView Health Centre",
    "wait_time": "0 hr 34 min",
    "note": "Open 24 hours<br />This location is in Stony Plain"
  },
  {
    "region": "RedDeer",
    "category": "Emergency",
    "name": "Red Deer Regional Hospital",
    "wait_time": "2 hr 21 min",
    "note": "Open 24 hours"
  },
  {
    "region": "RedDeer",
    "category": "Emergency",
    "name": "Innisfail Health Centre",
    "wait_time": "Wait times unavailable",
    "note": "Open 24 hours"
  },
  {
    "region": "RedDeer",
    "category": "Emergency",
    "name": "Lacombe Hospital and Care Centre",
    "wait_time": "Wait times unavailable",
    "note": "Open 24 hours"
  },
  {
    "region": "Lethbridge",
    "category": "Emergency",
    "name": "Chinook Regional Hospital",
    "wait_time": "0 hr 56 min",
    "note": "Open 24 hours"
  },
  {
    "region": "MedicineHat",
    "category": "Emergency",
    "name": "Medicine Hat Regional Hospital",
    "wait_time": "0 hr 36 min",
    "note": "Open 24 hours"
  },
  {
    "region": "GrandePrairie",
    "category": "Emergency",
    "name": "Grande Prairie Regional Hospital",
    "wait_time": "0 hr 30 min",
    "note": "Open 24 hours"
  },
  {
    "region": "FortMcMurray",
    "category": "Emergency",
    "name": "Northern Lights Regional Health Centre",
    "wait_time": "1 hr 36 min",
    "note": "Open 24 hours"
  }
]

# Clean out any bad placeholder keys
r.delete("hospital:")

# Push hospitals into Redis with auto IDs
for idx, hospital in enumerate(HOSPITALS, start=1):
    key = f"hospital:{idx}"
    r.set(key, json.dumps(hospital))
    print(f"✅ Seeded {key} -> {hospital['name']}")

print("🎉 Hospital seeding completed!")
