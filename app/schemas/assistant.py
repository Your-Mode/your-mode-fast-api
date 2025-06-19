from pydantic import BaseModel


class MessageRequest(BaseModel):
    user_input: str

class MessageResponse(BaseModel):
    assistant_response: str
