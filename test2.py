import requests
import threading

url = "https://my.rcell.me/plans"

headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "accept": "text/x-component",
    "origin": "https://my.rcell.me",
    "referer": "https://my.rcell.me/plans",
    "next-action": "40c6f04721d58080b1f139420bc99a5c3374129034",
    "cookie": "Next-Locale=ar; selfcare-application=Fe26.2*1*17e15db9580c2242049e340bfea262a6342dbfb1ce2b9a8f889059f0f8fefa1d*nURzFWK--CQTr51E0L2d8Q*0Z6y4pHsmPbTWfgZoQR1ibv44aUxgzoMcvTA7b84mCrwfToDjbn7OuVPMGE-Ubi9e2Ipx8bmZS-orh1yE2oDwoe-lxyRrSNsYjgXMPoAQts1yVjTJ7VmP9IDXFWfiTfZBVK5HNjjCzBZDJDBwfLrImX9fYumh-8YSfSnfxY2msVd5t4j8WOqzy8PMziPEi2G4szxsB1hsPU81lx-GrZp5HWnyNh-jBbvaK4-eZW3x4fnK6AAUvR7IQuMRUu8YmULuV7hSn8JZSS46GUf0ae1vNvrrmZ8KV3eZeHNWMbbUcRxSz8wPNVdW2hLc-wpf6ktyJQWu7F4VBhXZZ5U6NBDpYSRtr8DfePdPFxeXMsUY4i5aiOZEMMZrto7r7SC9IijLsl1KrnrACBPDKu9mZFT_kHIGmxH3Y0HRvnVN026SbuFsxSCSJhRUMvj6Qwci-Jeb8yqZXKuf9cGk72_tKUoLazfGHFBYeqHfzI4FegIZJmUk5M3KZ-qTGnpKEY_qzrctRAVQ5yqHFB2wqKtGL04Sk8-WoVaJ_C386xo-Oxx5E-USF3GPQr1D0yth8KGkMSASaVS0CAxg4DnRXwHbWvThTB-TkdPxAaqJDuN8TzivFGEPHswXT78U8r9b9bKBsWMxynxJVwTF8J2ABejefS-TXgib9Nx86XCXul_Tj91jvp7vgbzr42TSNY0s8bpD605xPQ_U3iGwtE4y4FUoNDOU8zhukHDrv8GHcarmgNZWqOwaP77rBZwI_q8uzFdVQ6hBtECSzJGGkuz1CVufJFJOODOyGOr1AS-PsKNBdLfECL63VTY6mG4p5fP6u0L8AdzsPrkkpUyaLKL5Ry8T15w2t0eSPWlFG6P3KdrtfTqolNAn3KR4tvGGVX6gnpc7B1txVI8VJjlF3M8CrN6EUICnEVtNwzEd0YEIKJFTQvVXQYdDir0Dv7uD_2jc45AwiTq-8k3jeMKzFe6rFHssVPj7w*1776356989694*51632a6d58b52769e2048908b4a1d6ef52d667f7df9367e5ff84315170f62c7e*TmhtjMET8e7QgrZb4-iaNALhQHsA4O6rGpLwUBioVPE~2 host my.rcell.me next-action 40c6f04721d58080b1f139420bc99a5c3374129034 next-router-state-tree %5B%22%22%2C%7B%22children%22%3A%5B%5B%22locale%22%2C%22ar%22%2C%22d%22%5D%2C%7B%22children%22%3A%5B%22(root)%22%2C%7B%22children%22%3A%5B%22(main)%22%2C%7B%22children%22%3A%5B%22(plans)%22%2C%7B%22children%22%3A%5B%22plans%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2C%22%2Fplans%22%2C%22refresh%22%5D%7D%5D%7D%2Cnull%2Cnull%2Ctrue%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D%7D%2Cnull%2Cnull%5D",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

}

counter = 0

def worker():
    global counter
    while True:
        current = counter
        counter += 1

        payload = {
            "1_plan_id": f"{current}",
            "0": f'[{current},"$undefined","$K1"]'
        }

        try:
            r = requests.post(url, headers=headers, data=payload)
            print(current, r.status_code)
        except Exception as e:
            print(f"Error occurred for {current}: {e}")

threads = []

for _ in range(1):  # عدد الثريدات
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)