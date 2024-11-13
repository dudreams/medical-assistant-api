import os, json, sqlite3

from dotenv import load_dotenv
from datetime import datetime
from typing_extensions import override
from typing import Any
from openai.types.beta.threads import Message
from openai import AssistantEventHandler, OpenAI
from fastapi import APIRouter, HTTPException

from tools.hospital_search import getHospBasisList
from database.db import save_thread, delete_thread, init_db


load_dotenv()
assistant_id = os.getenv("OPENAI_ASSISTANT_ID")
client = OpenAI()
router = APIRouter()
db = init_db()
INSTRUCTIONS = """
"""

class EventHandler(AssistantEventHandler):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.current_message = ""

    def on_event(self, event: Any) -> None:
        if event.event == 'thread.run.requires_action':
            run_id = event.data.id
            self.handle_requires_action(event.data, run_id)
    @override
    def on_thread_created(self, thread):
        print(f"Thread Created: {thread.id}")
    @override
    def on_run_created(self, run):
        print(f"Run Created: {run.id}")

    @override
    def on_error(self, error: Any) -> None:
        print(f"Error 발생: {error}")

    @override
    def on_tool_call_created(self, tool_call):
        print(f"Tool Call Created: {tool_call.function}")
        self.function_name = tool_call.function.name       
        self.tool_id = tool_call.id
        print({self.current_run.status})
        print(f"\nassistant > {tool_call.type} {self.function_name}\n")
        
    @override
    def on_run_step_delta(self, delta, snapshot):
        new_text = delta.text
        self.current_message += new_text

        thread_id = self.current_run.thread_id
        save_thread(thread_id, None, self.current_message)
        print('on_run_step_delta > ', self.current_message)
        
    @override
    def on_message_done(self, message: Message) -> None:
        save_thread(self.current_run.thread_id, None, message.content[0].text.value)

    @override
    def handle_requires_action(self, data):
        tool_outputs = []

        for tool in data.required_action.submit_tool_outputs.tool_calls:
            tool_arguments = json.loads(tool.function.arguments) if tool.function.arguments else {}
            if tool.function.name == "getHospBasisList":
                result = getHospBasisList(self.current_run.thread_id, **tool_arguments)


            if isinstance(result, dict):
                result = json.dumps(result, ensure_ascii=False)
            elif not isinstance(result, str):
                result = str(result)
            tool_outputs.append({"tool_call_id" : tool.id, "output": result})
        self.submit_tool_outputs(tool_outputs)
        
    @override
    def submit_tool_outputs(self, tool_outputs):
        with client.beta.threads.runs.submit_tool_outputs_stream(
            run_id=self.current_run.id,
            event_handler=EventHandler(self.db),
            tool_outputs=tool_outputs,
        ) as stream:
            for text in stream.text_deltas:
                print(f"{text}", end="", flush=True)





@router.post("/threads/")
async def create_thread():
    thread = client.beta.threads.create()
    return {"message": "Thread created successfully.", "thread_id": thread.id}

@router.post("/threads/{thread_id}/messages/")
async def send_message(thread_id: str, content: str):
    # 사용자의 메시지를 저장
    save_thread(thread_id, content, None)
    date_time = datetime.now().strftime(" (%Y-%m-%d %H:%M:%S %A)")
    response = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=f"{content}\n - 참고사항[현재 날짜와 날씨정보] : {date_time}",
    )
    with client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant_id,
        instructions=INSTRUCTIONS,
        event_handler=EventHandler(db),
    ) as stream:
        stream.until_done()
    return {"status": "Message created and executed", "response": response}


@router.delete("/threads/{thread_id}")
async def remove_thread(thread_id: str):
    client.beta.threads.delete(thread_id)
    delete_thread(thread_id)
    
    return {"message": "Thread deleted successfully."}

@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str):
    conn = sqlite3.connect('assistant.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_message, assistant_message FROM threads WHERE id = ?', (thread_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"thread_id": thread_id, "user_message": result[0], "assistant_message": result[1]}
    else:
        raise HTTPException(status_code=404, detail="Thread not found")