# import requests
# import time

# API_KEY = "3a945a7a01msh728da461f150235p193e34jsn95c4e1ef24aa"

# JUDGE0_URL = "https://judge0-ce.p.rapidapi.com/submissions?base64_encoded=false&wait=false"

# LANGUAGE_MAP = {
#     "python": 71,
#     "javascript": 63,
#     "java": 62,
#     "cpp": 54,
#     "c": 50
# }


# def execute_code(code, language, puzzle_input=""):

#     if language not in LANGUAGE_MAP:
#         return {
#             "status": "error",
#             "stderr": "Unsupported language"
#         }

#     payload = {
#         "language_id": LANGUAGE_MAP[language],
#         "source_code": code,
#         "stdin": puzzle_input
#     }

#     headers = {
#         "Content-Type": "application/json",
#         "X-RapidAPI-Key": API_KEY,
#         "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com"
#     }

#     try:

#         # Submit code
#         response = requests.post(JUDGE0_URL, json=payload, headers=headers)

#         print("SUBMIT RESPONSE:", response.text)

#         data = response.json()

#         if "token" not in data:
#             return {
#                 "status": "error",
#                 "stderr": data
#             }

#         token = data["token"]

#         # wait for execution
#         time.sleep(2)

#         # fetch result
#         result = requests.get(
#             f"https://judge0-ce.p.rapidapi.com/submissions/{token}?base64_encoded=false",
#             headers=headers
#         )

#         print("RESULT RESPONSE:", result.text)

#         result_data = result.json()

#         return {
#             "status": "success",
#             "stdout": (result_data.get("stdout") or "").strip(),
#             "stderr": (result_data.get("stderr") or "").strip(),
#             "executionTime": result_data.get("time")
#         }

#     except Exception as e:
#         return {
#             "status": "error",
#             "stderr": str(e)
#         }