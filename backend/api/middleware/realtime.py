"""
Real-time Collaboration Middleware
====================================
Provides real-time features using Socket.io.

Features:
- Presence (who's online)
- Live cursor tracking
- Real-time dashboard updates
- Collaborative report editing
"""

import logging
from typing import Dict, Set
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import Socket.io
try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    logger.warning("Socket.io not installed. Install with: pip install python-socketio")


if SOCKETIO_AVAILABLE:
    sio = socketio.AsyncServer(
        async_mode='asgi',
        cors_allowed_origins="*",
        logger=True,
        engineio_logger=True,
    )
    app = socketio.ASGIApp(sio)
    
    # Presence tracking
    connected_users: Dict[str, Set[str]] = {}
    user_rooms: Dict[str, str] = {}
    
    @sio.event
    async def connect(sid, environ, auth):
        user_id = auth.get('user_id') if auth else None
        if user_id:
            if user_id not in connected_users:
                connected_users[user_id] = set()
            connected_users[user_id].add(sid)
            logger.info(f"User {user_id} connected (sid: {sid})")
            await sio.emit('user_joined', {
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            })
    
    @sio.event
    async def disconnect(sid):
        for user_id, sids in list(connected_users.items()):
            if sid in sids:
                sids.remove(sid)
                if not sids:
                    del connected_users[user_id]
                logger.info(f"User {user_id} disconnected (sid: {sid})")
                await sio.emit('user_left', {
                    'user_id': user_id,
                    'timestamp': datetime.now().isoformat()
                })
                break
    
    @sio.event
    async def join_room(sid, data):
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        if room_id and user_id:
            await sio.enter_room(sid, room_id)
            user_rooms[sid] = room_id
            await sio.emit('user_joined_room', {
                'room_id': room_id,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }, room=room_id, skip_sid=sid)
    
    @sio.event
    async def leave_room(sid, data):
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        if room_id:
            await sio.leave_room(sid, room_id)
            await sio.emit('user_left_room', {
                'room_id': room_id,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat()
            }, room=room_id)
    
    @sio.event
    async def cursor_move(sid, data):
        room_id = user_rooms.get(sid)
        if room_id:
            await sio.emit('cursor_update', {
                'user_id': data.get('user_id'),
                'x': data.get('x'),
                'y': data.get('y'),
                'timestamp': datetime.now().isoformat()
            }, room=room_id, skip_sid=sid)
    
    @sio.event
    async def report_edit(sid, data):
        room_id = user_rooms.get(sid)
        if room_id:
            await sio.emit('report_updated', {
                'report_id': data.get('report_id'),
                'changes': data.get('changes'),
                'user_id': data.get('user_id'),
                'timestamp': datetime.now().isoformat()
            }, room=room_id, skip_sid=sid)
    
    @sio.event
    async def dashboard_update(sid, data):
        room_id = user_rooms.get(sid)
        if room_id:
            await sio.emit('dashboard_updated', {
                'widget_id': data.get('widget_id'),
                'changes': data.get('changes'),
                'user_id': data.get('user_id'),
                'timestamp': datetime.now().isoformat()
            }, room=room_id, skip_sid=sid)
    
    def get_online_users() -> Dict[str, int]:
        return {user_id: len(sids) for user_id, sids in connected_users.items()}
    
    def is_user_online(user_id: str) -> bool:
        return user_id in connected_users and len(connected_users[user_id]) > 0

else:
    class StubSio:
        def emit(self, *args, **kwargs):
            logger.debug("Socket.io not available — emit suppressed")
        def enter_room(self, *args, **kwargs):
            logger.debug("Socket.io not available — enter_room suppressed")
        def leave_room(self, *args, **kwargs):
            logger.debug("Socket.io not available — leave_room suppressed")
    
    sio = StubSio()
    app = None
    connected_users = {}
    user_rooms = {}
    
    def get_online_users() -> Dict[str, int]:
        return {}
    
    def is_user_online(user_id: str) -> bool:
        return False