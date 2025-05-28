import os
from openai import OpenAI


client = OpenAI(
    api_key = os.environ.get("OPENAI_API_KEY")
)



def createResponse(messages):

    completion = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages = [
            {"role":"developer", "content":"""You are an AI Article writer, your job is to fulfill the user's request of writing an article.


  You can only write articles about the following topics

  - Lifestyle
  - Health 
  - Fashion


  You must NEVER write articles or talk about topics related to tech, or science."""},
  *messages
        ]
    )

    return completion.choices[0].message.content




