#Code start from there 
from langchain.chat_models import ChatGooglePalm
from google.ai import generativelanguage as glm
from langchain import PromptTemplate, LLMChain
import google.generativeai as palm
import matplotlib.pyplot as plt
import chainlit as cl
import aiofiles
import json
import os


# Read API key from the text file
with open('api.sty', 'r') as file:
    api_key = file.read().strip()


#THis line is not use currently, i want the chat can remember context of 
#A previous conversation which i can't right now so i use module to have access to context in palm.chat() 
#Here's an example : 
# palm.configure(api_key=api)

# context = None

# while True:
#     user_input = input(f'[User]: ')
#     response = palm.chat(messages=user_input,
#                         context=context)
#     bot_response = response.last
#     context = bot_response

#     # Print user input in default color, and bot response in green
#     print(f'[Bot]: {bot_response}')
palm.configure(api_key=api_key)


# Configure the Google API key
client = glm.DiscussServiceClient(
    client_options={'api_key':api_key})

chat = ChatGooglePalm(
    model_name='models/chat-bison-001',
    temperature=0.5,
    top_k=2048,
    google_api_key=api_key
)


# Sample template
template = """Question: {question}  
Answer: Let's think step by step"""

# Promt Template 
prompt = PromptTemplate(template=template, input_variables=['question'])

# Initiate LLM(currently not use)
llm_chain = LLMChain(
    prompt=prompt, 
    llm=chat,
    verbose=True
)

context = None

# Create a function to generate AI response
async def generate_ai_response(input_text):
    global context

    response = palm.chat(messages=input_text, context=context)
    bot_response = response.last
    context = bot_response

    # Extract the text of the response
    response_text = bot_response 

    # Create a dictionary with the response text
    response_dict = {"text": response_text}

    # Serialize the dictionary as a JSON string
    serialized_response = json.dumps(response_dict)

    # Call the chain asynchronously (With langchain)
    # res = await llm_chain.acall(message, callbacks=[cl.AsyncLangchainCallbackHandler()])


    return serialized_response

    
    # This is how to use the chatbot without LLM wrapper
    # Do not delete this ---------------------------------------------------------
    # request = glm.GenerateMessageRequest(                                      |
    #     model='models/chat-bison-001',                                         |
    #     temperature=0.5,                                                       |
    #     top_k=2048,                                                            |
    #     prompt=glm.MessagePrompt(                                              |
    #         messages=[glm.Message(content=input_text)]))                       |
    #                                                                            |        
    # result = client.generate_message(request)                                  |
    # if result.candidates:  # Check if candidates list is not empty             |
    #     return str(result.candidates[0].content)                               |
    # else:                                                                      |
    #     return "No response available."                                        |
    #-----------------------------------------------------------------------------


#Create action button----- This can be used to create button to perform difference action such as upload picture , file , etc.
@cl.action_callback("Start Chat")
async def on_action(action):
    # Avatar
    await cl.Avatar(
        name="Tool 1",
        url="https://avatars.githubusercontent.com/u/128686189?s=400&u=a1d1553023f8ea0921fba0debbe92a8c5f840dd9&v=4",
    ).send()

    # Optionally remove the action button from the chatbot user interface
    await action.remove()


@cl.on_chat_start
async def start():
    #Avartar 
    await cl.Avatar(
        name="Tool 1",
        url="https://avatars.githubusercontent.com/u/128686189?s=400&u=a1d1553023f8ea0921fba0debbe92a8c5f840dd9&v=4",
    ).send()


    # Sending an action button within a chatbot message
    actions = [
        cl.Action(name="Start Chat", value="Start chat", description="Click me!")
    ]

    await cl.Message(content="Click this button to start chat",author='Tool 1', actions=actions).send()


@cl.action_callback("Send img")
async def sendIMG(action):
    await cl.Avatar(
    name="Tool 1",
    url="https://avatars.githubusercontent.com/u/128686189?s=400&u=a1d1553023f8ea0921fba0debbe92a8c5f840dd9&v=4",
    ).send()


    SendFile = [
        cl.Action(name="Send file",value='Send file' ,description="Click me to send a file"),
        cl.Action(name="Send img",value='Send image' ,description="Click me to send an image"),
    ]


    files = None


    # List of accepted image MIME types
    accepted_image_types = ["image/png", "image/jpeg", "image/svg+xml"]  # Add more if needed


    # Wait for the user to upload an image file
    while files is None:
        files = await cl.AskFileMessage(
            content="This feature is still underdevelopment",

          accept=accepted_image_types,
            author='Tool 1'
        ).send()


    # Transfer to byte (i have tried to print it out, its format as deximal)
    img_file = files[0] 


    # Sending an image with file content as bytes
    image = cl.Image(
        name=img_file.name,
        display="inline",
        size="large",
        content=img_file.content,  # Using the uploaded file's content directly
        actions=SendFile
    )


    element = [image]
    # result = await generate_ai_response(img_file.content)


    # Let the user know that the system is ready
    await cl.Message(
        content=f"{img_file.name} uploaded successfully!",
        elements= element,     
    ).send()


    # await cl.Message(
    #     content=result,
    #     actions=SendFile,
    #     author='Tool 1'
    # ).send()


#-----------------------------------------------------------------------------------


@cl.action_callback("Send file")
async def sendFile(action):
    await cl.Avatar(
        name="Tool 1",
        url="https://avatars.githubusercontent.com/u/128686189?s=400&u=a1d1553023f8ea0921fba0debbe92a8c5f840dd9&v=4",
    ).send()


    SendFile = [
        cl.Action(name="Send file",value='Send file' ,description="Click me to send a file"),
        cl.Action(name="Send img",value='Send image' ,description="Click me to send an image"),
    ]


    files = None


    accepted_mime_types = {
    "text/plain": [".txt", ".py"],
    "text/csv": [".csv"],
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
}


    # Wait for the user to upload a file
    while files == None:
        files = await cl.AskFileMessage(
            content="Please upload a text file to begin!", accept=accepted_mime_types
        ).send()


    # Decode the file only with text-based file , with binary based type , i need to handle it diffirently 
    text_file = files[0]
    # Handle different file types differently
    if text_file.type in {"text/plain":[".txt",".py"], "text/csv":[".csv"]}:
        text = text_file.content.decode("utf-8")
    elif text_file.type == "application/pdf":
        # Handle PDF content extraction here
        # text = extract_pdf_content(file.content)
        pass
    elif text_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        # Handle Excel content extraction here
        # text = extract_excel_content(file.content)
        pass
    else:
        await cl.Message(
        content="Unsupported file type",
        actions=SendFile
        ).send()


    message_content = f"Content of `{text_file.name}`:\n{text}"


    # Let the user know that the system is ready
    await cl.Message(
        content=f"`{text_file.name}` uploaded, it contains {len(text)} characters!\n{message_content}",
    ).send()


    response = await generate_ai_response(text)
    response_dict = json.loads(response)
    result = response_dict["text"]


    await cl.Message(
        content=result,
        author='Tool 1',
        actions=SendFile
    ).send()


# Send and display messages on screen----------------------------------
@cl.on_message
async def main(message: str):


    await cl.Avatar(
        name="Tool 1",
        url="https://avatars.githubusercontent.com/u/128686189?s=400&u=a1d1553023f8ea0921fba0debbe92a8c5f840dd9&v=4",
    ).send()


    SendFile = [
        cl.Action(name="Send file",value='Send file' ,description="Click me to send a file"),
        cl.Action(name="Send img",value='Send image' ,description="Click me to send an image"),
    ]


    response = await generate_ai_response(message)
    response_dict = json.loads(response)
    result = response_dict["text"]

    #This line is used when not using llm_chain
    await cl.Message(content=result,author='Tool 1',actions=SendFile).send()

    #THis line is used when using llm_chain 
    # await cl.Message(content=result['text'],author='Tool 1',actions=SendFile).send()


# Download file -------------------------------------------------------
# @cl.on_chat_start
# async def start():
#     elements = [
#         cl.File(
#             name="test.py",
#             path="./test.py",
#             display="inline",
#         ),
#     ]
#
#     await cl.Message(
#         content="This message has a file element", elements=elements
#     ).send()