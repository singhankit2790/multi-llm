from pydantic import BaseModel


class ProviderInfo(BaseModel):
    name: str
    display_name: str
    model: str
    available: bool


class ProvidersResponse(BaseModel):
    providers: list[ProviderInfo]
