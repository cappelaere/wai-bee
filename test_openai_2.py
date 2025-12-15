from openai import OpenAI
client = OpenAI()
models = client.models.list()
print([m.id for m in models.data])

response = client.responses.create(
    #model="gpt-5-nano",
    model="gpt-4",
    input="Write a one-sentence bedtime story about a unicorn."
)

print(response.output_text)