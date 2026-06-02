"""CrewAI Structured Data Extraction for Veronica."""

import os
from .skills import AssistantContext, SkillResult

def is_extraction_request(message: str) -> bool:
    """Matcher for Extraction requests."""
    lowered = message.lower().strip()
    return lowered.startswith(("extract data", "parse receipt"))

def handle_extraction_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to extract JSON data using CrewAI and Pydantic."""
    try:
        from crewai import Agent, Task, Crew, Process
        from pydantic import BaseModel, Field
        from typing import List
    except ImportError:
        return SkillResult(True, "Extraction dependencies are missing. Please run: pip install crewai pydantic")

    # Define the Pydantic models for the structured output
    class ReceiptItem(BaseModel):
        name: str = Field(description="Name of the purchased item")
        price: float = Field(description="Price of the item")

    class ReceiptData(BaseModel):
        vendor: str = Field(description="Name of the store or vendor")
        date: str = Field(description="Date of the transaction")
        total_amount: float = Field(description="Total amount paid")
        items: List[ReceiptItem] = Field(description="List of individual items purchased")

    # Extract the raw text to parse
    lowered = message.lower().strip()
    raw_text = message
    if "from:" in lowered:
        parts = message.split("from:", 1)
        if len(parts) > 1:
            raw_text = parts[1].strip()
    elif lowered.startswith("extract data "):
        raw_text = message[len("extract data "):].strip()
    elif lowered.startswith("parse receipt "):
        raw_text = message[len("parse receipt "):].strip()

    if not raw_text:
        return SkillResult(True, "Please provide some text to extract data from. Example: 'extract data from: bought 2 coffees for 5 bucks at Starbucks today'")

    # Set up LLM
    llm = os.environ.get("GEMINI_MODEL", "gemini/gemini-1.5-flash")
    if "GEMINI_API_KEY" in os.environ:
        os.environ["LITELLM_API_KEY"] = os.environ["GEMINI_API_KEY"]
    else:
        llm = None

    try:
        # Define the Data Extractor Agent
        extractor_agent = Agent(
            role='Data Extraction Specialist',
            goal='Extract precise, structured data from raw text',
            backstory='You are an expert at reading messy text and converting it into perfect JSON structures.',
            verbose=False,
            llm=llm
        )

        # Define the Extraction Task
        extraction_task = Task(
            description=f'Read the following text and extract the receipt information: "{raw_text}"',
            expected_output='A JSON object matching the ReceiptData schema.',
            agent=extractor_agent,
            output_pydantic=ReceiptData  # This enforces the structured output!
        )

        # Assemble the Crew
        crew = Crew(
            agents=[extractor_agent],
            tasks=[extraction_task],
            process=Process.sequential,
            verbose=False
        )

        # Run the extraction
        result = crew.kickoff()
        
        # The result includes the pydantic output if it was successfully parsed
        pydantic_output = extraction_task.output.pydantic
        
        if pydantic_output:
            # Convert back to nicely formatted JSON string to show the user
            json_result = pydantic_output.model_dump_json(indent=2)
            return SkillResult(True, f"Extracted Data:\n```json\n{json_result}\n```")
        else:
            return SkillResult(True, f"Failed to extract structured data. Raw output:\n{result}")

    except Exception as e:
        return SkillResult(True, f"An error occurred during extraction: {str(e)}")
