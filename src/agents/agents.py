import base64
import os
from pathlib import Path
from typing import Dict
from .planner import Planner
from .researcher import Researcher
from .formatter import Formatter
from .coder import Coder
from .action import Action
from .internal_monologue import InternalMonologue
from .answer import Answer
from .runner import Runner
from .incdev import Incdev
from .feature import Feature
from .patcher import Patcher
from .reporter import Reporter
from .decision import Decision
from .prq import Prq
from ..experts.chemistry import Chemistry
from .svgmaker import Svgmaker

from src.services import git
from src.agents.drawuml import Drawuml

from src.agents.reviewer import Codereviewfile
from src.project import ProjectManager
from src.state import AgentState
from src.logger import Logger

from src.bert.sentence import SentenceBert
from src.memory import KnowledgeBase
from src.browser.search import BingSearch, GoogleSearch, DuckDuckGoSearch
from src.browser import Browser
from src.browser import start_interaction
from src.filesystem import ReadCode
from src.services import Netlify, Git
from src.documenter.pdf import PDF
from src.config import Config
from src.memory.rag import scrape_website
import json
import time
import platform

import tiktoken
import asyncio

from src.socket_instance import emit_agent


class Agents:
    """A class to manage Atlas's agents and coordinate their actions."""

    def __init__(self, base_model: str, search_engine: str, browser: Browser = None):
        self.base_model = base_model
        config = Config()
        self.scrape_website = scrape_website
        self.project_dir = config.get_projects_dir()
        if not base_model:
            raise ValueError("base_model is required")

        self.logger = Logger()

        """
        Accumulate contextual keywords from chained prompts of all preparation agents
        """
        self.collected_context_keywords = []

        """
        Agents
        """
        self.svgmaker = Svgmaker(base_model=base_model)
        self.chemistry = Chemistry(base_model=base_model)
        self.prq = Prq(base_model=base_model)
        self.planner = Planner(base_model=base_model)
        self.researcher = Researcher(base_model=base_model)
        self.formatter = Formatter(base_model=base_model)
        self.coder = Coder(base_model=base_model)
        self.action = Action(base_model=base_model)
        self.internal_monologue = InternalMonologue(base_model=base_model)
        self.answer = Answer(base_model=base_model)
        self.runner = Runner(base_model=base_model)
        self.incdev = Incdev(base_model=base_model, search_engine=search_engine)
        self.feature = Feature(base_model=base_model, search_engine=search_engine)
        self.patcher = Patcher(base_model=base_model)
        self.reporter = Reporter(base_model=base_model)
        self.decision = Decision(base_model=base_model)
        self.codereviewfile = Codereviewfile(base_model=base_model)
        self.drawuml = Drawuml(base_model=base_model)
        self.git = None
        self.project_manager = ProjectManager()
        self.agent_state = AgentState()
        self.engine = search_engine
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    async def open_page(self, project_name, url):
        browser = await Browser().start()

        await browser.go_to(url)
        _, raw = await browser.screenshot(project_name)
        data = await browser.extract_text()
        await browser.close()

        return browser, raw, data

    def wSearchAndFaissToggle(self, project_name: str, focus: str, plans: list, wsearch: bool = False,
                              searchFaiss: bool = False):
        if not wsearch and not searchFaiss:
            search_results = {}
            return search_results

        self.update_contextual_keywords(focus)
        print("\ncontext_keywords :: ", self.collected_context_keywords, "\n")

        context_keywords_html = "<mark>Context Keywords:</mark> "
        for keyword in self.collected_context_keywords:
            context_keywords_html += f"<span style='border:1px solid; padding:2px; margin:2px;'>{keyword}</span>"
        self.project_manager.add_message_from_devika(project_name, context_keywords_html)

        research = self.researcher.execute(
            plans, self.collected_context_keywords, project_name=project_name
        )
        print("\nresearch :: ", research, "\n")

        queries = research["queries"]
        queries_combined = ", ".join(queries)
        ask_user = research["ask_user"]

        if (queries and len(queries) > 0) or ask_user != "":
            responseresearcher = "<mark>Agent Researcher: </mark><br>I am browsing the web to research the following queries:<br>"
            for i, query in enumerate(queries, start=1):
                responseresearcher += f"<b>Query {i}</b> : <u>{query}</u><br>"
            self.project_manager.add_message_from_devika(project_name, responseresearcher)
        else:
            self.project_manager.add_message_from_devika(
                project_name, "<mark>Agent Researcher: </mark><br>I think I can proceed without searching the web."
            )

        if queries and len(queries) > 0:
            search_results = self.search_queries(queries, project_name, wsearch, searchFaiss)
            print(search_results)
        else:
            search_results = {}

        return search_results

    def search_queries(self, queries: list, project_name: str, wsearch: bool = False,
                       searchFaiss: bool = False) -> dict:
        results = {}

        if wsearch and not searchFaiss:
            # Web search only
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
                    results[query] += self.formatter.execute(data, query, project_name)
                    self.logger.info(f"got the search results for : {query}")
                else:
                    results[query] = self.formatter.execute(data, query, project_name)
                    self.logger.info(f"got the search results for : {query}")

            return results

        elif wsearch and searchFaiss:
            # Web search and Faiss
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

                knowledge = knowledge_base.get_knowledge(query)
                if knowledge:
                    if query in results:
                        results[query] += self.formatter.execute(knowledge, query, project_name)
                        self.logger.info(f"got the search results for : {query}")
                        knowledge_base.add_knowledge(query, results[query])
                    else:
                        results[query] = self.formatter.execute(knowledge, query, project_name)
                        self.logger.info(f"got the search results for : {query}")
                        knowledge_base.add_knowledge(query, results[query])

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
                    results[query] += self.formatter.execute(data, query, project_name)
                    self.logger.info(f"got the search results for : {query}")
                    knowledge_base.add_knowledge(query, results[query])
                else:
                    results[query] = self.formatter.execute(data, query, project_name)
                    self.logger.info(f"got the search results for : {query}")
                    knowledge_base.add_knowledge(query, results[query])

            return results

        elif searchFaiss and not wsearch:
            # Faiss search only
            knowledge_base = KnowledgeBase()

            for query in queries:
                query = query.strip().lower()

                knowledge = knowledge_base.get_knowledge(query)
                if knowledge:
                    if query in results:
                        results[query] += self.formatter.execute(knowledge, query, project_name)
                        self.logger.info(f"got the search results for : {query}")
                        knowledge_base.add_knowledge(query, results[query])
                    else:
                        results[query] = self.formatter.execute(knowledge, query, project_name)
                        self.logger.info(f"got the search results for : {query}")
                        knowledge_base.add_knowledge(query, results[query])

            return results

        return results

    def update_contextual_keywords(self, sentence: str):
        """
        Update the context keywords with the latest sentence/prompt
        """
        keywords = SentenceBert(sentence).extract_keywords()
        for keyword in keywords:
            self.collected_context_keywords.append(keyword[0])

        return self.collected_context_keywords

    def debugselectedfile(self, prompt: str, selectedfiles: list[str], project_name: str) -> str:
        os_system = platform.platform()

        self.agent_state.set_agent_active(project_name, True)
        # conversation = self.project_manager.get_all_messages_formatted(project_name)
        # self.agent_state.get_project_files1(project_name)

        self.codereviewfile.execute4selectedfile(
            prompt=prompt,
            selected_files=selectedfiles,
            project_name=project_name,
        )

        self.project_manager.add_message_from_devika(
            project_name,
            "I have completed my task. \n"
            "if you would like me to do anything else, please let me know. \n",
        )
        self.agent_state.set_agent_active(project_name, False)

        # print("Auto Commit :: ", self.project_manager.get_auto_commit(project_name))
        if self.project_manager.get_auto_commit(project_name):
            conversation = self.project_manager.get_all_messages_formatted(project_name)
            code_markdown = ReadCode(project_name).code_set_to_markdown()
            print("\n Committing the code\n")
            project_path = self.project_manager.get_project_path(project_name)
            if self.git == None:
                self.git = Git(project_path, self.base_model)

            commit_message = self.git.generate_commit_message(project_name, conversation, code_markdown)
            self.git.commit(commit_message)

        self.agent_state.set_agent_completed(project_name, True)

    def inc_dev(self, prompt: str, selectedfiles: list[str], project_name: str) -> str:
        self.agent_state.get_project_files1(project_name)
        os_system = platform.platform()

        self.agent_state.set_agent_active(project_name, True)
        conversation = self.project_manager.get_all_messages_formatted(project_name)
        print("\nicremental dev agent :: ", "d", "\n")
        # productrq = self.prq.execute(prompt, project_name)
        # plan = self.planner.execute1(prompt, productrq, project_name)
        # updated no incremental "using the current system design"
        search_results, plans = self.feature.execute4memory1(conversation=conversation, selectedfiles=selectedfiles,
                                                             project_name_from_user=project_name)
        print("plans in action feature output of feature.execute4memory")
        print(plans)
        print(search_results)
        print("                                   ")
        self.incdev.execute1(
            conversation=conversation,
            selectedfiles=selectedfiles,
            search_results=search_results, plans=plans,
            project_name=project_name,
            system_os=os_system
        )
        self.project_manager.add_message_from_devika(
            project_name,
            "I have completed my task. \n"
            "if you would like me to do anything else, please let me know. \n",
        )
        self.agent_state.set_agent_active(project_name, False)

        # print("Auto Commit :: ", self.project_manager.get_auto_commit(project_name))
        if self.project_manager.get_auto_commit(project_name):
            code_markdown = ReadCode(project_name).code_set_to_markdown()
            print("\n Committing the code\n")
            project_path = self.project_manager.get_project_path(project_name)
            if self.git == None:
                self.git = Git(project_path, self.base_model)

            commit_message = self.git.generate_commit_message(project_name, conversation, code_markdown)
            self.git.commit(commit_message)

        self.agent_state.set_agent_completed(project_name, True)

    def logo_expert(self, prompt: str, project_name: str) -> str:

        self.agent_state.set_agent_active(project_name, True)
        # conversation = self.project_manager.get_all_messages_formatted(project_name)

        svgcode = self.svgmaker.execute(prompt, project_name)
        # Create a div with SVG embedded as an image source
        res1 = f'<div>{svgcode}</div>'
        print(res1)
        self.project_manager.add_message_from_devika(project_name, res1)

        self.project_manager.add_message_from_devika(
            project_name,
            "I have completed my task. \n"
            "if you would like me to do anything else, please let me know. \n",
        )
        self.agent_state.set_agent_active(project_name, False)

        # print("Auto Commit :: ", self.project_manager.get_auto_commit(project_name))
        if self.project_manager.get_auto_commit(project_name):
            code_markdown = ReadCode(project_name).code_set_to_markdown()
            print("\n Committing the code\n")
            project_path = self.project_manager.get_project_path(project_name)
            if self.git == None:
                self.git = Git(project_path, self.base_model)

            commit_message = self.git.generate_commit_message(project_name, conversation, code_markdown)
            self.git.commit(commit_message)

        self.agent_state.set_agent_completed(project_name, True)

    def chemistry_expert(self, prompt: str, project_name: str) -> str:

        # os_system = platform.platform()
        str_prompt = prompt.replace("/chemistry", "")
        self.agent_state.set_agent_active(project_name, True)
        # conversation = self.project_manager.get_all_messages_formatted(project_name)

        validresponse = self.chemistry.execute(str_prompt, project_name)
        # print(validresponse)
        chemistry_response = self.chemistry.parse_response(validresponse)
        problem_description = chemistry_response["Problem Description"]
        plans = chemistry_response["plans"]
        innov_Sol = chemistry_response["Innovative Solutions"]
        smilelist = chemistry_response["smile_annotations"]
        # Format the plans into a readable string

        plans_str = "\n".join([
            f'<span style="background-color: red; color: white; padding: 2px 5px; border-radius: 3px;">Step {step}:</span> {desc}<br>'
            for step, desc in sorted(plans.items())])
        # smilelist1 = smilelist
        # Combine all parts into a single formatted string
        # Combine all parts into a single formatted string
        res1 = f"""
        <span style="background-color: green; color: white; padding: 2px 5px; border-radius: 3px;">Problem Description:</span><br>
        {problem_description}

        <br><span style="background-color: green; color: white; padding: 2px 5px; border-radius: 3px;">Plan:</span><br>
        {plans_str}

        <span style="background-color: green; color: white; padding: 2px 5px; border-radius: 3px;">Innovative Solution:</span><br>
        {innov_Sol}
        """
        self.project_manager.add_message_from_devika(project_name, res1)
        for smile in smilelist:
            try:
                mol = self.chemistry.parse_smile(smile)
                if mol is None:
                    continue  # Skip to the next SMILE if parsing failed
                properties = self.chemistry.get_molecule_properties(mol)
                dictmol = self.chemistry.print_molecule_properties(properties)

                res2 = "\n".join([f"{key}: {value}<br>" for key, value in dictmol.items()])
                self.project_manager.add_message_from_devika(project_name, res2)

                resss = self.chemistry.visualize_molecule(mol, img_format="png")
                # Convert image bytes to base64
                image_base64 = base64.b64encode(resss).decode('utf-8')
                image_src = f"data:image/png;base64,{image_base64}"
                # Embed in HTML
                res = f'<div><img src="{image_src}"></div>'
                self.project_manager.add_message_from_devika(project_name, res)
            except ValueError as e:
                # Log the error or handle it as needed
                print(f"Skipping invalid SMILES: {smile}. Error: {e}")
        self.project_manager.add_message_from_devika(
            project_name,
            "I have completed my task. \n"
            "if you would like me to do anything else, please let me know. \n",
        )
        self.agent_state.set_agent_active(project_name, False)

        # print("Auto Commit :: ", self.project_manager.get_auto_commit(project_name))
        if self.project_manager.get_auto_commit(project_name):
            code_markdown = ReadCode(project_name).code_set_to_markdown()
            print("\n Committing the code\n")
            project_path = self.project_manager.get_project_path(project_name)
            if self.git == None:
                self.git = Git(project_path, self.base_model)

            commit_message = self.git.generate_commit_message(project_name, conversation, code_markdown)
            self.git.commit(commit_message)

        self.agent_state.set_agent_completed(project_name, True)

    def make_decision(self, prompt: str, project_name: str) -> str:
        decision = self.decision.execute(prompt, project_name)

        for item in decision:
            function = item["function"]
            args = item["args"]
            reply = item["reply"]

            self.project_manager.add_message_from_devika(project_name, reply)

            if function == "git_clone":
                url = args["url"]
                # Implement git clone functionality here

            elif function == "generate_pdf_document":
                user_prompt = args["user_prompt"]
                # Call the reporter agent to generate the PDF document
                markdown = self.reporter.execute([user_prompt], "", project_name)
                _out_pdf_file = PDF().markdown_to_pdf(markdown, project_name)

                project_name_space_url = project_name.replace(" ", "%20")
                pdf_download_url = "http://127.0.0.1:1337/api/download-project-pdf?project_name={}".format(
                    project_name_space_url
                )
                response = f"I have generated the PDF document. You can download it from here: {pdf_download_url}"

                # asyncio.run(self.open_page(project_name, pdf_download_url))

                self.project_manager.add_message_from_devika(project_name, response)

            elif function == "browser_interaction":
                user_prompt = args["user_prompt"]
                # Call the interaction agent to interact with the browser
                start_interaction(self.base_model, user_prompt, project_name)

            elif function == "coding_project":
                user_prompt = args["user_prompt"]
                # Call the planner, researcher, coder agents in sequence
                plan = self.planner.execute(user_prompt, project_name)
                planner_response = self.planner.parse_response(plan)

                research = self.researcher.execute(
                    plan, self.collected_context_keywords, project_name
                )
                search_results = self.search_queries(research["queries"], project_name)

                code = self.coder.execute(
                    step_by_step_plan=plan,
                    user_context=research["ask_user"],
                    search_results=search_results,
                    project_name=project_name,
                )
                self.coder.save_code_to_project(code, project_name)

    def subsequent_execute(self, prompt: str, project_name: str):
        """
        Subsequent flow of execution
        """

        os_system = platform.platform()

        self.agent_state.set_agent_active(project_name, True)

        conversation = self.project_manager.get_all_messages_formatted(project_name)
        code_markdown = ReadCode(project_name).code_set_to_markdown()

        response, action = self.action.execute(conversation, project_name)
        responsecore = "<b>Agent Core: </b><br>" + response

        self.project_manager.add_message_from_devika(project_name, responsecore)

        print("\naction :: ", action, "\n")

        if action == "answer":
            response = self.answer.execute(
                conversation=conversation,
                code_markdown=code_markdown,
                project_name=project_name,
            )
            responseAgent = "<mark>Agent Answer: </mark><br>" + response
            self.project_manager.add_message_from_devika(project_name, responseAgent)

        elif action == "run":
            project_path = self.project_manager.get_project_path(project_name)
            self.runner.execute(
                conversation=conversation,
                code_markdown=code_markdown,
                os_system=os_system,
                project_path=project_path,
                project_name=project_name,
            )


        elif action == "deploy":
            deploy_metadata = Netlify().deploy(project_name)
            deploy_url = deploy_metadata["deploy_url"]

            response = {
                "message": "Done! I deployed your project on Netlify.",
                "deploy_url": deploy_url,
            }
            response = json.dumps(response, indent=4)

            self.project_manager.add_message_from_devika(project_name, response)

        elif action == "feature":
            self.agent_state.get_project_files1(project_name)
            print("features")
            str_prompt = prompt.replace("/feature", "")
            conv = [str_prompt]
            search_results, plans = self.feature.execute4memory(conversation=conv,
                                                                project_name_from_user=project_name)
            print("plans in action feature output of feature.execute4memory")
            #print(plans)
            # print(search_results)
            #print("                                   ")
            self.incdev.execute(
                conversation=conv,
                search_results=search_results, plans=plans,
                project_name=project_name,
                system_os=os_system
            )
            self.project_manager.add_message_from_devika(
                project_name,
                "I have completed my task. \n"
                "if you would like me to do anything else, please let me know. \n",
            )

            ## print("\nfeature code :: ", code, "\n")
            ## self.feature.save_code_to_project(code, project_name)

        elif action == "bug":
            print("bugs")
            self.agent_state.get_project_files1(project_name)
            str_prompt = prompt.replace("/bugs", "")
            conv = [str_prompt]
            self.codereviewfile.execute(
                conversation=conv,
                project_name=project_name,
            )

            # self.patcher.save_code_to_project(code, project_name)

        elif action == "browser_interaction":
            try:
                start_interaction(self.base_model, conversation[-1], project_name)
            except Exception as e:
                print(f"An error occurred: {e}")

            # user_prompt = args["user_prompt"]
            # Call the interaction agent to interact with the browser




        elif action == "generate_uml":
            print("uml diagramm")
            agentumlrep = "<mark>Agent Draw UML</mark>"
            self.project_manager.add_message_from_devika(project_name, agentumlrep)
            self.drawuml.execute(prompt, code_markdown, project_name)

        elif action == "download_project":
            print("download_project")

            project_name_space_url = project_name.replace(" ", "%20")
            pdf_download_url = (
                "http://127.0.0.1:1337/api/download-project?project_name={}".format(
                    project_name_space_url
                )
            )
            response = f"I have generated the PROJECT . You can download it from here: {pdf_download_url} .zip"

            # asyncio.run(self.open_page(project_name, pdf_download_url))

            self.project_manager.add_message_from_devika(project_name, response)

        elif action == "report":
            markdown = self.reporter.execute(conversation, code_markdown, project_name)

            _out_pdf_file = PDF().markdown_to_pdf(markdown, project_name)

            project_name_space_url = project_name.replace(" ", "%20")
            pdf_download_url = (
                "http://127.0.0.1:1337/api/download-project-pdf?project_name={}".format(
                    project_name_space_url
                )
            )
            response = f"I have generated the PDF document. You can download it from here: {pdf_download_url}"
            agentreport = "<mark>Agent Report</mark>:<br>" + response
            # asyncio.run(self.open_page(project_name, pdf_download_url))

            self.project_manager.add_message_from_devika(project_name, agentreport)

        elif action == "git_init":
            project_path = self.project_manager.get_project_path(project_name)
            if self.git == None:
                self.git = Git(project_path, self.base_model)

        elif action == "git_clone":
            project_path = self.project_manager.get_project_path(project_name)
            if self.git == None:
                self.git = Git(project_path, self.base_model)

            self.git.clone(project_path, project_name, conversation)

        elif action == "git_commit":
            project_path = self.project_manager.get_project_path(project_name)
            if self.git == None:
                self.git = Git(project_path, self.base_model)

            commit_message = self.git.generate_commit_message(project_name, conversation, code_markdown)
            self.git.commit(commit_message)

        elif action == "git_reset":
            project_path = self.project_manager.get_project_path(project_name)
            if self.git == None:
                self.git = Git(project_path, self.base_model)
            self.git.reset_to_previous_commit()


        elif action == "git_start_auto_commit":
            self.project_manager.start_auto_commit(project_name)

        elif action == "git_stop_auto_commit":
            self.project_manager.stop_auto_commit(project_name)

        self.agent_state.set_agent_active(project_name, False)
        # print("Auto Commit :: ", self.project_manager.get_auto_commit(project_name))
        if self.project_manager.get_auto_commit(project_name):
            print("\n Committing the code\n")
            project_path = self.project_manager.get_project_path(project_name)
            if self.git == None:
                self.git = Git(project_path, self.base_model)

            commit_message = self.git.generate_commit_message(project_name, conversation, code_markdown)
            self.git.commit(commit_message)

        self.agent_state.set_agent_completed(project_name, True)

    def execute(self, prompt: str, project_name_from_user: str = None, wsearch: bool = False,
                searchFaiss: bool = False):
        """
        Agentic flow of execution

        """
        os_system = platform.platform()
        print("coder")
        if project_name_from_user:
            self.project_manager.add_message_from_user(project_name_from_user, prompt)
            agentcoder = "<b><i>Agentic Flow Of First Creation</i></b>"
            self.project_manager.add_message_from_devika(project_name_from_user, agentcoder)
            self.agent_state.set_agent_active(project_name_from_user, True)
        productrq = self.prq.execute(prompt, project_name_from_user)
        productrqresponse = "<mark>Agent Product Requirement</mark>:<br>" + productrq
        self.project_manager.add_message_from_devika(project_name_from_user, productrqresponse)
        print("prompt refactored        ")
        print(productrq)
        plan = self.planner.execute(prompt, productrq, project_name_from_user)

        print("\nplan :: ", plan, "\n")

        planner_response = self.planner.parse_response(plan)
        project_name = planner_response["project"]
        reply = planner_response["reply"]
        focus = planner_response["focus"]
        plans = planner_response["plans"]
        summary = planner_response["summary"]

        if project_name_from_user:
            project_name = project_name_from_user
        else:
            project_name = planner_response["project"]
            self.project_manager.create_project(project_name)
            self.project_manager.add_message_from_user(project_name, prompt)

        responseplanner = "<mark>Agent planner: </mark><br>" + reply
        self.project_manager.add_message_from_devika(project_name, responseplanner)
        self.project_manager.add_message_from_devika(
            project_name, json.dumps(plans, indent=4)
        )
        self.project_manager.add_message_from_devika(project_name, f"In summary: {summary}")

        internal_monologue = self.internal_monologue.execute(
            current_prompt=plan, project_name=project_name
        )
        print("\ninternal_monologue :: ", internal_monologue, "\n")

        new_state = self.agent_state.new_state()
        new_state["internal_monologue"] = internal_monologue
        self.agent_state.add_to_current_state(project_name, new_state)

        ###
        search_results = self.wSearchAndFaissToggle(project_name, focus, plans, wsearch, searchFaiss)
        print(search_results)
        # Define the path to systemdesign.txt
        sstemdesign = "systemdesign"
        sstemdesign_txt = "systemdesign.txt"
        systemdesign_path = os.path.join(self.project_dir, project_name, sstemdesign, sstemdesign_txt)
        filenames = []

        # Attempt to read systemdesign.txt and handle potential errors
        try:
            with open(systemdesign_path, "r") as file:
                # Split the content into a list of filenames
                filenames = file.read().splitlines()
        except FileNotFoundError:
            print(f"systemdesign.txt not found at: {systemdesign_path}")
            return

        except Exception as e:
            print(f"Error reading systemdesign.txt: {e}")
            return

        # Check if any filenames were found
        if not filenames:
            print("No valid file names found in systemdesign.txt")
        print("                                                                                            ")
        print("                                                                                            ")
        print("                                                                                            ")
        print(filenames)

        # Process each filename found in systemdesign.txt
        for file_name in filenames:
            try:
                formatted_name_path = os.path.normpath(file_name)
                ext = Path(file_name).suffix.lower()
                if '.' not in file_name:
                    continue
                if ext in ['.jpg', '.png', '.jpeg', '.gif', '.bmp', '.tiff', '.placeholder', '.ico', '.md', '.json']:
                    path_for_file = os.path.join(self.project_dir, project_name, formatted_name_path)
                    formatted_forfile = os.path.normpath(path_for_file)
                    # Check if the file exists; if not, create an empty file
                    if not os.path.isfile(formatted_forfile):
                        # Ensure the directory exists
                        os.makedirs(os.path.dirname(formatted_forfile), exist_ok=True)

                        # Create an empty file
                        with open(formatted_forfile, 'w') as f:
                            pass
                        continue
                    else:
                        continue

                print("                                                                                            ")
                print("                                                                                            ")
                print("                                                                                            ")
                print(formatted_name_path)
                print("                                                                                            ")
                print("                                                                                            ")
                print("                                                                                            ")
                ask_user_prompt = "Be Professional."
                # Execute the coder logic for each file
                code = self.coder.execute(step_by_step_plan=plans, user_context=ask_user_prompt,
                                          search_results=search_results, project_name=project_name,
                                          file_name=formatted_name_path, filenames=filenames, system_os=os_system)
                print("\ncode :: ", code, "\n")
                # time.sleep(4)
                # Save the generated code to the project
                self.coder.save_code_to_project(code, project_name)
                continue
            except Exception as e:
                # Handle any exceptions that occur during execution
                print(f"An error occurred while processing {file_name}: {e}")
                continue  # Continue with the next file
        self.agent_state.get_project_files1(project_name)
        # End of file processing loop
        # self.codereviewfile.executeofcoder(prompt=prompt, project_name=project_name)

        self.agent_state.set_agent_active(project_name, False)

        self.agent_state.set_agent_completed(project_name, True)
        self.project_manager.add_message_from_devika(
            project_name,
            "I have completed my task. \n"
            "if you would like me to do anything else, please let me know. \n",
        )
