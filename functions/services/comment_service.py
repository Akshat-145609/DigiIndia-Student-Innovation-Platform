import time
import uuid
from api.providers.firebase import FirestoreRepository

comments_repo = FirestoreRepository("comments")
profiles_repo = FirestoreRepository("profiles")

class CommentService:

    @classmethod
    def get_project_comments(cls, project_id: str):
        raw_comments = comments_repo.query(filters=[("projectId", "==", project_id)], limit=200)
        # Sort chronologically
        sorted_comments = sorted(raw_comments, key=lambda x: x.get("createdAt", 0))

        # Build hierarchical comment tree
        comment_map = {}
        tree = []

        for c in sorted_comments:
            c["replies"] = []
            comment_map[c["id"]] = c

        for c in sorted_comments:
            parent_id = c.get("parentCommentId")
            if parent_id and parent_id in comment_map:
                comment_map[parent_id]["replies"].append(c)
            else:
                tree.append(c)

        return tree

    @classmethod
    def add_comment(cls, student_uid: str, project_id: str, text: str, parent_comment_id: str = None):
        if not text or not text.strip():
            raise Exception("Comment text cannot be empty")

        profile = profiles_repo.get(student_uid) or {}
        author_name = profile.get("fullName", "Student Member")
        author_avatar = profile.get("avatarURL", "")

        comment_id = str(uuid.uuid4())
        comment_doc = {
            "id": comment_id,
            "projectId": project_id,
            "studentUID": student_uid,
            "authorName": author_name,
            "authorAvatar": author_avatar,
            "parentCommentId": parent_comment_id or "",
            "text": text.strip(),
            "likesCount": 0,
            "createdAt": time.time()
        }

        comments_repo.set(comment_id, comment_doc)
        return comment_doc

    @classmethod
    def like_comment(cls, comment_id: str):
        comment = comments_repo.get(comment_id)
        if not comment:
            raise Exception("Comment not found")

        comment["likesCount"] = comment.get("likesCount", 0) + 1
        comments_repo.set(comment_id, comment)
        return {"id": comment_id, "likesCount": comment["likesCount"]}
