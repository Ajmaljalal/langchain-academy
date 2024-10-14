import logging
from langgraph.graph import StateGraph, MessagesState, START
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode, tools_condition
import json
import requests
from langgraph.checkpoint.memory import MemorySaver

logging.basicConfig(level=logging.DEBUG)

# Define our state
class EmailState(MessagesState):
    pass

# Tool definitions (these would call actual APIs in a real implementation)
@tool
def reply_to_email(recipient: str, subject: str, body: str) -> str:
    """Replies to an email with the given recipient, subject, and body."""
    reply_email_response = requests.post('http://127.0.0.1:5000/reply_email', json={'to': recipient, 'subject': subject, 'body': body})
    if reply_email_response.status_code == 200:
        return f"Email replied to {recipient}"
    else:
        return f"Failed to reply to email: {reply_email_response.text}"

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
    send_email_response = requests.post('http://127.0.0.1:5000/send_email', json={'to': recipient, 'subject': subject, 'body': body})
    if send_email_response.status_code == 200:
        return f"Email sent to {recipient} with subject '{subject}'"
    else:
        return f"Failed to send email: {send_email_response.text}"

# Create LLM and bind tools
llm = ChatOpenAI(model="gpt-4o")
llm_with_tools = llm.bind_tools([retrieve_emails, send_email])

# System message
system_prompt = """
You are a helpful assistant managing emails, responsible for retrieving, analyzing, summarizing, and sending emails based on user requests. Your role includes presenting information in a clear, concise, and smooth narrative.

### Retrieving Emails:
- Summarize the email content in one brief, clear paragraph.
- Present the email details in a complete, narrative style.
- Mention if it's a reply and exclude irrelevant content like signatures, footers, or non-essential text.
- Remove special characters or formatting such as HTML.

### Sending Emails:
- Verify the recipient’s email address is correct.
- Draft the subject and body of the email as requested.
- Confirm with the user before sending, if needed.

### Notes:
- Ensure clarity, completeness, and a conversational flow.
- Address any technical issues with retrieving or sending emails and notify the user.
- Maintain privacy and security standards at all times.
"""
sys_msg = SystemMessage(content=system_prompt)

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

memory = MemorySaver()

# Compile the graph
email_manager_agent = workflow.compile(checkpointer=memory)

def run_email_manager(user_input: str, thread_id: str):
    if not user_input or not isinstance(user_input, str):
        raise ValueError("user_input must be a non-empty string.")
    
    config = {"configurable": {"thread_id": thread_id}}
    messages = [HumanMessage(content=user_input)]
    
    try:
        result = email_manager_agent.invoke({"messages": messages}, config)

        for m in result['messages']:
            m.pretty_print()
        

        return result.get("messages", [])
    except Exception as e:
        logging.error(f"Exception during run_email_manager: {str(e)}")
        raise





