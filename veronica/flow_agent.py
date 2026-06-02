"""CrewAI Flow orchestration for Veronica."""

import os
import re
from .skills import AssistantContext, SkillResult

def is_flow_request(message: str) -> bool:
    """Matcher for Flow requests."""
    lowered = message.lower().strip()
    return lowered.startswith(("run analysis flow", "start flow", "market flow", "flow"))

def handle_flow_request(message: str, context: AssistantContext) -> SkillResult:
    """Handler to execute a CrewAI Flow."""
    try:
        from crewai.flow.flow import Flow, listen, start, router, or_
        from crewai import Crew, Agent, Task, Process
        from pydantic import BaseModel
    except ImportError:
        return SkillResult(True, "CrewAI Flow dependencies are missing. Please run: pip install crewai crewai-tools pydantic")

    # Extract sector if provided (e.g. "run analysis flow for the tech sector")
    lowered = message.lower().strip()
    sector = "technology"
    if "for" in lowered:
        parts = lowered.split("for", 1)
        if len(parts) > 1:
            sector = parts[1].strip()

    # Set up LLM if user specified Gemini
    llm = os.environ.get("GEMINI_MODEL", "gemini/gemini-1.5-flash")
    if "GEMINI_API_KEY" in os.environ:
        os.environ["LITELLM_API_KEY"] = os.environ["GEMINI_API_KEY"]
    else:
        llm = None

    class MarketState(BaseModel):
        sentiment: str = "neutral"
        confidence: float = 0.0
        recommendations: list[str] = []
        final_strategy: str = ""

    class AdvancedAnalysisFlow(Flow[MarketState]):
        @start()
        def fetch_market_data(self):
            # Simulate fetching data
            self.state.sentiment = "analyzing"
            return {"sector": sector, "timeframe": "1W"}

        @listen(fetch_market_data)
        def analyze_with_crew(self, market_data):
            analyst = Agent(
                role="Senior Market Analyst",
                goal="Conduct deep market analysis with expert insight",
                backstory="You're a veteran analyst known for identifying subtle market patterns.",
                verbose=False,
                llm=llm
            )
            researcher = Agent(
                role="Data Researcher",
                goal="Gather and validate supporting market data",
                backstory="You excel at finding and correlating multiple data sources.",
                verbose=False,
                llm=llm
            )

            analysis_task = Task(
                description="Analyze {sector} sector data for the past {timeframe}. You must end your analysis with a final numerical confidence score between 0.0 and 1.0, e.g., 'Confidence: 0.85'.",
                expected_output="Detailed market analysis with a confidence score.",
                agent=analyst
            )
            
            analysis_crew = Crew(
                agents=[analyst, researcher],
                tasks=[analysis_task],
                process=Process.sequential,
                verbose=False
            )
            
            result = analysis_crew.kickoff(inputs=market_data)
            output_str = str(result)
            
            # Extract confidence score
            match = re.search(r"confidence:\s*(0\.\d+|1\.0)", output_str, re.IGNORECASE)
            if match:
                self.state.confidence = float(match.group(1))
            else:
                self.state.confidence = 0.6  # default
                
            return output_str

        @router(analyze_with_crew)
        def determine_next_steps(self):
            if self.state.confidence > 0.8:
                return "high_confidence"
            return "low_confidence"

        @listen("high_confidence")
        def execute_strategy(self):
            strategy_crew = Crew(
                agents=[Agent(role="Strategy Expert", goal="Develop optimal market strategy", backstory="Strategic thinker.", llm=llm)],
                tasks=[Task(description=f"Create detailed step-by-step strategy for the {sector} sector.", expected_output="Step-by-step action plan")]
            )
            result = strategy_crew.kickoff()
            self.state.final_strategy = str(result)
            return self.state.final_strategy

        @listen("low_confidence")
        def request_additional_analysis(self):
            self.state.recommendations.append("Gather more data before proceeding.")
            self.state.final_strategy = f"Confidence was too low ({self.state.confidence}). Recommended to gather more data."
            return self.state.final_strategy

    try:
        flow = AdvancedAnalysisFlow()
        flow.kickoff()
        return SkillResult(True, f"Flow Execution Complete for {sector}!\n\nConfidence: {flow.state.confidence}\n\nOutcome:\n{flow.state.final_strategy}")
    except Exception as e:
        return SkillResult(True, f"An error occurred while running the flow: {str(e)}")
