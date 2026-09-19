from __future__ import annotations

ACTIVE_FOLDER = "Active"
ARCHIVED_FOLDER = "Archived"
DEFAULT_NEW_CHAT_FOLDER = "Parking_Lot"
HIDDEN_FOLDER_PREFIX = "_"
MESSAGES_FOLDER_NAME = "messages"
STATE_FILE_NAME = "state.json"
LOCK_FILE_NAME = "write.lock"
CONSUMERS_FOLDER_NAME = "consumers"

STATE_SCHEMA_VERSION = "chatroom.state.v2"
MESSAGE_SCHEMA_VERSION = "chatroom.message.v2"
COMPILED_SCHEMA_VERSION = "chatroom.compiled.v2"
CURSOR_SCHEMA_VERSION = "chatroom.cursor.v1"
VERSION_PREP_CURSOR_SCHEMA_VERSION = "codex.version_prep_cursor.v1"
CONSUMER_STATE_SCHEMA_VERSION = "chatroom.consumer_state.v1"
STANDIN_SCHEMA_VERSION = "chatroom.standin.v1"
OPERATION_REPORT_SCHEMA_VERSION = "chatroom.operation_report.v1"
OPERATION_LOG_SCHEMA_VERSION = "chatroom.operation_log.v1"
VERSION_PREP_SCHEMA_VERSION = "codex_message_versions.v1"

MESSAGE_VERSION_MIN_LEVEL = 0
MESSAGE_VERSION_MAX_LEVEL = 9
DEFAULT_CONSUMER_THRESHOLD_CHARS = 180000

ALLOWED_MESSAGE_KINDS = {
    "message",
    "proposal",
    "review",
    "decision",
    "status",
    "system",
}

DEFAULT_LOCK_TIMEOUT_SECONDS = 300
