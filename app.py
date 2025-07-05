from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import sqlite3
import os
from openai import OpenAI

app = FastAPI()

# connect to OpenRouter with your key
client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url="https://openrouter.ai/api/v1"
)

class AgentRequest(BaseModel):
    user: str
    task_type: str
    input_text: Optional[str] = None

def retrieve_prompt(user, task_type):
    conn = sqlite3.connect("tracy_memory.db")
    c = conn.cursor()
    c.execute("""
        SELECT prompt FROM prompts
        WHERE user=? AND task_type=?
        ORDER BY version DESC
        LIMIT 1
    """, (user, task_type))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "You are a helpful Tracy agent."

def log_response(user, task_type, response):
    conn = sqlite3.connect("tracy_memory.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO responses (user, task_type, response)
        VALUES (?, ?, ?)
    """, (user, task_type, response))
    conn.commit()
    conn.close()

@app.post("/prompt-agent")
async def prompt_agent(req: AgentRequest):
    prompt = retrieve_prompt(req.user, req.task_type)
    if req.input_text:
        prompt += f"\nUser input: {req.input_text}"

    completion = client.chat.completions.create(
        model="deepseek-ai/deepseek-llm-v3",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": req.input_text or ""}
        ],
        # you can add provider routing preferences here:
        extra_body={
            "provider": {
                "sort": "throughput",  # or "price" or "latency"
                "allow_fallbacks": True
            }
        },
        extra_headers={
            "HTTP-Referer": "https://tracy-prompt-agent.onrender.com",
            "X-Title": "Tracy Prompt Agent"
        }
    )

    result = completion.choices[0].message.content
    log_response(req.user, req.task_type, result)
    return {"result": result}
