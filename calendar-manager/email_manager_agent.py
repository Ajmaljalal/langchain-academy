import logging
from langgraph.graph import StateGraph, MessagesState, START
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode, tools_condition
from prompts import get_email_management_prompt
import requests
from langgraph.checkpoint.memory import MemorySaver

logging.basicConfig(level=logging.DEBUG)

# Define our state
class EmailState(MessagesState):
    pass

# Tool definitions (these would call actual APIs in a real implementation)
@tool
def reply_to_email(thread_id: str, subject: str, sender: str, body: str, message_id: str) -> str:
    """Replies to an email with the given thread_id, subject, message_id, sender, and body."""
    reply_email_response = requests.post('http://127.0.0.1:5000/reply_email', json={'thread_id': thread_id, 'subject': subject, 'sender': sender, 'body': body, 'message_id': message_id})
    if reply_email_response.status_code == 200:
        return f"Email replied to {thread_id}"
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
            print(email)
            summary = f"From: {email['sender']}\n"
            summary += f"Subject: {email['subject']}\n"
            summary += f"Date: {email['date']}\n"
            summary += f"Snippet: {email['snippet']}\n"
            summary += f"Thread ID: {email['thread_id']}\n"
            summary += f"Message ID: {email['message_id']}\n"
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
llm_with_tools = llm.bind_tools([retrieve_emails, send_email, reply_to_email])

# System message
system_prompt = get_email_management_prompt()
sys_msg = SystemMessage(content=system_prompt)

# Node definition
def assistant(state: EmailState):
    return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

# Create the graph
workflow = StateGraph(EmailState)

# Add nodes
workflow.add_node("assistant", assistant)
workflow.add_node("tools", ToolNode([retrieve_emails, send_email, reply_to_email]))

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

        # for m in result['messages']:
        #     m.pretty_print()
        
        return result.get("messages", [])
    except Exception as e:
        logging.error(f"Exception during run_email_manager: {str(e)}")
        raise





