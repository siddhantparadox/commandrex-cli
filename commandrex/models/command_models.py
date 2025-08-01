from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ComponentType(str, Enum):
    COMMAND = "command"
    SUBCOMMAND = "subcommand"
    FLAG = "flag"
    ARGUMENT = "argument"
    OPERATOR = "operator"
    PIPE = "pipe"
    REDIRECTION = "redirection"
    OTHER = "other"


class CommandComponent(BaseModel):
    part: str = Field(..., description="The literal token or segment of the command")
    description: str = Field(..., description="Explanation of what this part does")
    type: ComponentType = Field(
        default=ComponentType.OTHER, description="Categorized type for the component"
    )


class CommandOption(BaseModel):
    command: str
    description: str
    components: List[CommandComponent] = Field(default_factory=list)
    # Minimal safety fields kept for compatibility; not rendered in simple mode
    safety_level: str = Field(default="unknown")
    safety_assessment: Optional[Dict[str, Any]] = None
