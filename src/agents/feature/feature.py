import json
import os
import re
import time
from typing import List, Dict, Union

from jinja2 import Environment, BaseLoader

from src.agents.internal_monologue import InternalMonologue
from src.agents.planner import Planner
from src.agents.researcher import Researcher
from src.bert.sentence import SentenceBert
from src.browser.search import BingSearch, GoogleSearch, DuckDuckGoSearch
from src.config import Config
from src.llm import LLM
from src.memory import KnowledgeBase
from src.project import ProjectManager
from src.socket_instance import emit_agent
from src.state import AgentState
from src.utils import shorten_path
from src.logger import Logger
from src.agents.formatter import Formatter
from src.agents.prq import Prq
from src.memory.rag import scrape_website

PROMPT = open("src/agents/feature/prompt.jinja2", "r").read().strip()


class Feature:
    def __init__(self, base_model: str, search_engine: str):
        config = Config()
        self.project_dir = config.get_projects_dir()
        self.shorten_path = shorten_path("")
        self.llm = LLM(model_id=base_model)
        self.project_manager = ProjectManager()
        self.prq = Prq(base_model=base_model)
        self.planner = Planner(base_model=base_model)
        self.agent_state = AgentState()
        self.internal_monologue = InternalMonologue(base_model=base_model)
        self.researcher = Researcher(base_model=base_model)
        self.agent_state = AgentState()
        self.logger = Logger()
        self.formatter = Formatter(base_model=base_model)
        self.engine = search_engine
        self.scrape_website = scrape_website

        """
        Accumulate contextual keywords from chained prompts of all preparation agents
        """
        self.collected_context_keywords = []

    def render(
            self,
            file_code: str,
            file_name: str,
            gitdiff: str,
            plans: str | dict,
            systemdesign: list[str],
            summarydiff: str,
            system_os: str

    ) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(
            file_code=file_code,
            file_name=file_name,
            gitdiff=gitdiff,
            plans=plans,
            systemdesign=systemdesign,
            summarydiff=summarydiff,
            system_os=system_os
        )

    def validate_response(self, response: str) -> Union[List[Dict[str, str]], bool]:
        response = response.strip()

        # Replace '~~~' at the beginning and end of the response
        if response.startswith("~~~"):
            response = response.replace("~~~", "", 1)
        if response.endswith("~~~"):
            response = response[::-1].replace("~~~"[::-1], "", 1)[::-1]

        response = response.strip()

        #if "~~~" in response:
         #   return False

        result = []
        current_file = None
        current_code = []
        code_block = False

        for line in response.split("\n"):
            if line.startswith("File:"):
                if current_file and current_code:
                    result.append({"file": os.path.normpath(current_file), "code": "\n".join(current_code)})
                if "`" in line:
                    current_file = line.split("`")[1].strip()
                elif line.startswith("File:") and line.endswith(":") and "`" not in line:
                    current_file = line.split(":")[1].strip()
                else:
                    print("Error: Line does not contain a backtick (`).")
                    return False
                current_code = []
                code_block = False
            elif line.startswith("```"):
                code_block = not code_block
            else:
                current_code.append(line)

        if current_file and current_code:
            result.append({"file": os.path.normpath(current_file), "code": "\n".join(current_code)})

        return result

    def save_code_to_project(self, response: List[Dict[str, str]], project_name: str):
        project_name = project_name.lower().replace(" ", "-")
        project_dir = os.path.join(self.project_dir, project_name)

        # Check if the project directory already exists
        if not os.path.exists(project_dir):
            os.makedirs(project_dir, exist_ok=True)

        for file in response:
            # No need to redefine file_path for each iteration
            file_path = os.path.join(project_dir, file['file'])
            # Remove any duplicate path separators
            # file_path1 = re.sub(r'\\+', '/', file_path)
            # file_path2 = shorten_path(file_path1)
            file_path2 = os.path.normpath(file_path)
            if not os.path.isfile(file_path2):
                # file_subpath = os.path.normpath(file['file'])
                createdfile = "<b>Creating New file...</b>:" + file['file']
                self.project_manager.add_message_from_devika(project_name, createdfile)
            # Create the directory structure if it doesn't exist
            os.makedirs(os.path.dirname(file_path2), exist_ok=True)
            with open(file_path2, "w+", encoding="utf-8") as f:
                f.write(file["code"])

        return os.path.join(project_dir, project_name)

    def get_project_path(self, project_name: str):
        project_name = project_name.lower().replace(" ", "-")
        return f"{self.project_dir}/{project_name}"

    def response_to_markdown_prompt(self, response: List[Dict[str, str]]) -> str:
        response = "\n".join([f"File: `{file['file']}`:\n```\n{file['code']}\n```" for file in response])
        return f"~~~\n{response}\n~~~"

    def emulate_code_writing(self, code_set: list, project_name: str):
        files = []
        for file in code_set:
            filename = file["file"]
            code = file["code"]
            new_state = AgentState().new_state()
            new_state["internal_monologue"] = "Writing code..."
            new_state["terminal_session"]["title"] = f"Editing {filename}"
            new_state["terminal_session"]["command"] = f"vim {filename}"
            new_state["terminal_session"]["output"] = code
            files.append({
                "file": filename,
                "code": code,
            })
            AgentState().add_to_current_state(project_name, new_state)
            # time.sleep(1)
        emit_agent("code", {
            "files": files,
            "from": "feature"
        })

    def execute(
            self,
            file_code: str,
            file_name: str,
            gitdiff: str,
            plans: str | dict,
            systemdesign: list[str],
            summarydiff: str,
            project_name: str,
            system_os: str
    ) -> list[dict[str, str]] | bool:
        # this has to have other agent "search_results, plans"

        # summary_code = self.reviewer.execute(code_markdown,project_name)
        prompt = self.render(file_code, file_name, gitdiff, plans, systemdesign, summarydiff, system_os)
        response = self.llm.inference(prompt, project_name)

        valid_response = self.validate_response(response)

        while not valid_response:
            print("Invalid response from the model feauture, trying again...")
            return self.execute(file_code, file_name, gitdiff, plans, systemdesign, summarydiff, project_name,
                                system_os)

        self.emulate_code_writing(valid_response, project_name)

        return valid_response

    def search_queries_faiss(self, queries: list, project_name: str) -> dict:
        results = {}

        knowledge_base = KnowledgeBase()

        for query in queries:
            query = query.strip().lower()

            knowledge = knowledge_base.get_knowledge(query)
            if knowledge:
                if query in results:
                    # If the same query is encountered again, combine the results
                    results[query] += self.formatter.execute(knowledge, query, project_name)
                    self.logger.info(f"got the search results for : {query}")
                    knowledge_base.add_knowledge(query, results[query])
                else:
                    results[query] = self.formatter.execute(knowledge, query, project_name)
                    self.logger.info(f"got the search results for : {query}")
                    knowledge_base.add_knowledge(query, results[query])

            # self.logger.info(f"got the search results for : {query}")
            # knowledge_base.add_knowledge(query, results[query])
        return results

    def search_queries(self, queries: list, project_name: str) -> dict:

        results = {}

        knowledge_base = KnowledgeBase()

        if self.engine == "bing":
            web_search = BingSearch()
        elif self.engine == "google":
            web_search = GoogleSearch()
        else:
            web_search = DuckDuckGoSearch()

        self.logger.info(f"\nSearch Engine :: {self.engine}")
        i = 1
        for query in queries:
            query = query.strip().lower()

            # knowledge = knowledge_base.get_knowledge(query)
            # if knowledge:
            #   if query in results:
            #       # If the same query is encountered again, combine the results
            #       results[query] += self.formatter.execute(knowledge,query, project_name)
            #       self.logger.info(f"got the search results for : {query}")
            #       knowledge_base.add_knowledge(query, results[query])
            #    else:
            #        results[query] = self.formatter.execute(knowledge,query, project_name)
            #       self.logger.info(f"got the search results for : {query}")
            #       knowledge_base.add_knowledge(query, results[query])

            web_search.search(query)
            link = web_search.get_first_link()
            if link:
                print("\nLink :: ", link, "\n")
                linkadress = "<b>Link" + str(i) + ":" + link
                self.project_manager.add_message_from_devika(project_name, linkadress)
                i += 1
            if not link:
                continue
            data = self.scrape_website(link)

            if query in results:
                # If the same query is encountered again, combine the results
                results[query] += self.formatter.execute(data,query, project_name)
                self.logger.info(f"got the search results for : {query}")
                # knowledge_base.add_knowledge(query, results[query])
            else:
                results[query] = self.formatter.execute(data,query, project_name)
                self.logger.info(f"got the search results for : {query}")
                # knowledge_base.add_knowledge(query, results[query])

            # self.logger.info(f"got the search results for : {query}")
            # knowledge_base.add_knowledge(query, results[query])
        return results

    def execute4memory(self, conversation: list, project_name_from_user: str = None) -> tuple:
        """
        Agentic flow of execution
        """
        if project_name_from_user:
            responsefeature = "<mark>Agent Feature: </mark><br>" + conversation[-1]
            self.project_manager.add_message_from_user(project_name_from_user, responsefeature)
            self.agent_state.set_agent_active(project_name_from_user, True)
        productrq = self.prq.execute(conversation[-1], project_name_from_user)
        productrqresponse = "<mark>Agent Product Requirement</mark>:<br>" + productrq
        self.project_manager.add_message_from_devika(project_name_from_user, productrqresponse)
        plan = self.planner.execute(conversation[-1], productrq, project_name_from_user)
        print("\nplan :: ", plan, "\n")

        planner_response = self.planner.parse_response(plan)
        project_name = planner_response["project"]
        reply = planner_response["reply"]
        focus = planner_response["focus"]
        plans = planner_response["plans"]
        summary = planner_response["summary"]
        print("plans inside execute4memory")
        print(plans)
        print("                            ")
        if project_name_from_user:
            project_name = project_name_from_user
        else:
            project_name = planner_response["project"]
            self.project_manager.create_project(project_name)
            self.project_manager.add_message_from_user(project_name, conversation[-1])
        responseplanner = "<mark>Agent planner: </mark><br>" + reply
        self.project_manager.add_message_from_devika(project_name, responseplanner)
        self.project_manager.add_message_from_devika(
            project_name, json.dumps(plans, indent=4)
        )
        # self.project_manager.add_message_from_devika(project_name, f"In summary: {summary}")

        self.update_contextual_keywords(focus)
        print("\ncontext_keywords :: ", self.collected_context_keywords, "\n")
        context_keywords_html = "<mark>Context Keywords:</mark> "
        for keyword in self.collected_context_keywords:
            context_keywords_html += f"<span style='border:1px solid; padding:2px; margin:2px;'>{keyword}</span>"
        self.project_manager.add_message_from_devika(project_name, context_keywords_html)

        internal_monologue = self.internal_monologue.execute(
            current_prompt=plan, project_name=project_name
        )
        print("\ninternal_monologue :: ", internal_monologue, "\n")

        new_state = self.agent_state.new_state()
        new_state["internal_monologue"] = internal_monologue
        self.agent_state.add_to_current_state(project_name, new_state)

        research = self.researcher.execute(
            plan, self.collected_context_keywords, project_name=project_name
        )
        print("\nresearch :: ", research, "\n")

        queries = research["queries"]
        # queries_combined = ", ".join(queries)
        # ask_user = research["ask_user"]



        #self.agent_state.set_agent_active(project_name, True)

        if queries and len(queries) > 0:
            responseresearcher = "<mark>Agent Researcher: </mark><br>I am browsing the web to research the following queries:<br>"
            for i, query in enumerate(queries, start=1):
                responseresearcher += f"<b>Query {i}</b> : <u>{query}</u><br>"
            self.project_manager.add_message_from_devika(project_name, responseresearcher)
            search_results = self.search_queries(queries, project_name)
        else:
            self.project_manager.add_message_from_devika(
                project_name, "<mark>Agent Researcher: </mark><br>I think I can proceed without searching the web."
            )
            search_results = {}

        return search_results, plans

    def execute4memory1(self, conversation: list,selectedfiles, project_name_from_user: str = None) -> tuple:
        """
        Agentic flow of execution
        """
        if project_name_from_user:
            responsefeature = "<mark>Agent Feature: </mark><br>" + conversation[-1]
            self.project_manager.add_message_from_user(project_name_from_user, responsefeature)
            self.agent_state.set_agent_active(project_name_from_user, True)
        productrq = self.prq.execute1(conversation[-1], selectedfiles, project_name_from_user)
        productrqresponse = "<mark>Agent Product Requirement</mark>:<br>" + productrq
        self.project_manager.add_message_from_devika(project_name_from_user, productrqresponse)
        plan = self.planner.execute1(conversation[-1], productrq,selectedfiles, project_name_from_user)
        print("\nplan :: ", plan, "\n")

        planner_response = self.planner.parse_response(plan)
        project_name = planner_response["project"]
        reply = planner_response["reply"]
        focus = planner_response["focus"]
        plans = planner_response["plans"]
        summary = planner_response["summary"]
        print("plans inside execute4memory")
        print(plans)
        print("                            ")
        if project_name_from_user:
            project_name = project_name_from_user
        else:
            project_name = planner_response["project"]
            self.project_manager.create_project(project_name)
            self.project_manager.add_message_from_user(project_name, conversation[-1])
        responseplanner = "<mark>Agent planner: </mark><br>" + reply
        self.project_manager.add_message_from_devika(project_name, responseplanner)
        self.project_manager.add_message_from_devika(
            project_name, json.dumps(plans, indent=4)
        )
        # self.project_manager.add_message_from_devika(project_name, f"In summary: {summary}")

        self.update_contextual_keywords(focus)
        print("\ncontext_keywords :: ", self.collected_context_keywords, "\n")
        context_keywords_html = "<mark>Context Keywords:</mark> "
        for keyword in self.collected_context_keywords:
            context_keywords_html += f"<span style='border:1px solid; padding:2px; margin:2px;'>{keyword}</span>"
        self.project_manager.add_message_from_devika(project_name, context_keywords_html)

        internal_monologue = self.internal_monologue.execute(
            current_prompt=plan, project_name=project_name
        )
        print("\ninternal_monologue :: ", internal_monologue, "\n")

        new_state = self.agent_state.new_state()
        new_state["internal_monologue"] = internal_monologue
        self.agent_state.add_to_current_state(project_name, new_state)

        research = self.researcher.execute(
            plan, self.collected_context_keywords, project_name=project_name
        )
        print("\nresearch :: ", research, "\n")

        queries = research["queries"]
        queries_combined = ", ".join(queries)
        ask_user = research["ask_user"]



        # self.agent_state.set_agent_active(project_name, True)

        if queries and len(queries) > 0:
            responseresearcher = "<mark>Agent Researcher: </mark><br>I am browsing the web to research the following queries:<br>"
            for i, query in enumerate(queries, start=1):
                responseresearcher += f"<b>Query {i}</b> : <u>{query}</u><br>"
            self.project_manager.add_message_from_devika(project_name, responseresearcher)
            search_results = self.search_queries(queries, project_name)
        else:
            self.project_manager.add_message_from_devika(
                project_name, "<mark>Agent Researcher: </mark><br>I think I can proceed without searching the web."
            )
            search_results = {}

        return search_results, plans

    def update_contextual_keywords(self, sentence: str):
        """
        Update the context keywords with the latest sentence/prompt
        """
        keywords = SentenceBert(sentence).extract_keywords()
        for keyword in keywords:
            self.collected_context_keywords.append(keyword[0])

        return self.collected_context_keywords
