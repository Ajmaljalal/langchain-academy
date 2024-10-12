from langgraph.graph import StateGraph, MessagesState, START
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode, tools_condition
import json
import requests

# Define our state
class EmailState(MessagesState):
    pass

# Tool definitions (these would call actual APIs in a real implementation)
@tool
def retrieve_emails() -> str:
    """Retrieves today's emails."""
    try:
        # Make an API call to the /todays_emails route
        response = requests.get('http://127.0.0.1:5000/todays_emails')
        response.raise_for_status()  # Raise an exception for bad status codes
        
        data = response.json()
        
        emails = data.get('emails', [])
        if not emails:
            return "You have no emails for today."
        
        email_summaries = []
        for email in emails:
            summary = f"From: {email['sender']}\n"
            summary += f"Subject: {email['subject']}\n"
            summary += f"Date: {email['date']}\n"
            summary += f"Snippet: {email['snippet']}\n"
            email_summaries.append(summary)
        
        return "Here are your emails for today:\n\n" + "\n---\n".join(email_summaries)
    
    except requests.RequestException as e:
        return f"Error retrieving emails: {str(e)}"

@tool
def send_email(recipient: str, subject: str, body: str) -> str:
    """Sends an email with the given recipient, subject, and body."""
    return f"Email sent to {recipient} with subject '{subject}'"

# Create LLM and bind tools
llm = ChatOpenAI()
llm_with_tools = llm.bind_tools([retrieve_emails, send_email])

# System message
sys_msg = SystemMessage(content="You are a helpful assistant tasked with managing emails. You can retrieve emails or send emails based on user requests.")

# Node definition
def assistant(state: EmailState):
    return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

# Create the graph
workflow = StateGraph(EmailState)

# Add nodes
workflow.add_node("assistant", assistant)
workflow.add_node("tools", ToolNode([retrieve_emails, send_email]))

# Add edges
workflow.add_edge(START, "assistant")
workflow.add_conditional_edges(
    "assistant",
    tools_condition,
)
workflow.add_edge("tools", "assistant")

# Compile the graph
email_manager_agent = workflow.compile()



