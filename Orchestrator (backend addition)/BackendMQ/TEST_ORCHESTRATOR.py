from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import string
import time
import random

URL = "http://127.0.0.1:4351/api/predict"
REQUEST_COUNT = 100
TEXTS_PER_REQUEST = 60
CONCURRENCY = 10
TIMEOUT = 10

def make_fake_text(number):
    alphabet = string.ascii_letters + string.digits
    return {
        f"request_{number:03d}_text_{text_number:02d}": " ".join(
            "".join(random.choice(alphabet) for _ in range(8))
            for _ in range(8)
        )
        for text_number in range(TEXTS_PER_REQUEST)
    }


def send_request(payload):
    st = time.perf_counter()
    
    try:
        response = requests.post(URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or set(result) != set(payload) or not all(isinstance(value, float) and 0.0 <= value <= 1.0 for value in result.values()):
            return False, time.perf_counter() - st, "Invalid response format"
        
        return True, time.perf_counter() - st, None
    
    except (requests.RequestException, ValueError) as error:
        return False, time.perf_counter() - st, str(error)

payloads = [make_fake_text(number) for number in range(REQUEST_COUNT)]
results = []

with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
    futures = [executor.submit(send_request, payload) for payload in payloads]
    for number, future in enumerate(as_completed(futures), start=1):
        success, time_taken, error = future.result()
        results.append((success, time_taken))
        if not success:
            print(f"Request failed ({number}/{REQUEST_COUNT}, {time_taken:.2f}s): {error}")

durations = [time_taken for _, time_taken in results]
successful = sum(success for success, _ in results)

print(
    f"Finished: {successful} succeeded, {REQUEST_COUNT - successful} failed; "
    f"average {sum(durations) / len(durations):.2f}s"
)