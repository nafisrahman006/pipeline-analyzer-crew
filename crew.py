# from crewai import Crew, Process
# from langchain_openai import ChatOpenAI
# from agents.agents import create_agents
# from tasks.tasks import create_tasks
# from dotenv import load_dotenv
# import os

# load_dotenv()

# def build_crew() -> Crew:

#     llm = ChatOpenAI(
#         model="openai/gpt-oss-120b:free",
#         openai_api_key=os.getenv("OPENROUTER_API_KEY"),
#         openai_api_base="https://openrouter.ai/api/v1",
#         temperature=0.2,
#     )

#     agents = create_agents(llm)
#     tasks = create_tasks(agents)

#     crew = Crew(
#         agents=list(agents.values()),
#         tasks=tasks,
#         process=Process.sequential,
#         verbose=True,
#         memory=False,
#         max_rpm=10,
#     )

#     return crew


from crewai import Crew, Process, LLM
from agents.agents import create_agents
from tasks.tasks import create_tasks
from dotenv import load_dotenv
import os

load_dotenv()

def build_crew() -> Crew:

    llm = LLM(
        model="openrouter/openai/gpt-oss-120b:free",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=0.2,
    )

    agents = create_agents(llm)
    tasks = create_tasks(agents)

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=False,
        max_rpm=10,
    )

    return crew