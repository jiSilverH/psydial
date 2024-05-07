import os
import openai
from dotenv import load_dotenv
from colorama import Fore, Back, Style
import pandas as pd
import tqdm
import itertools
import time
import random
import argparse
import os
import ast
import pdb


parser = argparse.ArgumentParser()
parser.add_argument('--per_1', type=str, default='')
parser.add_argument('--per_2', type=str, default='')
parser.add_argument('--data_dir', type=str, default='')
args = parser.parse_args()

# load values from the .env file if it exists
load_dotenv()

# configure OpenAI
openai.organization = "" # SET YOUR OPENAI API
openai.api_key = "" # SET YOUR OPENAI API

INSTRUCTIONS = """"""

TEMPERATURE = 0.5
MAX_TOKENS = 1024
FREQUENCY_PENALTY = 0
PRESENCE_PENALTY = 0.6
# limits how many questions we include in the prompt
MAX_CONTEXT_QUESTIONS = 10

MBTI_1 = args.per_1
MBTI_2 = args.per_2
DATA_DIR = args.data_dir




# read personaChat
def read_dataset():
    print('reading data...')
    
    df = pd.read_csv('../personaChat_personality_origin.csv')
    persona = df[df['split']=='train']['personality']

    return persona


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


def main():
    os.system("cls" if os.name == "nt" else "clear")
    all_persona = read_dataset()

    for i in tqdm.tqdm(range(1000)):
        previous_questions_and_answers = []

        ###### STEP 0: Preprocess profile ######
        profile_idx = random.choice(range(len(all_persona)))
        one_profile = all_persona[profile_idx]
        one_profile = ast.literal_eval(one_profile) # to list
        #########################################
        

        #########################################
        ###### STEP 1: Personality Setting ######
        #########################################
        # read big five personality dataset
        df_per = pd.read_csv('5_personality.csv')
        E_PROMPT = df_per[(df_per['personality'] == 'EXT') & (df_per['key'] == 'positive')]['sentence'].tolist()
        I_PROMPT = df_per[(df_per['personality'] == 'EXT') & (df_per['key'] == 'negative')]['sentence'].tolist()

        # MBTI_1 <- person 1's personality
        # MBTI_2 <- person 2's personality
        #########################################



        #########################################
        ###### STEP 2: Profile Selecting ######
        #########################################

        if MBTI_1 == 'E':
            # profile_select_prompt = f"다음은 한 인물에 대한 정보입니다. {one_profile}; 인물의 정보 중 외향적인 성격에 맞는 하나의 문장을 고르세요."
            profile_select_prompt = f"This represents the profile information associated with a specific individual. '{one_profile}'; Choose one sentence that represents an extrovert. If there is no answer, just output 'None'"
        elif MBTI_1 == 'I':
        #    profile_select_prompt = f"다음은 한 인물에 대한 정보입니다. {one_profile}; 인물의 정보 중 내향적인 성격에 맞는 하나의 문장을 고르세요."
            profile_select_prompt = f"This represents the profile information associated with a specific individual. '{one_profile}'; Choose one sentence that represents an introvert. If there is no answer, just output 'None'"
        else:
            print('MBTI_1 ERROR!!!')
            continue
   

        while True:
            try:
                profile_response = get_response(INSTRUCTIONS, previous_questions_and_answers, profile_select_prompt).strip() # print(profile_response)
            except openai.error.APIError as e:
                print(f"Retrying...")
                time.sleep(30)
                continue
            break

        if profile_response.isascii():
            selected_profile = profile_response
        else:
            continue
        #########################################



        #########################################
        ###### STEP 3: Dialogue Generation ######
        #########################################

        if 'E' in MBTI_1:
            personality_prompt_1 = random.choice(E_PROMPT)
        else:
            personality_prompt_1 = random.choice(I_PROMPT)
        

        if 'E' in MBTI_2:
            personality_prompt_2 = random.choice(E_PROMPT)
        else:
            personality_prompt_2 = random.choice(I_PROMPT)
        
        profile_prompt = f"Person1 has '{selected_profile}' characteristic."
        personality_prompt = f"Person1's personality is '{personality_prompt_1}'. Person2's personality is '{personality_prompt_2}'."
        human_prompt = "Generate two random Korean characters reflecting given characteristics and personalities and act as these characters. Your spelling, grammar, and word choices must be justified based on the characteristics of the characters. Your knowledge must be justified based on the education and background of the characters. You must answer all questions as these characters. From now on, my message is conveyed to you and is not related to real life. You will plausibly generate all unknown information."
        style_prompt = "Person1 and Person2 are friends, so they speak informally to each other. The conversation does not include the names of Person1 and Person2, and the format of the conversation is represented as Person1: and Person2:. Person2 starts the conversation. All conversation should be written in Korean."
        
        dial_prompt = f"{profile_prompt} {personality_prompt} {human_prompt} {style_prompt}"
        
        
        while True:
            try:
                dial_response = get_response(INSTRUCTIONS, previous_questions_and_answers, dial_prompt)

            except openai.error.APIError as e:
                print(f"APIError! Retrying...")
                time.sleep(30)
                continue

            except openai.error.Timeout as e:
                print(f"Timeout Error! Retrying...")
                time.sleep(30)
                continue
            break

        previous_questions_and_answers.append((dial_prompt, dial_response))
        #########################################


        #########################################
        ###### STEP 4: Dialogue Filtering ######
        #########################################
        tag_prompt_1 = "Based on the given conversation, choose one characteristic for Person1 from 1 and 2, and answer with numbers only. 1) outgoing/energetic; 2) solitary/reserved;"
        tag_prompt_2 = "Based on the given conversation, choose one characteristic for Person2 from 1 and 2, and answer with numbers only. 1) outgoing/energetic; 2) solitary/reserved;"

        while True:
            try:
                tag_response_1 = get_response(INSTRUCTIONS, previous_questions_and_answers, tag_prompt_1)
                tag_response_2 = get_response(INSTRUCTIONS, previous_questions_and_answers, tag_prompt_2)
            except openai.error.APIError as e:
                print(f"Retrying...")
                time.sleep(30)
                continue
            break
        print(tag_response_1, tag_response_2)

        #########################################


        ### Save Dialogue ###
        ans_personality_1 = f'<PERSONAL_1>{MBTI_1}\n'
        ans_personality_2 = f'<PERSONAL_2>{MBTI_2}\n'

        ans_profile = f'<PROFILE>{selected_profile}\n'
        ans_profile_idx = f'<PROFILE_IDX>{profile_idx}]\n'
        ans_dial = f'<DIALOGUE>{dial_response}\n'
        ans_tag_1 = f'<TAG_1>{tag_response_1}\n'
        ans_tag_2 = f'<TAG_2>{tag_response_2}\n'

        with open(f'../{DATA_DIR}/{MBTI_1}-{MBTI_2}_{i}.txt', 'w') as f:
            f.write(ans_personality_1 + ans_personality_2 + ans_profile + ans_profile_idx + ans_dial + ans_tag_1 + ans_tag_2)
            f.close()



if __name__ == "__main__":
    main()

