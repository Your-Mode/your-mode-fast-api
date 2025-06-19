import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def send_message_to_assistant(user_input: str) -> str:
    assistant_id = "asst_iWTKo91WQwkODYWlP6JZfIbx"

    thread = client.beta.threads.create()
    client.beta.threads.messages.create(thread_id=thread.id, role="user", content=user_input)

    run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)

    # polling until run status is 'completed'
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == "completed":
            break

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    return messages.data[0].content[0].text.value