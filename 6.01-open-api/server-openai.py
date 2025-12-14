from pydantic import BaseModel, Field
from strands import Agent
from strands.models.openai import OpenAIModel

class PersonInfo(BaseModel):
    """Extract person information from text."""
    name: str = Field(description="Full name of the person")
    age: int = Field(description="Age in years")
    occupation: str = Field(description="Job or profession")

model = OpenAIModel(
        client_args={
            "api_key": "token",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/"
        },
        model_id="gemini-2.5-flash",
        params={
            "max_tokens": 1000,
            "temperature": 0.7,
        }
)



agent = Agent(model=model)

result = agent.structured_output(
    PersonInfo,
    "John Smith is a 30-year-old software engineer working at a tech startup."
)

print(f"Name: {result.name}")      # "John Smith"
print(f"Age: {result.age}")        # 30
print(f"Job: {result.occupation}") # "software engineer"