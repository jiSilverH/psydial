import argparse
import os
import pdb
import ast
import openai
from dotenv import load_dotenv
import time
import tqdm

parser = argparse.ArgumentParser()
parser.add_argument('--dir', type=str, default='../data_v4_filter')
parser.add_argument('--filter_profile', type=bool, default=False)
parser.add_argument('--filter_personality', type=bool, default=False)
parser.add_argument('--filter_style', type=bool, default=False)

args = parser.parse_args()

print('main dir:', args.dir)
# print(os.listdir(args.dir))
file_li = os.listdir(args.dir)
folder = args.dir

# load values from the .env file if it exists
load_dotenv()

openai.organization = "" # SET YOUR OPENAI API
openai.api_key = "" # SET YOUR OPENAI API

INSTRUCTIONS = """"""

TEMPERATURE = 0.5
MAX_TOKENS = 1024
FREQUENCY_PENALTY = 0
PRESENCE_PENALTY = 0.6
# limits how many questions we include in the prompt
MAX_CONTEXT_QUESTIONS = 10


def get_response(instructions, previous_questions_and_answers, new_question):
    """Get a response from ChatCompletion

    Args:
        instructions: The instructions for the chat bot - this determines how it will behave
        previous_questions_and_answers: Chat history
        new_question: The new question to ask the bot

    Returns:
        The response text
    """
    # build the messages
    messages = [
        { "role": "system", "content": instructions },
    ]
    # add the previous questions and answers
    for question, answer in previous_questions_and_answers[-MAX_CONTEXT_QUESTIONS:]:
        messages.append({ "role": "user", "content": question })
        messages.append({ "role": "assistant", "content": answer })
    # add the new question
    messages.append({ "role": "user", "content": new_question })

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        top_p=1,
        frequency_penalty=FREQUENCY_PENALTY,
        presence_penalty=PRESENCE_PENALTY,
    )
    return completion.choices[0].message.content


def get_moderation(question):
    """
    Check the question is safe to ask the model

    Parameters:
        question (str): The question to check

    Returns a list of errors if the question is not safe, otherwise returns None
    """

    errors = {
        "hate": "Content that expresses, incites, or promotes hate based on race, gender, ethnicity, religion, nationality, sexual orientation, disability status, or caste.",
        "hate/threatening": "Hateful content that also includes violence or serious harm towards the targeted group.",
        "self-harm": "Content that promotes, encourages, or depicts acts of self-harm, such as suicide, cutting, and eating disorders.",
        "sexual": "Content meant to arouse sexual excitement, such as the description of sexual activity, or that promotes sexual services (excluding sex education and wellness).",
        "sexual/minors": "Sexual content that includes an individual who is under 18 years old.",
        "violence": "Content that promotes or glorifies violence or celebrates the suffering or humiliation of others.",
        "violence/graphic": "Violent content that depicts death, violence, or serious physical injury in extreme graphic detail.",
    }
    response = openai.Moderation.create(input=question)
    if response.results[0].flagged:
        # get the categories that are flagged and generate a message
        result = [
            error
            for category, error in errors.items()
            if response.results[0].categories[category]
        ]
        return result
    return None

def defTag(true_mbti_tag):
    if true_mbti_tag == 'E':
        true_tag = 1
    elif true_mbti_tag == 'I':
        true_tag = 2

    return true_tag
    

FLAG = 0

for file in tqdm.tqdm(file_li):
    if not file.endswith('.txt'):
        continue

    file_path = f"{folder}/{file}"
    print(file_path)

    true_mbti_p1 = file.split('-')[0]
    true_mbti_p2 = file.split('-')[1].split('_')[0]

    true_tag_1 = defTag(true_mbti_p1)
    true_tag_2 = defTag(true_mbti_p2)

    with open(file_path, 'r') as f:
        # filter profile
        lines = [line.rstrip() for line in f]

    profile = [line for line in lines if line.startswith('<PROFILE>')][0].replace('<PROFILE>', '')
    # profile = lines[0].replace('<PROFILE>', '')

    # Get the index of DIALOGUE
    dial_idx = int([i for i in range(len(lines)) if lines[i].startswith('<DIALOGUE>')][0])
    tag_idx =  int([i for i in range(len(lines)) if lines[i].startswith('<TAG_1>')][0])
    dialogue = lines[dial_idx : tag_idx]
    dialogue = ''.join(dialogue)
    
    if 'None of the sentences' in profile:
        os.rename(file_path, f"{folder}/none_profile/{file}")
        print('None profile')
        continue

    if args.filter_profile == True:

        profile_prompt = f"This is Person1's profile information: {profile}. Does Person1 show given profile information? Select one - Ture or False."
        previous_questions_and_answers = []
        while True:
                try:
                    profile_response = get_response(INSTRUCTIONS, previous_questions_and_answers, profile_prompt)
                    time.sleep(5)
                except openai.error.APIError as e:
                    print(f"APIError! Retrying...")
                    time.sleep(30)
                    continue

                except openai.error.Timeout as e:
                    print(f"Timeout Error! Retrying...")
                    time.sleep(30)
                    continue
                break
        
        if profile_response == "False":
            # regenerate
            os.rename(file_path, f"{folder}/profile_false/{file}")
            print('profile false')
            continue

    if args.filter_personality == True:
        # lines = [line.rstrip() for line in f if '<TAG_1>' or '<TAG_2>' in line]
        p1_tag = int([line for line in lines if line.startswith('<TAG_1>')][0].replace('<TAG_1>', ''))
        p2_tag = int([line for line in lines if line.startswith('<TAG_2>')][0].replace('<TAG_2>', ''))

        if p2_tag != true_tag_2 or p1_tag != true_tag_1:
            os.rename(file_path, f"{folder}/personality_false/{file}")
            print('personality_false')
            continue
        # else:
        #     os.rename(file_path, f"{folder}/personality_true/{file}")

    if args.filter_style == True:
        # Korean informal speech detection
        style_prompt = f"Read the following dialogue and determine: Does this dialogue's conversation follow informal speech patterns commonly used in Korea? Select one - Ture or False."
        dialogue = f"{dialogue}"

        previous_questions_and_answers = []
        while True:
                try:
                    dialogue_response = get_response(INSTRUCTIONS, previous_questions_and_answers, style_prompt + dialogue)
                    # time.sleep(10)
                except openai.error.APIError as e:
                    print(f"APIError! Retrying...")
                    time.sleep(5)
                    continue

                except openai.error.Timeout as e:
                    print(f"Timeout Error! Retrying...")
                    time.sleep(30)
                    continue
                break
        if dialogue_response == 'False':
            os.rename(file_path, f"{folder}/style_false/{file}")
            print('style false')
            continue

    os.rename(file_path, f"{folder}/filtered/{file}")