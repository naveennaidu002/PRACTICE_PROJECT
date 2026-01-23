from rag_agent import Main, Metadata

def chatbot(sessionId, userPrompt, dataSource, userId):
    agent = Main(sessionId, userPrompt, dataSource, userId)
    return agent.start_agent()

def metadata_extraction(datasource):
    """
    Wrapper for Metadata class in rag_agent.py
    """
    try:
        meta = Metadata(datasource)
        meta.process()
        return meta.tables
    except Exception as e:
        print(f"Error in metadata_extraction: {e}")
        return []
