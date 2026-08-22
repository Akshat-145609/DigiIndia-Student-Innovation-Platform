import time
import uuid
from api.providers.firebase import FirestoreRepository

followers_repo = FirestoreRepository("followers")
connections_repo = FirestoreRepository("connections")
requests_repo = FirestoreRepository("connectionRequests")
blocked_repo = FirestoreRepository("blockedUsers")
profiles_repo = FirestoreRepository("profiles")

class NetworkService:

    @staticmethod
    def follow_user(follower_uid: str, following_uid: str):
        if follower_uid == following_uid:
            raise Exception("Cannot follow yourself")
        
        doc_id = f"{follower_uid}_{following_uid}"
        followers_repo.set(doc_id, {
            "followerUID": follower_uid,
            "followingUID": following_uid,
            "createdAt": time.time()
        })
        return {"message": "Followed user successfully"}

    @staticmethod
    def unfollow_user(follower_uid: str, following_uid: str):
        doc_id = f"{follower_uid}_{following_uid}"
        followers_repo.delete(doc_id)
        return {"message": "Unfollowed user successfully"}

    @staticmethod
    def send_connection_request(sender_uid: str, receiver_uid: str, message: str = ""):
        if sender_uid == receiver_uid:
            raise Exception("Cannot send connection request to yourself")
        
        req_id = f"{sender_uid}_{receiver_uid}"
        # Auto approve & activate connection immediately
        requests_repo.set(req_id, {
            "requestId": req_id,
            "senderUID": sender_uid,
            "receiverUID": receiver_uid,
            "status": "accepted",
            "message": message,
            "createdAt": time.time()
        })

        conn_id = f"{min(sender_uid, receiver_uid)}_{max(sender_uid, receiver_uid)}"
        connections_repo.set(conn_id, {
            "studentA": sender_uid,
            "studentB": receiver_uid,
            "status": "active",
            "connectedAt": time.time()
        })

        return {"message": "Connection request sent and auto-approved!", "requestId": req_id}


    @staticmethod
    def respond_connection_request(receiver_uid: str, request_id: str, accept: bool):
        req = requests_repo.get(request_id)
        if not req or req.get("receiverUID") != receiver_uid:
            raise Exception("Connection request not found or unauthorized")
        
        if accept:
            req["status"] = "accepted"
            sender_uid = req.get("senderUID")
            conn_id = f"{min(sender_uid, receiver_uid)}_{max(sender_uid, receiver_uid)}"
            connections_repo.set(conn_id, {
                "studentA": sender_uid,
                "studentB": receiver_uid,
                "status": "active",
                "connectedAt": time.time()
            })
        else:
            req["status"] = "rejected"

        requests_repo.set(request_id, req)
        return {"message": f"Connection request {'accepted' if accept else 'rejected'}"}

    @staticmethod
    def withdraw_connection_request(sender_uid: str, receiver_uid: str):
        req_id = f"{sender_uid}_{receiver_uid}"
        requests_repo.delete(req_id)
        return {"message": "Connection request withdrawn successfully"}

    @staticmethod
    def disconnect_users(uid1: str, uid2: str):
        conn_id = f"{min(uid1, uid2)}_{max(uid1, uid2)}"
        connections_repo.delete(conn_id)
        # Also clean requests
        requests_repo.delete(f"{uid1}_{uid2}")
        requests_repo.delete(f"{uid2}_{uid1}")
        return {"message": "Disconnected successfully"}

    @staticmethod
    def get_connection_status(user_a: str, user_b: str):
        # 1. Check if connected
        conn_id = f"{min(user_a, user_b)}_{max(user_a, user_b)}"
        if connections_repo.get(conn_id):
            return {"connectState": "CONNECTED"}

        # 2. Check pending request sent by user_a to user_b
        req_sent = requests_repo.get(f"{user_a}_{user_b}")
        if req_sent and req_sent.get("status") == "pending":
            return {"connectState": "PENDING_SENT", "requestId": req_sent.get("requestId")}

        # 3. Check pending request received by user_a from user_b
        req_received = requests_repo.get(f"{user_b}_{user_a}")
        if req_received and req_received.get("status") == "pending":
            return {"connectState": "PENDING_RECEIVED", "requestId": req_received.get("requestId")}

        # 4. Check follow status
        is_following = bool(followers_repo.get(f"{user_a}_{user_b}"))

        return {
            "connectState": "NONE",
            "isFollowing": is_following
        }

    @staticmethod
    def list_network(uid: str):
        followers = followers_repo.query(filters=[("followingUID", "==", uid)])
        following = followers_repo.query(filters=[("followerUID", "==", uid)])
        connections = connections_repo.query(filters=[("studentA", "==", uid)]) + connections_repo.query(filters=[("studentB", "==", uid)])
        pending_requests = requests_repo.query(filters=[("receiverUID", "==", uid), ("status", "==", "pending")])

        detailed_pending = []
        for r in pending_requests:
            sender_profile = profiles_repo.get(r.get("senderUID")) or {}
            detailed_pending.append({
                "requestId": r.get("requestId"),
                "senderUID": r.get("senderUID"),
                "senderName": sender_profile.get("fullName", "Student"),
                "spn": sender_profile.get("spn", "--------"),
                "college": sender_profile.get("college", "University"),
                "avatarURL": sender_profile.get("avatarURL", ""),
                "message": r.get("message", "")
            })

        return {
            "followersCount": len(followers),
            "followingCount": len(following),
            "connectionsCount": len(connections),
            "pendingRequests": detailed_pending
        }


    @staticmethod
    def get_ai_connection_suggestions(uid: str):
        """AI Compatibility recommendation based on college & skills"""
        user_prof = profiles_repo.get(uid) or {}
        user_skills = set(user_prof.get("skills", []))
        user_college = user_prof.get("college", "")

        all_profiles = profiles_repo.query(limit=20)
        suggestions = []

        for prof in all_profiles:
            other_uid = prof.get("studentUID") or prof.get("id")
            if other_uid == uid:
                continue
            match_score = 50
            other_skills = set(prof.get("skills", []))
            common_skills = user_skills.intersection(other_skills)
            match_score += len(common_skills) * 10

            if user_college and user_college.lower() in prof.get("college", "").lower():
                match_score += 15

            suggestions.append({
                "profile": prof,
                "compatibilityScore": min(match_score, 99),
                "commonSkills": list(common_skills)
            })

        suggestions.sort(key=lambda x: x["compatibilityScore"], reverse=True)
        return suggestions[:6]
