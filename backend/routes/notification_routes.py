"""
Notification Routes for Student OD & Leave Approval System.
"""

from flask import Blueprint, request, jsonify
from routes.auth_routes import get_current_user
from services.notification_service import (
    get_user_notifications,
    get_unread_count,
    mark_notification_read,
    mark_all_notifications_read
)

notification_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@notification_bp.route('', methods=['GET'])
def list_notifications():
    current_user = get_current_user(request)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    limit = request.args.get('limit', 30, type=int)
    notifications = get_user_notifications(current_user['id'], limit)
    unread = get_unread_count(current_user['id'])

    return jsonify({
        'notifications': notifications,
        'unread_count': unread
    }), 200

@notification_bp.route('/unread-count', methods=['GET'])
def unread_count():
    current_user = get_current_user(request)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    unread = get_unread_count(current_user['id'])
    return jsonify({'unread_count': unread}), 200

@notification_bp.route('/<int:notification_id>/read', methods=['PUT'])
def mark_read(notification_id):
    current_user = get_current_user(request)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    success = mark_notification_read(notification_id, current_user['id'])
    return jsonify({'success': success, 'message': 'Marked as read'}), 200

@notification_bp.route('/read-all', methods=['PUT'])
def mark_all_read():
    current_user = get_current_user(request)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    count = mark_all_notifications_read(current_user['id'])
    return jsonify({'success': True, 'count': count, 'message': f'Marked {count} notifications as read.'}), 200
