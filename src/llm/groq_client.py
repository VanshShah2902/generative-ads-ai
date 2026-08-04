import os
import time
import concurrent.futures
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class TimeoutException(Exception):
    pass

class GroqClient:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found")

        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
        print("[Groq] API Key Loaded:", bool(self.client))

    def generate(self, prompt: str):
        print("[Groq] Sending request...")
        start_time = time.time()
        
        def _make_request():
            print(f"[Groq] Using model: {self.model}")
            try:
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=800,
                    timeout=20.0
                )
            except Exception as primary_err:
                print(f"[Groq] Primary model failed ({primary_err}), switching to fallback")
                return self.client.chat.completions.create(
                    model="mixtral-8x7b-32768",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=800,
                    timeout=20.0
                )

        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_make_request)
                response = future.result(timeout=20.0)

            duration = time.time() - start_time
            print(f"[Groq] Response received in {duration:.2f}s")

            output = response.choices[0].message.content
            print(f"[Groq] Output preview: {output[:200]}...")

            return output

        except concurrent.futures.TimeoutError:
            print("[Groq ERROR] Request timed out")
            raise TimeoutException("Groq request timed out")
        except Exception as e:
            print(f"[Groq ERROR]: {e}")
            raise e
