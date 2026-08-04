import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    """Connects to Groq API for technical and creative reasoning."""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("[LLMClient] WARNING: GROQ_API_KEY not found in environment.")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "openai/gpt-oss-120b"
        
    def generate_llm_response(self, prompt: str, json_mode: bool = False) -> str:
        """
        Sends a prompt to Groq and returns the text response.
        """
        if not self.api_key:
            return "Error: No API Key provided for LLM reasoning."
            
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional advertising creative strategist and technical prompt engineer."
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
                response_format={"type": "json_object"} if json_mode else None,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"[LLMClient] Error generating response: {e}")
            return f"Error: {str(e)}"
