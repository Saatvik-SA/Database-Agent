# SQL_agent.py

import os
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.agent_toolkits import create_sql_agent
from dotenv import load_dotenv

load_dotenv()

def create_agent(db_path: str):  # <-- Now the parameter matches
    abs_path = os.path.abspath(db_path)
    db = SQLDatabase.from_uri(f"sqlite:///{abs_path}")  # <-- Correct usage

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)

    agent = create_sql_agent(
        llm=llm,
        db=db,
        verbose=True,
        agent_type="zero-shot-react-description",
        handle_parsing_errors=True,
    )

    return agent

def run_query(agent, full_query: str):
    return agent.run(full_query)
