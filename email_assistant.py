import os, re, json, time
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from llama_cpp_agent.llm_agent import LlamaCppAgent
from llama_cpp_agent.messages_formatter import MessagesFormatterType
from llama_cpp_agent.providers.llama_cpp_endpoint_provider import LlamaCppEndpointSettings
from llama_cpp_agent.structured_output_agent import StructuredOutputAgent

os.environ['OPENAI_BASE_URL'] = 'http://localhost:3003/v1'
os.environ['OPENAI_API_KEY'] = 'sk-xxx'

main_model = LlamaCppEndpointSettings(
    completions_endpoint_url="http://127.0.0.1:3003/completion"
)
structured_output_agent = StructuredOutputAgent(main_model, debug_output=False)

EMAIL_DB="""
Steve Jobs: sjobs@apple.com 
"""
def find_email(query: str) -> str:
    s = EMAIL_DB+"\n[INST] "+query+" [/INST]"
    try:
        output = llm.invoke(input=s,stop=stop).content
    except Exception as e:
        error_str = f"Exception: {e}"
        output = error_str
    return output

def real_time_web_search(query):
    print(f"TODO real_time_web_search: {query}")
    
def web_search(query: str) -> str:
    result = real_time_web_search(query)
    s = str(result) + "[INST] "+query+" [/INST]"
    try:
        output = llm.invoke(input=s,stop=stop).content
    except Exception as e:
        error_str = f"Exception: {e}"
        output = error_str
    return output

MYCLENDAR="""
Michael's weekly meetings:
Mon 9:30-10:30pm PST w/ Steve and Tim (AI)
"""
def read_calendar(query: str) -> str:
    return MYCLENDAR

class Email(BaseModel):
    to_addr: str = Field(..., description="the recipient email.")
    subject: str = Field(..., description="the email subject.")
    body: str = Field(..., description="the email body.")

def send_email(llm_json_str: str) -> str:
    try:
        patch_json_content = json.loads(llm_json_str)
        to_addr = patch_json_content["to_addr"]
        subject = patch_json_content["subject"]
        body = patch_json_content["body"]

    except Exception as e:
        error_str = f"Exception: {e}"
        # todo: use structured_output_agent
        results = structured_output_agent.create_object(Email, llm_json_str)
        to_addr = results.to_addr
        subject = results.subject
        body = results.body

    print(f"To: {to_addr}\n{subject}\n==============================\n{body}\n=================================\n")
    # TODO: user approval
    return "email sent successfully"

from string import Template
tao_template=Template("""
My name is Michael Humor. You are my email assistant, Monica. You have access to the following tools:
                 
    FindEmail: "Find the email addresses of my contacts."
    ReadCalendar: "Read my current calendar."
    SendEmail: "Send email tool. Input is a json object with {"to_addr: str, "subject": str, "body": str"}."
    WebSearch: "Search the web to answer questions. Input should be a search query."

To craft an email, you should use FindEmail to find correct email addresses (to_addr) of my contacts.

Use the following format:
    
    Thought: you should always think about what to do
    Action: the action to take, should be one of [FindEmail, ReadCalendar, SendEmail, WebSearch]
    Action Input: the input to the action
    Observation: the result of the action
    ... (this Thought/Action/Action Input/Observation can repeat N times)
    Thought: I have now completed the task 
    Done: the final message to the task
    
Always generate Action and Action Input. Missing them will produce an error!
    
    Begin!               
    
    Question:
    $question

    Thought:
""")

llm = ChatOpenAI(model="gpt-4")
stop = ['Observation:', 'Observation ']
def invoke_llm(input:str) -> str:
    try:
        s = "[INST] "+input+" [/INST]"
        output = llm.invoke(input=s,stop=stop).content
    except Exception as e:
        output = f"Exception: {e}"

    return output

MAX_ITERATION = 10
def llm_do_task(question: str):
    prompt=str(tao_template.substitute(question=question))
    iteration = 0
    while True:
        iteration =iteration+1
        if iteration>MAX_ITERATION:
            break
        llm_output = invoke_llm(prompt)
        regex = (
                r"Action\s*\d*\s*:[\s]*(.*?)[\s]*Action\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)"
            )
        action_match = re.search(regex, llm_output, re.DOTALL)
        if action_match:
            action = action_match.group(1).strip()
            action_input = action_match.group(2)
            tool_input = action_input.strip("\n")
            if llm_output.startswith("Thought:"):
                prompt = prompt+llm_output[8:]
            else:
                prompt = prompt+llm_output

            print(f"------- tool: {action} input: {tool_input}\n")

            if action=="WebSearch":
                tool_output = web_search(tool_input)
            elif action=="ReadCalendar":
                tool_output = read_calendar(tool_input)
            elif action=="SendEmail":
                tool_output = send_email(tool_input)
            elif action=="FindEmail":
                tool_output = find_email(tool_input)
            else:
                tool_output = "Error: Action "+f"'{action}' is not a valid!"

            print(f"------- tool_output ------- \n{tool_output}\n")

        elif 'Done:' in llm_output:
            print(f"\n\n{llm_output}")
            return
        else:  
            print(f"Error: wrong LLM response\n{llm_output}\n")

        prompt = prompt+"\nObservation: "+str(tool_output)+"\n"

print(f"I'm your email assistant, Monica.")
while True:
    try:
        user_input = input("Please enter a new task: ")
        tic = time.time()
        llm_do_task(user_input)
        latency = time.time() - tic
        print(f"\nLatency: {latency:.3f}s")
    except KeyboardInterrupt:
            print("\nExiting.\n")
            break
