from crewai import Task


class CrewTasks:
    def research_task(self, agent, topic):
        return Task(
            description=f"""
                Conduct a comprehensive analysis of {topic}.
                Identify key trends, potential impacts, and major players.
                Your final answer must be a detailed summary of findings.
            """,
            agent=agent,
            async_execution=True,
            expected_output="A detailed summary of the research findings.",
        )

    def analysis_task(self, agent, context):
        return Task(
            description="""
                Using the research findings, create a final report.
                The report should be structured and highlight the most important points.
            """,
            agent=agent,
            context=context,
            expected_output="A structured final report.",
        )

    def tool_task(self, agent, request):
        return Task(
            description=f"""
                Use your available tools to handle the following request:
                "{request}"
                
                If the request requires finding an event, use the calendar tools to find potential matches.
                If the request requires creating an item, do so.
                Provide a clear summary of the action taken or information retrieved.
            """,
            agent=agent,
            expected_output="A summary of the tool execution or retrieved information.",
        )
