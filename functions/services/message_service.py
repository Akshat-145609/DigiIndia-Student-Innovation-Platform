import time
import uuid
from api.providers.firebase import FirestoreRepository

connections_repo = FirestoreRepository("connections")
rooms_repo = FirestoreRepository("conversationRooms")
messages_repo = FirestoreRepository("messages")

class MessageService:

    @classmethod
    def send_message(cls, sender_uid: str, room_id: str, message_text: str, message_type: str = "text", attachments: list = None):
        room = rooms_repo.get(room_id)
        if not room:
            # Try to auto-create room if participants are connected
            parts = room_id.split("_")
            if len(parts) == 2 and sender_uid in parts:
                receiver_uid = parts[0] if parts[1] == sender_uid else parts[1]
                # Check connection
                conn_id = f"{min(sender_uid, receiver_uid)}_{max(sender_uid, receiver_uid)}"
                conn = connections_repo.get(conn_id)
                if not conn or conn.get("status") != "active":
                    raise Exception("Permission Denied: You can only message students in your active connections network.")
                
                room = {
                    "roomId": room_id,
                    "participants": [sender_uid, receiver_uid],
                    "createdAt": time.time(),
                    "updatedAt": time.time()
                }
                rooms_repo.set(room_id, room)
            else:
                raise Exception("Conversation room not found")

        msg_id = str(uuid.uuid4())
        msg_doc = {
            "messageId": msg_id,
            "roomId": room_id,
            "senderUID": sender_uid,
            "messageType": message_type,
            "message": message_text,
            "attachments": attachments or [],
            "createdAt": time.time()
        }
        messages_repo.set(msg_id, msg_doc)

        room["lastMessage"] = message_text
        room["lastMessageTime"] = time.time()
        rooms_repo.set(room_id, room)

        return msg_doc

    @staticmethod
    def list_room_messages(user_uid: str, room_id: str):
        room = rooms_repo.get(room_id)
        if not room or user_uid not in room.get("participants", []):
            raise Exception("Room not found or unauthorized")

        msgs = messages_repo.query(filters=[("roomId", "==", room_id)], limit=100)
        msgs.sort(key=lambda x: x.get("createdAt", 0))
        return msgs

    @staticmethod
    def list_user_rooms(user_uid: str):
        # Query rooms containing user_uid
        all_rooms = rooms_repo.query(limit=50)
        user_rooms = [r for r in all_rooms if user_uid in r.get("participants", [])]
        user_rooms.sort(key=lambda x: x.get("lastMessageTime", 0), reverse=True)
        return user_rooms
