"""
Schemas package initialization
"""
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token, TokenData
from app.schemas.user_settings import (
    UserSettingsCreate, UserSettingsUpdate, UserSettingsResponse, OllamaModelInfo
)
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectStats, ProjectList,
    ProjectFeatures, FinancialConfig
)
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskValidate, TaskResponse, TaskWithProject, TaskList
)
from app.schemas.task_log import TaskLogCreate, TaskLogResponse, TaskLogList
from app.schemas.time_entry import (
    TimeEntryStart, TimeEntryStop, TimeEntryResponse,
    TimeEntryWithDetails, TimeEntryList, TimeEntrySummary
)
from app.schemas.ideation import (
    IdeationMessageCreate, IdeationMessageResponse, IdeationConversationResponse,
    IdeationStartRequest, IdeationStartResponse,
    IdeationSendMessageRequest, IdeationSendMessageResponse,
    IdeationStreamChunk, IdeationCompleteRequest, IdeationCompleteResponse,
    IdeationContextExtracted
)
from app.schemas.veille_result import (
    VeilleResultResponse, VeilleResultList,
    RadarPepite, RadarStats, RadarAffinage, RadarReport, VeilleRefineRequest, VeilleResultUpdate
)

__all__ = [
    # User
    "UserCreate", "UserLogin", "UserResponse", "Token", "TokenData",
    # UserSettings
    "UserSettingsCreate", "UserSettingsUpdate", "UserSettingsResponse", "OllamaModelInfo",
    # Project
    "ProjectCreate", "ProjectUpdate", "ProjectResponse", "ProjectStats", "ProjectList",
    "ProjectFeatures", "FinancialConfig",
    # Task
    "TaskCreate", "TaskUpdate", "TaskValidate", "TaskResponse", "TaskWithProject", "TaskList",
    # TaskLog
    "TaskLogCreate", "TaskLogResponse", "TaskLogList",
    # TimeEntry
    "TimeEntryStart", "TimeEntryStop", "TimeEntryResponse",
    "TimeEntryWithDetails", "TimeEntryList", "TimeEntrySummary",
    # Ideation
    "IdeationMessageCreate", "IdeationMessageResponse", "IdeationConversationResponse",
    "IdeationStartRequest", "IdeationStartResponse",
    "IdeationSendMessageRequest", "IdeationSendMessageResponse",
    "IdeationStreamChunk", "IdeationCompleteRequest", "IdeationCompleteResponse",
    "IdeationContextExtracted",
    # VeilleResult & Radar
    "VeilleResultResponse", "VeilleResultList",
    "RadarPepite", "RadarStats", "RadarAffinage", "RadarReport", "VeilleRefineRequest", "VeilleResultUpdate",
]
