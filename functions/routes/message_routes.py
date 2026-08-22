from fastapi import APIRouter, HTTPException, Depends
from models.schemas import MessageSendSchema
from services.message_service import MessageService
from middleware.auth_middleware import require_authenticated_user

router = APIRouter(prefix="/messages", tags=["Messaging"])

@router.post("")
def send_message(schema: MessageSendSchema, user: dict = Depends(require_authenticated_user)):
    try:
        return MessageService.send_message(user["uid"], schema.roomId, schema.message, schema.messageType, schema.attachments)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/rooms")
def list_my_rooms(user: dict = Depends(require_authenticated_user)):
    return MessageService.list_user_rooms(user["uid"])

@router.get("/room/{room_id}")
def list_messages(room_id: str, user: dict = Depends(require_authenticated_user)):
    try:
        return MessageService.list_room_messages(user["uid"], room_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
