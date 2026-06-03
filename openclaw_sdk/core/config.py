"""OpenClaw client configuration."""

from pydantic import BaseModel, Field


class ClientConfig(BaseModel):
    """Configuration for connecting to the OpenClaw gateway."""

    gateway_ws_url: str = Field(default="ws://127.0.0.1:18789/gateway")
    api_key: str = Field(default="")
    mock_mode: bool = Field(default=False)
