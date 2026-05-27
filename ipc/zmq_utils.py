"""
ZMQ helpers with logging, timeouts, and error handling.
"""
import zmq
import logging
import json
from typing import Optional
from .protocol import Message

logger = logging.getLogger(__name__)


def create_context() -> zmq.Context:
    """Create ZMQ context with safe defaults."""
    ctx = zmq.Context()
    ctx.setsockopt(zmq.LINGER, 0)  # Don't block on close
    return ctx


def bind_rep_socket(ctx: zmq.Context, port: int, logger_name: str) -> zmq.Socket:
    """Bind REP socket for server-side."""
    socket = ctx.socket(zmq.REP)
    socket.bind(f"tcp://127.0.0.1:{port}")
    logger.info(f"[{logger_name}] ZMQ REP server bound to port {port}")
    return socket


def connect_req_socket(ctx: zmq.Context, port: int, timeout_ms: int = 3000,
                       logger_name: str = "ipc") -> zmq.Socket:
    """Connect REQ socket for client-side with timeout."""
    socket = ctx.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
    socket.setsockopt(zmq.SNDTIMEO, timeout_ms)
    socket.connect(f"tcp://127.0.0.1:{port}")
    logger.info(f"[{logger_name}] ZMQ REQ client connected to port {port}")
    return socket


def send_message(socket: zmq.Socket, msg: Message, logger_name: str) -> bool:
    """Send message with debug logging."""
    try:
        logger.debug(f"[{logger_name}] SEND: {msg.command} (id={msg.msg_id})")
        socket.send_string(msg.to_json())
        return True
    except zmq.Again:
        logger.error(f"[{logger_name}] SEND timeout: {msg.command}")
        return False
    except Exception as e:
        logger.error(f"[{logger_name}] SEND error: {e}", exc_info=True)
        return False


def recv_message(socket: zmq.Socket, logger_name: str) -> Optional[Message]:
    """Receive message with debug logging. Returns None on timeout."""
    try:
        raw = socket.recv_string(flags=zmq.NOBLOCK)
        msg = Message.from_json(raw)
        logger.debug(f"[{logger_name}] RECV: {msg.command} (id={msg.msg_id})")
        return msg
    except zmq.Again:
        return None
    except json.JSONDecodeError as e:
        logger.error(f"[{logger_name}] RECV JSON error: {e}")
        return None
    except Exception as e:
        logger.error(f"[{logger_name}] RECV error: {e}", exc_info=True)
        return None


def poll_socket(socket: zmq.Socket, timeout_ms: int = 100) -> bool:
    """Non-blocking poll for incoming messages."""
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)
    socks = dict(poller.poll(timeout_ms))
    return socket in socks and socks[socket] == zmq.POLLIN