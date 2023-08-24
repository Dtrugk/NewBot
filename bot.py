from langchain.embeddings.google_palm import GooglePalmEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.memory import ConversationBufferMemory, ConversationBufferWindowMemory
from langchain.chains import ConversationChain
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chat_models import ChatGooglePalm
from google.ai import generativelanguage as glm
from langchain import PromptTemplate, LLMChain
import google.generativeai as palm
import chainlit as cl


# Read API key from the text file
with open('api.sty', 'r') as file:
    api_key = file.read().strip()


memory = ConversationBufferMemory(k=2)

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

system_template = """Use the following pieces of context to answer the users question.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
ALWAYS return a "SOURCES" part in your answer.
The "SOURCES" part should be a reference to the source of the document from which you got your answer.

Example of your response should be:

```
The answer is foo
SOURCES: xyz
```

Begin!
----------------
{summaries}"""
messages = [
    SystemMessagePromptTemplate.from_template(system_template),
    HumanMessagePromptTemplate.from_template("{question}"),
]


palm.configure(api_key=api_key)


chat = ChatGooglePalm(
    model_name='models/chat-bison-001',
    temperature=0.5,
    top_k=2048,
    google_api_key=api_key
)


llm_chain = ConversationChain(
    llm=chat,
    verbose=True,
    memory=ConversationBufferWindowMemory(k=2)
)


# Sample template
template = """Question: {question}  
Answer: Let's think step by step"""


messages = [
    SystemMessagePromptTemplate.from_template(system_template),
    HumanMessagePromptTemplate.from_template("{question}"),
]
prompt = ChatPromptTemplate.from_messages(messages)
chain_type_kwargs = {"prompt": prompt}


# Create a function to generate AI response
async def generate_ai_response(input_text):

    res = await llm_chain.acall(input_text, callbacks=[cl.AsyncLangchainCallbackHandler()])

    if res != None:
        return str(res['response'])
    else:
        return 'No response available'

    
    # This is how to use the chatbot without LLM wrapper(low level module)
    # Do not delete this ---------------------------------------------------------
    # request = glm.GenerateMessageRequest(                                      |
    #     model='models/chat-bison-001',                                         |
    #     temperature=0.5,                                                       |
    #     top_k=2048,                                                            |
    #     prompt=glm.MessagePrompt(                                              |
    #         messages=[glm.Message(content=input_text)]))                       |
    #                                                                            |        
    # result = client.generate_message(request)                                  |
    # if result.candidates:                                                      |
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
        size="medium",
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


#----------------------------------------File Processing-----------------------------------#


# Define a separate function to handle the Q&A process after sending the file
async def handle_file_qna(file_name, texts, metadatas, embeddings, docsearch, chain, cb):
    user_input = await cl.AskUserMessage(content=f"Processing `{file_name}` done. You can now ask questions!").send()

    message = {
        'question': user_input.get('content'),  
    }

    res = await chain.acall(message, callbacks=[cb])

    input_data = {
        'user_input': user_input.get('content')
    }

    combined_output = {
        'answer': res['answer']
    }

    cb = cl.AsyncLangchainCallbackHandler(
        stream_final_answer=True, answer_prefix_tokens=["FINAL", "ANSWER"]
    )
    cb.answer_reached = True

    # Save the combined output to the memory
    memory.save_context(inputs=input_data, outputs=combined_output)

    answer = res["answer"]
    sources = res["sources"].strip()
    source_elements = []

    all_sources = [m["source"] for m in metadatas]

    if sources:
        found_sources = []

        # Add the sources to the message
        for source in sources.split(","):
            source_name = source.strip().replace(".", "")
            # Get the index of the source
            try:
                index = all_sources.index(source_name)
            except ValueError:
                continue
            text = texts[index]
            found_sources.append(source_name)
            # Create the text element referenced in the message
            source_elements.append(cl.Text(content=text, name=source_name))

        if found_sources:
            answer += f"\nSources: {', '.join(found_sources)}"
        else:
            answer += "\nNo sources found"

    if cb.has_streamed_final_answer:
        cb.final_stream.elements = source_elements
        await cb.final_stream.update()
    else:
        await cl.Message(content=answer, elements=source_elements).send()

@cl.action_callback("Send file") #sendFile
async def sendFile(m = memory):
    files = None

    # Wait for the user to upload a file
    while files == None:
        files = await cl.AskFileMessage(
            content="Please upload a text file to begin!", accept=["text/plain"]
        ).send()

    file = files[0]

    msg = cl.Message(content=f"Processing `{file.name}`...")
    await msg.send()

    # Decode the file
    text = file.content.decode("utf-8")

    # Split the text into chunks
    texts = text_splitter.split_text(text)

    # Create a metadata for each chunk
    metadatas = [{"source": f"{i}-pl"} for i in range(len(texts))]

    # Create a Chroma vector store
    embeddings = GooglePalmEmbeddings(google_api_key=api_key)
    docsearch = await cl.make_async(Chroma.from_texts)(
        texts, embeddings, metadatas=metadatas
    )
    # Create a chain that uses the Chroma vector store
    chain = RetrievalQAWithSourcesChain.from_chain_type(
        ChatGooglePalm(temperature=0, google_api_key=api_key),
        chain_type="stuff",
        retriever=docsearch.as_retriever(),
    )

    cb = cl.AsyncLangchainCallbackHandler(
        stream_final_answer=True, answer_prefix_tokens=["FINAL", "ANSWER"]
    )
    cb.answer_reached = True

    # Call the separate function to handle the Q&A process
    await handle_file_qna(file.name, texts, metadatas, embeddings, docsearch, chain, cb)



# Send and display messages on screen-----------------------------------Normal back-and-forth conversation
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
    result = response

    #This line is used when not using llm_chain
    await cl.Message(content=result,author='Tool 1',actions=SendFile).send()

