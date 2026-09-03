"""
In-app notification service for Student OD & Leave Approval System.
"""

from database import get_db_connection

def create_notification(user_id: int, title: str, message: str, link: str = None) -> int:
    """Create a new notification for a specific user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO notifications (user_id, title, message, link, is_read)
        VALUES (?, ?, ?, ?, 0)
    """, (user_id, title, message, link))
    notif_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return notif_id

def get_user_notifications(user_id: int, limit: int = 30):
    """Retrieve notifications for a user, sorted by newest first."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, title, message, link, is_read, created_at
        FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_unread_count(user_id: int) -> int:
    """Get count of unread notifications for badge."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def mark_notification_read(notification_id: int, user_id: int) -> bool:
    """Mark a single notification as read."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notification_id, user_id))
    affected = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return affected

def mark_all_notifications_read(user_id: int) -> int:
    """Mark all notifications as read for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0", (user_id,))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count
