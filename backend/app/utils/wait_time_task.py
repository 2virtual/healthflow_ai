# # wait_time_task.py (DEV-ONLY MOCK)
# import redis
# import json
# import time
# import random

# # Connect to Redis
# r = redis.Redis(host="redis", port=6379, decode_responses=True)

# def update_hospital_wait_times():
#     keys = r.keys("hospital:*")
#     if not keys:
#         print("⚠️ No hospital data in Redis. Run update_hospital_data.py first.")
#         return

#     for key in keys:
#         try:
#             raw = r.get(key)
#             if not raw:
#                 continue
#             hospital_data = json.loads(raw)

#             # Preserve original name/category; only update wait_time
#             # Mimic real AHS states:
#             states = ["open", "closed", "unavailable"]
#             state = random.choices(states, weights=[70, 20, 10], k=1)[0]

#             if state == "closed":
#                 wait_time = "Closed"
#             elif state == "unavailable":
#                 wait_time = "Wait times unavailable"
#             else:
#                 # Realistic wait: 0–8 hours
#                 wait_hours = random.randint(0, 8)
#                 wait_minutes = random.choice([0, 15, 30, 45])
#                 wait_time = f"{wait_hours} hr {wait_minutes} min"

#             hospital_data["wait_time"] = wait_time  # matches AHS field name

#             r.set(key, json.dumps(hospital_data))
#             print(f"✅ Updated {key} -> {hospital_data.get('name', 'Unknown')} (wait: {wait_time})")

#         except Exception as e:
#             print(f"❌ Error updating {key}: {e}")

# if __name__ == "__main__":
#     print("🔄 Starting mock hospital wait time updater (DEV MODE)")
#     while True:
#         update_hospital_wait_times()
#         time.sleep(300)  # every 5 minutes






# # # wait_time_task.py
# # import redis
# # import json
# # import time
# # import random

# # # Connect to Redis (Docker container service name = "redis")
# # r = redis.Redis(host="redis", port=6379, decode_responses=True)

# # def update_hospital_wait_times():
# #     keys = r.keys("hospital:*")
# #     for key in keys:
# #         hospital_data = json.loads(r.get(key))

# #         # ✅ Just update wait_time, leave everything else untouched
# #         wait_hours = random.randint(0, 4)
# #         wait_minutes = random.randint(0, 59)
# #         hospital_data["wait_time"] = f"{wait_hours} hr {wait_minutes} min"

# #         # Save back into Redis
# #         r.set(key, json.dumps(hospital_data))
# #         print(f"✅ Updated {key} -> {hospital_data['name']} (wait {hospital_data['wait_time']})")

# # if __name__ == "__main__":
# #     while True:
# #         update_hospital_wait_times()
# #         time.sleep(300)  # update every 5 minutes
