from utils  import Node ,call_llm ,Flow
from tools import analyze_results , SearchTool , WebSearchTool
import datetime ,json ,yaml
from typing import List, Dict

# Planner_Prep is a Node that prepares a research plan based on user input.
# It generates a detailed plan for information gathering tasks using a team of specialized agents.
class Planner_Prep(Node):
    def prep(self, shared):
        return shared.get("user_query"),shared.get("max_step_num", 5) ,shared.get("locale", "en") ,shared.get("webtype", "tavily")
    
    
    def exec(self, shared):
        current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_query, max_step_num, locale ,  web_type = shared

        prompt=f""" 
            ---
        CURRENT_TIME: {current_date}
        ---

        You are a professional Deep Researcher. Study and plan information gathering tasks using a team of specialized agents to collect comprehensive data.

        # Details

        You are tasked with orchestrating a research team to gather comprehensive information for a given requirement. The final goal is to produce a thorough, detailed report, so it's critical to collect as much relevant information as possible.

        As a Deep Researcher, you can breakdown the major subject into sub-topics and expand the depth breadth of user's initial question if applicable.

        ## Information Quantity and Quality Standards

        The successful research plan must meet these standards:

        1. **Comprehensive Coverage**:
        - Information must cover ALL aspects of the topic
        - Multiple perspectives must be represented
        - Both mainstream and alternative viewpoints should be included

        2. **Sufficient Depth**:
        - Surface-level information is insufficient
        - Detailed data points, facts, statistics are required
        - In-depth analysis from multiple sources is necessary

        3. **Adequate Volume**:
        - Collecting "just enough" information is not acceptable
        - Aim for abundance of relevant information
        - More high-quality information is always better than less

        ## Context Assessment

        Before creating a detailed plan, assess if there is sufficient context to answer the user's question. Apply strict criteria for determining sufficient context:

        1. **Sufficient Context** (apply very strict criteria):
        - Set `has_enough_context` to true ONLY IF ALL of these conditions are met:
            - Current information fully answers ALL aspects of the user's question with specific details
            - Information is comprehensive, up-to-date, and from reliable sources
            - No significant gaps, ambiguities, or contradictions exist in the available information
            - Data points are backed by credible evidence or sources
            - The information covers both factual data and necessary context
            - The quantity of information is substantial enough for a comprehensive report
        - Even if you're 90% certain the information is sufficient, choose to gather more

        2. **Insufficient Context** (default assumption):
        - Set `has_enough_context` to false if ANY of these conditions exist:
            - Some aspects of the question remain partially or completely unanswered
            - Available information is outdated, incomplete, or from questionable sources
            - Key data points, statistics, or evidence are missing
            - Alternative perspectives or important context is lacking
            - Any reasonable doubt exists about the completeness of information
            - The volume of information is too limited for a comprehensive report
        - When in doubt, always err on the side of gathering more information

        ## Step Types and Web Search

        Different types of steps have different web search requirements:

        1. **Research Steps** (`need_search: true`):
        - Gathering market data or industry trends
        - Finding historical information
        - Collecting competitor analysis
        - Researching current events or news
        - Finding statistical data or reports

        2. **Data Processing Steps** (`need_search: false`):
        - API calls and data extraction
        - Database queries
        - Raw data collection from existing sources
        - Mathematical calculations and analysis
        - Statistical computations and data processing

        ## Exclusions

        - **No Direct Calculations in Research Steps**:
        - Research steps should only gather data and information
        - All mathematical calculations must be handled by processing steps

        ## Analysis Framework

        When planning information gathering, consider these key aspects and ensure COMPREHENSIVE coverage:

        1. **Historical Context**
        2. **Current State**
        3. **Future Indicators**
        4. **Stakeholder Data**
        5. **Quantitative Data**
        6. **Qualitative Data**
        7. **Comparative Data**
        8. **Risk Data**

        ## Step Constraints

        - **Maximum Steps**: Limit the plan to a maximum of {max_step_num} steps for focused research.
        - Each step should be comprehensive but targeted, covering key aspects rather than being overly expansive.
        - Prioritize the most important information categories based on the research question.
        - Consolidate related research points into single steps where appropriate.

        ## Execution Rules

        - To begin with, repeat user's requirement in your own words as `thought`.
        - Rigorously assess if there is sufficient context to answer the question using the strict criteria above.
        - If context is sufficient:
        - Set `has_enough_context` to true
        - No need to create information gathering steps
        - If context is insufficient (default assumption):
        - Break down the required information using the Analysis Framework
        - Create NO MORE THAN {max_step_num} focused and comprehensive steps that cover the most essential aspects
        - Ensure each step is substantial and covers related information categories
        - Prioritize breadth and depth within the {max_step_num}-step constraint
        - For each step, carefully assess if web search is needed:
            - Research and external data gathering: Set `need_search: true`
            - Internal data processing: Set `need_search: false`
        - Specify the exact data to be collected in step's `description`.
        - Prioritize depth and volume of relevant information - limited information is not acceptable.
        - If `discription` is too long, reduce it to 400 characters, but ensure it remains concise and informative.
        - Use the same language as the user to generate the plan.
        - Do not include steps for summarizing or consolidating the gathered information.
        - The discription of each step should be detailed and specific, outlining the exact data to be collected or processed.
        # Output Format
        Directly output the raw JSON format of `Plan` without "```json". The `Plan` interface is defined as follows:

        interface Step {{
        need_search: boolean;
        title: string;
        description: string;
        step_type: "research" | "processing";
        }}

        interface Plan {{
        locale: string;
        has_enough_context: boolean;
        thought: string;
        title: string;
        steps: Step[];
        }}

        # User Query
        {user_query}
                """
        

        response = call_llm(prompt)
        try:
            # Try to find and parse JSON from the LLM output
            json_str = response.split("{", 1)[1].rsplit("}", 1)[0]
            json_str = "{" + json_str + "}"
            plan = json.loads(json_str)
           
            return plan
        except Exception as e:
            print(f"Error parsing LLM response for plan generation: {e}")
            print(f"Raw LLM response: {response}")
            return {"topic": "Fallback Research", "sub_queries": ["Re-evaluate original query"]}
        

    def post(self, shared, prep_res, exec_res):
        # Post-processing can be added here if needed
        shared["plan"] = exec_res
        print(exec_res)
        yaml_output = yaml.dump( exec_res, sort_keys=False, allow_unicode=True)
        print(yaml_output + '\n')
        return shared["webtype"]
    
#this class node here  will search the web for the plan using tavily and the search information was from shared[plan][discription]
class TavilySearch(Node):
    def prep(self, shared):
        return shared.get("plan", {})

    def exec(self, shared):
        plan = shared
        web_type = plan.get("webtype", "tavily")
        steps = plan.get("steps", [])
        
        # Here you would implement the logic to search using Tavily or any other web service
        # For demonstration, we will just return the steps as is
        for step in steps:
            step["search_results"] = f"Results for {step['description']} using {web_type}"
            print(step["search_results"])
        return steps


class SearchNode(Node):
    """Node to perform web search using SerpAPI"""
    
    def prep(self, shared):
       return shared.get("plan", {})
        
    def exec(self,shared):
        steps = shared.get("steps", [])
       
        num_results = 10
        searcher = WebSearchTool()
        if not  steps:
            return []
        for step in steps:
            if step.get("need_search"):
                shared["track_activity"]=step['description']
                return searcher.search(step['description'], num_results)              
        #return searcher.search(query, num_results)
        
    def post(self, shared, prep_res, exec_res):
        shared["search_results"] = exec_res
        steps = shared.get("plan", {}).get("steps", [])
        print(shared["search_results"])
        for item in steps:
            if not item.get("need_search"):
                return "VerifySearchNode"
        return "default"
    
class VerifySearchNode(Node):
    """Node to verify search results"""
    
    def prep(self, shared):
        return shared.get("search_results", []),shared.get("track_activity", "No description provided")
        
    def exec(self, shared):
        search_results,description = shared
        if not search_results:
            return "No search results to verify"
        prompt = f"""
            You are a research assistant your only job is to verify the relevance of the search results.

            #You are given:
            - A step description: \"\"\"{description}\"\"\"
            - A list of search results, each with a 'snippet' and a 'url' (passed separately).

            #Your task:
            - For each search result, check if it is strongly relevant to the description.
            - Keep ONLY the results that are clearly relevant.
            - Disregard any result that is not relevant.
            - Return the filtered results in the SAME JSON structure, but only include relevant results.
            - Each result you include must have both its 'snippet' and its associated 'url'.

         
            Output in YAML format , with no irrelevant results, and no extra commentary:
            ```yaml
            filtered_results:
                    - snippet: <string>
                    - url: <string>
                   
            ```
            #Search Results:
            {search_results}
            """
        
        try:
            response = call_llm(prompt)
            # Extract YAML between code fences
            yaml_str = response.split("```yaml")[1].split("```")[0].strip()
            
            import yaml
            filtered_results = yaml.safe_load(yaml_str)
            return filtered_results
            
        except Exception as e:
            print(f"Error analyzing results: {str(e)}")
            return {
                "summary": "Error analyzing results",
                "key_points": [],
                "follow_up_queries": []
            }
        # Here you would implement the logic to verify the search results
        # For demonstration, we will just return the results as is
  
        
    def post(self, shared, prep_res, exec_res):
        print("\nVerified Search Results:")
        shared["verified_results"] = exec_res
        print(shared["verified_results"])
        return "search_node"


class AnalyzeResultsNode(Node):
    """Node to analyze search results using LLM"""
    
    def prep(self, shared):
        
        return shared.get("user_query", ""), shared.get("search_results", [])
        
    def exec(self, shared):
        query, results = shared
        if not results:
            return {
                "summary": "No search results to analyze",
                "key_points": [],
                "follow_up_queries": []
            }
            
        return analyze_results(query, results)
        
    def post(self, shared, prep_res, exec_res):
        shared["analysis"] = exec_res
        
        # Print analysis
        print("\nSearch Analysis:")
        print("\nSummary:", exec_res["summary"])
        
        print("\nKey Points:")
        for point in exec_res["key_points"]:
            print(f"- {point}")
            
        print("\nSuggested Follow-up Queries:")
        for query in exec_res["follow_up_queries"]:
            print(f"- {query}")
            
        return "default"


    
  
if __name__ == "__main__":
    # Example usage
    user_query = "what is a bitcoin?"
    max_step_num = 5
    locale = "en"
    web_type = "tavily"  # Example web type, can be changed as needed
    planner = Planner_Prep()
    search = SearchNode()
    analyze = AnalyzeResultsNode()
    websearcher = TavilySearch()
    verifySearch = VerifySearchNode()
    shared_data = {
        "user_query": user_query,
        "max_step_num": max_step_num,
        "locale": locale,
        "webtype": web_type
    }
    

    planner - 'tavily'>> search
    search - 'VerifySearchNode' >> verifySearch
    verifySearch - 'search_node' >> search
    # plan = planner.run(shared_data)
    # print(json.dumps(plan, indent=2))
    flow = Flow(start=planner)
    flow.run(shared_data)
