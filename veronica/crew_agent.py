"""CrewAI orchestration for Veronica."""

import os
from .skills import AssistantContext, SkillResult

def is_crew_request(message: str) -> bool:
    """Matcher for CrewAI requests."""
    lowered = message.lower().strip()
    return lowered.startswith(("assemble a crew", "crewai", "research crew", "run crew"))

def handle_crew_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to execute a CrewAI process."""
    try:
        from crewai import Agent, Task, Crew, Process
    except ImportError:
        return SkillResult(True, "CrewAI is not installed. Please run: pip install crewai crewai-tools")

    # Extract the task description from the command
    lowered = message.lower().strip()
    task_desc = message
    for prefix in ["assemble a crew to ", "assemble a crew ", "crewai ", "research crew ", "run crew "]:
        if lowered.startswith(prefix):
            # Keep original case for the task
            task_desc = message[len(prefix):].strip()
            break
            
    if not task_desc:
        return SkillResult(True, "What would you like the crew to do? For example: 'assemble a crew to research AI news'")

    # Set up LLM if user specified Gemini
    llm = os.environ.get("GEMINI_MODEL", "gemini/gemini-1.5-flash")
    if "GEMINI_API_KEY" in os.environ:
        os.environ["LITELLM_API_KEY"] = os.environ["GEMINI_API_KEY"]
    else:
        # Default to whatever environment they have (usually OpenAI)
        llm = None

    try:
        # Define Agents
        researcher = Agent(
            role='Senior Data Researcher',
            goal=f'Uncover cutting-edge developments and detailed information regarding: {task_desc}',
            backstory="You are a seasoned researcher with a knack for uncovering the most relevant and accurate information. You present findings clearly.",
            verbose=False,
            allow_delegation=False,
            llm=llm
        )

        writer = Agent(
            role='Technical Writer & Summarizer',
            goal='Synthesize the research findings into a clear, concise, and structured report.',
            backstory="You are a meticulous writer known for turning complex data into easy-to-understand summaries.",
            verbose=False,
            allow_delegation=False,
            llm=llm
        )

        # Define Tasks
        research_task = Task(
            description=f'Conduct thorough research on: {task_desc}. Gather key facts, recent updates, and comprehensive details.',
            expected_output='A detailed list of findings, facts, and relevant information.',
            agent=researcher
        )

        writing_task = Task(
            description='Review the research findings and write a final, comprehensive summary report. Format it nicely using markdown.',
            expected_output='A fully fledged markdown report summarizing the findings.',
            agent=writer
        )

        # Assemble the Crew
        crew = Crew(
            agents=[researcher, writer],
            tasks=[research_task, writing_task],
            process=Process.sequential,
            verbose=False
        )

        # Run the Crew
        result = crew.kickoff()
        
        # Result from crew kickoff is a CrewOutput object in newer crewai versions, cast to string
        final_output = str(result)
        
        return SkillResult(True, f"Crew Execution Complete:\n\n{final_output}")
        
    except Exception as e:
        return SkillResult(True, f"An error occurred while running the crew: {str(e)}")
