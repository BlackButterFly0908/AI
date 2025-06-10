from pocketflow import Node, BatchNode, AsyncParallelBatchNode
from utils.call_llm import call_llm
from utils.streamlit_utils import display_message, get_user_input, display_plan_review, display_final_report, update_progress_details
from utils.tavily_search import tavily_search
import streamlit as st
import yaml
import asyncio
import json
import datetime

class UserInputNode(Node):
    def exec(self, _):
        # In Streamlit, this node's 'exec' is primarily to signal that user input is needed
        # The actual Streamlit UI interaction happens in main.py.
        return None # No direct exec result, as input is external

    def post(self, shared, prep_res, exec_res):
        # The 'exec_res' for UserInputNode will come from main.py's handling of the input.
        # This node will only transition if the user_query is set in shared state.
        if shared.get("user_query") is not None and shared["user_query"] != "":
            shared["current_activity_prompt"] = "Query received, generating plan..."
            return "default"
        else:
            # If no input yet, keep the current state and re-run this node by main.py
            shared["current_activity_prompt"] = "Please enter your research query below."
            return "stay"

class PlanGenerationNode(Node):
    def prep(self, shared):
        return shared["user_query"]

    def exec(self, user_query):
        # This node is purely computational, no direct Streamlit calls.
        prompt = f"""Generate a detailed research plan (list of sub-queries or topics) for the following query: {user_query}

Provide the plan as a YAML list, for example:

```yaml
- topic: "Topic 1"
  sub_queries:
    - "Sub-query 1.1"
    - "Sub-query 1.2"
- topic: "Topic 2"
  sub_queries:
    - "Sub-query 2.1"
```"""
        response = call_llm(prompt)
        try:
            yaml_str = response.split("```yaml")[1].split("```")[0].strip()
            plan = yaml.safe_load(yaml_str)
            return plan
        except Exception as e:
            print(f"Error parsing LLM response for plan generation: {e}")
            print(f"Raw LLM response: {response}")
            return [{"topic": "Fallback Research", "sub_queries": ["Re-evaluate original query"]}]

    def post(self, shared, prep_res, exec_res):
        shared["research_plan"] = exec_res
        shared["plan_status"] = "pending_review"
        shared["current_activity_prompt"] = "Research plan generated, awaiting human review."
        return "default"

class HumanReviewPlanNode(Node):
    def prep(self, shared):
        return shared["research_plan"]

    def exec(self, research_plan):
        # This node's exec method doesn't directly interact with Streamlit.
        # It will rely on main.py to render the review UI and update shared state.
        # We return the plan to post, which will then check the shared['plan_status']
        return research_plan # Pass the plan to post for status checking

    def post(self, shared, prep_res, exec_res):
        # The status and edited plan are set by main.py based on user interaction
        status = shared.get("plan_status")
        # In this revised flow, edited_plan is already updated in shared["research_plan"] by main.py
        
        if status == "approved":
            shared["current_activity_prompt"] = "Research plan approved, performing web searches."
            shared["plan_status"] = None # Reset plan_status in shared for next review if flow loops
            return "approved"
        elif status == "rejected":
            shared["feedback"] = "Plan rejected or edited by user."
            shared["current_activity_prompt"] = "Research plan rejected or edited, re-generating plan."
            shared["plan_status"] = None # Reset plan_status in shared for next review if flow loops
            return "rejected_or_edit"
        else:
            # If status is not approved/rejected, it's pending, so stay on this node.
            # main.py will detect 'pending_review' and render the review UI.
            shared["current_activity_prompt"] = "Reviewing research plan, awaiting human feedback."
            return "stay"

class WebSearchBatchNode(AsyncParallelBatchNode):
    async def prep_async(self, shared):
        research_plan = shared["research_plan"]
        search_queries = []
        for item in research_plan:
            topic = item.get("topic", "")
            sub_queries = item.get("sub_queries", [])
            for sq in sub_queries:
                search_queries.append(f"{topic} {sq}" if topic else sq)
        shared["current_activity_prompt"] = "Performing web searches..."
        shared["progress_details"] = ["Starting web searches..."]
        return search_queries

    async def exec_async(self, query):
        results = await asyncio.to_thread(tavily_search, query)
        # Return the progress message along with the results
        return {"query": query, "results": results, "progress_message": f"Finished searching for: '{query}'"}

    async def post_async(self, shared, prep_res, exec_res_list):
        shared["raw_search_results"] = []
        for item in exec_res_list:
            shared["raw_search_results"].append({"query": item["query"], "results": item["results"]})
            shared["progress_details"].append(item["progress_message"])

        shared["current_activity_prompt"] = "Web searches complete, summarizing results."
        shared["progress_details"].append("All web searches completed.")
        return "default"

class SummarizeResultsBatchNode(AsyncParallelBatchNode):
    async def prep_async(self, shared):
        raw_search_results = shared["raw_search_results"]
        contents_to_summarize = []
        for search_bundle in raw_search_results:
            query = search_bundle["query"]
            for result in search_bundle["results"]:
                if result.get("content"):
                    contents_to_summarize.append({"query": query, "content": result["content"]})
        
        shared["current_activity_prompt"] = "Summarizing search results..."
        shared["progress_details"].append("Starting summarization of search results...")
        return contents_to_summarize

    async def exec_async(self, item_to_summarize):
        query = item_to_summarize["query"]
        content = item_to_summarize["content"]
        prompt = f"""Summarize the following text in a concise manner, focusing on key information relevant to the query: {query}

Text: {content}

Summary:"""
        summary = await asyncio.to_thread(call_llm, prompt)
        # Return the progress message along with the summary
        return {"query": query, "summary": summary, "progress_message": f"Finished summarizing for: '{query}'"}

    async def post_async(self, shared, prep_res, exec_res_list):
        individual_summaries = {}
        for item in exec_res_list:
            individual_summaries[item["query"]] = item["summary"]
            shared["progress_details"].append(item["progress_message"])
        
        shared["individual_summaries"] = individual_summaries
        shared["current_activity_prompt"] = "Search results summarized, assessing relevance."
        shared["progress_details"].append("All search results summarized.")
        return "default"

class ReflectionSupervisorNode(Node):
    def prep(self, shared):
        return shared["user_query"], shared["individual_summaries"]

    def exec(self, inputs):
        # This node is purely computational, no direct Streamlit calls.
        user_query, individual_summaries = inputs
        summaries_str = json.dumps(individual_summaries, indent=2)
        
        prompt = f"""You are a research supervisor. Based on the original user query and the individual summaries provided, assess the relevance, completeness, and quality of the research findings.

Original Query: {user_query}

Individual Summaries:
{summaries_str}

Based on the above, decide if the research findings are:
- 'relevant': The summaries adequately address the original query.
- 'needs_more': The summaries are somewhat relevant but require additional research or refinement.
- 'irrelevant': The summaries do not address the original query effectively.

Return your assessment as a YAML object with the following structure:

```yaml
assessment: <relevant/needs_more/irrelevant>
reason: <brief explanation for the assessment>
```"""
        
        response = call_llm(prompt)
        try:
            yaml_str = response.split("```yaml")[1].split("```")[0].strip()
            assessment_result = yaml.safe_load(yaml_str)
            
            assert "assessment" in assessment_result
            assert assessment_result["assessment"] in ["relevant", "needs_more", "irrelevant"]
            
            return assessment_result["assessment"]
        except Exception as e:
            print(f"Error parsing LLM response for relevance assessment: {e}")
            print(f"Raw LLM response: {response}")
            return "needs_more"
    
    def post(self, shared, prep_res, exec_res):
        shared["relevance_assessment"] = exec_res
        if exec_res == "relevant":
            shared["current_activity_prompt"] = "Summaries deemed relevant, compiling final report."
            return "relevant"
        else:
            shared["current_activity_prompt"] = f"Summaries deemed {exec_res}, revisiting research plan."
            return "not_relevant_or_needs_more"

class CombineSummariesNode(Node):
    def prep(self, shared):
        return shared["individual_summaries"]

    def exec(self, individual_summaries):
        # This node is purely computational, no direct Streamlit calls.
        combined_summaries_text = ""
        for query, summary in individual_summaries.items():
            combined_summaries_text += f"Query: {query}\nSummary: {summary}\n\n"

        prompt = f"""Combine the following individual research summaries into one comprehensive and coherent final report. Ensure the report flows well and covers all key points from the individual summaries.

Individual Summaries:
{combined_summaries_text}

Final Research Report:"""
        
        final_report = call_llm(prompt)
        return final_report

    def post(self, shared, prep_res, exec_res):
        shared["final_report"] = exec_res
        shared["current_activity_prompt"] = "Final report compiled, presenting results."
        return "default"

class PresentFinalReportNode(Node):
    def prep(self, shared):
        return shared["final_report"]

    def exec(self, final_report):
        # This node's exec method doesn't directly interact with Streamlit.
        # It simply returns the final report.
        return final_report
    
    def post(self, shared, prep_res, exec_res):
        # The final report is already in shared["final_report"] from prep_res
        shared["current_activity_prompt"] = "Research complete. Enter a new query to start again."
        # Clear relevant shared data for a new run
        shared["user_query"] = None
        shared["research_plan"] = None
        shared["plan_status"] = None # Reset for next review
        shared["raw_search_results"] = None
        shared["individual_summaries"] = None
        shared["relevance_assessment"] = None
        shared["final_report"] = exec_res # Ensure final_report is set from exec_res
        shared["feedback"] = None
        shared["progress_details"] = []
        
        return "new_query"